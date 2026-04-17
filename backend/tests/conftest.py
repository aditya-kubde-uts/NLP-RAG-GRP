"""Shared pytest fixtures.

Real Supabase / Azure fixtures will be added in Phase 2+.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous FastAPI test client."""
    return TestClient(app)
