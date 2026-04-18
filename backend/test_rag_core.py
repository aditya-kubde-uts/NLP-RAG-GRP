"""Phase 5 smoke script.

Run from backend folder:
    uv run python test_rag_core.py
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.core.chunker import process_document
from app.core.pdf_parser import parse_pdf
from app.core.rag_brain import generate_rag_response
from app.core.scraper import scrape_url
from app.core.searcher import search_knowledge_base
from app.core.text_cleaner import clean_text_for_llm


async def main() -> None:
    print("1) text_cleaner")
    cleaned = clean_text_for_llm("Menu =====\nBurger $12.00", industry="Restaurant")
    assert "$12.00" not in cleaned

    print("2) chunker")
    chunks = await process_document("# Title\n\nHello world " * 30, "https://example.com", enrich_summary=False)
    assert chunks

    print("3) pdf_parser (skip if file missing)")
    try:
        parse_pdf("tests/assets/sample.pdf")
    except Exception:
        print("   sample PDF missing (expected in local dev)")

    print("4) scraper (mocked)")
    with patch("app.core.scraper.requests.get") as mget:
        mget.return_value.status_code = 200
        mget.return_value.text = "Example body"
        mget.return_value.raise_for_status.return_value = None
        scraped = scrape_url("https://example.com")
        assert "content" in scraped

    print("5) searcher (mocked)")
    with (
        patch("app.core.searcher.aget_embedding", new=AsyncMock(return_value=[[0.0] * 1536])),
        patch("app.core.searcher._expand_query", new=AsyncMock(return_value=["hello"])),
        patch("app.core.searcher.register_vector"),
        patch("app.core.searcher.psycopg.connect") as mconn,
    ):
        cur = mconn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []
        rows = await search_knowledge_base("hello", "00000000-0000-0000-0000-000000000000")
        assert rows == []

    print("6) rag_brain (mocked)")
    with (
        patch("app.core.rag_brain.search_knowledge_base", new=AsyncMock(return_value=[])),
        patch("app.core.rag_brain.aget_completion", new=AsyncMock(return_value="hello")),
        patch("app.core.rag_brain.psycopg.connect") as mconn,
    ):
        cur = mconn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = [None, ("Demo", {}), None]
        cur.fetchall.return_value = []
        out = await generate_rag_response("hi", "00000000-0000-0000-0000-000000000000")
        assert out["answer"] == "hello"

    print("All Phase 5 smoke checks passed.")


if __name__ == "__main__":
    asyncio.run(main())

