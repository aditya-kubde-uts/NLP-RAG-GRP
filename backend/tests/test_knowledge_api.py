"""Knowledge API tests (Phase 6 baseline)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import require_business_admin
from app.main import app


@pytest.fixture
def kb_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_override() -> None:
    yield
    app.dependency_overrides.pop(require_business_admin, None)


@pytest.fixture
def override_business_admin() -> None:
    async def _fake(_business_id=None) -> SimpleNamespace:
        return SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    app.dependency_overrides[require_business_admin] = _fake


def _mock_connect_cm(*, fetchall: list | None = None, fetchone: tuple | None = None) -> MagicMock:
    cur = MagicMock()
    if fetchall is not None:
        cur.fetchall.return_value = fetchall
    if fetchone is not None:
        cur.fetchone.return_value = fetchone

    cur_cm = MagicMock()
    cur_cm.__enter__.return_value = cur
    cur_cm.__exit__.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = cur_cm
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = None

    outer = MagicMock()
    outer.__enter__.return_value = conn
    outer.__exit__.return_value = None
    return outer


def test_task_status_not_found(kb_client: TestClient, override_business_admin: None) -> None:
    r = kb_client.get(
        "/api/business/11111111-1111-1111-1111-111111111111/knowledge/tasks/missing",
        headers={"Authorization": "Bearer token"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "task_not_found"


@patch("app.api.knowledge.psycopg.connect")
def test_list_chunks_empty(
    mock_connect: MagicMock,
    kb_client: TestClient,
    override_business_admin: None,
) -> None:
    mock_connect.return_value = _mock_connect_cm(fetchall=[], fetchone=(0,))
    r = kb_client.get(
        "/api/business/11111111-1111-1111-1111-111111111111/knowledge/chunks?page=1&page_size=10",
        headers={"Authorization": "Bearer token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
