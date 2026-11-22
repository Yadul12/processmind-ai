"""
Edge-Case & Adversarial Validation Tests:
- Ambiguous wording & missing information (never inventing missing actors/thresholds)
- Contradictory instructions & circular dependency cycles
- Complex multi-branch workflows
- Non-silent approval enforcement
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.agents.orchestrator import process_orchestrator
from backend.config import settings
from backend.schemas.process import (
    ProcessModelSchema,
    ReviewStatusEnum,
    ValidationStatusEnum,
)


def test_ambiguous_wording_and_missing_actor_flagged_not_invented() -> None:
    fpath = Path(settings.sample_data_dir) / "edge_01_ambiguous_missing_actor.txt"
    raw_text = fpath.read_text(encoding="utf-8")

    model = process_orchestrator.execute_pipeline(
        document_id="DOC-EDGE-001",
        filename=fpath.name,
        file_type="txt",
        checksum_sha256="edge1",
        raw_text=raw_text,
    )

    assert model.validation_status == ValidationStatusEnum.NEEDS_REVIEW
    error_codes = {e.error_code for e in model.validation_errors}
    assert "MISSING_ACTOR" in error_codes
    assert "AMBIGUOUS_STATEMENT" in error_codes
    assert "INCOMPLETE_DECISION" in error_codes

    # Verify ACT-802 and ACT-803 kept responsible_role as UNASSIGNED rather than inventing a role
    act_802 = next(a for a in model.activities if a.activity_id == "ACT-802")
    assert act_802.responsible_role == "UNASSIGNED"
    assert act_802.is_uncertain is True
    assert act_802.confidence_score < settings.confidence_review_threshold


def test_contradictory_instructions_and_cyclic_dependencies_detected() -> None:
    fpath = Path(settings.sample_data_dir) / "edge_02_contradictory_instructions.txt"
    raw_text = fpath.read_text(encoding="utf-8")

    model = process_orchestrator.execute_pipeline(
        document_id="DOC-EDGE-002",
        filename=fpath.name,
        file_type="txt",
        checksum_sha256="edge2",
        raw_text=raw_text,
    )

    assert model.validation_status == ValidationStatusEnum.NEEDS_REVIEW
    error_codes = {e.error_code for e in model.validation_errors}
    assert "CONTRADICTORY_DEPENDENCY_CYCLE" in error_codes
    cycle_err = next(e for e in model.validation_errors if e.error_code == "CONTRADICTORY_DEPENDENCY_CYCLE")
    assert "ACT-902" in cycle_err.message and "ACT-903" in cycle_err.message


def test_complex_multibranch_workflow_extraction() -> None:
    fpath = Path(settings.sample_data_dir) / "edge_03_complex_multibranch.txt"
    raw_text = fpath.read_text(encoding="utf-8")

    model = process_orchestrator.execute_pipeline(
        document_id="DOC-EDGE-003",
        filename=fpath.name,
        file_type="txt",
        checksum_sha256="edge3",
        raw_text=raw_text,
    )

    assert model.validation_status == ValidationStatusEnum.VALID
    assert len(model.conditions) == 2
    assert len(model.approvals) == 1
    cond_ids = {c.condition_id for c in model.conditions}
    assert "COND-701" in cond_ids
    assert "COND-702" in cond_ids


def test_schema_forbids_silent_approval_without_human_approver() -> None:
    fpath = Path(settings.sample_data_dir) / "sop_01_invoice_processing.txt"
    model = process_orchestrator.execute_pipeline(
        document_id="DOC-SILENT-CHECK",
        filename=fpath.name,
        file_type="txt",
        checksum_sha256="silent",
        raw_text=fpath.read_text(encoding="utf-8"),
    )
    dump = model.model_dump(mode="json")
    dump["review_status"] = ReviewStatusEnum.APPROVED.value
    dump["approved_by"] = None

    with pytest.raises(ValidationError, match="without an explicit human approved_by actor"):
        ProcessModelSchema.model_validate(dump)


def test_duplicate_activity_detection_and_freeform_unstructured_sop() -> None:
    # Free-form unstructured document without [ACT-XXX] tags, plus duplicate sentences
    freeform_text = """
    Section 1.0 - Custom Freeform Vendor Onboarding
    1. The Procurement Analyst collects vendor W-9 tax certificate and banking form.
    2. The Procurement Analyst collects vendor W-9 tax certificate and banking form for verification.
    3. If the vendor contract exceeds $25,000, the Finance Director must approve the onboarding request.
    4. If the vendor fails compliance screening, escalate immediately to the Legal Counsel team.
    """
    model = process_orchestrator.execute_pipeline(
        document_id="DOC-FREEFORM-01",
        filename="custom_unstructured_sop.txt",
        file_type="txt",
        checksum_sha256="freeform01",
        raw_text=freeform_text,
    )
    assert len(model.activities) >= 3
    # Activity 2 should be flagged as a potential duplicate of Activity 1 by Agent 3 & Agent 4
    dup_flags = [a for a in model.activities if a.potential_duplicate_of is not None]
    assert len(dup_flags) >= 1
    assert any(e.error_code == "POTENTIAL_DUPLICATE_ACTIVITY" for e in model.validation_errors)

