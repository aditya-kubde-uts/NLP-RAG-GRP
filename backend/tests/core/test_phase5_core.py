from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.chunker import process_document
from app.core.text_cleaner import clean_text_for_llm


def test_clean_text_restaurant_price_removed() -> None:
    out = clean_text_for_llm("Pizza $19.99\nPage 1 of 2", industry="Restaurant")
    assert "$19.99" not in out


@pytest.mark.asyncio
async def test_chunker_produces_hashes() -> None:
    text = "# Header\n\n" + ("This is long enough content. " * 40)
    with patch("app.core.chunker.aget_completion", new=AsyncMock(return_value="summary")):
        chunks = await process_document(text, "https://example.com", enrich_summary=True)
    assert chunks
    assert "content_hash" in chunks[0]
    assert chunks[0]["content_hash"]

