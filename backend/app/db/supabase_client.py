"""Supabase Python clients: anon (RLS) + service role (admin)."""

from __future__ import annotations

import base64
import json

from supabase import Client, create_client

from app.config import get_settings

_settings = get_settings()


def _jwt_role(jwt_token: str) -> str | None:
    parts = jwt_token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
    except Exception:
        return None
    role = data.get("role")
    return role if isinstance(role, str) else None


def _jwt_ref(jwt_token: str) -> str | None:
    parts = jwt_token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
    except Exception:
        return None
    ref = data.get("ref")
    return ref if isinstance(ref, str) else None


service_role = _jwt_role(_settings.supabase_service_role_key)
is_test_stub = _settings.supabase_service_role_key.startswith("test-")
if not is_test_stub and service_role != "service_role":
    raise RuntimeError(
        "SUPABASE_SERVICE_ROLE_KEY is not a service_role key. "
        "Open Supabase Dashboard > Project Settings > API and set backend/.env "
        "SUPABASE_SERVICE_ROLE_KEY to the `service_role` JWT (not `anon`)."
    )

if not is_test_stub:
    key_ref = _jwt_ref(_settings.supabase_service_role_key)
    url_ref = _settings.supabase_url.removeprefix("https://").split(".", 1)[0]
    if key_ref and url_ref and key_ref != url_ref:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY belongs to a different project than SUPABASE_URL. "
            f"Key ref={key_ref}, URL ref={url_ref}. "
            "Use the service_role key from the same Supabase project as SUPABASE_URL."
        )

# Public client — anon key, respects RLS for end-user flows
supabase: Client = create_client(_settings.supabase_url, _settings.supabase_anon_key)

# Service client — bypasses RLS; backend-only
supabase_admin: Client = create_client(
    _settings.supabase_url,
    _settings.supabase_service_role_key,
)
