"""Phase 0 smoke test: FastAPI app boots and /api/health returns healthy."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "healthy", "service": "RAG Factory API"}
