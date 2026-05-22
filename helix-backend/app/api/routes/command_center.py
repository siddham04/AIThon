"""SDLC Command Center API.

GET /api/command-center/{project_id}  — one-screen KPI snapshot
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import CommandCenterSnapshot
from ...services.command_center import build_command_center
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.get("/{project_id}", response_model=CommandCenterSnapshot)
def get_command_center(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommandCenterSnapshot:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return build_command_center(project)
