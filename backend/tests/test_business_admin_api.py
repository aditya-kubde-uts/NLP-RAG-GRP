"""Business-admin API (mocked Supabase)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_business_admin
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> None:
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_business_admin, None)


def _override_current_user(user_id: str) -> None:
    async def _fake() -> SimpleNamespace:
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_current_user] = _fake


BUSINESS_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "name": "Acme",
    "slug": "acme",
    "description": "desc",
    "industry": "Retail",
    "logo_url": None,
    "settings": {"welcome_message": "Hi"},
    "is_active": True,
    "created_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
}


def _supabase_for_slug(
    *, super_admin: bool, member: bool, business_found: bool = True
) -> MagicMock:
    """Mock ``supabase_admin`` for the by-slug endpoint."""

    mock = MagicMock()

    def table_side(name: str) -> MagicMock:
        t = MagicMock()
        if name == "businesses":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[BUSINESS_ROW] if business_found else [])
            )
        elif name == "user_profiles":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[{"is_super_admin": super_admin}])
            )
        elif name == "business_members":
            data = [{"role": "admin"}] if member else []
            t.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=data
            )
        return t

    mock.table.side_effect = table_side
    return mock


@patch("app.api.business_admin.supabase_admin")
def test_by_slug_allows_super_admin_even_without_membership(
    mock_admin: MagicMock, client: TestClient
) -> None:
    _override_current_user("sa-1")
    mock_admin.table.side_effect = _supabase_for_slug(
        super_admin=True, member=False
    ).table.side_effect

    r = client.get(
        "/api/business/by-slug/acme", headers={"Authorization": "Bearer t"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "acme"


@patch("app.api.business_admin.supabase_admin")
def test_by_slug_allows_business_member(
    mock_admin: MagicMock, client: TestClient
) -> None:
    _override_current_user("biz-admin-1")
    mock_admin.table.side_effect = _supabase_for_slug(
        super_admin=False, member=True
    ).table.side_effect

    r = client.get(
        "/api/business/by-slug/acme", headers={"Authorization": "Bearer t"}
    )
    assert r.status_code == 200


@patch("app.api.business_admin.supabase_admin")
def test_by_slug_rejects_outsider(mock_admin: MagicMock, client: TestClient) -> None:
    _override_current_user("outsider-1")
    mock_admin.table.side_effect = _supabase_for_slug(
        super_admin=False, member=False
    ).table.side_effect

    r = client.get(
        "/api/business/by-slug/acme", headers={"Authorization": "Bearer t"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


@patch("app.api.business_admin.supabase_admin")
def test_by_slug_404_when_missing(mock_admin: MagicMock, client: TestClient) -> None:
    _override_current_user("sa-1")
    mock_admin.table.side_effect = _supabase_for_slug(
        super_admin=True, member=False, business_found=False
    ).table.side_effect

    r = client.get(
        "/api/business/by-slug/ghost", headers={"Authorization": "Bearer t"}
    )
    assert r.status_code == 404
