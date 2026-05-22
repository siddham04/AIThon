"""Requirement-to-Code Impact Analysis API.

POST /api/impact/analyze              — analyze raw text + optional inline catalog
POST /api/impact/{project_id}/analyze — analyze raw text against THIS project's catalog
POST /api/impact/{project_id}/run     — analyze the project's stored requirement,
                                          persist + return
GET  /api/impact/{project_id}         — most-recent persisted report
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import ImpactAnalysisReport
from ...services.impact_analysis import analyze_impact
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class CatalogEntryBody(BaseModel):
    name: str
    layer: str = "service"
    responsibility: str = ""


class AnalyzeBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=8000)
    use_ai: bool = True
    inline_catalog: Optional[List[CatalogEntryBody]] = None


@router.post("/analyze", response_model=ImpactAnalysisReport)
async def analyze_text(
    body: AnalyzeBody,
    _user: User = Depends(get_current_user),
) -> ImpactAnalysisReport:
    """Analyze a requirement against an OPTIONAL inline catalog.

    No project required — useful for one-off / external callers.
    """
    return await analyze_impact(
        body.requirement,
        project=None,
        use_ai=body.use_ai,
    )


@router.post("/{project_id}/analyze", response_model=ImpactAnalysisReport)
async def analyze_for_project(
    project_id: str,
    body: AnalyzeBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImpactAnalysisReport:
    """Analyze ad-hoc requirement text against the project's known catalog
    (Architecture Brief). Does NOT persist."""
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return await analyze_impact(body.requirement, project=project, use_ai=body.use_ai)


@router.post("/{project_id}/run", response_model=ImpactAnalysisReport)
async def run_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImpactAnalysisReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to analyze.",
        )
    report = await analyze_impact(text, project=project, use_ai=use_ai)
    project.impact_report = report
    save_project_to_db(db, row, project)
    db.commit()
    return report


@router.get("/{project_id}", response_model=ImpactAnalysisReport)
def get_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImpactAnalysisReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.impact_report is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Impact analysis has not been run yet for this project.",
        )
    return project.impact_report
