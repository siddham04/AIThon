"""Requirement Version Diff API.

The diff is fully stateless — the frontend sends two text versions
(typically pulled from `requirement-versions`) and gets back a
structured diff with added / removed / changed sentences plus an
AI-authored summary of what materially changed.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...models import RequirementDiffReport
from ...services.requirement_diff import compute_requirement_diff
from ...sqla_models import User
from ..deps import get_current_user


router = APIRouter()


class _DiffBody(BaseModel):
    version_a: str = Field(..., min_length=1, max_length=20000)
    version_b: str = Field(..., min_length=1, max_length=20000)
    title_a: Optional[str] = None
    title_b: Optional[str] = None
    use_ai: bool = True


@router.post("/compare", response_model=RequirementDiffReport)
async def compare_text(
    body: _DiffBody,
    _user: User = Depends(get_current_user),
) -> RequirementDiffReport:
    return await compute_requirement_diff(
        body.version_a,
        body.version_b,
        title_a=body.title_a or "Version A",
        title_b=body.title_b or "Version B",
        use_ai=body.use_ai,
    )


__all__ = ["router"]
