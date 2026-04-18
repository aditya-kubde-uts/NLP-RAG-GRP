"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.business_admin import router as business_admin_router
from app.api.knowledge import router as knowledge_router
from app.api.super_admin import router as super_admin_router
from app.config import get_settings
from app.errors import api_error
from app.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: logging + ensure DB / Supabase modules import cleanly."""
    settings = get_settings()
    configure_logging(settings.log_level)
    # Import side effect: create Supabase clients (fail fast if misconfigured)
    from app.db import supabase_client  # noqa: F401

    log.info("startup_complete", service="RAG Factory API")
    yield
    log.info("shutdown")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id for correlation (structlog context can be added later)."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="RAG Factory API",
        description="Multi-tenant RAG platform backend",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail),
                }
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    @application.get("/api/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "RAG Factory API"}

    @application.get("/api/health/db", tags=["Health"])
    async def health_db() -> dict[str, Any]:
        """Cheap DB connectivity check (``SELECT 1`` via ``DATABASE_URL``)."""
        try:
            with (
                psycopg.connect(settings.database_url, connect_timeout=5) as conn,
                conn.cursor() as cur,
            ):
                cur.execute("SELECT 1")
                cur.fetchone()
            return {"status": "healthy", "database": "reachable"}
        except Exception as exc:
            log.warning("health_db_failed", error=str(exc))
            raise api_error(
                503,
                code="database_unreachable",
                message="Cannot reach Postgres with DATABASE_URL.",
                details={"reason": str(exc)},
            ) from exc

    application.include_router(auth_router)
    application.include_router(super_admin_router)
    application.include_router(business_admin_router)
    application.include_router(knowledge_router)

    return application


app = create_app()
