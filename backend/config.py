"""
Environment-based configuration for ProcessMind AI.
Never hardcodes API keys; supports deterministic mock mode when OPENAI_API_KEY is absent.
Supports both local/Docker execution and Vercel Serverless (/tmp writable storage).
"""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.environ.get("VERCEL"))

DEFAULT_DB_URL = (
    "sqlite:////tmp/processmind.db"
    if IS_VERCEL
    else f"sqlite:///{(BASE_DIR / 'processmind.db').as_posix()}"
)
DEFAULT_UPLOAD_DIR = (
    "/tmp/processmind_uploads"
    if IS_VERCEL
    else str(BASE_DIR / "storage" / "uploads")
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="ProcessMind AI — SOP-to-Process Intelligence Agent", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database URL (supports PostgreSQL in production/Docker and SQLite for local/serverless execution)
    database_url: str = Field(
        default=DEFAULT_DB_URL,
        alias="DATABASE_URL",
    )

    # LLM Provider settings
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Rate limits, retries, and LangGraph bounds
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    llm_retry_base_delay_seconds: float = Field(default=0.25, alias="LLM_RETRY_BASE_DELAY_SECONDS")
    llm_rate_limit_rpm: int = Field(default=60, alias="LLM_RATE_LIMIT_RPM")
    langgraph_max_retries: int = Field(default=2, alias="LANGGRAPH_MAX_RETRIES")
    confidence_review_threshold: float = Field(default=0.75, alias="CONFIDENCE_REVIEW_THRESHOLD")

    # Directories
    upload_storage_dir: str = Field(
        default=DEFAULT_UPLOAD_DIR,
        alias="UPLOAD_STORAGE_DIR",
    )
    sample_data_dir: str = Field(
        default=str(BASE_DIR / "data" / "sample_sops"),
        alias="SAMPLE_DATA_DIR",
    )
    ground_truth_dir: str = Field(
        default=str(BASE_DIR / "data" / "labelled_ground_truth"),
        alias="GROUND_TRUTH_DIR",
    )

    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_llm_provider(self) -> str:
        """If provider is set to openai but no API key is configured, safely fall back to deterministic mock."""
        if self.llm_provider.lower() == "openai" and self.openai_api_key.strip():
            return "openai"
        return "mock"


settings = Settings()

# Ensure writable upload directory exists
try:
    os.makedirs(settings.upload_storage_dir, exist_ok=True)
    if not IS_VERCEL:
        os.makedirs(settings.sample_data_dir, exist_ok=True)
        os.makedirs(settings.ground_truth_dir, exist_ok=True)
except OSError:
    pass
