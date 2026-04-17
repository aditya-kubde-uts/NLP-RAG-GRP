"""Auth dependency behaviour (mocked Supabase)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.dependencies import get_current_user, get_optional_user


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization=None)
    assert exc.value.status_code == 401
    assert "error" in (exc.value.detail or {})


@pytest.mark.asyncio
async def test_get_current_user_accepts_valid_token() -> None:
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000001"

    mock_resp = MagicMock()
    mock_resp.user = mock_user

    with patch("app.dependencies.supabase") as supa:
        supa.auth.get_user.return_value = mock_resp
        user = await get_current_user(authorization="Bearer good.jwt.token")
        assert user.id == mock_user.id
        supa.auth.get_user.assert_called_once_with("good.jwt.token")


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_when_no_header() -> None:
    assert await get_optional_user(authorization=None) is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_on_bad_token() -> None:
    with patch("app.dependencies.supabase") as supa:
        supa.auth.get_user.side_effect = RuntimeError("network")
        assert await get_optional_user(authorization="Bearer bad") is None
