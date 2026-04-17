"""FastAPI application entry point.

Phase 0 scaffold only. Full implementation lands in Phase 2.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="RAG Factory API",
    description="Multi-tenant RAG platform backend",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Liveness probe. Returns a static healthy payload."""
    return {"status": "healthy", "service": "RAG Factory API"}
