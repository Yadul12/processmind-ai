"""
Core Process Intelligence & Governance Service Layer.
Coordinates document ingestion, multi-agent LangGraph extraction, editing,
re-validation, activity-level review, full process approval/rejection guards, and seeding.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.agents.agent1_understanding import agent1_understanding
from backend.agents.agent4_validation import agent4_validation
from backend.agents.agent5_review_prep import agent5_review_prep
from backend.agents.orchestrator import process_orchestrator
from backend.config import settings
from backend.repositories.document_repo import document_repository
from backend.repositories.process_repo import process_repository
from backend.schemas.api import (
    ActivityReviewRequest,
    ProcessApprovalRequest,
    ProcessRejectionRequest,
    ProcessUpdateRequest,
    ProcessValidationResponse,
    ProcessVersionHistoryResponse,
)
from backend.schemas.document import (
    DocumentFileTypeEnum,
    DocumentRecordSchema,
    ParsedDocumentStructure,
)
from backend.schemas.process import (
    ActivityDependencySchema,
    ActivityReviewDecisionEnum,
    AuditLogEntrySchema,
    DependencyTypeEnum,
    ProcessActorSchema,
    ProcessModelSchema,
    ReviewerCommentSchema,
    ReviewStatusEnum,
    ValidationSeverityEnum,
    ValidationStatusEnum,
)
from backend.services.document_parsers import document_parser

logger = logging.getLogger("processmind.process_service")


class ProcessService:
    """High-level application service enforcing business rules, versioning, and human review governance."""

    def ingest_document(
        self,
        db: Session,
        filename: str,
        content_bytes: bytes,
    ) -> DocumentRecordSchema:
        checksum = hashlib.sha256(content_bytes).hexdigest()
        existing = document_repository.get_by_checksum(db, checksum)
        if existing and existing.filename == filename:
            return existing

        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        ftype, raw_text, blocks, tables, page_count = document_parser.parse_bytes(
            content_bytes,
            filename,
            doc_id,
        )
        meta = agent1_understanding.extract_metadata(
            filename,
            blocks,
            len(tables),
            page_count,
        )
        parsed_struct = ParsedDocumentStructure(
            document_id=doc_id,
            filename=filename,
            file_type=DocumentFileTypeEnum(ftype.value),
            metadata=meta,
            headings=[b.text for b in blocks if b.block_type == "heading"],
            blocks=blocks,
            tables=tables,
            numbered_steps=[b.text for b in blocks if b.block_type == "numbered_step"],
            decision_statements=[b.text for b in blocks if b.is_decision_statement],
        )

        safe_name = f"{doc_id}_{Path(filename).name}"
        storage_path = Path(settings.upload_storage_dir) / safe_name
        storage_path.write_bytes(content_bytes)

        doc_record = DocumentRecordSchema(
            id=doc_id,
            filename=filename,
            file_type=DocumentFileTypeEnum(ftype.value),
            file_size_bytes=len(content_bytes),
            checksum_sha256=checksum,
            raw_text=raw_text,
            parsed_structure=parsed_struct,
            metadata=meta,
            created_at=datetime.now(timezone.utc),
        )
        document_repository.save_document(db, doc_record, str(storage_path))
        return doc_record

    def extract_process_from_document(
        self,
        db: Session,
        document_id: str,
        custom_process_name: Optional[str] = None,
        force_reextract: bool = False,
    ) -> ProcessModelSchema:
        doc = document_repository.get_by_id(db, document_id)
        if not doc:
            raise KeyError(f"Document '{document_id}' not found")

        if not force_reextract:
            existing_proc = process_repository.get_by_document_id(db, document_id)
            if existing_proc:
                return existing_proc

        process_model = process_orchestrator.execute_pipeline(
            document_id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type.value,
            checksum_sha256=doc.checksum_sha256,
            raw_text=doc.raw_text,
            parsed_document=doc.parsed_structure,
            custom_process_name=custom_process_name,
        )
        return process_repository.create_process(
            db,
            process_model,
            changed_by="LangGraph 5-Agent Pipeline",
            change_summary=f"Extracted process model v1 from '{doc.filename}'",
        )

    def _resync_derived_actors_and_dependencies(self, model: ProcessModelSchema) -> None:
        """Synchronizes top-level actors and dependencies whenever activities are edited."""
        actors_by_role = {a.role_name: a for a in model.actors}
        apr_act_ids = {ap.activity_id for ap in model.approvals}
        new_actors: List[ProcessActorSchema] = []
        seen_roles = set()

        for act in model.activities:
            rname = act.responsible_role.strip()
            if not rname or rname.upper() == "UNASSIGNED":
                continue
            if rname not in seen_roles:
                seen_roles.add(rname)
                existing_actor = actors_by_role.get(rname)
                assigned = [a.activity_id for a in model.activities if a.responsible_role.strip() == rname]
                is_apr = any(
                    a.activity_type.value == "approval" or a.activity_id in apr_act_ids
                    for a in model.activities
                    if a.responsible_role.strip() == rname
                )
                new_actors.append(
                    ProcessActorSchema(
                        actor_id=existing_actor.actor_id if existing_actor else f"ROLE-{len(new_actors) + 1:03d}",
                        role_name=rname,
                        department=act.department,
                        is_approver=is_apr,
                        assigned_activity_ids=assigned,
                        source_reference=act.source_reference,
                    )
                )
        model.actors = new_actors

        # Re-sync dependency edges from activity.dependencies while preserving dependency types
        existing_dep_map = {
            (d.source_activity_id, d.target_activity_id): d for d in model.dependencies
        }
        rebuilt_deps: List[ActivityDependencySchema] = []
        dep_idx = 1
        for act in model.activities:
            for upstream_id in act.dependencies:
                key = (upstream_id, act.activity_id)
                if key in existing_dep_map:
                    prev = existing_dep_map[key]
                    rebuilt_deps.append(prev)
                else:
                    rebuilt_deps.append(
                        ActivityDependencySchema(
                            dependency_id=f"DEP-{dep_idx:03d}-{uuid.uuid4().hex[:4].upper()}",
                            source_activity_id=upstream_id,
                            target_activity_id=act.activity_id,
                            dependency_type=DependencyTypeEnum.SEQUENTIAL,
                            source_reference=act.source_reference,
                        )
                    )
                dep_idx += 1
        model.dependencies = rebuilt_deps

    def _revalidate_model_in_place(self, db: Session, model: ProcessModelSchema) -> None:
        doc = document_repository.get_by_id(db, model.document_source.document_id)
        raw_text_lower = (doc.raw_text if doc else "").lower()

        model_dict = model.model_dump(mode="json")
        errors, val_status = agent4_validation.validate_extraction_dict(model_dict)
        model.validation_errors = errors
        model.validation_status = val_status

        issues_by_act = {}
        for err in errors:
            if err.activity_id:
                issues_by_act.setdefault(err.activity_id, []).append(err)

        for act in model.activities:
            act_issues = issues_by_act.get(act.activity_id, [])
            breakdown = agent5_review_prep._score_activity(
                act.model_dump(mode="json"),
                raw_text_lower,
                act_issues,
            )
            act.confidence_score = breakdown.final_score
            act.confidence_breakdown = breakdown
            is_low = breakdown.final_score < settings.confidence_review_threshold
            act.is_uncertain = bool(is_low or len(act_issues) > 0)
            if act.is_uncertain:
                reasons = [i.message for i in act_issues]
                if is_low and not reasons:
                    reasons.append(f"Confidence {breakdown.final_score:.2f} < {settings.confidence_review_threshold}")
                act.uncertainty_reason = " | ".join(reasons)
            else:
                act.uncertainty_reason = None

        if model.activities:
            model.overall_confidence = round(
                sum(a.confidence_score for a in model.activities) / len(model.activities),
                3,
            )

    def update_process_model(
        self,
        db: Session,
        process_id: str,
        req: ProcessUpdateRequest,
    ) -> ProcessModelSchema:
        model = process_repository.get_by_id(db, process_id)
        if not model:
            raise KeyError(f"Process '{process_id}' not found")

        if req.process_name is not None:
            model.process_name = req.process_name
        if req.activities is not None:
            model.activities = req.activities
        if req.conditions is not None:
            model.conditions = req.conditions
        if req.inputs is not None:
            model.inputs = req.inputs
        if req.outputs is not None:
            model.outputs = req.outputs
        if req.exceptions is not None:
            model.exceptions = req.exceptions
        if req.approvals is not None:
            model.approvals = req.approvals

        if req.actors is not None:
            model.actors = req.actors
        if req.dependencies is not None:
            model.dependencies = req.dependencies
        else:
            self._resync_derived_actors_and_dependencies(model)

        # Increment version on edit and reset approval state to IN_REVIEW (never silently stay approved after edits)
        model.version += 1
        if model.review_status == ReviewStatusEnum.APPROVED:
            model.review_status = ReviewStatusEnum.IN_REVIEW
            model.approved_by = None
            model.approved_at = None
        elif model.review_status == ReviewStatusEnum.PENDING_REVIEW:
            model.review_status = ReviewStatusEnum.IN_REVIEW
        model.needs_human_review = True

        self._revalidate_model_in_place(db, model)

        if req.comment:
            model.reviewer_comments.append(
                ReviewerCommentSchema(
                    comment_id=f"CMT-{uuid.uuid4().hex[:6].upper()}",
                    author=req.reviewer_name,
                    comment=req.comment,
                )
            )

        model.audit_logs.append(
            AuditLogEntrySchema(
                log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                version=model.version,
                action="PROCESS_UPDATED",
                actor=req.reviewer_name,
                details=f"{req.change_summary} (now v{model.version}, validation={model.validation_status.value})",
            )
        )

        return process_repository.update_process(
            db,
            model,
            changed_by=req.reviewer_name,
            change_summary=req.change_summary,
            record_new_version=True,
        )

    def review_single_activity(
        self,
        db: Session,
        process_id: str,
        activity_id: str,
        req: ActivityReviewRequest,
    ) -> ProcessModelSchema:
        model = process_repository.get_by_id(db, process_id)
        if not model:
            raise KeyError(f"Process '{process_id}' not found")

        target_act = next((a for a in model.activities if a.activity_id == activity_id), None)
        if not target_act:
            raise KeyError(f"Activity '{activity_id}' not found in process '{process_id}'")

        target_act.review_decision = req.decision
        if req.reviewer_note is not None:
            target_act.reviewer_note = req.reviewer_note

        if model.review_status == ReviewStatusEnum.PENDING_REVIEW:
            model.review_status = ReviewStatusEnum.IN_REVIEW

        if req.reviewer_note:
            model.reviewer_comments.append(
                ReviewerCommentSchema(
                    comment_id=f"CMT-{uuid.uuid4().hex[:6].upper()}",
                    author=req.reviewer_name,
                    activity_id=activity_id,
                    comment=f"[{req.decision.value}] {req.reviewer_note}",
                )
            )

        model.audit_logs.append(
            AuditLogEntrySchema(
                log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                version=model.version,
                action=f"ACTIVITY_{req.decision.value}",
                actor=req.reviewer_name,
                details=f"Activity '{activity_id}' marked as {req.decision.value} by {req.reviewer_name}.",
            )
        )

        return process_repository.update_process(
            db,
            model,
            changed_by=req.reviewer_name,
            change_summary=f"Activity {activity_id} reviewed: {req.decision.value}",
            record_new_version=False,
        )

    def validate_process(
        self,
        db: Session,
        process_id: str,
    ) -> ProcessValidationResponse:
        model = process_repository.get_by_id(db, process_id)
        if not model:
            raise KeyError(f"Process '{process_id}' not found")

        self._revalidate_model_in_place(db, model)
        process_repository.update_process(
            db,
            model,
            changed_by="Agent 4 — Process Validation",
            change_summary="Executed on-demand validation check",
            record_new_version=False,
        )

        errs = model.validation_errors
        err_cnt = sum(1 for e in errs if e.severity == ValidationSeverityEnum.ERROR)
        warn_cnt = sum(1 for e in errs if e.severity == ValidationSeverityEnum.WARNING)
        amb_cnt = sum(1 for e in errs if e.severity == ValidationSeverityEnum.AMBIGUITY)

        return ProcessValidationResponse(
            process_id=model.process_id,
            version=model.version,
            validation_status=model.validation_status,
            is_schema_valid=(err_cnt == 0),
            error_count=err_cnt,
            warning_count=warn_cnt,
            ambiguity_count=amb_cnt,
            validation_errors=errs,
        )

    def approve_process(
        self,
        db: Session,
        process_id: str,
        req: ProcessApprovalRequest,
    ) -> ProcessModelSchema:
        model = process_repository.get_by_id(db, process_id)
        if not model:
            raise KeyError(f"Process '{process_id}' not found")

        self._revalidate_model_in_place(db, model)

        blocking_errors = [
            e for e in model.validation_errors if e.severity == ValidationSeverityEnum.ERROR
        ]
        if blocking_errors:
            codes = ", ".join(sorted({e.error_code for e in blocking_errors}))
            raise ValueError(
                f"Cannot approve process '{process_id}' with {len(blocking_errors)} unresolved blocking "
                f"validation error(s) ({codes}). Resolve missing actors or dependency errors first."
            )

        rejected_acts = [
            a.activity_id for a in model.activities if a.review_decision == ActivityReviewDecisionEnum.REJECTED
        ]
        if rejected_acts:
            raise ValueError(
                f"Cannot approve complete process while activities {rejected_acts} are marked REJECTED."
            )

        if req.approve_all_pending_activities:
            for act in model.activities:
                if act.review_decision in (ActivityReviewDecisionEnum.PENDING, ActivityReviewDecisionEnum.EDITED):
                    act.review_decision = ActivityReviewDecisionEnum.APPROVED

        unapproved_acts = [
            a.activity_id for a in model.activities if a.review_decision != ActivityReviewDecisionEnum.APPROVED
        ]
        if unapproved_acts:
            raise ValueError(
                f"All activities must be reviewed and approved before process approval. Pending: {unapproved_acts}"
            )

        now = datetime.now(timezone.utc)
        model.review_status = ReviewStatusEnum.APPROVED
        model.needs_human_review = False
        model.approved_by = req.reviewer_name
        model.approved_at = now
        model.rejected_by = None
        model.rejected_at = None
        model.rejection_reason = None

        if req.comment:
            model.reviewer_comments.append(
                ReviewerCommentSchema(
                    comment_id=f"CMT-{uuid.uuid4().hex[:6].upper()}",
                    author=req.reviewer_name,
                    comment=f"[PROCESS APPROVED] {req.comment}",
                    created_at=now,
                )
            )

        model.audit_logs.append(
            AuditLogEntrySchema(
                log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                version=model.version,
                action="PROCESS_APPROVED",
                actor=req.reviewer_name,
                details=f"Complete process model v{model.version} formally approved by {req.reviewer_name}.",
                timestamp=now,
            )
        )

        return process_repository.update_process(
            db,
            model,
            changed_by=req.reviewer_name,
            change_summary=f"Approved v{model.version} ({req.comment})",
            record_new_version=False,
        )

    def reject_process(
        self,
        db: Session,
        process_id: str,
        req: ProcessRejectionRequest,
    ) -> ProcessModelSchema:
        model = process_repository.get_by_id(db, process_id)
        if not model:
            raise KeyError(f"Process '{process_id}' not found")

        now = datetime.now(timezone.utc)
        model.review_status = ReviewStatusEnum.REJECTED
        model.needs_human_review = True
        model.rejected_by = req.reviewer_name
        model.rejected_at = now
        model.rejection_reason = req.reason
        model.approved_by = None
        model.approved_at = None

        model.reviewer_comments.append(
            ReviewerCommentSchema(
                comment_id=f"CMT-{uuid.uuid4().hex[:6].upper()}",
                author=req.reviewer_name,
                comment=f"[PROCESS REJECTED] {req.reason}",
                created_at=now,
            )
        )

        model.audit_logs.append(
            AuditLogEntrySchema(
                log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                version=model.version,
                action="PROCESS_REJECTED",
                actor=req.reviewer_name,
                details=f"Process model v{model.version} rejected by {req.reviewer_name}: {req.reason}",
                timestamp=now,
            )
        )

        return process_repository.update_process(
            db,
            model,
            changed_by=req.reviewer_name,
            change_summary=f"Rejected v{model.version}: {req.reason}",
            record_new_version=False,
        )

    def get_version_history(
        self,
        db: Session,
        process_id: str,
    ) -> ProcessVersionHistoryResponse:
        current_ver, versions = process_repository.get_versions(db, process_id)
        return ProcessVersionHistoryResponse(
            process_id=process_id,
            current_version=current_ver,
            versions=versions,
        )

    def import_process_json(
        self,
        db: Session,
        process_model: ProcessModelSchema,
        imported_by: str = "Process Architect",
    ) -> ProcessModelSchema:
        existing_doc = document_repository.get_by_id(db, process_model.document_source.document_id)
        if not existing_doc:
            # Create a stub document entry if importing an external process JSON
            synthetic_lines = [a.source_reference.exact_quote for a in process_model.activities]
            doc = self.ingest_document(
                db,
                filename=process_model.document_source.filename,
                content_bytes="\n".join(synthetic_lines).encode("utf-8"),
            )
            process_model.document_source.document_id = doc.id

        # Never silently import an unverified process as approved unless approved_by is present
        if process_model.review_status == ReviewStatusEnum.APPROVED and not process_model.approved_by:
            process_model.review_status = ReviewStatusEnum.PENDING_REVIEW

        existing_proc = process_repository.get_by_id(db, process_model.process_id)
        if existing_proc:
            process_model.process_id = f"PROC-{uuid.uuid4().hex[:8].upper()}"

        process_model.audit_logs.append(
            AuditLogEntrySchema(
                log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                version=process_model.version,
                action="PROCESS_IMPORTED_JSON",
                actor=imported_by,
                details=f"Imported structured process JSON '{process_model.process_name}'.",
            )
        )
        return process_repository.create_process(
            db,
            process_model,
            changed_by=imported_by,
            change_summary="Imported from JSON package",
        )

    def seed_initial_enterprise_dataset(self, db: Session) -> int:
        """
        Seeds the 5 primary enterprise SOP documents (PDF, DOCX, XLSX, TXT) + 3 edge cases
        and runs initial multi-agent extraction if the database is empty.
        """
        if document_repository.count_documents(db) > 0:
            return document_repository.count_documents(db)

        sample_dir = Path(settings.sample_data_dir)
        if not list(sample_dir.glob("*.*")):
            from data.generate_sample_files import generate_all_samples

            generate_all_samples()

        primary_files = [
            "sop_01_invoice_processing.pdf",
            "sop_02_employee_onboarding.docx",
            "sop_03_procurement_approvals.xlsx",
            "sop_04_customer_complaint_resolution.pdf",
            "sop_05_it_access_management.docx",
            "edge_01_ambiguous_missing_actor.txt",
            "edge_02_contradictory_instructions.txt",
            "edge_03_complex_multibranch.txt",
        ]

        seeded_count = 0
        for fname in primary_files:
            fpath = sample_dir / fname
            if not fpath.exists():
                continue
            doc = self.ingest_document(db, fname, fpath.read_bytes())
            self.extract_process_from_document(db, doc.id)
            seeded_count += 1

        logger.info("Seeded %d enterprise SOP documents and extracted process models.", seeded_count)
        return seeded_count


process_service = ProcessService()
