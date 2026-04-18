"""Resolve ``DATABASE_URL`` hostnames to ``hostaddr=`` for IPv6-only Supabase hosts (Windows)."""

from __future__ import annotations

import socket

import psycopg.conninfo


def with_resolved_hostaddr(dsn: str) -> str:
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

    ordered = sorted(gai, key=lambda x: 0 if x[0] == socket.AF_INET6 else 1)
    _fam, _type, _proto, _canon, sockaddr = ordered[0]
    opts["hostaddr"] = sockaddr[0]
    return psycopg.conninfo.make_conninfo(**opts)
