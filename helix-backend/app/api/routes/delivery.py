"""Delivery API — PRD Generator (18), Digital Twin (19), PM Agent (20).

PRD:
  POST /api/delivery/prd/generate                 → {requirement, title?, use_ai?}
  POST /api/delivery/prd/{project_id}/generate    → from project + persist
  GET  /api/delivery/prd/{project_id}             → cached
  GET  /api/delivery/prd/{project_id}/markdown    → raw text/markdown

Digital Twin:
  GET  /api/delivery/twin/{project_id}            → live (build on the fly)
  POST /api/delivery/twin/{project_id}/run        → build + persist

PM:
  POST /api/delivery/pm/{project_id}/run          → forecast + persist
  GET  /api/delivery/pm/{project_id}              → cached
  GET  /api/delivery/pm/{project_id}/json         → simple {timeline, critical_path, release_risk}
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import (
    DigitalTwinReport,
    ProductRequirementsDocument,
    ProjectManagerForecast,
)
from ...services.digital_twin import build_digital_twin
from ...config import get_settings
from ...services.prd_generator import (
    generate_prd,
    generate_prd_for_project,
    to_markdown,
)
from ...services.project_bridge import save_project_to_db
from ...services.project_manager import forecast_project, to_simple_json
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


def _prd_use_ai(requested: bool) -> bool:
    if get_settings().helix_demo_fast:
        return False
    return requested


def _project_requirement_text(project) -> str:
    text = (project.raw_input or "").strip()
    if text:
        return text
    if project.source_clauses:
        return "\n".join(c.text for c in project.source_clauses)
    if project.stories:
        parts = []
        for s in project.stories[:12]:
            parts.append(f"{s.title}: {s.goal or ''}".strip())
        return "\n".join(parts)
    if project.summary and project.summary.objective:
        return project.summary.objective
    return project.name or "Helix project"


# ---------- PRD ------------------------------------------------------- #


class _PRDBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=12000)
    title: Optional[str] = None
    use_ai: bool = True


@router.post("/prd/generate", response_model=ProductRequirementsDocument)
async def generate_prd_text(
    body: _PRDBody,
    _user: User = Depends(get_current_user),
) -> ProductRequirementsDocument:
    return await generate_prd(body.requirement, title=body.title or "", use_ai=body.use_ai)


@router.post("/prd/{project_id}/generate", response_model=ProductRequirementsDocument)
async def generate_prd_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductRequirementsDocument:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    prd = await generate_prd_for_project(project, use_ai=use_ai)
    project.prd_document = prd
    save_project_to_db(db, row, project)
    db.commit()
    return prd


@router.get("/prd/{project_id}", response_model=ProductRequirementsDocument)
async def get_prd(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductRequirementsDocument:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    use_ai = _prd_use_ai(use_ai)
    if project.prd_document is None:
        text = _project_requirement_text(project)
        if not text.strip():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "PRD not available — ingest requirements first.",
            )
        prd = await generate_prd_for_project(project, use_ai=use_ai)
        project.prd_document = prd
        save_project_to_db(db, row, project)
        db.commit()
    return project.prd_document


@router.get("/prd/{project_id}/markdown")
async def get_prd_markdown(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.prd_document is None:
        doc = await get_prd(project_id, use_ai=use_ai, db=db, user=user)
        project.prd_document = doc
    md = to_markdown(project.prd_document)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="PRD-{project_id}.md"',
        },
    )


# ---------- Digital Twin --------------------------------------------- #


@router.get("/twin/{project_id}", response_model=DigitalTwinReport)
def get_twin(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DigitalTwinReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    # Always assemble fresh — this is a derived view, never stale.
    return build_digital_twin(project)


@router.post("/twin/{project_id}/run", response_model=DigitalTwinReport)
def run_twin(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DigitalTwinReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    twin = build_digital_twin(project)
    project.digital_twin = twin
    save_project_to_db(db, row, project)
    db.commit()
    return twin


# ---------- PM Agent ------------------------------------------------- #


@router.post("/pm/{project_id}/run", response_model=ProjectManagerForecast)
async def run_pm(
    project_id: str,
    team_size: int = 4,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectManagerForecast:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    forecast = await forecast_project(project, team_size=team_size, use_ai=use_ai)
    project.pm_forecast = forecast
    save_project_to_db(db, row, project)
    db.commit()
    return forecast


@router.get("/pm/{project_id}", response_model=ProjectManagerForecast)
def get_pm(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectManagerForecast:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.pm_forecast is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PM forecast not generated yet.")
    return project.pm_forecast


@router.get("/pm/{project_id}/json")
def get_pm_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.pm_forecast is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PM forecast not generated yet.")
    return to_simple_json(project.pm_forecast)


__all__ = ["router"]
