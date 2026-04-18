"""Super-admin API: platform businesses and stats."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends
from postgrest.exceptions import APIError

from app.config import get_settings
from app.db.conninfo import with_resolved_hostaddr
from app.db.supabase_client import supabase_admin
from app.dependencies import require_super_admin
from app.errors import api_error
from app.logging import get_logger
from app.models.business import (
    DEFAULT_BUSINESS_SETTINGS,
    AdminCredentials,
    BusinessAdminInvite,
    BusinessAdminSummary,
    BusinessCreate,
    BusinessCreateResponse,
    BusinessMemberCreate,
    BusinessResponse,
    BusinessUpdate,
    PlatformStatsResponse,
)
from app.services.users import create_or_get_admin_user

log = get_logger(__name__)

SuperAdmin = Annotated[Any, Depends(require_super_admin)]

router = APIRouter(
    prefix="/api/super-admin",
    tags=["Super Admin"],
)


def _pg_dsn() -> str:
    return with_resolved_hostaddr(get_settings().database_url)


def _row_to_business(row: tuple[Any, ...], keys: list[str]) -> BusinessResponse:
    d = dict(zip(keys, row, strict=True))
    settings = d.get("settings") or {}
    if not isinstance(settings, dict):
        settings = dict(settings) if hasattr(settings, "keys") else {}
    created = d["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    return BusinessResponse(
        id=str(d["id"]),
        name=str(d["name"]),
        slug=str(d["slug"]),
        description=d.get("description"),
        industry=str(d.get("industry") or "Other"),
        logo_url=d.get("logo_url"),
        settings=settings,
        is_active=bool(d.get("is_active", True)),
        created_at=created,
        chunk_count=int(d.get("chunk_count") or 0),
        chat_count=int(d.get("chat_count") or 0),
        admin_count=int(d.get("admin_count") or 0),
    )


_BUSINESS_SELECT_SQL = """
SELECT b.id, b.name, b.slug, b.description, b.industry, b.logo_url, b.settings, b.is_active, b.created_at,
  COALESCE(c.cnt, 0)::int AS chunk_count,
  COALESCE(m.cnt, 0)::int AS chat_count,
  COALESCE(a.cnt, 0)::int AS admin_count
FROM public.businesses b
LEFT JOIN (
  SELECT business_id, COUNT(*)::bigint AS cnt
  FROM public.knowledge_chunks
  GROUP BY business_id
) c ON c.business_id = b.id
LEFT JOIN (
  SELECT business_id, COUNT(*)::bigint AS cnt
  FROM public.chat_messages
  GROUP BY business_id
) m ON m.business_id = b.id
LEFT JOIN (
  SELECT business_id, COUNT(*)::bigint AS cnt
  FROM public.business_members
  WHERE role IN ('admin', 'super_admin')
  GROUP BY business_id
) a ON a.business_id = b.id
"""


@router.get("/businesses", response_model=list[BusinessResponse])
def list_businesses(_user: SuperAdmin) -> list[BusinessResponse]:
    keys = [
        "id",
        "name",
        "slug",
        "description",
        "industry",
        "logo_url",
        "settings",
        "is_active",
        "created_at",
        "chunk_count",
        "chat_count",
        "admin_count",
    ]
    sql = _BUSINESS_SELECT_SQL + " ORDER BY b.created_at DESC;"
    try:
        with psycopg.connect(_pg_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception as exc:
        log.warning("list_businesses_failed", error=str(exc))
        raise api_error(
            500,
            code="database_error",
            message="Could not load businesses.",
            details={"reason": str(exc)},
        ) from exc
    return [_row_to_business(r, keys) for r in rows]


@router.get("/businesses/{business_id}", response_model=BusinessResponse)
def get_business(business_id: UUID, _user: SuperAdmin) -> BusinessResponse:
    keys = [
        "id",
        "name",
        "slug",
        "description",
        "industry",
        "logo_url",
        "settings",
        "is_active",
        "created_at",
        "chunk_count",
        "chat_count",
        "admin_count",
    ]
    sql = _BUSINESS_SELECT_SQL + " WHERE b.id = %s;"
    try:
        with psycopg.connect(_pg_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
            cur.execute(sql, (str(business_id),))
            row = cur.fetchone()
    except Exception as exc:
        log.warning("get_business_failed", error=str(exc))
        raise api_error(
            500,
            code="database_error",
            message="Could not load business.",
            details={"reason": str(exc)},
        ) from exc
    if not row:
        raise api_error(404, code="not_found", message="Business not found.")
    return _row_to_business(row, keys)


@router.post("/businesses", response_model=BusinessCreateResponse, status_code=201)
def create_business(body: BusinessCreate, user: SuperAdmin) -> BusinessCreateResponse:
    """Create a business.

    If ``admin_email`` is provided the new business is assigned to that user
    (creating the auth account when needed). The calling super admin is NOT
    auto-added as a member — super admins already have platform-wide access.
    """

    admin_user_id: str = str(user.id)
    admin_payload: AdminCredentials | None = None
    if body.admin_email:
        provisioned = create_or_get_admin_user(
            email=str(body.admin_email),
            password=body.admin_password,
            full_name=body.admin_full_name,
        )
        admin_user_id = provisioned.user_id
        admin_payload = AdminCredentials(
            email=provisioned.email,
            password=provisioned.password,
            was_created=provisioned.was_created,
        )

    merged_settings = {**DEFAULT_BUSINESS_SETTINGS, **(body.settings or {})}
    payload: dict[str, Any] = {
        "name": body.name.strip(),
        "slug": body.slug,
        "description": body.description,
        "industry": body.industry,
        "owner_id": admin_user_id,
        "settings": merged_settings,
    }
    try:
        ins = supabase_admin.table("businesses").insert(payload).execute()
    except APIError as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise api_error(
                409,
                code="slug_exists",
                message="A business with this slug already exists.",
            ) from exc
        log.warning("create_business_api_error", error=str(exc))
        raise api_error(
            400,
            code="create_failed",
            message="Could not create business.",
            details={"reason": str(exc)},
        ) from exc
    except Exception as exc:
        log.warning("create_business_failed", error=str(exc))
        raise api_error(
            500,
            code="create_failed",
            message="Could not create business.",
            details={"reason": str(exc)},
        ) from exc

    rows = getattr(ins, "data", None) or []
    if not rows:
        raise api_error(500, code="create_failed", message="Business insert returned no row.")
    new_id = rows[0]["id"]
    try:
        supabase_admin.table("business_members").insert(
            {
                "business_id": new_id,
                "user_id": admin_user_id,
                "role": "admin",
            }
        ).execute()
    except APIError as exc:
        # If user is already a member of this business (edge case when re-using
        # an existing auth user), that's fine.
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            pass
        else:
            log.exception("business_member_insert_failed", business_id=new_id)
            raise api_error(
                500,
                code="member_create_failed",
                message="Business was created but assigning the admin failed.",
                details={"reason": str(exc)},
            ) from exc
    except Exception as exc:
        log.exception("business_member_insert_failed", business_id=new_id)
        raise api_error(
            500,
            code="member_create_failed",
            message="Business was created but assigning the admin failed.",
            details={"reason": str(exc)},
        ) from exc

    base = get_business(UUID(str(new_id)), user)
    return BusinessCreateResponse(**base.model_dump(), admin=admin_payload)


@router.put("/businesses/{business_id}", response_model=BusinessResponse)
def update_business(business_id: UUID, body: BusinessUpdate, user: SuperAdmin) -> BusinessResponse:
    _ = user
    try:
        existing = (
            supabase_admin.table("businesses")
            .select("id, settings")
            .eq("id", str(business_id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load business.",
            details={"reason": str(exc)},
        ) from exc

    erows = getattr(existing, "data", None) or []
    if not erows:
        raise api_error(404, code="not_found", message="Business not found.")

    patch = body.model_dump(exclude_none=True)
    if not patch:
        return get_business(business_id, user)

    if "settings" in patch and isinstance(patch["settings"], dict):
        base = erows[0].get("settings") or {}
        if not isinstance(base, dict):
            base = {}
        patch["settings"] = {**DEFAULT_BUSINESS_SETTINGS, **base, **patch["settings"]}

    patch["updated_at"] = datetime.now(UTC).isoformat()

    try:
        supabase_admin.table("businesses").update(patch).eq("id", str(business_id)).execute()
    except APIError as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg:
            raise api_error(409, code="slug_exists", message="Slug conflict.") from exc
        raise api_error(
            400,
            code="update_failed",
            message="Could not update business.",
            details={"reason": str(exc)},
        ) from exc
    except Exception as exc:
        log.warning("update_business_failed", error=str(exc))
        raise api_error(
            500,
            code="update_failed",
            message="Could not update business.",
            details={"reason": str(exc)},
        ) from exc

    return get_business(business_id, user)


@router.delete("/businesses/{business_id}", status_code=204)
def soft_delete_business(business_id: UUID, user: SuperAdmin) -> None:
    _ = user
    try:
        res = (
            supabase_admin.table("businesses")
            .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", str(business_id))
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="delete_failed",
            message="Could not deactivate business.",
            details={"reason": str(exc)},
        ) from exc
    rows = getattr(res, "data", None) or []
    if not rows:
        raise api_error(404, code="not_found", message="Business not found.")


@router.get("/stats", response_model=PlatformStatsResponse)
def platform_stats(_user: SuperAdmin) -> PlatformStatsResponse:
    sql = """
    SELECT
      (SELECT COUNT(*)::bigint FROM public.businesses) AS total_businesses,
      (SELECT COUNT(*)::bigint FROM public.user_profiles) AS total_users,
      (SELECT COUNT(*)::bigint FROM public.chat_messages) AS total_chat_messages;
    """
    try:
        with psycopg.connect(_pg_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
    except Exception as exc:
        log.warning("platform_stats_failed", error=str(exc))
        raise api_error(
            500,
            code="database_error",
            message="Could not load platform stats.",
            details={"reason": str(exc)},
        ) from exc
    if not row:
        return PlatformStatsResponse(total_businesses=0, total_users=0, total_chat_messages=0)
    return PlatformStatsResponse(
        total_businesses=int(row[0]),
        total_users=int(row[1]),
        total_chat_messages=int(row[2]),
        estimated_api_cost_usd=0.0,
    )


@router.get(
    "/businesses/{business_id}/admins",
    response_model=list[BusinessAdminSummary],
)
def list_business_admins(business_id: UUID, _user: SuperAdmin) -> list[BusinessAdminSummary]:
    """List admins/super_admins of a business with their profile info."""
    sql = """
    SELECT m.user_id, m.role, m.created_at,
           up.email, up.full_name
    FROM public.business_members m
    LEFT JOIN public.user_profiles up ON up.id = m.user_id
    WHERE m.business_id = %s
    ORDER BY m.created_at ASC;
    """
    try:
        with psycopg.connect(_pg_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
            cur.execute(sql, (str(business_id),))
            rows = cur.fetchall()
    except Exception as exc:
        log.warning("list_business_admins_failed", error=str(exc))
        raise api_error(
            500,
            code="database_error",
            message="Could not load business admins.",
            details={"reason": str(exc)},
        ) from exc
    result: list[BusinessAdminSummary] = []
    for uid, role, created_at, email, full_name in rows:
        result.append(
            BusinessAdminSummary(
                user_id=str(uid),
                role=str(role or "admin"),
                created_at=created_at,
                email=email,
                full_name=full_name,
            )
        )
    return result


@router.post(
    "/businesses/{business_id}/admins",
    status_code=201,
    response_model=AdminCredentials,
)
def invite_business_admin(
    business_id: UUID,
    body: BusinessAdminInvite,
    _user: SuperAdmin,
) -> AdminCredentials:
    """Invite (or attach) a Business Admin by email.

    Creates the auth user when needed (email auto-confirmed) and upserts a
    ``business_members`` row for the given business.
    """
    # Ensure the business exists
    try:
        biz = (
            supabase_admin.table("businesses")
            .select("id")
            .eq("id", str(business_id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load business.",
            details={"reason": str(exc)},
        ) from exc
    if not (getattr(biz, "data", None) or []):
        raise api_error(404, code="not_found", message="Business not found.")

    provisioned = create_or_get_admin_user(
        email=str(body.email),
        password=body.password,
        full_name=body.full_name,
    )

    try:
        supabase_admin.table("business_members").insert(
            {
                "business_id": str(business_id),
                "user_id": provisioned.user_id,
                "role": body.role,
            }
        ).execute()
    except APIError as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise api_error(
                409,
                code="already_member",
                message="This user is already a member of the business.",
            ) from exc
        raise api_error(
            400,
            code="member_add_failed",
            message="Could not add admin.",
            details={"reason": str(exc)},
        ) from exc
    except Exception as exc:
        raise api_error(
            500,
            code="member_add_failed",
            message="Could not add admin.",
            details={"reason": str(exc)},
        ) from exc

    return AdminCredentials(
        email=provisioned.email,
        password=provisioned.password,
        was_created=provisioned.was_created,
    )


@router.post("/businesses/{business_id}/members", status_code=201)
def add_business_member(
    business_id: UUID,
    body: BusinessMemberCreate,
    user: SuperAdmin,
) -> dict[str, str]:
    """Legacy: attach an existing user (by ``user_id``) to a business."""
    _ = user
    try:
        prof = (
            supabase_admin.table("user_profiles")
            .select("id")
            .eq("id", body.user_id.strip())
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not verify user.",
            details={"reason": str(exc)},
        ) from exc
    if not (getattr(prof, "data", None) or []):
        raise api_error(
            404, code="user_not_found", message="No user profile exists for this user_id."
        )

    try:
        supabase_admin.table("business_members").insert(
            {
                "business_id": str(business_id),
                "user_id": body.user_id.strip(),
                "role": body.role,
            }
        ).execute()
    except APIError as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise api_error(
                409,
                code="already_member",
                message="User is already a member of this business.",
            ) from exc
        raise api_error(
            400,
            code="member_add_failed",
            message="Could not add member.",
            details={"reason": str(exc)},
        ) from exc
    except Exception as exc:
        raise api_error(
            500,
            code="member_add_failed",
            message="Could not add member.",
            details={"reason": str(exc)},
        ) from exc
    return {"status": "created", "business_id": str(business_id), "user_id": body.user_id.strip()}


@router.delete("/businesses/{business_id}/members/{user_id}", status_code=204)
def remove_business_member(business_id: UUID, user_id: UUID, admin: SuperAdmin) -> None:
    _ = admin
    try:
        res = (
            supabase_admin.table("business_members")
            .delete()
            .eq("business_id", str(business_id))
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="member_remove_failed",
            message="Could not remove member.",
            details={"reason": str(exc)},
        ) from exc
    rows = getattr(res, "data", None) or []
    if not rows:
        raise api_error(404, code="not_found", message="Membership not found.")
