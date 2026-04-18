"""Business knowledge-base routes (Phase 6)."""

from __future__ import annotations

import asyncio
import hashlib
import io
import tempfile
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated, Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from pgvector.psycopg import register_vector

from app.core.chunker import process_document
from app.core.ingestor import ingest_chunks
from app.core.llm_router import aget_embedding
from app.core.pdf_parser import parse_pdf
from app.core.scraper import scrape_url
from app.core.text_cleaner import clean_text_for_llm
from app.db.conninfo import with_resolved_hostaddr
from app.db.supabase_client import supabase_admin
from app.dependencies import require_business_admin
from app.errors import api_error
from app.logging import get_logger
from app.models.knowledge import (
    KnowledgeBatchDeleteRequest,
    KnowledgeChunkListResponse,
    KnowledgeChunkSummary,
    KnowledgeChunkUpdateRequest,
    KnowledgeIngestTaskResponse,
    KnowledgeIngestTaskStatus,
    KnowledgeScrapeRequest,
    KnowledgeSourceSummary,
    KnowledgeStatsResponse,
)

log = get_logger(__name__)
router = APIRouter(prefix="/api/business", tags=["Business Knowledge"])
BusinessAdminUser = Annotated[Any, Depends(require_business_admin)]

_task_lock = Lock()
_ingest_tasks: dict[str, KnowledgeIngestTaskStatus] = {}


def _dsn() -> str:
    from app.config import get_settings

    return with_resolved_hostaddr(get_settings().database_url)


def _hash_for_chunk(source_url: str, content: str) -> str:
    payload = f"{source_url}|{content}".encode()
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()


def _set_task(
    task_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    error: str | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    with _task_lock:
        task = _ingest_tasks.get(task_id)
        if not task:
            return
        if status is not None:
            task.status = status  # type: ignore[assignment]
        if stage is not None:
            task.stage = stage
        if message is not None:
            task.message = message
        if error is not None:
            task.error = error
        if result is not None:
            task.result = result
        task.updated_at = datetime.now(UTC)


def _load_business_or_404(business_id: str) -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table("businesses")
            .select("id, slug, industry, is_active")
            .eq("id", business_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise api_error(
            500,
            code="database_error",
            message="Could not load business.",
            details={"reason": str(exc)},
        ) from exc
    rows = getattr(resp, "data", None) or []
    if not rows:
        raise api_error(404, code="not_found", message="Business not found.")
    return rows[0]


def _require_business_active_for_write(business: dict[str, Any]) -> None:
    if business.get("is_active", True):
        return
    raise api_error(
        409,
        code="business_inactive",
        message="This business is inactive; knowledge updates are disabled.",
    )


def _storage_upload_bytes(path: str, data: bytes, content_type: str) -> str | None:
    try:
        supabase_admin.storage.from_("uploads").upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return path
    except Exception as exc:
        # Storage upload failures should not block ingestion.
        log.warning("storage_upload_failed", path=path, error=str(exc))
        return None


async def _ingest_from_text(
    *,
    task_id: str,
    business_id: str,
    source_url: str,
    source_type: str,
    content: str,
    enrich_summary: bool,
) -> None:
    try:
        _set_task(task_id, status="processing", stage="chunking", message="Chunking content")
        chunks = await process_document(content, source_url, enrich_summary=enrich_summary)
        _set_task(
            task_id,
            stage="embedding",
            message="Embedding and ingesting chunks",
        )
        inserted = await ingest_chunks(
            chunks,
            business_id=business_id,
            source_url=source_url,
            source_type=source_type,
        )
        _set_task(
            task_id,
            status="completed",
            stage="done",
            message="Ingestion completed",
            result={"chunks_created": inserted, "chunks_processed": len(chunks)},
        )
    except Exception as exc:
        log.exception("knowledge_ingest_task_failed", task_id=task_id, error=str(exc))
        _set_task(
            task_id,
            status="failed",
            stage="failed",
            error=str(exc),
            message="Ingestion failed",
        )


@router.post(
    "/{business_id}/knowledge/upload",
    response_model=KnowledgeIngestTaskResponse,
    status_code=202,
)
async def upload_knowledge(
    business_id: UUID,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    enrich_summary: Annotated[bool, Form()] = True,
    _user: BusinessAdminUser = None,
) -> KnowledgeIngestTaskResponse:
    _ = _user
    bid = str(business_id)
    business = _load_business_or_404(bid)
    _require_business_active_for_write(business)

    filename = file.filename or "upload"
    source_url = f"upload://{filename}"
    content_type = (file.content_type or "").lower()
    raw = await file.read()
    if not raw:
        raise api_error(400, code="empty_file", message="Uploaded file is empty.")

    now = datetime.now(UTC)
    safe_name = filename.replace("/", "_").replace("\\", "_")
    storage_path = f"{bid}/{int(now.timestamp())}_{safe_name}"
    _storage_upload_bytes(storage_path, raw, content_type or "application/octet-stream")

    if content_type == "application/pdf" or safe_name.lower().endswith(".pdf"):
        from pathlib import Path

        tmp_dir = Path(tempfile.gettempdir()) / "rag_factory_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = tmp_dir / f"{uuid4()}_{safe_name}"
        temp_path.write_bytes(raw)
        parsed = parse_pdf(temp_path, industry=business.get("industry"))
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        content = parsed["content"]
    else:
        text = io.BytesIO(raw).getvalue().decode("utf-8", errors="replace")
        content = clean_text_for_llm(text, industry=business.get("industry"))

    task_id = str(uuid4())
    task = KnowledgeIngestTaskStatus(
        task_id=task_id,
        business_id=bid,
        status="queued",
        stage="queued",
        message="Ingestion queued",
        created_at=now,
        updated_at=now,
    )
    with _task_lock:
        _ingest_tasks[task_id] = task

    background_tasks.add_task(
        asyncio.run,
        _ingest_from_text(
            task_id=task_id,
            business_id=bid,
            source_url=source_url,
            source_type="pdf" if safe_name.lower().endswith(".pdf") else "text",
            content=content,
            enrich_summary=enrich_summary,
        ),
    )
    return KnowledgeIngestTaskResponse(task_id=task_id, status="queued", stage="queued")


@router.post(
    "/{business_id}/knowledge/scrape",
    response_model=KnowledgeIngestTaskResponse,
    status_code=202,
)
async def scrape_knowledge(
    business_id: UUID,
    body: KnowledgeScrapeRequest,
    background_tasks: BackgroundTasks,
    _user: BusinessAdminUser,
) -> KnowledgeIngestTaskResponse:
    _ = _user
    bid = str(business_id)
    business = _load_business_or_404(bid)
    _require_business_active_for_write(business)

    scraped = scrape_url(str(body.url), industry=business.get("industry"))
    content = scraped.get("content") or ""
    source_url = str(body.url)

    task_id = str(uuid4())
    now = datetime.now(UTC)
    with _task_lock:
        _ingest_tasks[task_id] = KnowledgeIngestTaskStatus(
            task_id=task_id,
            business_id=bid,
            status="queued",
            stage="queued",
            message="Ingestion queued",
            created_at=now,
            updated_at=now,
        )

    background_tasks.add_task(
        asyncio.run,
        _ingest_from_text(
            task_id=task_id,
            business_id=bid,
            source_url=source_url,
            source_type="web",
            content=content,
            enrich_summary=body.enrich_summary,
        ),
    )
    return KnowledgeIngestTaskResponse(task_id=task_id, status="queued", stage="queued")


@router.get(
    "/{business_id}/knowledge/tasks/{task_id}",
    response_model=KnowledgeIngestTaskStatus,
)
def get_ingest_task_status(
    business_id: UUID,
    task_id: str,
    _user: BusinessAdminUser,
) -> KnowledgeIngestTaskStatus:
    _ = _user
    with _task_lock:
        task = _ingest_tasks.get(task_id)
    if not task or task.business_id != str(business_id):
        raise api_error(404, code="task_not_found", message="Ingestion task not found.")
    return task


@router.get("/{business_id}/knowledge/chunks", response_model=KnowledgeChunkListResponse)
def list_chunks(
    business_id: UUID,
    _user: BusinessAdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    q: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
) -> KnowledgeChunkListResponse:
    _ = _user
    bid = str(business_id)
    offset = (page - 1) * page_size
    where: list[str] = ["business_id = %(business_id)s::uuid"]
    params: dict[str, Any] = {"business_id": bid, "limit": page_size, "offset": offset}
    if q:
        where.append("(content ILIKE %(q)s OR COALESCE(title, '') ILIKE %(q)s)")
        params["q"] = f"%{q}%"
    if source_type:
        where.append("source_type = %(source_type)s")
        params["source_type"] = source_type
    where_sql = " AND ".join(where)

    sql_total = f"SELECT COUNT(*)::int FROM public.knowledge_chunks WHERE {where_sql}"
    sql_items = f"""
    SELECT id, title, source_url, source_type, metadata, content, llm_summary, created_at
    FROM public.knowledge_chunks
    WHERE {where_sql}
    ORDER BY created_at DESC
    LIMIT %(limit)s OFFSET %(offset)s
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql_total, params)
        total = int(cur.fetchone()[0])
        cur.execute(sql_items, params)
        rows = cur.fetchall()

    items = [
        KnowledgeChunkSummary(
            id=str(row[0]),
            title=row[1],
            source_url=row[2],
            source_type=row[3],
            metadata=row[4] or {},
            content=row[5],
            llm_summary=row[6],
            created_at=row[7],
        )
        for row in rows
    ]
    return KnowledgeChunkListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get(
    "/{business_id}/knowledge/chunks/{chunk_id}",
    response_model=KnowledgeChunkSummary,
)
def get_chunk(
    business_id: UUID,
    chunk_id: UUID,
    _user: BusinessAdminUser,
) -> KnowledgeChunkSummary:
    _ = _user
    sql = """
    SELECT id, title, source_url, source_type, metadata, content, llm_summary, created_at
    FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid AND id = %(chunk_id)s::uuid
    LIMIT 1
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql, {"business_id": str(business_id), "chunk_id": str(chunk_id)})
        row = cur.fetchone()
    if not row:
        raise api_error(404, code="not_found", message="Chunk not found.")
    return KnowledgeChunkSummary(
        id=str(row[0]),
        title=row[1],
        source_url=row[2],
        source_type=row[3],
        metadata=row[4] or {},
        content=row[5],
        llm_summary=row[6],
        created_at=row[7],
    )


@router.put(
    "/{business_id}/knowledge/chunks/{chunk_id}",
    response_model=KnowledgeChunkSummary,
)
async def update_chunk(
    business_id: UUID,
    chunk_id: UUID,
    body: KnowledgeChunkUpdateRequest,
    _user: BusinessAdminUser,
) -> KnowledgeChunkSummary:
    _ = _user
    business = _load_business_or_404(str(business_id))
    _require_business_active_for_write(business)

    sql_get = """
    SELECT source_url, metadata
    FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid AND id = %(chunk_id)s::uuid
    LIMIT 1
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql_get, {"business_id": str(business_id), "chunk_id": str(chunk_id)})
        existing = cur.fetchone()
    if not existing:
        raise api_error(404, code="not_found", message="Chunk not found.")

    source_url = existing[0] or "manual://chunk"
    vector = (await aget_embedding([body.content]))[0]
    content_hash = _hash_for_chunk(source_url, body.content)

    sql_update = """
    UPDATE public.knowledge_chunks
    SET content = %(content)s,
        embedding = %(embedding)s,
        title = %(title)s,
        llm_summary = %(llm_summary)s,
        metadata = %(metadata)s::jsonb,
        content_hash = %(content_hash)s
    WHERE business_id = %(business_id)s::uuid AND id = %(chunk_id)s::uuid
    """
    metadata = body.metadata if body.metadata is not None else (existing[1] or {})
    with psycopg.connect(_dsn(), connect_timeout=30) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                sql_update,
                {
                    "business_id": str(business_id),
                    "chunk_id": str(chunk_id),
                    "content": body.content,
                    "embedding": vector,
                    "title": body.title,
                    "llm_summary": body.llm_summary,
                    "metadata": Jsonb(metadata),
                    "content_hash": content_hash,
                },
            )
        conn.commit()

    return get_chunk(business_id, chunk_id, _user)


@router.delete("/{business_id}/knowledge/chunks/{chunk_id}", status_code=204)
def delete_chunk(
    business_id: UUID,
    chunk_id: UUID,
    _user: BusinessAdminUser,
) -> None:
    _ = _user
    business = _load_business_or_404(str(business_id))
    _require_business_active_for_write(business)

    sql = """
    DELETE FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid AND id = %(chunk_id)s::uuid
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql, {"business_id": str(business_id), "chunk_id": str(chunk_id)})
        count = int(cur.rowcount or 0)
        conn.commit()
    if count == 0:
        raise api_error(404, code="not_found", message="Chunk not found.")


@router.delete("/{business_id}/knowledge/chunks/batch")
def delete_chunks_batch(
    business_id: UUID,
    body: KnowledgeBatchDeleteRequest,
    _user: BusinessAdminUser,
) -> dict[str, int]:
    _ = _user
    business = _load_business_or_404(str(business_id))
    _require_business_active_for_write(business)

    sql = """
    DELETE FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid AND source_url = %(source_url)s
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql, {"business_id": str(business_id), "source_url": body.source_url})
        deleted = int(cur.rowcount or 0)
        conn.commit()
    return {"deleted": deleted}


@router.get(
    "/{business_id}/knowledge/sources",
    response_model=list[KnowledgeSourceSummary],
)
def list_sources(
    business_id: UUID,
    _user: BusinessAdminUser,
) -> list[KnowledgeSourceSummary]:
    _ = _user
    sql = """
    SELECT source_url, source_type, MAX(title) AS title, COUNT(*)::int AS chunk_count, MAX(created_at) AS latest_chunk_at
    FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid
    GROUP BY source_url, source_type
    ORDER BY latest_chunk_at DESC NULLS LAST
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql, {"business_id": str(business_id)})
        rows = cur.fetchall()
    return [
        KnowledgeSourceSummary(
            source_url=row[0],
            source_type=row[1],
            title=row[2],
            chunk_count=int(row[3]),
            latest_chunk_at=row[4],
        )
        for row in rows
    ]


@router.get("/{business_id}/knowledge/stats", response_model=KnowledgeStatsResponse)
def knowledge_stats(
    business_id: UUID,
    _user: BusinessAdminUser,
) -> KnowledgeStatsResponse:
    _ = _user
    bid = str(business_id)
    sql_total = "SELECT COUNT(*)::int FROM public.knowledge_chunks WHERE business_id = %(business_id)s::uuid"
    sql_types = """
    SELECT COALESCE(source_type, 'unknown') AS source_type, COUNT(*)::int AS cnt
    FROM public.knowledge_chunks
    WHERE business_id = %(business_id)s::uuid
    GROUP BY COALESCE(source_type, 'unknown')
    """
    with psycopg.connect(_dsn(), connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(sql_total, {"business_id": bid})
        total = int(cur.fetchone()[0])
        cur.execute(sql_types, {"business_id": bid})
        rows = cur.fetchall()
    return KnowledgeStatsResponse(total_chunks=total, by_source_type={str(k): int(v) for k, v in rows})
