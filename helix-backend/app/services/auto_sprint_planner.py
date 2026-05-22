"""Auto Sprint Planning — task-level decomposition from a requirement.

Input:
    "Build user authentication"

Output:
    | Task              | Story Points |
    | Login API         | 3            |
    | Registration API  | 3            |
    | JWT Auth          | 2            |
    | UI Screens        | 3            |
    | Testing           | 2            |
    Total: 13 → Suggested Sprint = Sprint 1

Hybrid heuristic + optional LLM refinement.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from ..models import AutoSprintPlan, SprintPlanTaskRow
from .ai_service import get_ai_service
from .effort_estimator import _to_fib

logger = logging.getLogger("helix.auto_sprint_planner")

_FIB = [1, 2, 3, 5, 8, 13, 21]


# Domain templates — (task, points, category)
_AUTH_TEMPLATE: Tuple[Tuple[str, int, str], ...] = (
    ("Login API", 3, "api"),
    ("Registration API", 3, "api"),
    ("JWT Auth", 2, "auth"),
    ("UI Screens", 3, "ui"),
    ("Testing", 2, "testing"),
)

_CRUD_TEMPLATE: Tuple[Tuple[str, int, str], ...] = (
    ("Data model & migrations", 3, "data"),
    ("REST API endpoints", 5, "api"),
    ("Validation & business rules", 3, "api"),
    ("UI list / detail views", 5, "ui"),
    ("Testing", 3, "testing"),
)

_PAYMENT_TEMPLATE: Tuple[Tuple[str, int, str], ...] = (
    ("Payment gateway integration", 5, "api"),
    ("Checkout API", 3, "api"),
    ("Webhook handlers", 3, "api"),
    ("Billing UI", 3, "ui"),
    ("PCI / security review", 2, "testing"),
    ("Testing", 3, "testing"),
)

_NOTIFICATION_TEMPLATE: Tuple[Tuple[str, int, str], ...] = (
    ("Notification service", 3, "api"),
    ("Email / SMS provider integration", 3, "api"),
    ("Template management", 2, "api"),
    ("Delivery status tracking", 2, "data"),
    ("Testing", 2, "testing"),
)

_GENERIC_TEMPLATE: Tuple[Tuple[str, int, str], ...] = (
    ("Backend API", 5, "api"),
    ("Core business logic", 3, "api"),
    ("UI implementation", 5, "ui"),
    ("Integration & configuration", 2, "infra"),
    ("Testing", 3, "testing"),
)


_PATTERNS: List[Tuple[re.Pattern[str], Tuple[Tuple[str, int, str], ...]]] = [
    (
        re.compile(
            r"\b(authentication|authorize|login|sign[- ]?up|register|jwt|session|"
            r"password|otp|mfa|oauth)\b",
            re.I,
        ),
        _AUTH_TEMPLATE,
    ),
    (re.compile(r"\b(payment|billing|checkout|stripe|invoice|subscription)\b", re.I), _PAYMENT_TEMPLATE),
    (re.compile(r"\b(notif(y|ication)|email|sms|push)\b", re.I), _NOTIFICATION_TEMPLATE),
    (re.compile(r"\b(crud|create|read|update|delete|manage|track|ticket|catalog)\b", re.I), _CRUD_TEMPLATE),
]


_AI_SYSTEM = """You are a Scrum Master planning the first sprint for a new requirement.

Break the requirement into 4-8 concrete engineering TASKS (not user stories).
Assign Fibonacci story points (1, 2, 3, 5, 8, 13) per task.
Use names managers recognize: "Login API", "UI Screens", "Testing", etc.

Be grounded in the requirement text only. Do not invent unrelated scope.
""".strip()


_AI_SCHEMA = """{
  "tasks": [
    {"task": "string", "story_points": 3, "category": "api|ui|auth|data|testing|infra|other"}
  ],
  "rationale": "string — one sentence for the PM"
}"""


def _capacity(team_size: int, sprint_weeks: float, points_per_engineer: float) -> int:
    team_size = max(1, min(team_size, 50))
    sprint_weeks = max(0.5, min(float(sprint_weeks), 8.0))
    points_per_engineer = max(1.0, min(float(points_per_engineer), 15.0))
    return int(round(team_size * points_per_engineer * (sprint_weeks / 2.0)))


def _pick_template(text: str) -> Tuple[Tuple[str, int, str], ...]:
    txt = (text or "").lower()
    for pat, template in _PATTERNS:
        if pat.search(txt):
            return template
    return _GENERIC_TEMPLATE


def _heuristic_plan(
    text: str,
    *,
    team_size: int,
    sprint_weeks: float,
    points_per_engineer: float,
) -> AutoSprintPlan:
    text = (text or "").strip()
    template = _pick_template(text)
    rows = [
        SprintPlanTaskRow(task=name, story_points=pts, category=cat)
        for name, pts, cat in template
    ]
    total = sum(r.story_points for r in rows)
    cap = _capacity(team_size, sprint_weeks, points_per_engineer)
    util = int(round(100 * total / cap)) if cap else 0
    fits = total <= cap
    sprint_no = 1
    if not fits and cap > 0:
        sprint_no = max(1, (total + cap - 1) // cap)

    return AutoSprintPlan(
        requirement=text,
        tasks=rows,
        total_story_points=total,
        suggested_sprint=f"Sprint {sprint_no}",
        suggested_sprint_number=sprint_no,
        sprint_capacity=cap,
        utilization_pct=min(util, 999),
        fits_in_sprint=fits,
        rationale=(
            f"{total} story points across {len(rows)} tasks — "
            f"{'fits' if fits else 'exceeds'} a {cap}-point sprint capacity "
            f"({team_size} engineers × {points_per_engineer:.0f} sp × {sprint_weeks:.0f}w)."
        ),
        method="heuristic",
    )


async def _ai_refine(
    text: str,
    baseline: AutoSprintPlan,
) -> Optional[AutoSprintPlan]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    try:
        user = (
            f"Requirement:\n{text.strip()[:4000]}\n\n"
            f"Baseline tasks (you may refine): "
            f"{[{'task': r.task, 'story_points': r.story_points} for r in baseline.tasks]}\n\n"
            f"Return JSON matching:\n{_AI_SCHEMA}"
        )
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=2000)
        if not data:
            return None
        rows: List[SprintPlanTaskRow] = []
        for t in data.get("tasks") or []:
            try:
                name = str(t.get("task") or "").strip()
                if not name:
                    continue
                pts = _to_fib(int(t.get("story_points") or 3))
                rows.append(
                    SprintPlanTaskRow(
                        task=name,
                        story_points=pts,
                        category=str(t.get("category") or "other").lower(),
                    )
                )
            except Exception:
                continue
        if not rows:
            return None
        total = sum(r.story_points for r in rows)
        cap = baseline.sprint_capacity
        util = int(round(100 * total / cap)) if cap else 0
        fits = total <= cap
        sprint_no = 1 if fits else max(1, (total + cap - 1) // cap) if cap else 1
        return AutoSprintPlan(
            requirement=text,
            tasks=rows,
            total_story_points=total,
            suggested_sprint=f"Sprint {sprint_no}",
            suggested_sprint_number=sprint_no,
            sprint_capacity=cap,
            utilization_pct=min(util, 999),
            fits_in_sprint=fits,
            rationale=str(data.get("rationale") or baseline.rationale).strip(),
            method="hybrid",
        )
    except Exception:
        logger.exception("Auto sprint planner AI failed")
        return None


async def plan_sprint_from_requirement(
    text: str,
    *,
    team_size: int = 6,
    sprint_weeks: float = 2.0,
    points_per_engineer: float = 6.0,
    use_ai: bool = True,
) -> AutoSprintPlan:
    """Decompose requirement text into tasks, points, and suggested sprint."""
    baseline = _heuristic_plan(
        text,
        team_size=team_size,
        sprint_weeks=sprint_weeks,
        points_per_engineer=points_per_engineer,
    )
    if use_ai:
        refined = await _ai_refine(text, baseline)
        if refined:
            return refined
    return baseline
