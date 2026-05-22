"""Control Tower API — Multi-Agent SDLC Pipeline views."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...agents.orchestrator import CONTROL_TOWER_STAGES, PIPELINE_AGENT_OUTPUTS
from ...database import get_db
from ...models import Project
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


_AGENT_DESCRIPTIONS: dict[str, str] = {
    "Requirement Analyst": (
        "Extracts features, actors, and business rules from messy input. "
        "Builds glossary and open questions."
    ),
    "Product Manager": (
        "Shapes the product backlog: one epic, user stories, and "
        "acceptance criteria per story."
    ),
    "Architect": (
        "Proposes APIs, database entities, system components, integrations, "
        "NFRs, and architecture decisions."
    ),
    "QA Agent": (
        "Authors test cases covering functional paths, edge cases, and "
        "negative scenarios."
    ),
    "Scrum Master": (
        "Breaks stories into sprint tasks with priorities and dependencies, "
        "then allocates work across sprints."
    ),
}


class ControlTowerStage(BaseModel):
    name: str
    description: str
    outputs: str = ""
    status: str
    elapsed_ms: int | None = None
    output_summary: str | None = None


class ControlTowerView(BaseModel):
    project_id: str
    has_run: bool
    pipeline_label: str = "Multi-Agent SDLC Pipeline"
    agent_count: int = 5
    stages: list[ControlTowerStage]
    requirement_brief: dict[str, Any] | None = None
    pipeline_epic: dict[str, Any] | None = None
    stories: list[dict[str, Any]] | None = None
    architecture_brief: dict[str, Any] | None = None
    test_cases: list[dict[str, Any]] | None = None
    sprint_plan: dict[str, Any] | None = None
    tasks: list[dict[str, Any]] | None = None


def _output_summary(stage: str, project: Project) -> str | None:
    if stage == "Requirement Analyst" and project.requirement_brief:
        rb = project.requirement_brief
        return (
            f"{len(rb.features)} features · "
            f"{len(rb.actors)} actors · "
            f"{len(rb.business_rules)} rules"
        )
    if stage == "Product Manager":
        parts = []
        if project.pipeline_epic:
            parts.append("1 epic")
        if project.stories:
            ac = sum(len(s.acceptance_criteria) for s in project.stories)
            parts.append(f"{len(project.stories)} stories · {ac} AC")
        return " · ".join(parts) if parts else None
    if stage == "Architect" and project.architecture_brief:
        ab = project.architecture_brief
        return (
            f"{len(ab.apis)} APIs · "
            f"{len(ab.components)} components · "
            f"{len(ab.data_entities)} entities"
        )
    if stage == "QA Agent" and project.test_cases:
        edge = sum(len(t.edge_cases or []) for t in project.test_cases)
        return f"{len(project.test_cases)} tests · {edge} edge probes"
    if stage == "Scrum Master":
        if project.tasks or project.sprint_plan:
            deps = sum(len(t.dependencies or []) for t in project.tasks)
            sp = project.sprint_plan
            sprint_part = f"{sp.total_sprints} sprints" if sp else "no plan"
            return f"{len(project.tasks)} tasks · {deps} deps · {sprint_part}"
    return None


def _stage_status(stage: str, project: Project, timings: dict[str, int]) -> str:
    if stage in timings:
        return "done"
    has_output = {
        "Requirement Analyst": project.requirement_brief is not None,
        "Product Manager": bool(project.pipeline_epic or project.stories),
        "Architect": project.architecture_brief is not None,
        "QA Agent": bool(project.test_cases),
        "Scrum Master": bool(project.tasks or project.sprint_plan),
    }.get(stage, False)
    return "done" if has_output else "pending"


def _build_view(project_id: str, project: Project) -> ControlTowerView:
    timings = project.last_pipeline_timings_ms or {}
    stages: list[ControlTowerStage] = []
    for name in CONTROL_TOWER_STAGES:
        stages.append(
            ControlTowerStage(
                name=name,
                description=_AGENT_DESCRIPTIONS.get(name, ""),
                outputs=PIPELINE_AGENT_OUTPUTS.get(name, ""),
                status=_stage_status(name, project, timings),
                elapsed_ms=timings.get(name),
                output_summary=_output_summary(name, project),
            )
        )
    return ControlTowerView(
        project_id=project_id,
        has_run=bool(timings),
        stages=stages,
        requirement_brief=(
            project.requirement_brief.model_dump(mode="json")
            if project.requirement_brief
            else None
        ),
        pipeline_epic=(
            project.pipeline_epic.model_dump(mode="json")
            if project.pipeline_epic
            else None
        ),
        stories=[s.model_dump(mode="json") for s in project.stories] if project.stories else None,
        architecture_brief=(
            project.architecture_brief.model_dump(mode="json")
            if project.architecture_brief
            else None
        ),
        test_cases=[t.model_dump(mode="json") for t in project.test_cases] if project.test_cases else None,
        sprint_plan=(
            project.sprint_plan.model_dump(mode="json")
            if project.sprint_plan
            else None
        ),
        tasks=[t.model_dump(mode="json") for t in project.tasks] if project.tasks else None,
    )


@router.get("/{project_id}", response_model=ControlTowerView)
def get_control_tower(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ControlTowerView:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return _build_view(project_id, project)
