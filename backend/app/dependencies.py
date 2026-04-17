"""FastAPI dependencies: auth and role checks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, Header

from app.db.supabase_client import supabase, supabase_admin
from app.errors import api_error


async def get_current_user(authorization: str | None = Header(None)) -> Any:
    """Validate JWT from Supabase Auth; return the Gotrue user object."""
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(
            401,
            code="missing_authorization",
            message="Missing or invalid Authorization header (expected Bearer token).",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise api_error(401, code="missing_token", message="Bearer token is empty.")

    try:
        user_response = supabase.auth.get_user(token)
    except Exception as exc:
        raise api_error(
            401,
            code="auth_failed",
            message="Authentication failed.",
            details={"reason": str(exc)},
        ) from exc

    if not user_response or not user_response.user:
        raise api_error(401, code="invalid_token", message="Invalid or expired token.")

    return user_response.user


async def require_super_admin(user: Any = Depends(get_current_user)) -> Any:
    """Require ``user_profiles.is_super_admin`` for this user."""
    uid = str(user.id)
    try:
        profile = (
            supabase_admin.table("user_profiles")
            .select("is_super_admin")
            .eq("id", uid)
            .single()
            .execute()
        )
    except Exception as exc:
        raise api_error(
            403,
            code="profile_lookup_failed",
            message="Could not verify admin role.",
            details={"reason": str(exc)},
        ) from exc

    if not profile.data or not profile.data.get("is_super_admin"):
        raise api_error(403, code="forbidden", message="Super admin access required.")

    return user


async def require_business_admin(business_id: UUID, user: Any = Depends(get_current_user)) -> Any:
    """Allow super admins or business ``admin`` / ``super_admin`` members."""
    uid = str(user.id)

    try:
        profile = (
            supabase_admin.table("user_profiles").select("is_super_admin").eq("id", uid).execute()
        )
    except Exception:
        profile = None

    rows = (profile.data or []) if profile else []
    if rows and rows[0].get("is_super_admin"):
        return user

    try:
        member = (
            supabase_admin.table("business_members")
            .select("role")
            .eq("business_id", str(business_id))
            .eq("user_id", uid)
            .execute()
        )
    except Exception as exc:
        raise api_error(
            403,
            code="membership_lookup_failed",
            message="Could not verify business membership.",
            details={"reason": str(exc)},
        ) from exc

    mrows = member.data or []
    role = mrows[0].get("role") if mrows else None
    if role in ("admin", "super_admin"):
        return user

    raise api_error(
        403,
        code="forbidden",
        message="Business admin access required for this resource.",
    )


async def get_optional_user(authorization: str | None = Header(None)) -> Any | None:
    """Return authenticated user or ``None`` (no error if missing/invalid)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user if user_response and user_response.user else None
    except Exception:
        return None
