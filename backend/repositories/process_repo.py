"""
Process Model, Version History, and Audit Trail Repository Layer.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.orm import AuditLogORM, ProcessORM, ProcessVersionORM
from backend.schemas.api import ProcessSummaryResponse, ProcessVersionItemSchema
from backend.schemas.process import (
    ProcessModelSchema,
    ReviewStatusEnum,
    ValidationStatusEnum,
)


class ProcessRepository:
    """Manages relational persistence of structured process models, version snapshots, and audit logs."""

    def create_process(
        self,
        db: Session,
        model: ProcessModelSchema,
        changed_by: str = "LangGraph Pipeline",
        change_summary: str = "Initial 5-Agent Process Extraction (v1)",
    ) -> ProcessModelSchema:
        now = datetime.now(timezone.utc)
        model_json = model.model_dump_json()

        orm_proc = ProcessORM(
            process_id=model.process_id,
            process_name=model.process_name,
            document_id=model.document_source.document_id,
            current_version=model.version,
            validation_status=model.validation_status.value,
            review_status=model.review_status.value,
            overall_confidence=model.overall_confidence,
            needs_human_review=model.needs_human_review,
            process_model_json=model_json,
            validation_errors_json=json.dumps([e.model_dump(mode="json") for e in model.validation_errors]),
            agent_trace_json=json.dumps([t.model_dump(mode="json") for t in model.agent_trace]),
            reviewer_comments_json=json.dumps([c.model_dump(mode="json") for c in model.reviewer_comments]),
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            rejected_by=model.rejected_by,
            rejected_at=model.rejected_at,
            rejection_reason=model.rejection_reason,
            created_at=now,
            updated_at=now,
        )
        db.add(orm_proc)

        orm_ver = ProcessVersionORM(
            process_id=model.process_id,
            version=model.version,
            validation_status=model.validation_status.value,
            review_status=model.review_status.value,
            overall_confidence=model.overall_confidence,
            process_model_json=model_json,
            change_summary=change_summary,
            changed_by=changed_by,
            created_at=now,
        )
        db.add(orm_ver)

        for log_entry in model.audit_logs:
            db.add(
                AuditLogORM(
                    process_id=model.process_id,
                    version=log_entry.version,
                    action=log_entry.action,
                    actor=log_entry.actor,
                    details=log_entry.details,
                    created_at=log_entry.timestamp,
                )
            )

        db.commit()
        db.refresh(orm_proc)
        return ProcessModelSchema.model_validate(json.loads(orm_proc.process_model_json))

    def update_process(
        self,
        db: Session,
        model: ProcessModelSchema,
        changed_by: str,
        change_summary: str,
        record_new_version: bool = True,
    ) -> ProcessModelSchema:
        row = db.query(ProcessORM).filter(ProcessORM.process_id == model.process_id).first()
        if not row:
            raise KeyError(f"Process '{model.process_id}' not found")

        now = datetime.now(timezone.utc)
        model_json = model.model_dump_json()

        row.process_name = model.process_name
        row.current_version = model.version
        row.validation_status = model.validation_status.value
        row.review_status = model.review_status.value
        row.overall_confidence = model.overall_confidence
        row.needs_human_review = model.needs_human_review
        row.process_model_json = model_json
        row.validation_errors_json = json.dumps([e.model_dump(mode="json") for e in model.validation_errors])
        row.agent_trace_json = json.dumps([t.model_dump(mode="json") for t in model.agent_trace])
        row.reviewer_comments_json = json.dumps([c.model_dump(mode="json") for c in model.reviewer_comments])
        row.approved_by = model.approved_by
        row.approved_at = model.approved_at
        row.rejected_by = model.rejected_by
        row.rejected_at = model.rejected_at
        row.rejection_reason = model.rejection_reason
        row.updated_at = now

        if record_new_version:
            db.add(
                ProcessVersionORM(
                    process_id=model.process_id,
                    version=model.version,
                    validation_status=model.validation_status.value,
                    review_status=model.review_status.value,
                    overall_confidence=model.overall_confidence,
                    process_model_json=model_json,
                    change_summary=change_summary,
                    changed_by=changed_by,
                    created_at=now,
                )
            )

        if model.audit_logs:
            latest_log = model.audit_logs[-1]
            db.add(
                AuditLogORM(
                    process_id=model.process_id,
                    version=latest_log.version,
                    action=latest_log.action,
                    actor=latest_log.actor,
                    details=latest_log.details,
                    created_at=latest_log.timestamp,
                )
            )

        db.commit()
        db.refresh(row)
        return ProcessModelSchema.model_validate(json.loads(row.process_model_json))

    def get_by_id(self, db: Session, process_id: str) -> Optional[ProcessModelSchema]:
        row = db.query(ProcessORM).filter(ProcessORM.process_id == process_id).first()
        if not row:
            return None
        return ProcessModelSchema.model_validate(json.loads(row.process_model_json))

    def get_by_document_id(self, db: Session, document_id: str) -> Optional[ProcessModelSchema]:
        row = (
            db.query(ProcessORM)
            .filter(ProcessORM.document_id == document_id)
            .order_by(ProcessORM.updated_at.desc())
            .first()
        )
        if not row:
            return None
        return ProcessModelSchema.model_validate(json.loads(row.process_model_json))

    def list_processes(self, db: Session) -> List[ProcessSummaryResponse]:
        rows = db.query(ProcessORM).order_by(ProcessORM.updated_at.desc()).all()
        summaries: List[ProcessSummaryResponse] = []
        for r in rows:
            model = ProcessModelSchema.model_validate(json.loads(r.process_model_json))
            summaries.append(
                ProcessSummaryResponse(
                    process_id=r.process_id,
                    process_name=r.process_name,
                    document_id=r.document_id,
                    document_filename=model.document_source.filename,
                    version=r.current_version,
                    activity_count=len(model.activities),
                    actor_count=len(model.actors),
                    condition_count=len(model.conditions),
                    approval_count=len(model.approvals),
                    exception_count=len(model.exceptions),
                    validation_status=ValidationStatusEnum(r.validation_status),
                    review_status=ReviewStatusEnum(r.review_status),
                    overall_confidence=r.overall_confidence,
                    needs_human_review=r.needs_human_review,
                    validation_error_count=len(model.validation_errors),
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return summaries

    def get_versions(self, db: Session, process_id: str) -> Tuple[int, List[ProcessVersionItemSchema]]:
        proc_row = db.query(ProcessORM).filter(ProcessORM.process_id == process_id).first()
        if not proc_row:
            raise KeyError(f"Process '{process_id}' not found")

        ver_rows = (
            db.query(ProcessVersionORM)
            .filter(ProcessVersionORM.process_id == process_id)
            .order_by(ProcessVersionORM.version.desc())
            .all()
        )
        items = [
            ProcessVersionItemSchema(
                version=v.version,
                validation_status=ValidationStatusEnum(v.validation_status),
                review_status=ReviewStatusEnum(v.review_status),
                overall_confidence=v.overall_confidence,
                change_summary=v.change_summary,
                changed_by=v.changed_by,
                created_at=v.created_at,
                process_model=ProcessModelSchema.model_validate(json.loads(v.process_model_json)),
            )
            for v in ver_rows
        ]
        return proc_row.current_version, items


process_repository = ProcessRepository()
