"""Delivery Readiness Center API — Screen 10.

GET  /api/readiness-center/demo              → curated demo checklist (auth required)
GET  /api/readiness-center/{project_id}      → live checklist
POST /api/readiness-center/{project_id}/run  → rebuild + persist
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import DeliveryReadinessCenter
from ...services.delivery_readiness_center import (
    build_demo_readiness_center,
    build_readiness_center,
)
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


@router.get("/demo", response_model=DeliveryReadinessCenter)
def get_demo_center(
    _user: User = Depends(get_current_user),
) -> DeliveryReadinessCenter:
    return build_demo_readiness_center()


@router.get("/{project_id}", response_model=DeliveryReadinessCenter)
async def get_readiness_center(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliveryReadinessCenter:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.delivery_readiness_center is not None:
        return project.delivery_readiness_center
    return await build_readiness_center(project, use_ai=False)


@router.post("/{project_id}/run", response_model=DeliveryReadinessCenter)
async def run_readiness_center(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliveryReadinessCenter:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if not (project.stories or project.raw_input or project.source_clauses):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Run the agent pipeline first — no artifacts to assess.",
        )
    center = await build_readiness_center(project, use_ai=use_ai)
    project.delivery_readiness_center = center
    save_project_to_db(db, row, project)
    db.commit()
    return center


__all__ = ["router"]
