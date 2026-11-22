"""
Process Extraction, Validation, Human Review, Versioning, and Import/Export REST Endpoints:
- POST /api/processes/extract
- GET /api/processes
- GET /api/processes/{id}
- PUT /api/processes/{id}
- POST /api/processes/{id}/validate
- POST /api/processes/{id}/approve
- POST /api/processes/{id}/reject
- GET /api/processes/{id}/versions
- POST /api/processes/{id}/activities/{activity_id}/review
- GET /api/processes/{id}/export
- POST /api/processes/import
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.process_repo import process_repository
from backend.schemas.api import (
    ActivityReviewRequest,
    ProcessApprovalRequest,
    ProcessExtractRequest,
    ProcessImportRequest,
    ProcessRejectionRequest,
    ProcessSummaryResponse,
    ProcessUpdateRequest,
    ProcessValidationResponse,
    ProcessVersionHistoryResponse,
)
from backend.schemas.process import ProcessModelSchema
from backend.services.process_service import process_service

router = APIRouter(prefix="/api/processes", tags=["Processes"])


@router.post("/extract", response_model=ProcessModelSchema, status_code=status.HTTP_201_CREATED)
def extract_process(
    payload: ProcessExtractRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    try:
        return process_service.extract_process_from_document(
            db,
            document_id=payload.document_id,
            custom_process_name=payload.custom_process_name,
            force_reextract=payload.force_reextract,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=List[ProcessSummaryResponse])
def list_processes(db: Session = Depends(get_db)) -> List[ProcessSummaryResponse]:
    return process_repository.list_processes(db)


@router.post("/import", response_model=ProcessModelSchema, status_code=status.HTTP_201_CREATED)
def import_process_json(
    payload: ProcessImportRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    return process_service.import_process_json(
        db,
        process_model=payload.process_model,
        imported_by=payload.imported_by,
    )


@router.get("/{id}", response_model=ProcessModelSchema)
def get_process(id: str, db: Session = Depends(get_db)) -> ProcessModelSchema:
    model = process_repository.get_by_id(db, id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Process '{id}' not found.")
    return model


@router.get("/{id}/export")
def export_process_json(id: str, db: Session = Depends(get_db)) -> JSONResponse:
    model = process_repository.get_by_id(db, id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Process '{id}' not found.")
    return JSONResponse(
        content=model.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="{model.process_id}_v{model.version}.json"'},
    )


@router.put("/{id}", response_model=ProcessModelSchema)
def update_process(
    id: str,
    payload: ProcessUpdateRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    try:
        return process_service.update_process_model(db, id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{id}/activities/{activity_id}/review", response_model=ProcessModelSchema)
def review_individual_activity(
    id: str,
    activity_id: str,
    payload: ActivityReviewRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    try:
        return process_service.review_single_activity(db, id, activity_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{id}/validate", response_model=ProcessValidationResponse)
def validate_process(
    id: str,
    db: Session = Depends(get_db),
) -> ProcessValidationResponse:
    try:
        return process_service.validate_process(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{id}/approve", response_model=ProcessModelSchema)
def approve_process(
    id: str,
    payload: ProcessApprovalRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    try:
        return process_service.approve_process(db, id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{id}/reject", response_model=ProcessModelSchema)
def reject_process(
    id: str,
    payload: ProcessRejectionRequest,
    db: Session = Depends(get_db),
) -> ProcessModelSchema:
    try:
        return process_service.reject_process(db, id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{id}/versions", response_model=ProcessVersionHistoryResponse)
def get_process_versions(
    id: str,
    db: Session = Depends(get_db),
) -> ProcessVersionHistoryResponse:
    try:
        return process_service.get_version_history(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
