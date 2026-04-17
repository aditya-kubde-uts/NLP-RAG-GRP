"""App wiring: health + OpenAPI."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_docs_available(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200


def test_openapi_json_available(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "RAG Factory API"


def test_health_db_returns_error_shape_or_ok(client: TestClient) -> None:
    """DB health may be 200 (reachable) or 503 (localhost:65432 not running in CI)."""
    r = client.get("/api/health/db")
    assert r.status_code in (200, 503)
    body = r.json()
    if r.status_code == 200:
        assert body.get("status") == "healthy"
    else:
        assert "error" in body
