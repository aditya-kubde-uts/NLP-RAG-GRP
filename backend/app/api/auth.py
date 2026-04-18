"""Auth routes: signup, login, profile, logout (Supabase Auth proxy)."""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, Header
from supabase_auth.errors import AuthApiError, AuthError, AuthWeakPasswordError

from app.db.supabase_client import supabase, supabase_admin
from app.dependencies import get_current_user
from app.errors import api_error
from app.logging import get_logger
from app.models.auth import (
    BusinessSummary,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SignupRequest,
    SignupResponse,
    TokenPair,
    UserProfile,
)

log = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _map_auth_api_error(exc: AuthApiError) -> None:
    code = exc.code or "auth_error"
    if code in ("invalid_credentials", "email_not_confirmed"):
        raise api_error(
            401,
            code=str(code),
            message=exc.message,
            details={"supabase_code": code},
        ) from exc
    if code in ("email_exists", "user_already_exists"):
        raise api_error(
            409,
            code="email_exists",
            message=exc.message,
            details={"supabase_code": code},
        ) from exc
    status = exc.status if 400 <= exc.status < 600 else 400
    raise api_error(
        status,
        code=str(code),
        message=exc.message,
        details={"supabase_code": code},
    ) from exc


def build_user_profile(user_id: str, default_email: str | None = None) -> UserProfile:
    """Load ``user_profiles`` row and admin businesses (service role)."""
    try:
        prof_resp = (
            supabase_admin.table("user_profiles")
            .select("id, email, full_name, is_super_admin")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="profile_load_failed",
            message="Could not load user profile.",
            details={"reason": str(exc)},
        ) from exc

    row = cast(dict[str, Any] | None, prof_resp.data)
    if not row:
        row = {
            "id": user_id,
            "email": (default_email or "") or "",
            "full_name": None,
            "is_super_admin": False,
        }

    businesses: list[BusinessSummary] = []
    try:
        members_resp = (
            supabase_admin.table("business_members")
            .select("role, businesses(id, name, slug)")
            .eq("user_id", user_id)
            .in_("role", ("admin", "super_admin"))
            .execute()
        )
        for mrow in members_resp.data or []:
            b = mrow.get("businesses")
            if isinstance(b, list):
                b = b[0] if b else None
            if isinstance(b, dict) and b.get("id"):
                businesses.append(
                    BusinessSummary(
                        id=str(b["id"]),
                        name=str(b.get("name") or ""),
                        slug=str(b.get("slug") or ""),
                        role=str(mrow.get("role") or "admin"),
                    )
                )
    except Exception as exc:
        log.warning("admin_businesses_load_failed", user_id=user_id, error=str(exc))

    return UserProfile(
        id=str(row["id"]),
        email=str(row.get("email") or default_email or ""),
        full_name=row.get("full_name"),
        is_super_admin=bool(row.get("is_super_admin")),
        businesses=businesses,
    )


def _session_tokens(session: Any) -> TokenPair:
    return TokenPair(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=int(session.expires_in),
        token_type=str(session.token_type or "bearer"),
    )


@router.post("/signup", response_model=SignupResponse)
def signup(body: SignupRequest) -> SignupResponse:
    try:
        res = supabase.auth.sign_up(
            {
                "email": str(body.email),
                "password": body.password,
                "options": {"data": {"full_name": body.full_name}},
            }
        )
    except AuthWeakPasswordError as exc:
        raise api_error(
            400,
            code="weak_password",
            message=exc.message,
            details={"reasons": list(exc.reasons)},
        ) from exc
    except AuthApiError as exc:
        _map_auth_api_error(exc)
    except AuthError as exc:
        raise api_error(400, code="auth_error", message=exc.message) from exc
    except Exception as exc:
        log.exception("signup_unexpected")
        raise api_error(
            500,
            code="signup_failed",
            message="Registration failed.",
            details={"reason": str(exc)},
        ) from exc

    if not res.user:
        raise api_error(400, code="signup_failed", message="Could not create user.")

    uid = str(res.user.id)
    profile = build_user_profile(uid, str(body.email))
    session_out = _session_tokens(res.session) if res.session else None
    message: str | None = None
    if not res.session:
        message = "Check your email to confirm your account before signing in."
    return SignupResponse(user=profile, session=session_out, message=message)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": str(body.email), "password": body.password}
        )
    except AuthWeakPasswordError as exc:
        raise api_error(
            400,
            code="weak_password",
            message=exc.message,
            details={"reasons": list(exc.reasons)},
        ) from exc
    except AuthApiError as exc:
        _map_auth_api_error(exc)
    except AuthError as exc:
        raise api_error(400, code="auth_error", message=exc.message) from exc
    except Exception as exc:
        log.exception("login_unexpected")
        raise api_error(
            500,
            code="login_failed",
            message="Login failed.",
            details={"reason": str(exc)},
        ) from exc

    if not res.session or not res.user:
        raise api_error(401, code="no_session", message="Invalid email or password.")

    profile = build_user_profile(str(res.user.id), res.user.email or str(body.email))
    return LoginResponse(session=_session_tokens(res.session), user=profile)


@router.get("/me", response_model=UserProfile)
async def me(user: Any = Depends(get_current_user)) -> UserProfile:
    return build_user_profile(str(user.id), getattr(user, "email", None))


@router.post("/logout", response_model=LogoutResponse)
def logout(authorization: str | None = Header(None)) -> LogoutResponse:
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
        supabase_admin.auth.admin.sign_out(jwt=token, scope="global")
    except AuthApiError as exc:
        if exc.status in (401, 403) or (exc.code and "jwt" in str(exc.code).lower()):
            raise api_error(401, code="invalid_token", message=exc.message) from exc
        log.warning("logout_auth_error", message=exc.message, code=exc.code)
        raise api_error(
            400,
            code="logout_failed",
            message="Could not revoke session.",
            details={"reason": exc.message},
        ) from exc
    except Exception as exc:
        log.warning("logout_failed", error=str(exc))
        raise api_error(
            400,
            code="logout_failed",
            message="Could not revoke session.",
            details={"reason": str(exc)},
        ) from exc

    return LogoutResponse()
