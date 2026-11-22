"""
Database Engine, Session Management, and Migration Runner for ProcessMind AI.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings
from backend.models.orm import Base, SchemaMigrationORM

logger = logging.getLogger("processmind.database")

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_migrations() -> None:
    """Apply SQLAlchemy metadata schema and record migration version."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = db.query(SchemaMigrationORM).filter_by(version="001_initial_schema").first()
        if not existing:
            db.add(SchemaMigrationORM(version="001_initial_schema"))
            db.commit()
            logger.info("Applied database migration: 001_initial_schema")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a scoped SQLAlchemy Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
