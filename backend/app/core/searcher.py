"""Hybrid knowledge search using Postgres `search_knowledge` function."""

from __future__ import annotations

from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from app.config import get_settings
from app.core.llm_router import aget_completion, aget_embedding
from app.db.conninfo import with_resolved_hostaddr


async def _expand_query(query: str) -> list[str]:
    prompt = (
        "Generate up to 2 alternative search queries for this user query. "
        "Return one query per line, no numbering.\n\n"
        f"Query: {query}"
    )
    try:
        text = (await aget_completion(prompt)).strip()
    except Exception:
        return [query]
    variants = [query]
    for line in text.splitlines():
        v = line.strip("-• \t")
        if v and v.lower() != query.lower():
            variants.append(v)
    return variants[:3]


async def search_knowledge_base(
    query: str,
    business_id: str,
    *,
    match_count: int = 8,
    similarity_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Search business knowledge with hybrid semantic + keyword scoring."""
    variants = await _expand_query(query)
    vectors = await aget_embedding(variants)

    sql = """
    SELECT id, content, title, source_url, source_type, department, llm_summary, metadata,
           similarity, keyword_rank, combined_score
    FROM search_knowledge(
      %(business_id)s::uuid,
      %(query_embedding)s,
      %(query_text)s,
      %(match_count)s,
      %(similarity_threshold)s
    )
    """
    dsn = with_resolved_hostaddr(get_settings().database_url)
    merged: dict[str, dict[str, Any]] = {}
    with psycopg.connect(dsn, connect_timeout=30) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for q, emb in zip(variants, vectors, strict=False):
                cur.execute(
                    sql,
                    {
                        "business_id": business_id,
                        "query_embedding": emb,
                        "query_text": q,
                        "match_count": match_count,
                        "similarity_threshold": similarity_threshold,
                    },
                )
                for row in cur.fetchall():
                    item = {
                        "id": str(row[0]),
                        "content": row[1],
                        "title": row[2],
                        "source_url": row[3],
                        "source_type": row[4],
                        "department": row[5],
                        "llm_summary": row[6],
                        "metadata": row[7] or {},
                        "similarity": float(row[8] or 0),
                        "keyword_rank": float(row[9] or 0),
                        "combined_score": float(row[10] or 0),
                    }
                    prev = merged.get(item["id"])
                    if not prev or item["combined_score"] > prev["combined_score"]:
                        merged[item["id"]] = item
    ranked = sorted(merged.values(), key=lambda x: x["combined_score"], reverse=True)
    return ranked[:match_count]

