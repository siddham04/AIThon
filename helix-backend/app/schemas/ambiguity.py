from __future__ import annotations

from pydantic import BaseModel, Field


class AmbiguityHit(BaseModel):
    span: str
    score: float = Field(ge=0.0, le=1.0)
    suggestion: str


class AmbiguityAnalyzeResponse(BaseModel):
    items: list[AmbiguityHit]
