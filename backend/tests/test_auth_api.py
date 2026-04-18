"""Auth API routes (mocked Supabase)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.models.auth import UserProfile


@pytest.fixture
def auth_client() -> TestClient:
    return TestClient(app)


@patch("app.api.auth.build_user_profile")
@patch("app.api.auth.supabase")
def test_signup_with_session_returns_tokens(
    mock_supa: MagicMock, mock_build: MagicMock, auth_client: TestClient
) -> None:
    mock_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000099", email="n@x.co")
    mock_session = SimpleNamespace(
        access_token="at",
        refresh_token="rt",
        expires_in=3600,
        token_type="bearer",
    )
    mock_supa.auth.sign_up.return_value = SimpleNamespace(user=mock_user, session=mock_session)
    mock_build.return_value = UserProfile(
        id="00000000-0000-0000-0000-000000000099",
        email="n@x.co",
        full_name="N",
        is_super_admin=False,
        businesses=[],
    )

    r = auth_client.post(
        "/api/auth/signup",
        json={"email": "n@x.co", "password": "longenough", "full_name": "N"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["id"] == "00000000-0000-0000-0000-000000000099"
    assert data["session"]["access_token"] == "at"
    assert data.get("message") is None


@patch("app.api.auth.build_user_profile")
@patch("app.api.auth.supabase")
def test_signup_without_session_sets_message(
    mock_supa: MagicMock, mock_build: MagicMock, auth_client: TestClient
) -> None:
    mock_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000088", email="v@x.co")
    mock_supa.auth.sign_up.return_value = SimpleNamespace(user=mock_user, session=None)
    mock_build.return_value = UserProfile(
        id="00000000-0000-0000-0000-000000000088",
        email="v@x.co",
        full_name="V",
        is_super_admin=False,
        businesses=[],
    )

    r = auth_client.post(
        "/api/auth/signup",
        json={"email": "v@x.co", "password": "longenough", "full_name": "V"},
    )
    assert r.status_code == 200
    assert r.json()["session"] is None
    assert "email" in (r.json().get("message") or "").lower()


@patch("app.api.auth.supabase")
def test_signup_weak_password(mock_supa: MagicMock, auth_client: TestClient) -> None:
    from supabase_auth.errors import AuthWeakPasswordError

    mock_supa.auth.sign_up.side_effect = AuthWeakPasswordError("weak", 422, ["too short"])

    r = auth_client.post(
        "/api/auth/signup",
        json={"email": "a@b.co", "password": "short", "full_name": "A"},
    )
    assert r.status_code == 422  # pydantic min_length before hitting supabase
    # Use valid length but still weak for SDK:
    r2 = auth_client.post(
        "/api/auth/signup",
        json={"email": "a@b.co", "password": "12345678", "full_name": "A"},
    )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "weak_password"


@patch("app.api.auth.supabase")
def test_login_invalid_credentials(mock_supa: MagicMock, auth_client: TestClient) -> None:
    from supabase_auth.errors import AuthApiError

    mock_supa.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login", 400, "invalid_credentials"
    )

    r = auth_client.post(
        "/api/auth/login",
        json={"email": "x@y.co", "password": "12345678"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


@patch("app.api.auth.build_user_profile")
@patch("app.api.auth.supabase")
def test_login_success(
    mock_supa: MagicMock, mock_build: MagicMock, auth_client: TestClient
) -> None:
    mock_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000011", email="ok@x.co")
    mock_session = SimpleNamespace(
        access_token="at2",
        refresh_token="rt2",
        expires_in=3600,
        token_type="bearer",
    )
    mock_supa.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=mock_user, session=mock_session
    )
    mock_build.return_value = UserProfile(
        id="00000000-0000-0000-0000-000000000011",
        email="ok@x.co",
        full_name="Ok",
        is_super_admin=False,
        businesses=[],
    )

    r = auth_client.post(
        "/api/auth/login",
        json={"email": "ok@x.co", "password": "12345678"},
    )
    assert r.status_code == 200
    assert r.json()["session"]["access_token"] == "at2"


def test_me_requires_auth(auth_client: TestClient) -> None:
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 401


@patch("app.api.auth.build_user_profile")
def test_me_returns_profile(mock_build: MagicMock, auth_client: TestClient) -> None:
    mock_build.return_value = UserProfile(
        id="00000000-0000-0000-0000-000000000033",
        email="me@x.co",
        full_name="Me",
        is_super_admin=True,
        businesses=[],
    )

    async def _fake_user():
        return SimpleNamespace(
            id="00000000-0000-0000-0000-000000000033",
            email="me@x.co",
        )

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        r = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["email"] == "me@x.co"
    assert r.json()["is_super_admin"] is True
    mock_build.assert_called_once()


@patch("app.api.auth.supabase_admin")
def test_logout_calls_admin_sign_out(mock_admin: MagicMock, auth_client: TestClient) -> None:
    r = auth_client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer jwt-to-revoke"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True
    mock_admin.auth.admin.sign_out.assert_called_once()
    _args, kwargs = mock_admin.auth.admin.sign_out.call_args
    assert kwargs.get("jwt") == "jwt-to-revoke"


def test_logout_missing_header(auth_client: TestClient) -> None:
    r = auth_client.post("/api/auth/logout")
    assert r.status_code == 401
