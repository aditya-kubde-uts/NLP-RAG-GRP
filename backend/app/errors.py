"""Structured API error payloads (STEPS.md: no bare exceptions on the wire)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def api_error(
    status_code: int,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """Return an HTTPException whose JSON body is ``{ \"error\": { ... } }``."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        body["error"]["details"] = details
    return HTTPException(status_code=status_code, detail=body)
