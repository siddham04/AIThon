from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    id: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtifactsBundleResponse(BaseModel):
    project_id: str
    stories: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    summary: dict[str, Any] | None = None
    citation_item_rate: float | None = Field(
        default=None,
        description="Fraction of stories+tasks+tests with ≥1 source clause (0–1).",
    )
    last_pipeline_timings_ms: dict[str, int] | None = None


class ApprovalBody(BaseModel):
    approved_for_export: bool
