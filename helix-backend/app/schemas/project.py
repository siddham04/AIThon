from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    raw_text: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    owner_id: int
    created_at: datetime | None = None
    sensitive_hints: list[str] = Field(
        default_factory=list,
        description="Optional ingest-time hints (e.g. email-like patterns).",
    )
