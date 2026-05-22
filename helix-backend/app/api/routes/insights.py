"""ML-powered project insights endpoint.

`GET /api/insights/{project_id}` returns the full insights bundle produced
by :mod:`app.services.ml_insights` (quality score, IsolationForest task
anomalies, TF-IDF duplicate stories, risk heatmap, burndown forecast).

Query params:
- ``velocity``: float, story points per week (default 20).
- ``duplicate_threshold``: float 0–1, cosine similarity cutoff (default 0.72).
- ``anomaly_top_k``: int, max anomalies to return (default 8).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...services.ml_insights import build_insights
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.get("/{project_id}")
def get_project_insights(
    project_id: str,
    velocity: float = Query(20.0, ge=1.0, le=200.0),
    duplicate_threshold: float = Query(0.72, ge=0.3, le=0.99),
    anomaly_top_k: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return build_insights(
        project,
        velocity_points_per_week=velocity,
        duplicate_threshold=duplicate_threshold,
        anomaly_top_k=anomaly_top_k,
    )
