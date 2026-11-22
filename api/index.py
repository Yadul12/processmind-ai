"""Vercel Python Serverless Function ASGI Entrypoint for ProcessMind AI."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import app, ensure_initialized  # noqa: E402

# Guarantee relational schema creation and 8 enterprise SOP seeding on serverless cold start
ensure_initialized()

__all__ = ["app"]
