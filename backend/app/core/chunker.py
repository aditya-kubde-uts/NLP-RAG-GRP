"""Document chunking pipeline + optional LLM summary enrichment."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.core.llm_router import aget_completion

MIN_CHUNK_LENGTH = 50


def _content_hash(source_url: str, chunk: str) -> str:
    payload = f"{source_url}|{chunk}".encode()
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()


async def _summarize_chunk(text: str) -> str:
    prompt = (
        "Summarize this chunk in <=10 words. Return plain text only.\n\n"
        f"Chunk:\n{text[:1500]}"
    )
    try:
        return (await aget_completion(prompt)).strip()[:200]
    except Exception:
        return ""


async def process_document(
    content: str,
    source_url: str,
    *,
    enrich_summary: bool = True,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> list[dict[str, Any]]:
    """Split markdown/text into chunks suitable for pgvector ingestion."""
    if not content.strip():
        return []

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
    )
    docs = header_splitter.split_text(content)

    recursive = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict[str, Any]] = []
    for doc in docs:
        text = getattr(doc, "page_content", "") or ""
        metadata = dict(getattr(doc, "metadata", {}) or {})
        for piece in recursive.split_text(text):
            clean = piece.strip()
            if len(clean) < MIN_CHUNK_LENGTH:
                continue
            chunks.append(
                {
                    "content": clean,
                    "metadata": metadata,
                    "title": metadata.get("h1") or metadata.get("h2"),
                    "content_hash": _content_hash(source_url, clean),
                    "source_url": source_url,
                }
            )

    if enrich_summary and chunks:
        sem = asyncio.Semaphore(8)

        async def enrich(idx: int):
            async with sem:
                chunks[idx]["llm_summary"] = await _summarize_chunk(chunks[idx]["content"])

        await asyncio.gather(*(enrich(i) for i in range(len(chunks))))
    return chunks

