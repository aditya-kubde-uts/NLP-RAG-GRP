"""Web scraping via Jina Reader endpoint with retries."""

from __future__ import annotations

import random
import time
from typing import Any

import requests

from app.core.text_cleaner import clean_text_for_llm
from app.errors import api_error

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]


def scrape_url(url: str, industry: str | None = None) -> dict[str, Any]:
    target = f"https://r.jina.ai/http://{url.removeprefix('http://').removeprefix('https://')}"
    attempts = 3
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            headers = {"User-Agent": random.choice(_USER_AGENTS)}
            res = requests.get(target, headers=headers, timeout=30)
            res.raise_for_status()
            content = clean_text_for_llm(res.text, industry=industry)
            return {
                "content": content,
                "metadata": {"source_type": "web", "source_url": url, "via": "jina_reader"},
            }
        except Exception as exc:
            last_exc = exc
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise api_error(
        400,
        code="scrape_failed",
        message="Could not scrape URL.",
        details={"reason": str(last_exc)},
    )

