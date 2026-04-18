"""Super-admin API (mocked Postgres + Supabase)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.dependencies import require_super_admin
from app.main import app
from app.models.business import BusinessResponse


@pytest.fixture
def sa_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_super_override() -> None:
    yield
    app.dependency_overrides.pop(require_super_admin, None)


@pytest.fixture
def override_super_admin() -> None:
    async def _fake() -> SimpleNamespace:
        return SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    app.dependency_overrides[require_super_admin] = _fake


def _mock_connect_cm(*, fetchall: list | None = None, fetchone: tuple | None = None) -> MagicMock:
    """Mimic ``with psycopg.connect(...) as conn, conn.cursor() as cur:``."""
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

    outer_cm = MagicMock()
    outer_cm.__enter__.return_value = conn
    outer_cm.__exit__.return_value = None
    return outer_cm


@patch("app.api.super_admin.psycopg.connect")
def test_list_businesses_empty(
    mock_connect: MagicMock, sa_client: TestClient, override_super_admin: None
) -> None:
    mock_connect.return_value = _mock_connect_cm(fetchall=[])
    r = sa_client.get(
        "/api/super-admin/businesses",
        headers={"Authorization": "Bearer token"},
    )
    assert r.status_code == 200
    assert r.json() == []


@patch("app.api.super_admin.psycopg.connect")
def test_list_businesses_one_row(
    mock_connect: MagicMock, sa_client: TestClient, override_super_admin: None
) -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    row = (
        UUID("11111111-1111-1111-1111-111111111111"),
        "Acme",
        "acme",
        "desc",
        "Retail",
        None,
        {"welcome_message": "Hi"},
        True,
        created,
        3,
        10,
        1,
    )
    mock_connect.return_value = _mock_connect_cm(fetchall=[row])
    r = sa_client.get(
        "/api/super-admin/businesses",
        headers={"Authorization": "Bearer token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["slug"] == "acme"
    assert data[0]["chunk_count"] == 3
    assert data[0]["chat_count"] == 10
    assert data[0]["admin_count"] == 1


@patch("app.api.super_admin.psycopg.connect")
def test_platform_stats(
    mock_connect: MagicMock, sa_client: TestClient, override_super_admin: None
) -> None:
    mock_connect.return_value = _mock_connect_cm(fetchone=(5, 12, 100))
    r = sa_client.get(
        "/api/super-admin/stats",
        headers={"Authorization": "Bearer token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_businesses"] == 5
    assert body["total_users"] == 12
    assert body["total_chat_messages"] == 100
    assert body["estimated_api_cost_usd"] == 0.0


@patch("app.api.super_admin.get_business")
@patch("app.api.super_admin.supabase_admin")
def test_create_business(
    mock_admin: MagicMock,
    mock_get_business: MagicMock,
    sa_client: TestClient,
    override_super_admin: None,
) -> None:
    bid = "22222222-2222-2222-2222-222222222222"
    mock_ins = MagicMock()
    mock_ins.data = [{"id": bid}]

    def table_side(name: str) -> MagicMock:
        t = MagicMock()
        if name == "businesses":
            t.insert.return_value.execute.return_value = mock_ins
        elif name == "business_members":
            t.insert.return_value.execute.return_value = MagicMock(data=[{}])
        return t

    mock_admin.table.side_effect = table_side

    mock_get_business.return_value = BusinessResponse(
        id=bid,
        name="N",
        slug="n",
        description=None,
        industry="Other",
        logo_url=None,
        settings={"welcome_message": "Hi"},
        is_active=True,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        chunk_count=0,
        chat_count=0,
        admin_count=1,
    )

    r = sa_client.post(
        "/api/super-admin/businesses",
        headers={"Authorization": "Bearer token"},
        json={
            "name": "N",
            "slug": "n",
            "description": None,
            "industry": "Other",
        },
    )
    assert r.status_code == 201
    assert r.json()["id"] == bid


def test_super_admin_requires_auth(sa_client: TestClient) -> None:
    r = sa_client.get("/api/super-admin/businesses")
    assert r.status_code == 401
