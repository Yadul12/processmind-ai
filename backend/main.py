"""
ProcessMind AI — FastAPI Application Entrypoint.
Configures structured logging, database migrations, enterprise sample SOP seeding, and REST routers.
"""

import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, settings
from backend.database import SessionLocal, run_migrations
from backend.routes import documents, evaluations, health, processes
from backend.services.process_service import process_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("processmind.main")

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def ensure_initialized() -> None:
    """Idempotently run migrations and seed initial enterprise SOP dataset once per worker process."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        run_migrations()
        with SessionLocal() as db:
            process_service.seed_initial_enterprise_dataset(db)
        _INITIALIZED = True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Initializing ProcessMind AI (%s) [LLM Provider: %s]",
        settings.app_version,
        settings.effective_llm_provider,
    )
    ensure_initialized()
    yield
    logger.info("Shutting down ProcessMind AI.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise Multi-Agent Process Intelligence System converting unstructured SOPs "
        "(PDF, DOCX, XLSX, TXT) into strictly validated, versioned, source-cited business process models."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(processes.router)
app.include_router(evaluations.router)

frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists() and not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
