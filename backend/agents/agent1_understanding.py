"""
Agent 1 — Document Understanding Agent
Responsibilities:
- Read PDF, DOCX, Excel, and TXT files (via MultiFormatDocumentParser or pre-parsed blocks).
- Extract text while preserving page, sheet, and section references.
- Identify document metadata and document structure.
- Detect tables, numbered steps, headings, and decision statements.
"""

import re
import time
from typing import Any, Dict, List

from backend.agents.state import ExtractionGraphState
from backend.schemas.document import (
    DocumentFileTypeEnum,
    DocumentMetadataSchema,
    DocumentSectionBlock,
    ParsedDocumentStructure,
)


class DocumentUnderstandingAgent:
    """Agent 1: Converts raw document text & blocks into structured metadata, headings, steps, tables, and decisions."""

    AGENT_NAME = "Agent 1 — Document Understanding"

    def extract_metadata(
        self,
        filename: str,
        blocks: List[DocumentSectionBlock],
        tables_count: int,
        page_or_sheet_count: int,
    ) -> DocumentMetadataSchema:
        title = filename.rsplit(".", 1)[0].replace("_", " ").title()
        doc_code = None
        department = "Enterprise Operations"
        effective_date = None
        owner_role = None

        for blk in blocks[:20]:
            txt = blk.text
            if "TITLE:" in txt.upper():
                after = re.split(r"TITLE:\s*", txt, flags=re.IGNORECASE)[1]
                title = after.split("|")[0].strip()
            if "DOCUMENT CODE:" in txt.upper():
                after = re.split(r"DOCUMENT CODE:\s*", txt, flags=re.IGNORECASE)[1]
                doc_code = after.split("|")[0].strip()
            if "DEPARTMENT:" in txt.upper():
                after = re.split(r"DEPARTMENT:\s*", txt, flags=re.IGNORECASE)[1]
                department = after.split("|")[0].strip()
            if "EFFECTIVE DATE:" in txt.upper():
                after = re.split(r"EFFECTIVE DATE:\s*", txt, flags=re.IGNORECASE)[1]
                effective_date = after.split("|")[0].strip()
            if "OWNER:" in txt.upper():
                after = re.split(r"OWNER:\s*", txt, flags=re.IGNORECASE)[1]
                owner_role = after.split("|")[0].strip()

        headings = [b for b in blocks if b.block_type == "heading"]
        steps = [b for b in blocks if b.block_type == "numbered_step"]
        decisions = [b for b in blocks if b.is_decision_statement]

        return DocumentMetadataSchema(
            title=title,
            document_code=doc_code,
            department=department,
            effective_date=effective_date,
            owner_role=owner_role,
            page_or_sheet_count=max(1, page_or_sheet_count),
            section_count=max(1, len(headings)),
            numbered_step_count=len(steps),
            table_count=tables_count,
            decision_statement_count=len(decisions),
        )

    def run(self, state: ExtractionGraphState) -> ExtractionGraphState:
        start_ts = time.perf_counter()
        parsed_doc_dict = state.get("parsed_document") or {}

        if parsed_doc_dict and "blocks" in parsed_doc_dict:
            parsed_struct = ParsedDocumentStructure.model_validate(parsed_doc_dict)
        else:
            from backend.services.document_parsers import document_parser

            raw_bytes = (state.get("raw_text") or "").encode("utf-8")
            ftype, _, blocks, tables, page_count = document_parser.parse_bytes(
                raw_bytes,
                state.get("filename", "document.txt"),
                state.get("document_id", "DOC-UNKNOWN"),
            )
            meta = self.extract_metadata(
                state.get("filename", "document.txt"),
                blocks,
                len(tables),
                page_count,
            )
            parsed_struct = ParsedDocumentStructure(
                document_id=state.get("document_id", "DOC-UNKNOWN"),
                filename=state.get("filename", "document.txt"),
                file_type=DocumentFileTypeEnum(ftype.value),
                metadata=meta,
                headings=[b.text for b in blocks if b.block_type == "heading"],
                blocks=blocks,
                tables=tables,
                numbered_steps=[b.text for b in blocks if b.block_type == "numbered_step"],
                decision_statements=[b.text for b in blocks if b.is_decision_statement],
            )

        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        trace = list(state.get("agent_trace") or [])
        trace.append(
            {
                "agent_name": self.AGENT_NAME,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "summary": (
                    f"Extracted {len(parsed_struct.blocks)} blocks across "
                    f"{parsed_struct.metadata.page_or_sheet_count} page(s)/sheet(s), "
                    f"{parsed_struct.metadata.numbered_step_count} numbered steps, "
                    f"{parsed_struct.metadata.table_count} table(s), and "
                    f"{parsed_struct.metadata.decision_statement_count} decision statements."
                ),
                "items_processed": len(parsed_struct.blocks),
                "warnings_count": 0,
                "retry_iteration": state.get("retry_count", 0),
            }
        )

        return {
            **state,
            "parsed_document": parsed_struct.model_dump(mode="json"),
            "agent_trace": trace,
        }


agent1_understanding = DocumentUnderstandingAgent()
