"""RAG answer generation pipeline with cache + optional logging."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncGenerator
from typing import Any

import psycopg

from app.config import get_settings
from app.core.llm_router import aget_completion, aget_completion_streaming, count_tokens
from app.core.searcher import search_knowledge_base
from app.db.conninfo import with_resolved_hostaddr


def _qhash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _dsn() -> str:
    return with_resolved_hostaddr(get_settings().database_url)


def _build_prompt(query: str, chunks: list[dict[str, Any]], alerts: list[str]) -> str:
    context_blocks = []
    for idx, ch in enumerate(chunks, start=1):
        src = ch.get("source_url") or "unknown_source"
        context_blocks.append(f"[{idx}] ({src})\n{ch.get('content','')}")
    alert_text = "\n".join(f"- {a}" for a in alerts) if alerts else "None"
    context_text = "\n\n".join(context_blocks)
    return (
        "Use ONLY the provided context to answer. If uncertain, say so.\n\n"
        f"Active alerts:\n{alert_text}\n\n"
        f"Context:\n\n{context_text}\n\n"
        f"User question: {query}\n"
    )


def _load_business_context(cur, business_id: str) -> tuple[str, str, list[str]]:
    cur.execute(
        "SELECT name, settings FROM public.businesses WHERE id = %s::uuid LIMIT 1", (business_id,)
    )
    row = cur.fetchone()
    name = row[0] if row else "Business"
    settings = row[1] if row else {}
    if not isinstance(settings, dict):
        settings = {}
    custom_prompt = str(settings.get("custom_system_prompt") or "")

    cur.execute(
        "SELECT content FROM public.alerts WHERE business_id = %s::uuid AND is_active = TRUE",
        (business_id,),
    )
    alerts = [r[0] for r in cur.fetchall()]
    return name, custom_prompt, alerts


async def generate_rag_response(
    query: str,
    business_id: str,
    *,
    user_id: str | None = None,
    conversation_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Return response + sources + confidence, with cache and optional chat log insert."""
    dsn = _dsn()
    qh = _qhash(query)
    with psycopg.connect(dsn, connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT response_text, sources, confidence
            FROM public.response_cache
            WHERE business_id = %s::uuid
              AND query_hash = %s
              AND expires_at > now()
            LIMIT 1
            """,
            (business_id, qh),
        )
        cached = cur.fetchone()
        if cached:
            cur.execute(
                "UPDATE public.response_cache SET hit_count = hit_count + 1 WHERE business_id=%s::uuid AND query_hash=%s",
                (business_id, qh),
            )
            conn.commit()
            return {
                "answer": cached[0],
                "sources": cached[1] or [],
                "confidence": float(cached[2] or 0),
                "cached": True,
            }

        name, custom_prompt, alerts = _load_business_context(cur, business_id)

    chunks = await search_knowledge_base(query, business_id, match_count=8)
    conf = (
        sum(float(c.get("combined_score", 0.0)) for c in chunks) / len(chunks) if chunks else 0.0
    )
    prompt = _build_prompt(query, chunks, alerts)
    history_text = ""
    if conversation_history:
        last = conversation_history[-5:]
        history_text = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in last)
        prompt = f"Recent conversation:\n{history_text}\n\n{prompt}"
    system_prompt = f"You are the assistant for {name}. {custom_prompt}".strip()

    answer = await aget_completion(prompt, system_prompt=system_prompt)
    sources = [
        {"id": c["id"], "title": c.get("title"), "source_url": c.get("source_url")} for c in chunks[:5]
    ]
    token_count = count_tokens(query) + count_tokens(answer)

    with psycopg.connect(dsn, connect_timeout=30) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.response_cache (business_id, query_hash, query_text, response_text, sources, confidence)
            VALUES (%s::uuid, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (business_id, query_hash)
            DO UPDATE SET response_text = EXCLUDED.response_text,
                          sources = EXCLUDED.sources,
                          confidence = EXCLUDED.confidence,
                          expires_at = now() + interval '24 hours'
            """,
            (business_id, qh, query, answer, json.dumps(sources), conf),
        )

        if conversation_id:
            cur.execute(
                """
                INSERT INTO public.chat_messages
                    (conversation_id, business_id, role, content, confidence, sources, token_count, is_failed)
                VALUES
                    (%s::uuid, %s::uuid, 'assistant', %s, %s, %s::jsonb, %s, FALSE)
                """,
                (conversation_id, business_id, answer, conf, json.dumps(sources), token_count),
            )
        conn.commit()
    return {"answer": answer, "sources": sources, "confidence": conf, "cached": False}


async def generate_rag_response_streaming(
    query: str,
    business_id: str,
    *,
    conversation_history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[str, None]:
    """Token streaming variant (cache write intentionally omitted for MVP)."""
    _ = conversation_history
    chunks = await search_knowledge_base(query, business_id, match_count=8)
    prompt = _build_prompt(query, chunks, [])
    async for token in aget_completion_streaming(prompt):
        yield token

