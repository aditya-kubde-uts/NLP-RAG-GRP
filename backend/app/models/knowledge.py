"""Knowledge-base API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class KnowledgeIngestTaskResponse(BaseModel):
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str | None = None
    message: str | None = None


class KnowledgeIngestTaskStatus(BaseModel):
    task_id: str
    business_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str | None = None
    message: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None


class KnowledgeScrapeRequest(BaseModel):
    url: HttpUrl
    enrich_summary: bool = True


class KnowledgeChunkSummary(BaseModel):
    id: str
    title: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: str
    llm_summary: str | None = None
    created_at: datetime


class KnowledgeChunkListResponse(BaseModel):
    items: list[KnowledgeChunkSummary]
    page: int
    page_size: int
    total: int


class KnowledgeChunkUpdateRequest(BaseModel):
    content: str = Field(min_length=1)
    title: str | None = None
    llm_summary: str | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeBatchDeleteRequest(BaseModel):
    source_url: str = Field(min_length=1)


class KnowledgeSourceSummary(BaseModel):
    source_url: str | None = None
    source_type: str | None = None
    title: str | None = None
    chunk_count: int
    latest_chunk_at: datetime | None = None


class KnowledgeStatsResponse(BaseModel):
    total_chunks: int
    by_source_type: dict[str, int]
