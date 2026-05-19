from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class IngestTextBody(BaseModel):
    text: str = Field(min_length=1)
    project_id: str | None = None
    name: str | None = None


class IngestUrlBody(BaseModel):
    url: HttpUrl
    project_id: str | None = None
    name: str | None = None
