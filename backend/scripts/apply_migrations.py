"""Apply SQL files in ../supabase/migrations/ to the hosted Postgres database.

Uses DATABASE_URL from backend/.env (Supabase "Direct connection" URI).

Some networks / libpq builds fail to resolve IPv6-only DB hostnames (no A record).
We resolve the hostname manually and pass hostaddr=… while keeping host=… for TLS SNI.

Usage (from repo root):
    cd backend && uv run python scripts/apply_migrations.py
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import psycopg
import psycopg.conninfo
import sqlparse
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _with_resolved_hostaddr(dsn: str) -> str:
    """If TCP connect info uses a hostname, add hostaddr for IPv6-only Supabase hosts."""
    try:
        opts = psycopg.conninfo.conninfo_to_dict(dsn)
    except Exception:
        return dsn

    host = opts.get("host")
    if not host or host.startswith("/") or host.startswith("@"):  # unix socket
        return dsn
    if opts.get("hostaddr"):
        return dsn

    port = int(opts.get("port") or 5432)
    gai: list[tuple] = []
    for family in (socket.AF_INET6, socket.AF_INET, socket.AF_UNSPEC):
        try:
            gai = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, family=family)
        except OSError:
            continue
        if gai:
            break
    if not gai:
        return dsn

    # Prefer IPv6, then IPv4 (pooler often has both)
    ordered = sorted(gai, key=lambda x: 0 if x[0] == socket.AF_INET6 else 1)
    _fam, _type, _proto, _canon, sockaddr = ordered[0]
    hostaddr = sockaddr[0]
    opts["hostaddr"] = hostaddr
    return psycopg.conninfo.make_conninfo(**opts)


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        print(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env.", file=sys.stderr
        )
        sys.exit(1)

    dsn = _with_resolved_hostaddr(raw)

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
