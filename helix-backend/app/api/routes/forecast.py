"""Forecast API — Defect Prediction (12) and Delivery Readiness (16).

Defect Prediction:
  POST /api/forecast/defects/analyze            → {requirement, use_ai} → DefectPrediction
  POST /api/forecast/defects/{project_id}/run   → uses project.raw_input
  GET  /api/forecast/defects/{project_id}       → cached
  GET  /api/forecast/defects/{project_id}/json  → simple {high_risk_modules}

Readiness:
  POST /api/forecast/readiness/{project_id}/run → assesses the whole project
  GET  /api/forecast/readiness/{project_id}     → cached
  GET  /api/forecast/readiness/{project_id}/json → simple {readiness, blocking_items}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import DefectPrediction, DeliveryReadiness
from ...services.defect_predictor import predict_defects
from ...services.defect_predictor import to_simple_json as _defect_simple
from ...services.delivery_readiness import assess_readiness
from ...services.delivery_readiness import to_simple_json as _readiness_simple
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class _TextBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=8000)
    use_ai: bool = True


def _project_text(project) -> str:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text and project.summary:
        text = (project.summary.objective or project.summary.one_liner or "").strip()
    return text


# ---------- Defect Prediction ----------------------------------------- #


@router.post("/defects/analyze", response_model=DefectPrediction)
async def analyze_defects_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> DefectPrediction:
    return await predict_defects(body.requirement, use_ai=body.use_ai)


@router.post("/defects/{project_id}/run", response_model=DefectPrediction)
async def run_defects_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DefectPrediction:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to predict defects from.",
        )
    pred = await predict_defects(text, use_ai=use_ai)
    project.defect_prediction = pred
    save_project_to_db(db, row, project)
    db.commit()
    return pred


@router.get("/defects/{project_id}", response_model=DefectPrediction)
def get_defects_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DefectPrediction:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.defect_prediction is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Defect prediction has not been generated yet.",
        )
    return project.defect_prediction


@router.get("/defects/{project_id}/json")
def get_defects_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.defect_prediction is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Defect prediction has not been generated yet.",
        )
    return _defect_simple(project.defect_prediction)


# ---------- Delivery Readiness ---------------------------------------- #


@router.post("/readiness/{project_id}/run", response_model=DeliveryReadiness)
async def run_readiness_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliveryReadiness:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    report = await assess_readiness(project, use_ai=use_ai)
    project.delivery_readiness = report
    save_project_to_db(db, row, project)
    db.commit()
    return report


@router.get("/readiness/{project_id}", response_model=DeliveryReadiness)
def get_readiness_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliveryReadiness:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.delivery_readiness is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Delivery readiness has not been computed yet.",
        )
    return project.delivery_readiness


@router.get("/readiness/{project_id}/json")
def get_readiness_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.delivery_readiness is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Delivery readiness has not been computed yet.",
        )
    return _readiness_simple(project.delivery_readiness)


__all__ = ["router"]
