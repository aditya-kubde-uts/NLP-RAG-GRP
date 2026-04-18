"""Text cleanup utilities before chunking/embedding."""

from __future__ import annotations

import re

_COMMON_PATTERNS = [
    r"[ \t]+\n",  # trailing spaces
    r"\n{3,}",  # excessive blank lines
    r"={4,}",  # divider lines
    r"-{4,}",
    r"_ {0,}_{3,}",
]

_RESTAURANT_PATTERNS = [
    r"\$\s?\d+(?:\.\d{2})?",  # prices like $9.99
    r"\b\d+\.\d{2}\b",  # prices without currency
]

_LEGAL_PATTERNS = [
    r"Page \d+ of \d+",
    r"CONFIDENTIAL",
    r"^\s*\d+\s*$",  # standalone page numbers
]


def clean_text_for_llm(text: str, industry: str | None = None) -> str:
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")

    for pat in _COMMON_PATTERNS:
        out = re.sub(pat, "\n", out, flags=re.MULTILINE)

    normalized = (industry or "").strip().lower()
    if normalized == "restaurant":
        for pat in _RESTAURANT_PATTERNS:
            out = re.sub(pat, " ", out, flags=re.MULTILINE)
    if normalized == "legal":
        for pat in _LEGAL_PATTERNS:
            out = re.sub(pat, " ", out, flags=re.MULTILINE)

    # collapse spaces then normalize newlines
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()

