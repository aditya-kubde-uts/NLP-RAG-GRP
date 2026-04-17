"""Supabase Python clients: anon (RLS) + service role (admin)."""

from __future__ import annotations

from supabase import Client, create_client

from app.config import get_settings

_settings = get_settings()

# Public client — anon key, respects RLS for end-user flows
supabase: Client = create_client(_settings.supabase_url, _settings.supabase_anon_key)

# Service client — bypasses RLS; backend-only
supabase_admin: Client = create_client(
    _settings.supabase_url,
    _settings.supabase_service_role_key,
)
