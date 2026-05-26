"""Executive Dashboard API.

GET /api/executive/dashboard                        — org-wide KPIs + AI health center
GET /api/executive/{project_id}/delivery-summary    — one-screen AI delivery manager view
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import DeliverySummary, ExecutiveDashboard
from ...services.delivery_summary import build_delivery_summary
from ...services.executive_dashboard import build_executive_dashboard
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.get("/dashboard", response_model=ExecutiveDashboard)
def get_executive_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveDashboard:
    return build_executive_dashboard(db, user)


@router.get("/{project_id}/delivery-summary", response_model=DeliverySummary)
def get_delivery_summary(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeliverySummary:
    """One-screen 'AI delivery manager' verdict for the project.

    Aggregates every pipeline artifact (requirements, epics, stories,
    tasks, APIs, tests, risks, ambiguities, architecture components,
    sprints) into a single counts-plus-GO/NO-GO response — used by the
    Approve & Export hero panel.
    """
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return build_delivery_summary(project)
