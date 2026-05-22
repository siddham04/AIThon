"""Executive Dashboard API.

GET /api/executive/dashboard — org-wide KPIs + AI health center
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import ExecutiveDashboard
from ...services.executive_dashboard import build_executive_dashboard
from ...sqla_models import User
from ..deps import get_current_user

router = APIRouter()


@router.get("/dashboard", response_model=ExecutiveDashboard)
def get_executive_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveDashboard:
    return build_executive_dashboard(db, user)
