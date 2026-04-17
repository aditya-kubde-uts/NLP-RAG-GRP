"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

# Load test env before any application imports (Settings + Supabase clients).
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.test")

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Isolate tests that tweak env / ``get_settings``."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Synchronous FastAPI test client."""
    return TestClient(app)
