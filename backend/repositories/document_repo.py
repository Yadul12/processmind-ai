"""
Document Repository Layer (SQLAlchemy Data Access).
"""

import json
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.orm import DocumentORM
from backend.schemas.document import (
    DocumentFileTypeEnum,
    DocumentMetadataSchema,
    DocumentRecordSchema,
    ParsedDocumentStructure,
)


class DocumentRepository:
    """Encapsulates database CRUD operations for ingested SOP documents."""

    def save_document(
        self,
        db: Session,
        doc_record: DocumentRecordSchema,
        storage_path: str,
    ) -> DocumentORM:
        orm_obj = DocumentORM(
            id=doc_record.id,
            filename=doc_record.filename,
            file_type=doc_record.file_type.value,
            file_size_bytes=doc_record.file_size_bytes,
            checksum_sha256=doc_record.checksum_sha256,
            storage_path=storage_path,
            raw_text=doc_record.raw_text,
            parsed_structure_json=doc_record.parsed_structure.model_dump_json(),
            metadata_json=doc_record.metadata.model_dump_json(),
            created_at=doc_record.created_at,
        )
        db.add(orm_obj)
        db.commit()
        db.refresh(orm_obj)
        return orm_obj

    def list_documents(self, db: Session) -> List[DocumentRecordSchema]:
        rows = db.query(DocumentORM).order_by(DocumentORM.created_at.desc()).all()
        return [self._to_schema(r) for r in rows]

    def get_by_id(self, db: Session, document_id: str) -> Optional[DocumentRecordSchema]:
        row = db.query(DocumentORM).filter(DocumentORM.id == document_id).first()
        return self._to_schema(row) if row else None

    def get_by_checksum(self, db: Session, checksum_sha256: str) -> Optional[DocumentRecordSchema]:
        row = db.query(DocumentORM).filter(DocumentORM.checksum_sha256 == checksum_sha256).first()
        return self._to_schema(row) if row else None

    def count_documents(self, db: Session) -> int:
        return db.query(DocumentORM).count()

    @staticmethod
    def _to_schema(row: DocumentORM) -> DocumentRecordSchema:
        return DocumentRecordSchema(
            id=row.id,
            filename=row.filename,
            file_type=DocumentFileTypeEnum(row.file_type),
            file_size_bytes=row.file_size_bytes,
            checksum_sha256=row.checksum_sha256,
            raw_text=row.raw_text,
            parsed_structure=ParsedDocumentStructure.model_validate(json.loads(row.parsed_structure_json)),
            metadata=DocumentMetadataSchema.model_validate(json.loads(row.metadata_json)),
            created_at=row.created_at,
        )


document_repository = DocumentRepository()
