"""Business schemas (STEPS.md Phase 4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Industry = Literal[
    "Education",
    "Restaurant",
    "Healthcare",
    "Retail",
    "Legal",
    "Technology",
    "Other",
]

DEFAULT_BUSINESS_SETTINGS: dict[str, Any] = {
    "user_login_required": False,
    "custom_system_prompt": "",
    "welcome_message": "Hello! How can I help you today?",
    "primary_color": "#6366f1",
    "max_chunks_per_query": 8,
    "confidence_threshold": 0.15,
}


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = None
    industry: Industry
    settings: dict[str, Any] | None = None

    @field_validator("slug")
    @classmethod
    def slug_ascii(cls, v: str) -> str:
        s = v.strip().lower()
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        if not s or any(c not in allowed for c in s):
            raise ValueError("Slug must be lowercase letters, digits, or hyphens only.")
        return s


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    industry: Industry | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None
    is_active: bool | None = None


class BusinessMemberCreate(BaseModel):
    user_id: str
    role: Literal["super_admin", "admin", "viewer"] = "admin"


class BusinessResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    industry: str
    logo_url: str | None
    settings: dict[str, Any]
    is_active: bool
    created_at: datetime
    chunk_count: int = 0
    chat_count: int = 0
    admin_count: int = 0


class PlatformStatsResponse(BaseModel):
    total_businesses: int
    total_users: int
    total_chat_messages: int
    estimated_api_cost_usd: float = 0.0
