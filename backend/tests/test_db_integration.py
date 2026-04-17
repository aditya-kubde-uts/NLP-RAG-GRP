"""Optional live DB smoke test — requires DATABASE_URL and outbound access to Postgres :5432."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

psycopg = pytest.importorskip("psycopg", reason="psycopg not installed")


@pytest.mark.integration
def test_database_connect_and_pgvector_enabled() -> None:
    if os.environ.get("RUN_LIVE_DB") != "1":
        pytest.skip("Set RUN_LIVE_DB=1 to run live Supabase/Postgres checks")

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL not set")

    with psycopg.connect(dsn, connect_timeout=15) as conn, conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        row = cur.fetchone()
        assert row is not None, "pgvector extension not installed"
