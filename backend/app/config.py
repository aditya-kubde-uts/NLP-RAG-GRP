"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic settings — env vars use UPPER_SNAKE names matching `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str = Field(description="https://<ref>.supabase.co")
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-02-01"
    azure_embedding_deployment_name: str = "text-embedding-3-small"
    azure_llm_deployment_name: str = "gpt-4.1-mini"

    # App
    super_admin_email: str = "admin@ragfactory.com"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
