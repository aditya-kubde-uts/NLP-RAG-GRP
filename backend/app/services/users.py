"""User provisioning helpers (admin-scoped)."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Any

from supabase_auth.errors import AuthApiError

from app.db.supabase_client import supabase_admin
from app.errors import api_error
from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class ProvisionedUser:
    user_id: str
    email: str
    was_created: bool
    password: str | None  # only populated on first-time create


_ALREADY_EXISTS_CODES = {
    "email_exists",
    "user_already_exists",
    "email_address_already_exists",
    "phone_exists",
}


def _generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    # Guarantee at least one letter + digit so Supabase length rule always passes
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _find_user_id_by_email(email: str) -> str | None:
    """Look up an existing auth user by email via admin.list_users (paginated)."""
    target = email.strip().lower()
    page = 1
    per_page = 1000
    # Supabase caps list_users pagination, but 5 pages (~5000 users) is enough for us.
    for _ in range(10):
        try:
            users = supabase_admin.auth.admin.list_users(page=page, per_page=per_page)
        except Exception as exc:  # pragma: no cover - network
            log.warning("list_users_failed", error=str(exc), page=page)
            return None
        if not users:
            return None
        for u in users:
            u_email = getattr(u, "email", None) or ""
            if u_email.lower() == target:
                return str(u.id)
        if len(users) < per_page:
            return None
        page += 1
    return None


def create_or_get_admin_user(
    *,
    email: str,
    password: str | None = None,
    full_name: str | None = None,
) -> ProvisionedUser:
    """Create a Supabase auth user (email-confirmed) or return the existing one.

    - Password is only returned when we created the user. If callers supplied a
      password we echo it back; otherwise we generate one and return it once so
      the super admin can share it.
    """
    clean_email = email.strip().lower()
    supplied_password = password
    effective_password = password or _generate_password()
    metadata: dict[str, Any] = {}
    if full_name:
        metadata["full_name"] = full_name

    try:
        resp = supabase_admin.auth.admin.create_user(
            {
                "email": clean_email,
                "password": effective_password,
                "email_confirm": True,
                "user_metadata": metadata,
            }
        )
        if not resp or not resp.user:
            raise api_error(
                500,
                code="provision_failed",
                message="Supabase returned no user on create.",
            )
        return ProvisionedUser(
            user_id=str(resp.user.id),
            email=clean_email,
            was_created=True,
            password=effective_password,
        )
    except AuthApiError as exc:
        code = (exc.code or "").lower()
        msg = (exc.message or "").lower()
        already = (
            code in _ALREADY_EXISTS_CODES or "already registered" in msg or "already exists" in msg
        )
        if not already:
            log.warning("admin_create_user_failed", code=code, message=exc.message)
            raise api_error(
                exc.status if 400 <= exc.status < 600 else 400,
                code=code or "provision_failed",
                message=exc.message,
            ) from exc
        existing = _find_user_id_by_email(clean_email)
        if not existing:
            raise api_error(
                500,
                code="provision_failed",
                message="User already exists but could not be located.",
            ) from exc
        # Do not echo the supplied password for pre-existing accounts —
        # we cannot verify it's correct without authenticating as that user.
        return ProvisionedUser(
            user_id=existing,
            email=clean_email,
            was_created=False,
            password=supplied_password if supplied_password is None else None,
        )
    except Exception as exc:  # pragma: no cover
        log.exception("admin_create_user_unexpected")
        raise api_error(
            500,
            code="provision_failed",
            message="Could not provision admin user.",
            details={"reason": str(exc)},
        ) from exc
