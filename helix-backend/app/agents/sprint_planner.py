"""Sprint Planning Agent — estimates effort, then allocates tasks into sprints.

Wraps the existing Estimator pass and adds a velocity-based allocation step
so the Project ends up with a concrete `sprint_plan` (sprints with goals,
task ids, points, weeks). This is the final AI step in the Control Tower
before Developer Copilot picks up.

Output: updated `tasks` (with estimates) + `sprint_plan` on the Project.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..models import Project, SprintItem, SprintPlan, Task
from .base import Agent
from .estimator import EstimatorAgent

logger = logging.getLogger("helix.sprint_planner")


SYSTEM = """You are a Sprint Planner / Engineering Manager.

You receive a backlog of tasks that already have story points + hour
estimates. Group them into 2-week sprints sized to a realistic team
velocity. Each sprint must:
  - have a clear, single-sentence GOAL,
  - respect dependencies (no task before what it depends on),
  - prefer high priority and high-confidence work first,
  - call out any RISK that this sprint is exposed to.

Aim for healthy sprint shape: meaningful progress per sprint, not just a
list of tickets. Do not invent tasks. Use only the task ids provided.
""".strip()


SCHEMA = """{
  "velocity_points_per_sprint": 20,
  "rationale": "string — 1-3 sentences explaining how you sliced the work",
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


def _task_block(tasks: List[Task]) -> str:
    lines = []
    for t in tasks:
        deps = ", ".join(t.dependencies) if t.dependencies else "—"
        pts = t.estimate_points if t.estimate_points is not None else "?"
        conf = (
            f"{t.confidence:.2f}" if t.confidence is not None else "?"
        )
        lines.append(
            f"- id={t.id} | {t.title} | priority={t.priority.value} | "
            f"points={pts} | confidence={conf} | deps=[{deps}]"
        )
    return "\n".join(lines)


def _heuristic_plan(tasks: List[Task], velocity: float) -> SprintPlan:
    """Greedy fallback when the LLM returns nothing usable."""
    if not tasks:
        return SprintPlan(velocity_points_per_sprint=velocity)

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            priority_rank.get(getattr(t.priority, "value", "medium"), 2),
            -(t.estimate_points or 3),
        ),
    )

    items: List[SprintItem] = []
    sprint_no = 1
    bucket: List[str] = []
    bucket_pts = 0
    for t in sorted_tasks:
        pts = int(t.estimate_points or 3)
        if bucket_pts + pts > velocity and bucket:
            items.append(
                SprintItem(
                    sprint_number=sprint_no,
                    goal=f"Sprint {sprint_no}: deliver next {len(bucket)} tasks",
                    task_ids=list(bucket),
                    total_points=bucket_pts,
                    weeks=2.0,
                )
            )
            sprint_no += 1
            bucket = []
            bucket_pts = 0
        bucket.append(t.id)
        bucket_pts += pts
    if bucket:
        items.append(
            SprintItem(
                sprint_number=sprint_no,
                goal=f"Sprint {sprint_no}: deliver next {len(bucket)} tasks",
                task_ids=list(bucket),
                total_points=bucket_pts,
                weeks=2.0,
            )
        )

    total_points = sum(it.total_points for it in items)
    return SprintPlan(
        velocity_points_per_sprint=velocity,
        total_sprints=len(items),
        total_points=total_points,
        total_weeks=round(sum(it.weeks for it in items), 1),
        items=items,
        rationale=(
            f"Heuristic allocation at {velocity:.0f} pts/sprint, "
            "sorted by priority then size."
        ),
    )


class SprintPlannerAgent(Agent):
    name = "sprint_planner"
    stage = "Sprint Planning"

    async def run(self, project: Project) -> Dict[str, Any]:
        # Step 1 — make sure every task has an estimate.
        estimator_patch: Dict[str, Any] = {}
        try:
            estimator_patch = await EstimatorAgent().run(project)
        except Exception:  # pragma: no cover — estimator already logs
            logger.exception("Sprint Planner: estimator pass failed")
            estimator_patch = {}

        tasks: List[Task] = list(estimator_patch.get("tasks") or project.tasks)

        if not tasks:
            return {
                "tasks": tasks,
                "sprint_plan": SprintPlan(
                    velocity_points_per_sprint=20.0,
                    rationale="No tasks to plan yet.",
                ),
            }

        velocity = 20.0
        user = (
            f"Team velocity assumption: ~{velocity:.0f} story points / 2-week sprint.\n\n"
            "Backlog (id | title | priority | points | confidence | deps):\n"
            f"{_task_block(tasks)}\n\n"
            "Allocate these into sprints. Reference each task by its id."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=3500,
        )

        valid_ids = {t.id for t in tasks}
        items: List[SprintItem] = []
        next_sprint = 1
        for raw in data.get("items") or []:
            try:
                ids = [tid for tid in (raw.get("task_ids") or []) if tid in valid_ids]
                if not ids:
                    continue
                sn_raw = raw.get("sprint_number")
                try:
                    sn = int(sn_raw) if sn_raw is not None else next_sprint
                except (TypeError, ValueError):
                    sn = next_sprint
                next_sprint = max(next_sprint, sn) + 1
                points_total = sum(
                    int(next((t.estimate_points or 3) for t in tasks if t.id == tid), 3)
                    for tid in ids
                )
                items.append(
                    SprintItem(
                        sprint_number=sn,
                        goal=str(raw.get("goal") or "").strip()
                        or f"Sprint {sn}",
                        task_ids=ids,
                        total_points=int(raw.get("total_points") or points_total),
                        weeks=float(raw.get("weeks") or 2.0),
                        risk_callouts=[
                            str(s).strip()
                            for s in (raw.get("risk_callouts") or [])
                            if str(s).strip()
                        ],
                    )
                )
            except Exception:
                continue

        velocity_out: Optional[float] = None
        try:
            v = data.get("velocity_points_per_sprint")
            if v is not None:
                velocity_out = float(v)
        except (TypeError, ValueError):
            velocity_out = None

        if items:
            plan = SprintPlan(
                velocity_points_per_sprint=velocity_out or velocity,
                total_sprints=len(items),
                total_points=sum(it.total_points for it in items),
                total_weeks=round(sum(it.weeks for it in items), 1),
                items=items,
                rationale=str(data.get("rationale") or "").strip(),
            )
        else:
            plan = _heuristic_plan(tasks, velocity_out or velocity)

        return {"tasks": tasks, "sprint_plan": plan}
