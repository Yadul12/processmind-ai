"""
Unit Tests for Multi-Format Document Parsers (PDF, DOCX, XLSX, TXT) and the 5 LangGraph Agents.
"""

from pathlib import Path
from backend.agents.agent1_understanding import agent1_understanding
from backend.agents.orchestrator import process_orchestrator
from backend.config import settings
from backend.schemas.document import DocumentFileTypeEnum, ParsedDocumentStructure
from backend.schemas.process import ProcessModelSchema, ReviewStatusEnum
from backend.services.document_parsers import document_parser


def test_pdf_parser_preserves_pages_and_sections() -> None:
    pdf_path = Path(settings.sample_data_dir) / "sop_01_invoice_processing.pdf"
    assert pdf_path.exists()

    ftype, raw_text, blocks, tables, page_count = document_parser.parse_bytes(
        pdf_path.read_bytes(), pdf_path.name, "DOC-TEST-PDF"
    )
    assert ftype == DocumentFileTypeEnum.PDF
    assert page_count == 2
    assert "Page 1" in raw_text
    assert "Page 2" in raw_text
    page_refs = {b.page_or_sheet for b in blocks}
    assert "Page 1" in page_refs
    assert "Page 2" in page_refs


def test_docx_parser_extracts_paragraphs_and_tables() -> None:
    docx_path = Path(settings.sample_data_dir) / "sop_02_employee_onboarding.docx"
    assert docx_path.exists()

    ftype, raw_text, blocks, tables, page_count = document_parser.parse_bytes(
        docx_path.read_bytes(), docx_path.name, "DOC-TEST-DOCX"
    )
    assert ftype == DocumentFileTypeEnum.DOCX
    assert len(tables) >= 1
    assert tables[0].headers[0] == "Activity ID"
    assert len(tables[0].rows) == 6
    assert any(b.block_type == "numbered_step" for b in blocks)


def test_xlsx_parser_extracts_sheets_and_rows() -> None:
    xlsx_path = Path(settings.sample_data_dir) / "sop_03_procurement_approvals.xlsx"
    assert xlsx_path.exists()

    ftype, raw_text, blocks, tables, sheet_count = document_parser.parse_bytes(
        xlsx_path.read_bytes(), xlsx_path.name, "DOC-TEST-XLSX"
    )
    assert ftype == DocumentFileTypeEnum.XLSX
    assert sheet_count == 2
    sheet_refs = {b.page_or_sheet for b in blocks}
    assert "Sheet: SOP_Overview" in sheet_refs
    assert "Sheet: Process_Activities" in sheet_refs


def test_full_langgraph_5_agent_pipeline_on_all_5_enterprise_sops() -> None:
    sample_files = [
        "sop_01_invoice_processing.pdf",
        "sop_02_employee_onboarding.docx",
        "sop_03_procurement_approvals.xlsx",
        "sop_04_customer_complaint_resolution.pdf",
        "sop_05_it_access_management.docx",
    ]
    for fname in sample_files:
        fpath = Path(settings.sample_data_dir) / fname
        content = fpath.read_bytes()
        ftype, raw_text, blocks, tables, pcount = document_parser.parse_bytes(content, fname, f"DOC-{fname}")
        meta = agent1_understanding.extract_metadata(fname, blocks, len(tables), pcount)
        parsed = ParsedDocumentStructure(
            document_id=f"DOC-{fname}",
            filename=fname,
            file_type=DocumentFileTypeEnum(ftype.value),
            metadata=meta,
            headings=[b.text for b in blocks if b.block_type == "heading"],
            blocks=blocks,
            tables=tables,
            numbered_steps=[b.text for b in blocks if b.block_type == "numbered_step"],
            decision_statements=[b.text for b in blocks if b.is_decision_statement],
        )

        model: ProcessModelSchema = process_orchestrator.execute_pipeline(
            document_id=f"DOC-{fname}",
            filename=fname,
            file_type=ftype.value,
            checksum_sha256="sha256-test",
            raw_text=raw_text,
            parsed_document=parsed,
        )

        # Verify all 13 mandatory ProcessModelSchema fields
        assert model.process_id.startswith("PROC-")
        assert len(model.process_name) > 5
        assert model.document_source.filename == fname
        assert model.version == 1
        assert len(model.activities) == 6
        assert len(model.actors) >= 5
        assert len(model.conditions) >= 1
        assert len(model.dependencies) >= 5
        assert len(model.inputs) >= 6
        assert len(model.outputs) >= 6
        assert len(model.exceptions) >= 1
        assert len(model.approvals) >= 1
        assert model.validation_status.value == "VALID"

        # Never silently convert an unapproved extraction into an approved process
        assert model.review_status == ReviewStatusEnum.PENDING_REVIEW
        assert model.approved_by is None

        # Verify all 5 agents executed in trace
        agent_names = [step.agent_name for step in model.agent_trace]
        assert len(agent_names) == 5
        assert "Agent 1" in agent_names[0]
        assert "Agent 5" in agent_names[4]

        # Verify all 12 mandatory fields on every activity
        for act in model.activities:
            assert act.activity_id
            assert act.activity_name
            assert act.description
            assert act.activity_type
            assert act.responsible_role and act.responsible_role != "UNASSIGNED"
            assert isinstance(act.input, list) and len(act.input) >= 1
            assert isinstance(act.output, list) and len(act.output) >= 1
            assert isinstance(act.preconditions, list) and len(act.preconditions) >= 1
            assert isinstance(act.postconditions, list) and len(act.postconditions) >= 1
            assert isinstance(act.dependencies, list)
            assert act.source_reference.exact_quote
            assert 0.80 <= act.confidence_score <= 1.0
