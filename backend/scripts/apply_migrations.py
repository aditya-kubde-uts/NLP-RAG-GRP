"""Apply SQL files in ../supabase/migrations/ to the hosted Postgres database.

Uses DATABASE_URL from backend/.env (Supabase "Direct connection" URI).

Some networks / libpq builds fail to resolve IPv6-only DB hostnames (no A record).
We resolve the hostname manually and pass hostaddr=… while keeping host=… for TLS SNI.

Usage (from repo root):
    cd backend && uv run python scripts/apply_migrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import sqlparse
from dotenv import load_dotenv

from app.db.conninfo import with_resolved_hostaddr

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        print(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env.", file=sys.stderr
        )
        sys.exit(1)

    dsn = with_resolved_hostaddr(raw)

    mig_dir = REPO_ROOT / "supabase" / "migrations"
    files = sorted(mig_dir.glob("*.sql"))
    if not files:
        print(f"No SQL files in {mig_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Applying {len(files)} migration file(s) to database...")

    with psycopg.connect(dsn, connect_timeout=60) as conn:
        conn.autocommit = True
        for path in files:
            sql = path.read_text(encoding="utf-8")
            statements = [s.strip() for s in sqlparse.split(sql) if s.strip()]
            print(f"  {path.name} ({len(statements)} statement(s))...")
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)

    print("Done. All migrations applied successfully.")


if __name__ == "__main__":
    main()
