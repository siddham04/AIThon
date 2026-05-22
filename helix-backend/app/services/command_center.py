"""SDLC Command Center — aggregate project health on one screen."""
from __future__ import annotations

from typing import List, Optional

from ..agents.orchestrator import CONTROL_TOWER_STAGES
from ..models import CommandCenterMetric, CommandCenterSnapshot, EffortEstimate, Project
from .delivery_cost import attach_delivery_rollup, sum_project_story_points


def _quality_overall(project: Project) -> Optional[int]:
    q = project.quality_score_report
    if not q:
        return None
    if getattr(q, "overall_score", None):
        return int(q.overall_score)
    dims = [
        getattr(q, "clarity", None),
        getattr(q, "completeness", None),
        getattr(q, "testability", None),
        getattr(q, "ambiguity", None),
    ]
    vals = [int(v) for v in dims if v is not None]
    return int(sum(vals) / len(vals)) if vals else None


def _pipeline_done(project: Project) -> int:
    timings = project.last_pipeline_timings_ms or {}
    if timings:
        return sum(1 for s in CONTROL_TOWER_STAGES if s in timings)
    done = 0
    if project.requirement_brief:
        done += 1
    if project.pipeline_epic or project.stories:
        done += 1
    if project.architecture_brief:
        done += 1
    if project.test_cases:
        done += 1
    if project.tasks or project.sprint_plan or project.auto_sprint_plan:
        done += 1
    return done


def build_command_center(project: Project) -> CommandCenterSnapshot:
    """Snapshot KPIs from persisted project artifacts (no LLM)."""
    pid = project.id
    base = f"/project/{pid}"

    quality_score = _quality_overall(project)
    amb_count = len(project.ambiguities or [])
    tasks_count = len(project.tasks or [])
    tests_count = len(project.test_cases or [])
    stories_count = len(project.stories or [])
    risks_count = len(project.risks or [])

    risk_score: Optional[int] = None
    if project.requirement_risk:
        risk_score = int(project.requirement_risk.score or 0)

    total_pts = sum_project_story_points(project)
    weeks = 0.0
    cost = 0.0
    developers = 4
    if project.requirement_estimate:
        est = project.requirement_estimate
        total_pts = est.total_story_points or total_pts or est.story_points
        weeks = float(est.estimated_weeks or 0)
        cost = float(est.estimated_cost_usd or 0)
        developers = int(est.developers or 4)
    elif total_pts:
        est = attach_delivery_rollup(EffortEstimate(), total_story_points=total_pts)
        weeks = est.estimated_weeks
        cost = est.estimated_cost_usd
        developers = est.developers

    sprint_label = ""
    if project.auto_sprint_plan:
        sprint_label = project.auto_sprint_plan.suggested_sprint or ""
    elif project.sprint_plan and project.sprint_plan.items:
        sprint_label = f"Sprint {project.sprint_plan.items[0].sprint_number}"

    def _status(ok: bool, warn: bool = False) -> str:
        if ok and not warn:
            return "ok"
        if warn:
            return "warn"
        return "pending"

    metrics: List[CommandCenterMetric] = [
        CommandCenterMetric(
            key="quality",
            label="Requirement score",
            value=f"{quality_score}/100" if quality_score is not None else "—",
            subvalue="Clarity · completeness · testability",
            status=_status(quality_score is not None, (quality_score or 100) < 60),
            href=f"{base}/quality",
        ),
        CommandCenterMetric(
            key="ambiguity",
            label="Ambiguities",
            value=str(amb_count),
            subvalue="Open clarification items",
            status=_status(amb_count == 0, amb_count > 0),
            href=f"{base}/workspace#ambiguity",
        ),
        CommandCenterMetric(
            key="tasks",
            label="Tasks generated",
            value=str(tasks_count),
            subvalue=f"{stories_count} stories",
            status=_status(tasks_count > 0),
            href=f"{base}/workspace",
        ),
        CommandCenterMetric(
            key="tests",
            label="Test cases",
            value=str(tests_count),
            subvalue="QA Agent output",
            status=_status(tests_count > 0),
            href=f"{base}/workspace#tests",
        ),
        CommandCenterMetric(
            key="risks",
            label="Risks",
            value=str(risks_count) if risks_count else (
                f"{risk_score}/100" if risk_score is not None else "—"
            ),
            subvalue="Pipeline + prediction",
            status=_status(risks_count > 0 or risk_score is not None, (risk_score or 0) >= 60),
            href=f"{base}/studio",
        ),
        CommandCenterMetric(
            key="effort",
            label="Effort",
            value=f"{total_pts} pts" if total_pts else "—",
            subvalue=f"{developers} devs · {weeks} wk · ${int(cost):,}" if total_pts else "Run AI Studio",
            status=_status(total_pts > 0),
            href=f"{base}/studio",
        ),
        CommandCenterMetric(
            key="sprint",
            label="Sprint plan",
            value=sprint_label or "—",
            subvalue=(
                f"{project.auto_sprint_plan.total_story_points} pts"
                if project.auto_sprint_plan
                else "Auto or team plan"
            ),
            status=_status(bool(sprint_label)),
            href=f"{base}/sprint-plan",
        ),
        CommandCenterMetric(
            key="pipeline",
            label="Multi-agent pipeline",
            value=f"{_pipeline_done(project)}/{len(CONTROL_TOWER_STAGES)}",
            subvalue="Analyst → PM → Architect → QA → Scrum",
            status=_status(_pipeline_done(project) >= 3),
            href=f"{base}/control-tower",
        ),
    ]

    return CommandCenterSnapshot(
        project_id=pid,
        project_name=project.name,
        metrics=metrics,
        requirement_score=quality_score,
        ambiguities_count=amb_count,
        tasks_count=tasks_count,
        test_cases_count=tests_count,
        stories_count=stories_count,
        risks_count=risks_count,
        risk_score=risk_score,
        total_story_points=total_pts,
        estimated_weeks=weeks,
        estimated_cost_usd=cost,
        suggested_sprint=sprint_label,
        pipeline_done=_pipeline_done(project),
        pipeline_total=len(CONTROL_TOWER_STAGES),
    )
