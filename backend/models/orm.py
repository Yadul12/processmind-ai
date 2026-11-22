"""
Database ORM Models for ProcessMind AI (SQLAlchemy 2.0).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SchemaMigrationORM(Base):
    __tablename__ = "schema_migrations"

    version = Column(String(64), primary_key=True)
    applied_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_type = Column(String(32), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    checksum_sha256 = Column(String(128), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_structure_json = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    processes = relationship("ProcessORM", back_populates="document", cascade="all, delete-orphan")


class ProcessORM(Base):
    __tablename__ = "processes"

    process_id = Column(String(64), primary_key=True, index=True)
    process_name = Column(String(255), nullable=False)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    current_version = Column(Integer, default=1, nullable=False)
    validation_status = Column(String(32), default="NEEDS_REVIEW", nullable=False, index=True)
    review_status = Column(String(32), default="PENDING_REVIEW", nullable=False, index=True)
    overall_confidence = Column(Float, default=0.0, nullable=False)
    needs_human_review = Column(Boolean, default=True, nullable=False)
    process_model_json = Column(Text, nullable=False)
    validation_errors_json = Column(Text, default="[]", nullable=False)
    agent_trace_json = Column(Text, default="[]", nullable=False)
    reviewer_comments_json = Column(Text, default="[]", nullable=False)
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(String(128), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    document = relationship("DocumentORM", back_populates="processes")
    versions = relationship("ProcessVersionORM", back_populates="process", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogORM", back_populates="process", cascade="all, delete-orphan")


class ProcessVersionORM(Base):
    __tablename__ = "process_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_id = Column(String(64), ForeignKey("processes.process_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    validation_status = Column(String(32), nullable=False)
    review_status = Column(String(32), nullable=False)
    overall_confidence = Column(Float, default=0.0, nullable=False)
    process_model_json = Column(Text, nullable=False)
    change_summary = Column(Text, nullable=False)
    changed_by = Column(String(128), default="system", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    process = relationship("ProcessORM", back_populates="versions")


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_id = Column(String(64), ForeignKey("processes.process_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False)
    details = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    process = relationship("ProcessORM", back_populates="audit_logs")


Index("ix_process_versions_pid_ver", ProcessVersionORM.process_id, ProcessVersionORM.version)
