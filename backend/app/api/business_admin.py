"""Business-admin-scoped API.

These routes are for *Business Admins* (the owner of a tenant), not the
platform Super Admin. Access is gated by ``require_business_admin`` which
allows both the super admin and users with a ``business_members`` row
(``role in ('admin', 'super_admin')``) for the given business.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from postgrest.exceptions import APIError

from app.db.supabase_client import supabase_admin
from app.dependencies import get_current_user, require_business_admin
from app.errors import api_error
from app.logging import get_logger
from app.models.business import (
    DEFAULT_BUSINESS_SETTINGS,
    BusinessResponse,
    BusinessUpdate,
)

log = get_logger(__name__)

router = APIRouter(prefix="/api/business", tags=["Business Admin"])

BusinessAdminUser = Annotated[Any, Depends(require_business_admin)]


def _is_super_admin(user_id: str) -> bool:
    try:
        prof = (
            supabase_admin.table("user_profiles")
            .select("is_super_admin")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return False
    rows = getattr(prof, "data", None) or []
    return bool(rows and rows[0].get("is_super_admin"))


def _is_business_member(user_id: str, business_id: str) -> bool:
    try:
        member = (
            supabase_admin.table("business_members")
            .select("role")
            .eq("business_id", business_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return False
    rows = getattr(member, "data", None) or []
    if not rows:
        return False
    role = rows[0].get("role")
    return role in ("admin", "super_admin")


def _row_to_business(row: dict[str, Any]) -> BusinessResponse:
    settings = row.get("settings") or {}
    if not isinstance(settings, dict):
        settings = {}
    created = row.get("created_at")
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    return BusinessResponse(
        id=str(row["id"]),
        name=str(row.get("name") or ""),
        slug=str(row.get("slug") or ""),
        description=row.get("description"),
        industry=str(row.get("industry") or "Other"),
        logo_url=row.get("logo_url"),
        settings=settings,
        is_active=bool(row.get("is_active", True)),
        created_at=created or datetime.now(UTC),
    )


@router.get("/by-slug/{slug}", response_model=BusinessResponse)
def get_business_by_slug(
    slug: str,
    user: Annotated[Any, Depends(get_current_user)],
) -> BusinessResponse:
    """Resolve a business by slug and return its detail.

    Accessible to the platform super admin (for any business) and to members
    of that specific business (``admin`` / ``super_admin`` roles). Unlike the
    ``/{business_id}`` route this lets super admins load the business-admin
    workspace at ``/b/<slug>/admin`` without being a ``business_members`` row.
    """
    try:
        resp = (
            supabase_admin.table("businesses")
            .select(
                "id, name, slug, description, industry, logo_url, settings, is_active, created_at"
            )
            .eq("slug", slug)
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

    rows = getattr(resp, "data", None) or []
    if not rows:
        raise api_error(404, code="not_found", message="Business not found.")

    uid = str(user.id)
    business_id = str(rows[0]["id"])
    if not (_is_super_admin(uid) or _is_business_member(uid, business_id)):
        raise api_error(
            403,
            code="forbidden",
            message="Business admin access required for this resource.",
        )
    return _row_to_business(rows[0])


@router.get("/{business_id}", response_model=BusinessResponse)
def get_business_detail(business_id: UUID, _user: BusinessAdminUser) -> BusinessResponse:
    try:
        resp = (
            supabase_admin.table("businesses")
            .select(
                "id, name, slug, description, industry, logo_url, settings, is_active, created_at"
            )
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

    rows = getattr(resp, "data", None) or []
    if not rows:
        raise api_error(404, code="not_found", message="Business not found.")
    return _row_to_business(rows[0])


@router.put("/{business_id}", response_model=BusinessResponse)
def update_business_settings(
    business_id: UUID,
    body: BusinessUpdate,
    _user: BusinessAdminUser,
) -> BusinessResponse:
    """Business admin update: name/description/industry/logo_url/settings.

    ``is_active`` is intentionally ignored here — only the super admin may
    deactivate a business.
    """
    patch = body.model_dump(exclude_none=True)
    patch.pop("is_active", None)
    if not patch:
        return get_business_detail(business_id, _user)

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

    if "settings" in patch and isinstance(patch["settings"], dict):
        base = erows[0].get("settings") or {}
        if not isinstance(base, dict):
            base = {}
        patch["settings"] = {**DEFAULT_BUSINESS_SETTINGS, **base, **patch["settings"]}

    patch["updated_at"] = datetime.now(UTC).isoformat()

    try:
        supabase_admin.table("businesses").update(patch).eq("id", str(business_id)).execute()
    except APIError as exc:
        log.warning("business_update_failed", error=str(exc))
        raise api_error(
            400,
            code="update_failed",
            message="Could not update business.",
            details={"reason": str(exc)},
        ) from exc
    except Exception as exc:
        raise api_error(
            500,
            code="update_failed",
            message="Could not update business.",
            details={"reason": str(exc)},
        ) from exc

    return get_business_detail(business_id, _user)



@router.get("/{business_id}/chat-logs")
def get_chat_logs(
    business_id: UUID,
    _user: BusinessAdminUser,
    limit: int = 20,
    offset: int = 0,
    role: str | None = None,
    is_failed: bool | None = None,
):
    try:
        query = (
            supabase_admin.table("chat_messages")
            .select("*")
            .eq("business_id", str(business_id))
        )

        if role:
            query = query.eq("role", role)

        if is_failed is not None:
            query = query.eq("is_failed", is_failed)

        resp = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return resp.data

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load chat logs.",
            details={"reason": str(exc)},
        ) from exc


@router.get("/{business_id}/failed-queries")
def get_failed_queries(
    business_id: UUID,
    _user: BusinessAdminUser,
    limit: int = 20,
    offset: int = 0,
):
    try:
        resp = (
            supabase_admin.table("chat_messages")
            .select("*")
            .eq("business_id", str(business_id))
            .eq("is_failed", True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return resp.data

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load failed queries.",
            details={"reason": str(exc)},
        ) from exc

@router.get("/{business_id}/analytics")
def get_business_analytics(
    business_id: UUID,
    _user: BusinessAdminUser,
):
    try:
        resp = (
            supabase_admin.table("chat_messages")
            .select("*")
            .eq("business_id", str(business_id))
            .execute()
        )

        rows = resp.data or []

        total_queries = len(rows)

        failed_queries = len(
            [r for r in rows if r.get("is_failed")]
        )

        confidences = [
            r.get("confidence")
            for r in rows
            if r.get("confidence") is not None
        ]

        avg_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0
        )

        total_tokens = sum(
            r.get("token_count") or 0
            for r in rows
        )

        estimated_cost = total_tokens * 0.000002

        confidence_distribution = {
            "high": len([r for r in rows if (r.get("confidence") or 0) >= 0.8]),
            "medium": len([r for r in rows if 0.5 <= (r.get("confidence") or 0) < 0.8]),
            "low": len([r for r in rows if (r.get("confidence") or 0) < 0.5]),
        }

        query_counts = {}

        for row in rows:
            content = row.get("content")

            if content:
                query_counts[content] = query_counts.get(content, 0) + 1

        top_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "query_volume": total_queries,
            "failed_queries": failed_queries,
            "average_confidence": avg_confidence,
            "confidence_distribution": confidence_distribution,
            "top_queries": top_queries,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
        }

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load analytics.",
            details={"reason": str(exc)},
        ) from exc


@router.get("/{business_id}/alerts")
def get_alerts(
    business_id: UUID,
    _user: BusinessAdminUser,
):
    try:
        resp = (
            supabase_admin.table("alerts")
            .select("*")
            .eq("business_id", str(business_id))
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        return resp.data

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load alerts.",
            details={"reason": str(exc)},
        ) from exc



@router.post("/{business_id}/alerts")
def create_alert(
    business_id: UUID,
    body: dict[str, Any],
    user: BusinessAdminUser,
):
    content = body.get("content")

    if not content:
        raise api_error(
            400,
            code="invalid_request",
            message="Alert content is required.",
        )

    try:
        resp = (
            supabase_admin.table("alerts")
            .insert({
                "business_id": str(business_id),
                "content": content,
                "created_by": str(user.id),
            })
            .execute()
        )

        return resp.data

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not create alert.",
            details={"reason": str(exc)},
        ) from exc


@router.delete("/{business_id}/alerts/{alert_id}")
def delete_alert(
    business_id: UUID,
    alert_id: UUID,
    _user: BusinessAdminUser,
):
    try:
        supabase_admin.table("alerts") \
            .delete() \
            .eq("id", str(alert_id)) \
            .eq("business_id", str(business_id)) \
            .execute()

        return {"success": True}

    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not delete alert.",
            details={"reason": str(exc)},
        ) from exc
