"""PDF parsing with markdown-first and OCR fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
import pymupdf4llm
import pytesseract
from PIL import Image

from app.core.text_cleaner import clean_text_for_llm
from app.errors import api_error
from app.logging import get_logger

log = get_logger(__name__)


def _ocr_pdf(path: Path) -> str:
    text_parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            mode = "RGB" if pix.alpha == 0 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            text_parts.append(pytesseract.image_to_string(img))
    return "\n\n".join(text_parts)


def parse_pdf(file_path: str | Path, industry: str | None = None) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise api_error(404, code="file_not_found", message=f"PDF not found: {path}")

    raw = ""
    parser = "pymupdf4llm"
    try:
        raw = pymupdf4llm.to_markdown(str(path))
    except Exception as exc:  # pragma: no cover - parser dependency/runtime
        log.warning("pdf_markdown_failed", path=str(path), error=str(exc))
        parser = "ocr"
        try:
            raw = _ocr_pdf(path)
        except Exception as ocr_exc:
            raise api_error(
                400,
                code="pdf_parse_failed",
                message="Could not parse PDF content.",
                details={"reason": str(ocr_exc)},
            ) from ocr_exc

    content = clean_text_for_llm(raw, industry=industry)
    return {
        "content": content,
        "metadata": {
            "source_type": "pdf",
            "file_name": path.name,
            "parser": parser,
        },
    }

