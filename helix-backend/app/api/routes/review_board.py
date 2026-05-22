"""Multi-Agent Requirement Review Board API.

POST /api/review-board/{project_id}/run  → execute all 5 agents in parallel,
                                            persist + return the report.
GET  /api/review-board/{project_id}      → return the most recent report
                                            (404 if the board hasn't run yet).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...agents.review_board import run_review_board
from ...database import get_db
from ...models import ReviewBoardReport
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


@router.post("/{project_id}/run", response_model=ReviewBoardReport)
async def run_board(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewBoardReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if not project.source_clauses:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Add requirement text before running the Review Board.",
        )
    report = await run_review_board(project)
    project.review_board_report = report
    save_project_to_db(db, row, project)
    db.commit()
    return report


@router.get("/{project_id}", response_model=ReviewBoardReport)
def get_board(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewBoardReport:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.review_board_report is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Review Board has not run yet for this project.",
        )
    return project.review_board_report
