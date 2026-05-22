"""AI Project Manager Agent (Feature 20).

Computes a delivery forecast for the project:

    {
      "timeline": "4 weeks",
      "critical_path": ["Backend API", "Authentication", "Testing"],
      "release_risk": "Medium"
    }

Approach:
    * Group tasks into "workstreams" by skill / type / keyword.
    * Estimate per-workstream effort (hours) from task estimates,
      defaulting from sprint plan velocity if estimates are missing.
    * Build a critical path by topologically ordering workstreams
      with dependency hints from task.dependencies and existing
      ambiguity / risk hints.
    * Convert effort to weeks using a simple per-engineer cap.
    * Risk score blends ambiguities + open risks + readiness gaps,
      with the LLM optionally rewriting the human-readable summary.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    CriticalPathStep,
    PMMilestone,
    Project,
    ProjectManagerForecast,
    Severity,
    Task,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.project_manager")


# Workstream taxonomy — the order here is the *typical* dependency
# order, used as a tiebreaker when no explicit task deps exist.
_WORKSTREAMS: List[Tuple[str, re.Pattern[str]]] = [
    ("Discovery & Spec", re.compile(r"\b(discov\w+|spec|design\s+doc|kick[- ]?off|workshop|brief)\b", re.I)),
    ("Architecture & Design", re.compile(r"\b(architect\w+|design|adr|decision|diagram)\b", re.I)),
    ("Database Schema", re.compile(r"\b(schema|migration|table|model|orm)\b", re.I)),
    ("Authentication", re.compile(r"\b(auth(?:enticat\w+)?|login|otp|2fa|mfa|sso|jwt|session|password)\b", re.I)),
    ("Backend API", re.compile(r"\b(api|endpoint|service|backend|controller|route|graphql|rest)\b", re.I)),
    ("Integrations", re.compile(r"\b(integration|webhook|third[- ]?party|sdk|stripe|twilio|sendgrid)\b", re.I)),
    ("Frontend", re.compile(r"\b(frontend|ui|react|component|page|screen|css|view)\b", re.I)),
    ("Testing", re.compile(r"\b(test|qa|quality|coverage|regression|smoke|e2e)\b", re.I)),
    ("Security & Compliance", re.compile(r"\b(secur\w+|encrypt\w*|owasp|gdpr|pci|hipaa|soc2|compliance)\b", re.I)),
    ("Performance & Scale", re.compile(r"\b(perf\w+|p99|latenc\w+|throughput|scale|cache)\b", re.I)),
    ("Observability", re.compile(r"\b(observ\w+|metric|log|trace|alert|dashboard)\b", re.I)),
    ("Deployment & Rollout", re.compile(r"\b(deploy|rollout|rollback|feature\s+flag|release|kill\s*switch)\b", re.I)),
]


def _workstream_for_task(task: Task) -> str:
    """Best-fit workstream for a task by scanning title, desc, skills."""
    blob = " ".join(filter(None, [
        task.title,
        getattr(task, "description", "") or "",
        " ".join(getattr(task, "skills", []) or []),
        str(getattr(task, "type", "")),
    ]))
    for name, pat in _WORKSTREAMS:
        if pat.search(blob):
            return name
    return "Backend API"  # fallback bucket


def _task_hours(task: Task) -> float:
    if task.estimate_hours and task.estimate_hours > 0:
        return float(task.estimate_hours)
    if task.estimate_points and task.estimate_points > 0:
        return float(task.estimate_points) * 4.5  # ~half-day per point
    # Severity-weighted default
    sev = getattr(task, "priority", Severity.MEDIUM)
    base = {
        Severity.CRITICAL: 24.0,
        Severity.HIGH: 16.0,
        Severity.MEDIUM: 10.0,
        Severity.LOW: 5.0,
    }
    return base.get(sev, 10.0)


def _bucket_tasks(project: Project) -> Dict[str, List[Task]]:
    buckets: Dict[str, List[Task]] = {}
    for t in (project.tasks or []):
        ws = _workstream_for_task(t)
        buckets.setdefault(ws, []).append(t)
    return buckets


def _critical_path(buckets: Dict[str, List[Task]]) -> List[CriticalPathStep]:
    """Pick the heaviest workstreams in their canonical dependency order."""
    if not buckets:
        return []

    # Effort per workstream (hours).
    effort: Dict[str, float] = {ws: sum(_task_hours(t) for t in tasks) for ws, tasks in buckets.items()}

    # Canonical order from the taxonomy keeps it intuitive.
    ordered = [ws for ws, _ in _WORKSTREAMS if ws in buckets]
    leftover = [ws for ws in buckets if ws not in ordered]
    ordered.extend(leftover)

    # Trim to top 3-5 by effort while preserving order.
    top = sorted(effort.items(), key=lambda kv: kv[1], reverse=True)
    keep = {ws for ws, _ in top[:5]}
    chain = [ws for ws in ordered if ws in keep]
    if len(chain) < 3 and len(ordered) >= 3:
        chain = ordered[:3]

    steps: List[CriticalPathStep] = []
    prev: Optional[str] = None
    for ws in chain:
        days = round(effort.get(ws, 0.0) / 6.0, 1)  # ~6 productive hours / day / engineer
        steps.append(
            CriticalPathStep(
                name=ws,
                duration_days=max(days, 1.0),
                depends_on=[prev] if prev else [],
                rationale=f"{len(buckets.get(ws, []))} task(s) totalling ~{int(effort.get(ws, 0))}h.",
            )
        )
        prev = ws
    return steps


def _timeline_string(weeks: float) -> str:
    """Render the canonical 'X weeks' string the user asked for."""
    if weeks <= 0:
        return "TBD"
    if weeks < 1:
        return "1 week"
    if weeks < 1.5:
        return "1 week"
    rounded = int(round(weeks))
    if rounded <= 1:
        return "1 week"
    return f"{rounded} weeks"


def _release_risk(project: Project, total_hours: float, ambig_open: int) -> Tuple[str, int, List[str]]:
    drivers: List[str] = []
    score = 0

    if ambig_open >= 5:
        drivers.append(f"{ambig_open} unresolved ambiguities")
        score += 25
    elif ambig_open:
        drivers.append(f"{ambig_open} unresolved ambiguities")
        score += 12

    high_risks = [r for r in (project.risks or []) if str(getattr(r, "severity", "")).endswith("high") or str(getattr(r, "severity", "")).endswith("critical")]
    if high_risks:
        drivers.append(f"{len(high_risks)} high/critical risks logged")
        score += min(25, len(high_risks) * 6)

    if project.delivery_readiness:
        gap = max(0, 90 - project.delivery_readiness.readiness)
        if gap > 0:
            drivers.append(f"Readiness gap of {gap} pts to release bar")
            score += min(25, gap // 2)

    if project.requirement_risk:
        rr = str(getattr(project.requirement_risk, "risk_level", "low"))
        if rr.endswith("critical"):
            score += 25
            drivers.append("Predicted critical risk")
        elif rr.endswith("high"):
            score += 18
            drivers.append("Predicted high risk")
        elif rr.endswith("medium"):
            score += 8

    if project.defect_prediction and len(project.defect_prediction.high_risk_modules) >= 2:
        drivers.append(
            f"Defect-prone modules: {', '.join(project.defect_prediction.high_risk_modules[:3])}"
        )
        score += 12

    if total_hours > 600:
        drivers.append("Large scope — over 600 effort hours")
        score += 10

    score = max(0, min(score, 100))
    if score >= 70:
        label = "Critical"
    elif score >= 45:
        label = "High"
    elif score >= 25:
        label = "Medium"
    else:
        label = "Low"
    return label, score, drivers


def _milestones(critical_path: List[CriticalPathStep], weeks: float) -> List[PMMilestone]:
    if not critical_path or weeks <= 0:
        return []
    total_days = sum(s.duration_days for s in critical_path) or 1
    out: List[PMMilestone] = []
    cum = 0.0
    for step in critical_path:
        cum += step.duration_days
        wk = max(1, int(math.ceil(weeks * cum / total_days)))
        out.append(PMMilestone(
            name=f"{step.name} complete",
            week=wk,
            description=step.rationale,
        ))
    return out


def _heuristic_forecast(project: Project, *, team_size: int = 4) -> ProjectManagerForecast:
    buckets = _bucket_tasks(project)
    total_hours = sum(_task_hours(t) for t in (project.tasks or []))

    # Sprint plan as an authoritative source if present.
    plan = project.team_sprint_plan
    if plan and plan.sprints:
        weeks = sum(getattr(s, "weeks", plan.sprint_weeks or 2.0) for s in plan.sprints)
        team_size = plan.team_size or team_size
    else:
        # Effort divided across the team, with capacity overhead.
        effective_hours_per_week = max(1.0, team_size * 30.0)  # 30 productive h/week
        weeks = total_hours / effective_hours_per_week if total_hours else 0.0
        if not weeks and project.stories:
            # Fallback: ~1 week per 3 stories.
            weeks = max(1.0, len(project.stories) / 3.0)

    weeks = max(0.0, weeks)
    timeline = _timeline_string(weeks)

    critical_path_detail = _critical_path(buckets)
    critical_path = [s.name for s in critical_path_detail]

    ambig_open = sum(1 for a in (project.ambiguities or []) if not getattr(a, "resolved", False))
    risk_label, risk_score, risk_drivers = _release_risk(project, total_hours, ambig_open)

    workstreams = sorted(buckets.keys(), key=lambda k: -sum(_task_hours(t) for t in buckets[k]))

    summary = (
        f"~{int(total_hours) if total_hours else 0}h across "
        f"{len(workstreams)} workstream{'' if len(workstreams) == 1 else 's'}; "
        f"{timeline} with a team of {team_size}; release risk {risk_label.lower()}."
    )

    return ProjectManagerForecast(
        project_id=project.id,
        timeline=timeline,
        timeline_weeks=round(weeks, 1),
        critical_path=critical_path,
        critical_path_detail=critical_path_detail,
        release_risk=risk_label,
        risk_score=risk_score,
        risk_drivers=risk_drivers,
        milestones=_milestones(critical_path_detail, weeks),
        workstreams=workstreams,
        summary=summary,
        method="heuristic",
    )


# ---------- AI augmentation ------------------------------------------ #


_AI_SYSTEM = (
    "You are an experienced delivery lead. From a heuristic project "
    "forecast and the project context, refine the human-readable summary "
    "and rewrite the critical path step rationales so they read like a "
    "weekly stand-up update. NEVER change the timeline or risk_score; "
    "you may relabel the risk only if the drivers strongly justify it. "
    "Output ONLY valid JSON."
)

_AI_SCHEMA = """{
  "summary": "string",
  "release_risk": "Low|Medium|High|Critical",
  "critical_path_detail": [
    {"name": "string", "rationale": "string — concise, manager-friendly"}
  ]
}"""


async def _ai_augment(
    project: Project,
    baseline: ProjectManagerForecast,
) -> Optional[ProjectManagerForecast]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    cp_blob = "\n".join(
        f"  - {s.name}: {s.duration_days}d — {s.rationale}"
        for s in baseline.critical_path_detail
    ) or "  (none)"
    user = (
        f"Project: {project.name}\n"
        f"Timeline (fixed): {baseline.timeline}\n"
        f"Risk score (fixed): {baseline.risk_score}\n"
        f"Risk drivers: {baseline.risk_drivers}\n"
        f"Workstreams: {baseline.workstreams}\n"
        f"Critical path:\n{cp_blob}\n\n"
        f"Stories: {len(project.stories or [])} · "
        f"Tasks: {len(project.tasks or [])} · "
        f"Ambiguities open: {sum(1 for a in (project.ambiguities or []) if not getattr(a, 'resolved', False))}\n\n"
        f"Schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=1400)
    except Exception:
        logger.exception("PM agent AI failed")
        return None

    summary = str(data.get("summary") or "").strip() or baseline.summary
    risk = str(data.get("release_risk") or baseline.release_risk).strip().title()
    if risk not in ("Low", "Medium", "High", "Critical"):
        risk = baseline.release_risk

    refined_steps = list(baseline.critical_path_detail)
    by_name = {s.name: s for s in refined_steps}
    for raw in (data.get("critical_path_detail") or []):
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        rationale = str(raw.get("rationale") or "").strip()
        if name in by_name and rationale:
            by_name[name].rationale = rationale

    return baseline.model_copy(update={
        "summary": summary,
        "release_risk": risk,
        "critical_path_detail": refined_steps,
        "method": "hybrid",
    })


async def forecast_project(
    project: Project,
    *,
    team_size: int = 4,
    use_ai: bool = True,
) -> ProjectManagerForecast:
    baseline = _heuristic_forecast(project, team_size=team_size)
    if not use_ai:
        return baseline
    refined = await _ai_augment(project, baseline)
    return refined or baseline


def to_simple_json(forecast: ProjectManagerForecast) -> Dict[str, Any]:
    """Canonical user-facing shape:
    `{timeline, critical_path, release_risk}`."""
    return {
        "timeline": forecast.timeline,
        "critical_path": list(forecast.critical_path),
        "release_risk": forecast.release_risk,
    }


__all__ = ["forecast_project", "to_simple_json"]
