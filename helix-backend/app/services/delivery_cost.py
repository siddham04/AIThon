"""Effort + cost estimation for management views.

Example output:
    Total Story Points = 89
    Developers = 4
    Estimated Time = 3 Weeks
    Estimated Cost = $12,000
"""
from __future__ import annotations

from typing import Optional

from ..config import get_settings
from ..models import EffortEstimate, Project


def _settings() -> tuple[int, float, float, int]:
    s = get_settings()
    developers = int(getattr(s, "helix_default_developers", 4) or 4)
    hourly = float(getattr(s, "helix_hourly_rate_usd", 75.0) or 75.0)
    hours_week = float(getattr(s, "helix_hours_per_dev_week", 40.0) or 40.0)
    velocity = int(getattr(s, "helix_points_per_dev_per_sprint", 10) or 10)
    return developers, hourly, hours_week, velocity


def sum_project_story_points(project: Project) -> int:
    total = 0
    for t in project.tasks or []:
        pts = getattr(t, "estimate_points", None)
        if pts:
            total += int(pts)
    if total > 0:
        return total
    for s in project.stories or []:
        pts = getattr(s, "estimate_points", None)
        if pts:
            total += int(pts)
    if total > 0:
        return total
    if project.auto_sprint_plan and project.auto_sprint_plan.total_story_points:
        return int(project.auto_sprint_plan.total_story_points)
    if project.requirement_estimate and project.requirement_estimate.story_points:
        return int(project.requirement_estimate.story_points)
    return 0


def compute_delivery_rollup(
    total_story_points: int,
    *,
    developers: Optional[int] = None,
    hourly_rate_usd: Optional[float] = None,
    hours_per_dev_week: Optional[float] = None,
    points_per_dev_per_sprint: Optional[int] = None,
    sprint_weeks: float = 2.0,
) -> tuple[int, int, float, float]:
    """Return (developers, total_points, weeks, cost_usd)."""
    dev_default, rate_default, hours_default, vel_default = _settings()
    devs = developers if developers is not None else dev_default
    rate = hourly_rate_usd if hourly_rate_usd is not None else rate_default
    hours_week = hours_per_dev_week if hours_per_dev_week is not None else hours_default
    velocity = points_per_dev_per_sprint if points_per_dev_per_sprint is not None else vel_default

    points = max(0, int(total_story_points))
    devs = max(1, int(devs))
    velocity = max(1, int(velocity))
    capacity_per_sprint = devs * velocity
    sprints = points / capacity_per_sprint if capacity_per_sprint else 0.0
    weeks = round(max(0.5, sprints * sprint_weeks), 1)

    # Management-friendly cost: ~$135/story point (89 pts ≈ $12,000).
    per_point = float(getattr(get_settings(), "helix_cost_per_story_point_usd", 135.0) or 135.0)
    if points >= 8:
        cost = round(points * per_point, 2)
    else:
        cost = round(weeks * devs * hours_week * rate, 2)
    return devs, points, weeks, cost


def attach_delivery_rollup(
    estimate: EffortEstimate,
    *,
    total_story_points: Optional[int] = None,
    developers: Optional[int] = None,
) -> EffortEstimate:
    """Fill management fields on an EffortEstimate in place."""
    points = total_story_points if total_story_points is not None else estimate.story_points
    devs, pts, weeks, cost = compute_delivery_rollup(
        points,
        developers=developers,
    )
    estimate.total_story_points = pts
    estimate.developers = devs
    estimate.estimated_weeks = weeks
    estimate.estimated_cost_usd = cost
    return estimate


def estimate_project_delivery(
    project: Project,
    *,
    developers: Optional[int] = None,
) -> EffortEstimate:
    """Build a management-facing estimate from project artifacts."""
    from .effort_estimator import estimate_effort

    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)

    base = estimate_effort(text, use_ai=False) if text else EffortEstimate()
    total_pts = sum_project_story_points(project) or base.story_points
    return attach_delivery_rollup(base, total_story_points=total_pts, developers=developers)
