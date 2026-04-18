"""Insert chunk embeddings into pgvector-backed knowledge store."""

from __future__ import annotations

from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from app.config import get_settings
from app.core.llm_router import aget_embedding
from app.db.conninfo import with_resolved_hostaddr
from app.logging import get_logger

log = get_logger(__name__)


async def ingest_chunks(
    chunks: list[dict[str, Any]],
    business_id: str,
    source_url: str,
    source_type: str,
) -> int:
    """Embed + insert chunks. Returns number of inserted rows."""
    if not chunks:
        return 0

    texts = [c["content"] for c in chunks]
    vectors = await aget_embedding(texts)

    dsn = with_resolved_hostaddr(get_settings().database_url)
    inserted = 0
    sql = """
    INSERT INTO public.knowledge_chunks
        (business_id, content, embedding, title, source_url, source_type, llm_summary, metadata, content_hash)
    SELECT
        %(business_id)s::uuid,
        %(content)s,
        %(embedding)s,
        %(title)s,
        %(source_url)s,
        %(source_type)s,
        %(llm_summary)s,
        %(metadata)s::jsonb,
        %(content_hash)s
    WHERE NOT EXISTS (
        SELECT 1 FROM public.knowledge_chunks
        WHERE business_id = %(business_id)s::uuid AND content_hash = %(content_hash)s
    )
    """
    with psycopg.connect(dsn, connect_timeout=30) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for chunk, vec in zip(chunks, vectors, strict=False):
                cur.execute(
                    sql,
                    {
                        "business_id": business_id,
                        "content": chunk.get("content", ""),
                        "embedding": vec,
                        "title": chunk.get("title"),
                        "source_url": source_url,
                        "source_type": source_type,
                        "llm_summary": chunk.get("llm_summary"),
                        "metadata": chunk.get("metadata") or {},
                        "content_hash": chunk.get("content_hash"),
                    },
                )
                inserted += int(cur.rowcount or 0)
        conn.commit()
    log.info("chunks_ingested", inserted=inserted, total=len(chunks), business_id=business_id)
    return inserted

