"""AI Risk Center API — Screen 8 heat map.

GET  /api/risk-center/demo              → curated demo heat map
GET  /api/risk-center/{project_id}      → project risks as bands
POST /api/risk-center/{project_id}/run  → refresh prediction + rebuild
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import RiskCenterHeatmap
from ...services.project_bridge import save_project_to_db
from ...services.risk_center import build_demo_risk_center, build_risk_center
from ...services.risk_predictor import predict_risk
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


def _project_text(project) -> str:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text and project.summary:
        text = (project.summary.objective or project.summary.one_liner or "").strip()
    return text


@router.get("/demo", response_model=RiskCenterHeatmap)
def get_demo_heatmap() -> RiskCenterHeatmap:
    return build_demo_risk_center()


@router.get("/{project_id}", response_model=RiskCenterHeatmap)
def get_risk_center(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RiskCenterHeatmap:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return build_risk_center(project)


@router.post("/{project_id}/run", response_model=RiskCenterHeatmap)
async def run_risk_center(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RiskCenterHeatmap:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if text:
        project.requirement_risk = await predict_risk(text, use_ai=use_ai)
    elif not (project.risks or []):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text or pipeline risks to assess.",
        )
    heatmap = build_risk_center(project)
    project.risk_center = heatmap
    save_project_to_db(db, row, project)
    db.commit()
    return heatmap


__all__ = ["router"]
