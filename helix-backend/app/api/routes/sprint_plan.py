"""Sprint Planning API.

Auto Sprint Planning (from raw requirement):
  POST /api/sprint-plan/auto                   — task table + suggested sprint
  POST /api/sprint-plan/{project_id}/auto      — same, persisted on project

Interactive story-level planning (needs stories on project):
  POST /api/sprint-plan/{project_id}/plan
  GET  /api/sprint-plan/{project_id}
  GET  /api/sprint-plan/{project_id}/markdown
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import AutoSprintPlan, SprintKanbanBoard, TeamSprintPlan
from ...services.auto_sprint_planner import plan_sprint_from_requirement
from ...services.project_bridge import save_project_to_db
from ...services.sprint_kanban_board import (
    build_auth_demo_kanban,
    build_kanban_from_auto_plan,
    build_kanban_from_requirement,
)
from ...services.team_sprint_planner import plan_team_sprints, to_markdown
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class AutoPlanBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=20000)
    team_size: int = Field(6, ge=1, le=50)
    sprint_weeks: float = Field(2.0, ge=0.5, le=8.0)
    points_per_engineer: float = Field(6.0, ge=1.0, le=15.0)
    use_ai: bool = True


@router.post("/auto", response_model=AutoSprintPlan)
async def auto_plan_text(
    body: AutoPlanBody,
    _user: User = Depends(get_current_user),
) -> AutoSprintPlan:
    """Auto Sprint Planning from requirement text (authenticated)."""
    return await plan_sprint_from_requirement(
        body.requirement,
        team_size=body.team_size,
        sprint_weeks=body.sprint_weeks,
        points_per_engineer=body.points_per_engineer,
        use_ai=body.use_ai,
    )


@router.post("/{project_id}/auto", response_model=AutoSprintPlan)
async def auto_plan_for_project(
    project_id: str,
    body: AutoPlanBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutoSprintPlan:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = (body.requirement or project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No requirement text to plan.")
    plan = await plan_sprint_from_requirement(
        text,
        team_size=body.team_size,
        sprint_weeks=body.sprint_weeks,
        points_per_engineer=body.points_per_engineer,
        use_ai=body.use_ai,
    )
    project.auto_sprint_plan = plan
    save_project_to_db(db, row, project)
    db.commit()
    return plan


@router.get("/{project_id}/auto", response_model=Optional[AutoSprintPlan])
def get_auto_plan_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[AutoSprintPlan]:
    # 200-with-null when the project exists but no plan has been
    # generated yet. The workspace UI fetches this on every page load;
    # returning 404 here floods the browser console with red errors
    # even though the empty-state UI is correct. (Project-missing /
    # not-owned still 404s via get_owned_project_row.)
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return project.auto_sprint_plan


class PlanBody(BaseModel):
    team_size: int = Field(6, ge=1, le=50)
    sprint_weeks: float = Field(2.0, ge=0.5, le=8.0)
    points_per_engineer: float = Field(6.0, ge=1.0, le=15.0)
    use_ai: bool = True


@router.post("/{project_id}/plan", response_model=TeamSprintPlan)
async def plan_for_project(
    project_id: str,
    body: PlanBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamSprintPlan:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if not project.stories:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Generate stories first (run the SDLC pipeline) before planning sprints.",
        )
    plan = await plan_team_sprints(
        project,
        team_size=body.team_size,
        sprint_weeks=body.sprint_weeks,
        points_per_engineer=body.points_per_engineer,
        use_ai=body.use_ai,
    )
    project.team_sprint_plan = plan
    save_project_to_db(db, row, project)
    db.commit()
    return plan


@router.get("/{project_id}", response_model=Optional[TeamSprintPlan])
def get_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[TeamSprintPlan]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return project.team_sprint_plan


@router.post("/kanban/generate", response_model=SprintKanbanBoard)
async def generate_kanban_text(
    body: AutoPlanBody,
    _user: User = Depends(get_current_user),
) -> SprintKanbanBoard:
    """Build multi-sprint Kanban from requirement text (no project)."""
    return await build_kanban_from_requirement(
        body.requirement,
        team_size=body.team_size,
        sprint_weeks=body.sprint_weeks,
        points_per_engineer=body.points_per_engineer,
        use_ai=body.use_ai,
    )


@router.get("/{project_id}/kanban", response_model=SprintKanbanBoard)
def get_kanban_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SprintKanbanBoard:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.sprint_kanban is not None:
        return project.sprint_kanban
    if project.auto_sprint_plan is not None:
        board = build_kanban_from_auto_plan(project.auto_sprint_plan)
        project.sprint_kanban = board
        save_project_to_db(db, row, project)
        db.commit()
        return board
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        "Sprint Kanban has not been generated yet.",
    )


@router.post("/{project_id}/kanban/generate", response_model=SprintKanbanBoard)
async def generate_kanban_for_project(
    project_id: str,
    body: AutoPlanBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SprintKanbanBoard:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = (body.requirement or project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No requirement text to plan.")
    plan = await plan_sprint_from_requirement(
        text,
        team_size=body.team_size,
        sprint_weeks=body.sprint_weeks,
        points_per_engineer=body.points_per_engineer,
        use_ai=body.use_ai,
    )
    project.auto_sprint_plan = plan
    board = build_kanban_from_auto_plan(plan)
    project.sprint_kanban = board
    save_project_to_db(db, row, project)
    db.commit()
    return board


@router.put("/{project_id}/kanban", response_model=SprintKanbanBoard)
def save_kanban_for_project(
    project_id: str,
    board: SprintKanbanBoard,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SprintKanbanBoard:
    """Persist drag-and-drop layout after cards move between sprints."""
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    total = sum(
        c.story_points for col in board.columns for c in col.cards
    )
    board.total_points = total
    project.sprint_kanban = board
    save_project_to_db(db, row, project)
    db.commit()
    return board


@router.get("/kanban/demo", response_model=SprintKanbanBoard)
def get_demo_kanban() -> SprintKanbanBoard:
    """Auth sprint board for judges — Sprint 1 / Sprint 2 cards."""
    return build_auth_demo_kanban()


@router.get("/{project_id}/markdown")
def download_markdown(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.team_sprint_plan is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Sprint plan has not been generated yet.",
        )
    body = to_markdown(project.team_sprint_plan, project)
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-sprint-plan-{project.id[:8]}.md"'
            )
        },
    )
