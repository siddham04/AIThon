"""Interactive Sprint Planner — capacity-aware allocator.

Given the project's stories + tasks AND the team-size / sprint-length
the user picks, allocate STORIES into sprints sized to a realistic
team velocity. The output is the sprint-by-sprint deliverable view a
Scrum Master would put up on a wall:

    Sprint 1
      - Story A
      - Story B
    Sprint 2
      - Story C

Allocation rules:

1. Each story's points = sum of its tasks' points (or a per-story
   default if no estimates exist yet).
2. Velocity = team_size × points_per_engineer × (sprint_weeks / 2).
   The "points per engineer per 2-week sprint" knob defaults to 6,
   which is the industry rule of thumb (5-8 sp / engineer / sprint).
3. Stories are sorted by priority (critical first) → has_risk first
   inside same priority → biggest first (do the elephants early).
4. Inter-story dependencies are honored: a story can only go into
   sprint N if all stories its tasks depend on are in sprint < N.
5. If a single story is bigger than the velocity, it gets a sprint
   of its own and a "spike" risk callout.
6. The LLM (when available) names each sprint goal and surfaces
   risks per sprint — never re-shuffles the allocation.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import (
    Project,
    Severity,
    StorySprint,
    StorySprintItem,
    Task,
    TeamSprintPlan,
    UserStory,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.team_sprint_planner")


_PRIORITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

_DEFAULT_STORY_POINTS = 5  # for stories where no task is estimated yet


def _story_priority(story: UserStory, tasks: List[Task]) -> Severity:
    """Use the highest priority among the story's tasks (or MEDIUM)."""
    sev: Severity = Severity.LOW
    seen = False
    for t in tasks:
        if t.story_id == story.id:
            seen = True
            if _PRIORITY_RANK.get(t.priority, 3) < _PRIORITY_RANK.get(sev, 3):
                sev = t.priority
    return sev if seen else Severity.MEDIUM


def _story_points(story: UserStory, tasks: List[Task]) -> int:
    pts = 0
    matched = False
    for t in tasks:
        if t.story_id == story.id:
            matched = True
            pts += int(t.estimate_points or 0) or 3  # task fallback
    if not matched:
        return _DEFAULT_STORY_POINTS
    return max(pts, 1)


def _story_tasks_count(story: UserStory, tasks: List[Task]) -> int:
    return sum(1 for t in tasks if t.story_id == story.id)


def _story_has_risk(story: UserStory, project: Project) -> bool:
    """A story is risk-tagged if any high/critical risk references one of its
    source clauses, or if a high/critical risk exists at all (best-effort)."""
    if not project.risks:
        return False
    story_clauses = set(getattr(story, "source_clause_ids", []) or [])
    for r in project.risks:
        if getattr(r, "severity", None) in (Severity.HIGH, Severity.CRITICAL):
            return True
        risk_clauses = set(getattr(r, "source_clause_ids", []) or [])
        if story_clauses and risk_clauses & story_clauses:
            return True
    return False


def _build_dep_graph(stories: List[UserStory], tasks: List[Task]) -> Dict[str, Set[str]]:
    """Story-level dependency map: story_id -> {depends_on_story_id, ...}."""
    task_to_story: Dict[str, str] = {t.id: (t.story_id or "") for t in tasks}
    out: Dict[str, Set[str]] = {s.id: set() for s in stories}
    for t in tasks:
        if not t.story_id:
            continue
        for dep in t.dependencies or []:
            dep_story = task_to_story.get(dep, "")
            if dep_story and dep_story != t.story_id:
                out[t.story_id].add(dep_story)
    return out


def _capacity(team_size: int, sprint_weeks: float, points_per_eng: float) -> float:
    weeks_factor = max(sprint_weeks / 2.0, 0.25)
    return round(max(1, team_size) * max(0.5, points_per_eng) * weeks_factor, 1)


def _allocate(
    stories: List[UserStory],
    tasks: List[Task],
    project: Project,
    *,
    capacity: float,
    sprint_weeks: float,
) -> Tuple[List[StorySprint], List[StorySprintItem]]:
    """Greedy capacity-aware allocator that respects story dependencies."""
    if not stories:
        return [], []

    items_by_story: Dict[str, StorySprintItem] = {}
    for s in stories:
        items_by_story[s.id] = StorySprintItem(
            story_id=s.id,
            story_title=s.title,
            persona=s.persona,
            points=_story_points(s, tasks),
            tasks_count=_story_tasks_count(s, tasks),
            has_risk=_story_has_risk(s, project),
        )

    # Order: priority asc → has_risk first → bigger first
    priority_of: Dict[str, Severity] = {
        s.id: _story_priority(s, tasks) for s in stories
    }
    ordered = sorted(
        stories,
        key=lambda s: (
            _PRIORITY_RANK.get(priority_of[s.id], 2),
            0 if items_by_story[s.id].has_risk else 1,
            -items_by_story[s.id].points,
        ),
    )

    deps = _build_dep_graph(stories, tasks)
    placed: Dict[str, int] = {}  # story_id -> sprint_number
    sprints: List[StorySprint] = []
    unscheduled: List[StorySprintItem] = []

    pending_ids = [s.id for s in ordered]
    sprint_no = 1
    safety = 50  # avoid pathological loops on dependency cycles

    while pending_ids and safety > 0:
        safety -= 1
        bucket: List[StorySprintItem] = []
        bucket_pts = 0.0

        # Walk pending in priority order; place every story whose deps are
        # already placed AND that fits in remaining capacity.
        progressed = False
        new_pending: List[str] = []
        for sid in pending_ids:
            item = items_by_story[sid]
            unmet = [d for d in deps.get(sid, set()) if d not in placed]
            if unmet:
                new_pending.append(sid)
                continue
            # Mega-story (bigger than full sprint): sprint of its own.
            if item.points > capacity and not bucket:
                bucket.append(item)
                bucket_pts += item.points
                placed[sid] = sprint_no
                progressed = True
                continue
            if bucket_pts + item.points <= capacity:
                bucket.append(item)
                bucket_pts += item.points
                placed[sid] = sprint_no
                progressed = True
            else:
                new_pending.append(sid)

        # If nothing got placed and there is still pending work, the next
        # story in priority order has unmet dependencies — break the cycle
        # by force-placing it (best we can do without ground truth).
        if not progressed and new_pending:
            forced = new_pending[0]
            placed[forced] = sprint_no
            bucket.append(items_by_story[forced])
            bucket_pts += items_by_story[forced].points
            new_pending = new_pending[1:]
            progressed = True

        if bucket:
            risks: List[str] = []
            if any(it.has_risk for it in bucket):
                risks.append(
                    "Sprint contains a high-risk story — schedule a mid-sprint check."
                )
            mega = next((it for it in bucket if it.points > capacity), None)
            if mega is not None:
                risks.append(
                    f"'{mega.story_title}' alone exceeds capacity ({mega.points} > "
                    f"{capacity:.0f}); consider splitting before development."
                )
            sprints.append(
                StorySprint(
                    sprint_number=sprint_no,
                    label=f"Sprint {sprint_no}",
                    goal="",
                    weeks=sprint_weeks,
                    capacity_points=capacity,
                    planned_points=int(round(bucket_pts)),
                    utilization_pct=int(min(round((bucket_pts / capacity) * 100), 200))
                    if capacity > 0
                    else 0,
                    stories=bucket,
                    risks=risks,
                )
            )
            sprint_no += 1

        pending_ids = new_pending

    if pending_ids:
        for sid in pending_ids:
            unscheduled.append(items_by_story[sid])

    return sprints, unscheduled


# ----------------------------------------------------------- AI augment -- #


_AI_SYSTEM = """You are a Scrum Master writing the GOAL line for each
sprint of a fixed allocation. You MUST NOT change which stories are in
which sprint. Goals must be one short sentence (<=14 words) capturing
the user-visible outcome of that sprint.""".strip()


_AI_SCHEMA = """{
  "sprint_goals": [
    {
      "sprint_number": 1,
      "goal": "string — one short sentence",
      "extra_risks": ["string"]
    }
  ]
}"""


async def _ai_name_goals(
    sprints: List[StorySprint],
    project: Project,
) -> bool:
    """Mutates `sprints` in-place. Returns True if AI actually contributed."""
    ai = get_ai_service()
    if not ai.enabled or not sprints:
        return False

    sprint_lines: List[str] = []
    for sp in sprints:
        st_lines = "\n".join(
            f"      - {it.story_title} ({it.points}sp, {it.persona or 'user'})"
            for it in sp.stories
        )
        sprint_lines.append(f"  Sprint {sp.sprint_number}:\n{st_lines}")
    blob = "\n\n".join(sprint_lines)

    objective = ""
    if project.summary:
        objective = (project.summary.objective or project.summary.one_liner or "").strip()

    user = (
        f"Project objective:\n{objective[:600]}\n\n"
        f"Allocation (do NOT change membership):\n{blob}\n\n"
        f"Return ONLY JSON in this shape:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=1500)
    except Exception:  # pragma: no cover — defensive
        logger.exception("Sprint goal AI naming failed")
        return False

    by_num = {sp.sprint_number: sp for sp in sprints}
    touched = False
    for raw in data.get("sprint_goals") or []:
        try:
            n = int(raw.get("sprint_number") or 0)
            sp = by_num.get(n)
            if sp is None:
                continue
            goal = str(raw.get("goal") or "").strip()
            if goal:
                sp.goal = goal[:140]
                touched = True
            extra = [
                str(s).strip()
                for s in (raw.get("extra_risks") or [])
                if str(s).strip()
            ]
            if extra:
                sp.risks = list(sp.risks) + extra
        except Exception:
            continue
    return touched


# ------------------------------------------------------------ Coordinator -- #


def _fallback_goals(sprints: List[StorySprint]) -> None:
    for sp in sprints:
        if sp.goal:
            continue
        if not sp.stories:
            sp.goal = f"Sprint {sp.sprint_number}"
            continue
        # Pick the highest-points story as the centerpiece.
        head = max(sp.stories, key=lambda it: it.points)
        if len(sp.stories) == 1:
            sp.goal = f"Ship {head.story_title}"
        else:
            sp.goal = (
                f"Deliver {head.story_title} + {len(sp.stories) - 1} supporting stor"
                f"{'y' if len(sp.stories) - 1 == 1 else 'ies'}"
            )


async def plan_team_sprints(
    project: Project,
    *,
    team_size: int = 6,
    sprint_weeks: float = 2.0,
    points_per_engineer: float = 6.0,
    use_ai: bool = True,
) -> TeamSprintPlan:
    team_size = max(1, min(team_size, 50))
    sprint_weeks = max(0.5, min(float(sprint_weeks), 8.0))
    points_per_engineer = max(1.0, min(float(points_per_engineer), 15.0))

    capacity = _capacity(team_size, sprint_weeks, points_per_engineer)

    sprints, unscheduled = _allocate(
        project.stories,
        project.tasks,
        project,
        capacity=capacity,
        sprint_weeks=sprint_weeks,
    )

    method = "heuristic"
    if use_ai and sprints:
        ai_touched = await _ai_name_goals(sprints, project)
        if ai_touched:
            method = "hybrid"
    _fallback_goals(sprints)

    total_points = sum(sp.planned_points for sp in sprints) + sum(
        it.points for it in unscheduled
    )
    total_weeks = round(sum(sp.weeks for sp in sprints), 1)

    rationale = (
        f"Velocity {capacity:.0f} pts/sprint based on {team_size} engineers × "
        f"{points_per_engineer:.0f} sp / engineer / {sprint_weeks:.0f}w sprint. "
        f"Allocated {len(project.stories) - len(unscheduled)} of "
        f"{len(project.stories)} stories across {len(sprints)} sprints."
    )

    return TeamSprintPlan(
        project_id=project.id,
        method=method,
        team_size=team_size,
        sprint_weeks=sprint_weeks,
        points_per_engineer_per_sprint=points_per_engineer,
        velocity_points_per_sprint=capacity,
        total_stories=len(project.stories),
        total_points=total_points,
        total_sprints=len(sprints),
        total_weeks=total_weeks,
        sprints=sprints,
        unscheduled_stories=unscheduled,
        rationale=rationale,
    )


# ----------------------------------------------------------- Markdown ---- #


def to_markdown(plan: TeamSprintPlan, project: Project) -> str:
    title = (
        (project.summary.title if project.summary and project.summary.title else project.name)
        or "Project"
    )
    lines: List[str] = [
        f"# Sprint Plan — {title}",
        "",
        f"_Team {plan.team_size} engineers · {plan.sprint_weeks:.0f}-week sprints · "
        f"velocity {plan.velocity_points_per_sprint:.0f} sp/sprint · "
        f"{plan.total_sprints} sprints · {plan.total_weeks:.0f} weeks_",
        "",
    ]
    if plan.rationale:
        lines.extend([f"> {plan.rationale}", ""])

    for sp in plan.sprints:
        lines.append(f"## Sprint {sp.sprint_number}  —  {sp.goal or '—'}")
        lines.append(
            f"_{sp.weeks:.0f}w · {sp.planned_points} sp / {sp.capacity_points:.0f} sp "
            f"({sp.utilization_pct}% utilization)_"
        )
        lines.append("")
        for it in sp.stories:
            risk = " ⚠️" if it.has_risk else ""
            lines.append(
                f"- **{it.story_title}** ({it.points} sp){risk}"
            )
        if sp.risks:
            lines.append("")
            lines.append("**Risks:**")
            for r in sp.risks:
                lines.append(f"- {r}")
        lines.append("")

    if plan.unscheduled_stories:
        lines.extend(
            [
                "## Unscheduled (capacity overflow)",
                "",
                *[
                    f"- **{it.story_title}** ({it.points} sp)"
                    for it in plan.unscheduled_stories
                ],
                "",
            ]
        )
    return "\n".join(lines)
