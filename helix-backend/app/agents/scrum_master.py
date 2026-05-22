"""Scrum Master Agent — sprint-ready engineering backlog.

Final planning agent in the Multi-Agent SDLC Pipeline:

    - Sprint tasks (small, owner-actionable)
    - Priorities (critical → low)
    - Dependencies (task-to-task)
    - Sprint allocation (velocity-based plan)

Requires stories from the Product Manager Agent.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..models import Project, Severity, SprintItem, SprintPlan, Task, TaskType
from .base import Agent
from .clause_utils import filter_clause_ids, resolve_story_id, valid_story_ids
from .estimator import EstimatorAgent
from .sprint_planner import _heuristic_plan

logger = logging.getLogger("helix.scrum_master")


SYSTEM = """You are a Scrum Master / Engineering Manager.

You receive user stories with acceptance criteria. Break them into small
engineering TASKS (≤1 day each) that a dev team can pull into sprints.

For each task specify:
  - title, description (concrete implementation step)
  - type: feature|bug|chore|spike|infra
  - priority: low|medium|high|critical
  - story_id (verbatim from input)
  - dependencies: list of other task ids THIS task waits on
  - skills: e.g. ["react", "fastapi", "postgres"]
  - source_clause_ids when known

Then allocate ALL task ids into 2-week sprints for a team velocity of ~20 pts.
Respect dependencies — never schedule a task before its dependencies.
Each sprint needs a goal, total_points, and optional risk_callouts.
""".strip()


SCHEMA = """{
  "tasks": [
    {
      "title": "string",
      "description": "string",
      "type": "feature|bug|chore|spike|infra",
      "priority": "low|medium|high|critical",
      "story_id": "story_xxxx",
      "dependencies": ["task_xxxx"],
      "skills": ["string"],
      "source_clause_ids": ["clause_xxxx"]
    }
  ],
  "velocity_points_per_sprint": 20,
  "rationale": "string",
  "items": [
    {
      "sprint_number": 1,
      "goal": "string",
      "task_ids": ["task_xxxx"],
      "total_points": 13,
      "weeks": 2,
      "risk_callouts": ["string"]
    }
  ]
}"""


def _heuristic_tasks_from_stories(project: Project) -> List[Task]:
    """Deterministic fallback when LLM returns no tasks (demo reliability)."""
    tasks: List[Task] = []
    for s in project.stories:
        prio = Severity.MEDIUM
        tasks.append(
            Task(
                title=f"Implement: {(s.title or 'Story')[:72]}",
                description=(
                    f"Deliver story {s.id}: {(s.goal or s.title or '')[:200]}. "
                    f"AC count: {len(s.acceptance_criteria or [])}."
                ),
                type=TaskType.FEATURE,
                priority=prio,
                story_id=s.id,
                source_clause_ids=filter_clause_ids(
                    project,
                    s.source_clause_ids,
                    agent="scrum_master",
                    context=f"heuristic:{s.id}",
                ),
                skills=["backend", "frontend"],
            )
        )
    return tasks


def _stories_block(project: Project) -> str:
    lines = []
    for s in project.stories:
        ac = "\n      - ".join(s.acceptance_criteria) or "—"
        lines.append(
            f"- id={s.id} | {s.title}\n"
            f"  persona: {s.persona} | goal: {s.goal}\n"
            f"  AC:\n      - {ac}"
        )
    return "\n".join(lines)


class ScrumMasterAgent(Agent):
    name = "scrum_master"
    stage = "Scrum Master"

    async def run(self, project: Project) -> Dict[str, Any]:
        if not project.stories:
            return {"tasks": [], "sprint_plan": SprintPlan()}

        user = (
            "User stories to decompose into sprint-ready tasks:\n\n"
            f"{_stories_block(project)}\n\n"
            "Output tasks with priorities and dependencies, then sprint allocation."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=6000,
        )
        if not data:
            logger.warning("Scrum Master: LLM returned empty JSON — using heuristic tasks")

        tasks: List[Task] = []
        skipped = 0
        for t in data.get("tasks") or []:
            title = t.get("title", "Untitled task")
            sid = resolve_story_id(
                project,
                t.get("story_id"),
                agent="scrum_master",
                title=str(title),
            )
            if sid is None and valid_story_ids(project):
                skipped += 1
                continue
            try:
                prio = str(t.get("priority") or "medium").lower()
                tasks.append(
                    Task(
                        title=title,
                        description=t.get("description", ""),
                        type=TaskType(t.get("type", "feature")),
                        priority=Severity(prio),
                        story_id=sid,
                        dependencies=list(t.get("dependencies") or []),
                        skills=list(t.get("skills") or []),
                        source_clause_ids=filter_clause_ids(
                            project,
                            t.get("source_clause_ids"),
                            agent="scrum_master",
                            context=str(title)[:40],
                        ),
                    )
                )
            except Exception as exc:
                skipped += 1
                logger.warning("Scrum Master skipped invalid task row: %s", exc)

        if skipped:
            logger.info("Scrum Master: skipped %s invalid task row(s)", skipped)

        if not tasks:
            tasks = _heuristic_tasks_from_stories(project)
        project.tasks = tasks

        estimator_patch: Dict[str, Any] = {}
        try:
            estimator_patch = await EstimatorAgent().run(project)
            est_tasks = estimator_patch.get("tasks")
            if est_tasks and len(est_tasks) > 0:
                project.tasks = est_tasks
        except Exception:
            logger.exception("Scrum Master: estimator failed")

        if not project.tasks and project.stories:
            project.tasks = _heuristic_tasks_from_stories(project)

        velocity = float(data.get("velocity_points_per_sprint") or 20)
        items: List[SprintItem] = []
        for raw in data.get("items") or []:
            try:
                items.append(
                    SprintItem(
                        sprint_number=int(raw.get("sprint_number") or 1),
                        goal=str(raw.get("goal") or "").strip(),
                        task_ids=list(raw.get("task_ids") or []),
                        total_points=int(raw.get("total_points") or 0),
                        weeks=float(raw.get("weeks") or 2.0),
                        risk_callouts=[
                            str(r).strip()
                            for r in (raw.get("risk_callouts") or [])
                            if str(r).strip()
                        ],
                    )
                )
            except Exception:
                continue

        if not items and project.tasks:
            plan = _heuristic_plan(project.tasks, velocity)
        else:
            total_points = sum(it.total_points for it in items)
            plan = SprintPlan(
                velocity_points_per_sprint=velocity,
                total_sprints=len(items),
                total_points=total_points,
                total_weeks=round(sum(it.weeks for it in items), 1),
                items=items,
                rationale=str(data.get("rationale") or "").strip()
                or f"Allocated {len(project.tasks)} tasks across {len(items)} sprints.",
            )

        return {
            "tasks": project.tasks,
            "sprint_plan": plan,
        }
