"""Requirement Quality Score API.

Most tools generate outputs. This route evaluates the requirement itself
and returns the canonical shape

    {
      "quality_score": 68,
      "ambiguity_score": 35,
      "missing_information": [...]
    }

plus a richer breakdown the UI uses.

Endpoints
---------
  POST /api/quality/score              — score raw text, no project required
  POST /api/quality/{project_id}/run   — score the project's stored input,
                                          persist the report, return it
  GET  /api/quality/{project_id}       — the most-recent persisted report
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import QualityScoreReport
from ...services.project_bridge import save_project_to_db
from ...services.quality_scorer import score_requirement_text
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class ScoreTextBody(BaseModel):
    text: str = Field(..., min_length=0, max_length=20000)
    use_ai: bool = True


@router.post("/score", response_model=QualityScoreReport)
async def score_text(
    body: ScoreTextBody,
    _user: User = Depends(get_current_user),
) -> QualityScoreReport:
    """Live score for arbitrary requirement text.

    Used by the editor for type-and-see-score interactions and by external
    callers who want a one-shot evaluation without creating a project.
    """
    return await score_requirement_text(body.text or "", use_ai=body.use_ai)


@router.post("/{project_id}/run", response_model=QualityScoreReport)
async def run_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QualityScoreReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to score.",
        )
    report = await score_requirement_text(text, use_ai=use_ai)
    project.quality_score_report = report
    save_project_to_db(db, row, project)
    db.commit()
    return report


@router.get("/{project_id}", response_model=QualityScoreReport)
def get_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QualityScoreReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.quality_score_report is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Quality score has not been computed yet for this project.",
        )
    return project.quality_score_report


# Re-export Optional so old imports do not break (defensive)
_ = Optional
