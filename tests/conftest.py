"""
Pytest Configuration and Fixtures for ProcessMind AI Test Suite.
"""

import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal, run_migrations
from backend.main import app
from backend.services.process_service import process_service
from data.generate_sample_files import generate_all_samples


@pytest.fixture(scope="session", autouse=True)
def setup_sample_data_and_db() -> None:
    generate_all_samples()
    run_migrations()
    with SessionLocal() as db:
        process_service.seed_initial_enterprise_dataset(db)


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
