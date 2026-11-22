"""
Health Check Endpoint (GET /api/health).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.repositories.document_repo import document_repository
from backend.schemas.api import HealthResponseSchema

router = APIRouter(tags=["Health"])


@router.get("/api/health", response_model=HealthResponseSchema)
def get_health(db: Session = Depends(get_db)) -> HealthResponseSchema:
    db_ok = True
    doc_count = 0
    try:
        db.execute(text("SELECT 1"))
        doc_count = document_repository.count_documents(db)
    except Exception:
        db_ok = False

    return HealthResponseSchema(
        status="healthy" if db_ok else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        llm_provider=settings.effective_llm_provider,
        database_connected=db_ok,
        sample_documents_loaded=doc_count,
        timestamp=datetime.now(timezone.utc),
    )
