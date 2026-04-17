"""Settings load correctly from environment."""

from __future__ import annotations

import pytest

from app.config import get_settings


def test_get_settings_reads_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/postgres")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/")
    get_settings.cache_clear()
    s = get_settings()
    assert s.supabase_url == "https://x.supabase.co"
    assert s.azure_llm_deployment_name == "gpt-4.1-mini"
