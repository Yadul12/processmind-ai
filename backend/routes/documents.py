"""
Document Ingestion & Inspection REST Endpoints:
- POST /api/documents/upload
- GET /api/documents
- GET /api/documents/{id}
"""

from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.document_repo import document_repository
from backend.schemas.api import DocumentDetailResponse, DocumentSummaryResponse
from backend.services.process_service import process_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="SOP Document file (.pdf, .docx, .xlsx, .txt)"),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc = process_service.ingest_document(db, file.filename, content_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        checksum_sha256=doc.checksum_sha256,
        metadata=doc.metadata,
        created_at=doc.created_at,
        raw_text=doc.raw_text,
        parsed_structure=doc.parsed_structure,
    )


@router.get("", response_model=List[DocumentSummaryResponse])
def list_documents(db: Session = Depends(get_db)) -> List[DocumentSummaryResponse]:
    docs = document_repository.list_documents(db)
    return [
        DocumentSummaryResponse(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size_bytes=d.file_size_bytes,
            checksum_sha256=d.checksum_sha256,
            metadata=d.metadata,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/{id}", response_model=DocumentDetailResponse)
def get_document(id: str, db: Session = Depends(get_db)) -> DocumentDetailResponse:
    doc = document_repository.get_by_id(db, id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{id}' not found.")

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        checksum_sha256=doc.checksum_sha256,
        metadata=doc.metadata,
        created_at=doc.created_at,
        raw_text=doc.raw_text,
        parsed_structure=doc.parsed_structure,
    )
