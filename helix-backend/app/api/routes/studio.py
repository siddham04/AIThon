"""AI Studio API — Effort, Risk, and Architecture Diagram for any requirement.

Project-bound endpoints persist the result on the project so judges can
see the artifacts inline; ad-hoc text endpoints return without persistence.

Effort:
  POST /api/studio/effort/analyze              → {requirement, use_ai} → EffortEstimate
  POST /api/studio/effort/{project_id}/run     → use project's raw_input
  GET  /api/studio/effort/{project_id}         → cached
  GET  /api/studio/effort/{project_id}/json    → simple {story_points, complexity, estimated_hours}

Risk:
  POST /api/studio/risk/analyze                → {requirement, use_ai} → RiskPrediction
  POST /api/studio/risk/{project_id}/run
  GET  /api/studio/risk/{project_id}
  GET  /api/studio/risk/{project_id}/json      → simple {risk_level, reasons}

Architecture / Diagram:
  POST /api/studio/architecture/generate       → layer tree + dual Mermaid
  POST /api/studio/diagram/generate            → alias (same payload)
  POST /api/studio/diagram/{project_id}/run
  GET  /api/studio/diagram/{project_id}
  GET  /api/studio/diagram/{project_id}/mermaid → raw text/plain
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import (
    ArchitectureDiagram,
    EffortEstimate,
    RiskPrediction,
)
from ...services.architecture_generator import generate_architecture
from ...services.effort_estimator import estimate_effort, estimate_effort_for_project
from ...services.effort_estimator import to_simple_json as _effort_simple
from ...services.project_bridge import save_project_to_db
from ...services.risk_predictor import predict_risk
from ...services.risk_predictor import to_simple_json as _risk_simple
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class _TextBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=8000)
    use_ai: bool = True


class _DiagramBody(_TextBody):
    title: Optional[str] = None


def _project_text(project) -> str:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text and project.summary:
        text = (project.summary.objective or project.summary.one_liner or "").strip()
    return text


# ---------- Effort ------------------------------------------------------ #


@router.post("/effort/analyze", response_model=EffortEstimate)
async def analyze_effort_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> EffortEstimate:
    return await estimate_effort(body.requirement, use_ai=body.use_ai)


@router.post("/effort/{project_id}/run", response_model=EffortEstimate)
async def run_effort_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EffortEstimate:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to estimate.",
        )
    est = await estimate_effort_for_project(project, use_ai=use_ai)
    project.requirement_estimate = est
    save_project_to_db(db, row, project)
    db.commit()
    return est


@router.get("/effort/{project_id}", response_model=Optional[EffortEstimate])
def get_effort_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[EffortEstimate]:
    # See review_board.get_board for the 200-with-null vs 404 rationale.
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return project.requirement_estimate


@router.get("/effort/{project_id}/json")
def get_effort_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[dict]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.requirement_estimate is None:
        return None
    return _effort_simple(project.requirement_estimate)


# ---------- Risk -------------------------------------------------------- #


@router.post("/risk/analyze", response_model=RiskPrediction)
async def analyze_risk_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> RiskPrediction:
    return await predict_risk(body.requirement, use_ai=body.use_ai)


@router.post("/risk/{project_id}/run", response_model=RiskPrediction)
async def run_risk_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RiskPrediction:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to assess.",
        )
    pred = await predict_risk(text, use_ai=use_ai)
    project.requirement_risk = pred
    save_project_to_db(db, row, project)
    db.commit()
    return pred


@router.get("/risk/{project_id}", response_model=Optional[RiskPrediction])
def get_risk_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[RiskPrediction]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return project.requirement_risk


@router.get("/risk/{project_id}/json")
def get_risk_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[dict]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.requirement_risk is None:
        return None
    return _risk_simple(project.requirement_risk)


# ---------- Diagram ----------------------------------------------------- #


@router.post("/architecture/generate", response_model=ArchitectureDiagram)
async def generate_architecture_text(
    body: _DiagramBody,
    _user: User = Depends(get_current_user),
) -> ArchitectureDiagram:
    return await generate_architecture(
        body.requirement,
        title=body.title or "Architecture",
        use_ai=body.use_ai,
    )


@router.post("/diagram/generate", response_model=ArchitectureDiagram)
async def generate_diagram_text(
    body: _DiagramBody,
    _user: User = Depends(get_current_user),
) -> ArchitectureDiagram:
    """Backward-compatible alias for the Architecture Generator."""
    return await generate_architecture(
        body.requirement,
        title=body.title or "Architecture",
        use_ai=body.use_ai,
    )


@router.post("/diagram/{project_id}/run", response_model=ArchitectureDiagram)
async def run_diagram_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ArchitectureDiagram:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to diagram.",
        )
    title = (
        project.summary.title if project.summary and project.summary.title else project.name
    )
    diagram = await generate_architecture(text, title=title, use_ai=use_ai)
    project.architecture_diagram = diagram
    save_project_to_db(db, row, project)
    db.commit()
    return diagram


@router.get("/diagram/{project_id}", response_model=Optional[ArchitectureDiagram])
def get_diagram_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[ArchitectureDiagram]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return project.architecture_diagram


@router.get("/diagram/{project_id}/mermaid")
def get_diagram_mermaid(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.architecture_diagram is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Architecture diagram has not been generated yet.",
        )
    return Response(
        content=project.architecture_diagram.mermaid,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-architecture-{project.id[:8]}.mmd"'
            )
        },
    )
