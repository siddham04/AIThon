"""Estimator Agent — adds effort estimates with confidence to every task.

Story points (Fibonacci 1/2/3/5/8/13), hours, and a 0-1 confidence based on
clarity, novelty, and dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai.prompts.effort_prompt import EFFORT_SYSTEM, effort_user_message

from ..models import Project, Task
from ..services.ai_service import get_ai_service
from .base import Agent


SYSTEM = """You are a Tech Lead estimating effort for engineering tasks.

For each task, output:
  - estimate_points: Fibonacci (1, 2, 3, 5, 8, 13)
  - estimate_hours: realistic hours including code review & basic tests
  - confidence: 0.0–1.0 (lower for ambiguous or novel work)

Calibrate against typical mid-level engineer velocity. Be conservative.
""".strip()


SCHEMA = """{
  "estimates": [
    {
      "task_id": "task_xxxx",
      "estimate_points": 3,
      "estimate_hours": 6.0,
      "confidence": 0.7
    }
  ]
}"""


class EstimatorAgent(Agent):
    name = "estimator"
    stage = "Estimating effort"

    async def run(self, project: Project) -> Dict[str, Any]:
        if not project.tasks:
            return {"task_estimates": []}

        block = "\n".join(
            f"- id={t.id} | {t.title} | type={t.type.value} | priority={t.priority.value}\n"
            f"  desc: {t.description}\n  skills: {', '.join(t.skills)}"
            for t in project.tasks
        )
        ai = get_ai_service()
        if ai.enabled:
            data = await ai.complete_json(
                EFFORT_SYSTEM,
                effort_user_message(block),
                max_tokens=4000,
            )
        else:
            user = (
                "Tasks to estimate:\n\n"
                f"{block}\n\n"
                "Return estimates referencing each task by its id."
            )
            data = await self.llm.chat_json_with_fallback(
                self.name,
                project,
                SYSTEM,
                user,
                schema_hint=SCHEMA,
                max_completion_tokens=4000,
            )

        by_id: Dict[str, Dict[str, Any]] = {}
        for e in data.get("estimates") or []:
            tid = e.get("task_id")
            if tid:
                by_id[tid] = e

        updated: List[Task] = []
        for t in project.tasks:
            patch = by_id.get(t.id)
            if patch:
                try:
                    pts = patch.get("story_points")
                    if pts is None:
                        pts = patch.get("estimate_points")
                    lo = float(patch.get("hours_low") or 0)
                    hi = float(patch.get("hours_high") or 0)
                    hours_mid = (lo + hi) / 2.0 if (lo or hi) else float(
                        patch.get("estimate_hours") or 4.0
                    )
                    t = t.model_copy(
                        update={
                            "estimate_points": int(pts or 3),
                            "estimate_hours": hours_mid,
                            "confidence": min(
                                1.0,
                                max(0.0, float(patch.get("confidence") or 0.6)),
                            ),
                        }
                    )
                except Exception:
                    pass
            updated.append(t)
        return {"tasks": updated}
