"""Executive Delivery Summary — the one-screen 'AI delivery manager'
verdict that the Approve & Export panel renders.

Aggregates every artifact the multi-agent pipeline produced into:

    Requirements · Epics · Stories · Tasks · APIs · Test Cases ·
    Risks · Ambiguities · Architecture Components · Readiness · Quality ·
    Sprints · Estimated Delivery (weeks) · Projected Cost · GO/NO-GO

The verdict logic is deterministic (not LLM-dependent) so judges
always see a stable answer even when Azure is offline:

    GO              → readiness >= 80, quality >= 70, no critical risks
    GO_WITH_CAVEATS → readiness >= 60, ≤1 critical risk
    NO_GO           → otherwise

Cost is a transparent estimate:

    total_hours      = sum(t.estimate_hours) or  total_points * 6
    projected_cost   = total_hours * blended_hourly_rate ($150 default)
    hours_saved      = clauses * 2  +  stories * 6  (analysis + refinement)
    cost_saved       = hours_saved * blended_hourly_rate

The blended rate matches mid-market consulting (engineer + PM + QA
loaded cost) and is exposed in the response so judges can re-do the
math live on stage.
"""
from __future__ import annotations

from typing import Iterable, List

from ..models import (
    DeliveryHeadlineMetric,
    DeliverySprintTile,
    DeliverySummary,
    DeliveryVerdict,
    Project,
    Severity,
)


_BLENDED_HOURLY_RATE = 150.0  # USD, mid-market loaded engineer + PM + QA
_HOURS_PER_POINT = 6.0        # fall-back when tasks have no estimate_hours
_MANUAL_HOURS_PER_CLAUSE = 2.0  # judge-defensible analyst effort
_MANUAL_HOURS_PER_STORY = 6.0   # PM+BA refinement per story
_MANUAL_HOURS_PER_TEST = 1.5    # QA case authoring
_SPRINT_WEEKS_DEFAULT = 2.0
_VELOCITY_POINTS_PER_SPRINT = 20.0


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


def _epic_count(project: Project) -> int:
    """Number of natural epics in the backlog.

    A real backlog has multiple epics (auth, billing, ordering, etc.)
    but our pipeline emits ONE `BacklogEpic` umbrella; we infer the
    real epic count by clustering stories on their leading meaningful
    word ("Customer ...", "Order ...", "Provisioning ...").

    Falls back to ``max(1, ceil(stories / 5))`` so a 50-story PRD
    never reports "1 epic".
    """
    if not project.stories:
        # If we have a backlog epic placeholder but no stories yet,
        # still report 1 so the dashboard shows "Epics: 1" not "0".
        return 1 if project.jira_backlog else 0

    keys: set[str] = set()
    for s in project.stories:
        head = (s.title or s.goal or "").strip().split()
        if not head:
            continue
        # Use the first 2 meaningful tokens as an epic key.
        token = " ".join(w.lower() for w in head[:2])
        keys.add(token)

    inferred = len(keys)
    fallback = max(1, -(-len(project.stories) // 5))  # ceil division
    return max(inferred, fallback)


def _architecture_components_count(project: Project) -> int:
    diagram = project.architecture_diagram
    if not diagram:
        return 0
    return sum(len(layer.items or []) for layer in (diagram.layers or []))


def _apis_count(project: Project) -> int:
    suite = project.api_contract_suite
    if not suite:
        return 0
    return len(suite.contracts or [])


def _readiness_score(project: Project) -> int:
    if project.delivery_readiness_center and project.delivery_readiness_center.readiness:
        return int(project.delivery_readiness_center.readiness)
    if project.delivery_readiness:
        return int(project.delivery_readiness.readiness or 0)
    return 0


def _quality_score(project: Project) -> int:
    rep = project.quality_score_report
    if not rep:
        return 0
    score = getattr(rep, "overall_score", 0) or getattr(rep, "score", 0) or 0
    return int(round(float(score)))


def _confidence_score(project: Project) -> int:
    rep = project.review_board_report
    if not rep:
        return 0
    score = getattr(rep, "confidence_score", 0) or getattr(rep, "confidence", 0) or 0
    return int(round(float(score)))


def _critical_risk_count(project: Project) -> int:
    return sum(
        1
        for r in (project.risks or [])
        if r.severity in (Severity.HIGH, Severity.CRITICAL)
    )


# --------------------------------------------------------------------- #
# Sprint plan
# --------------------------------------------------------------------- #


def _collect_sprints(project: Project) -> List[DeliverySprintTile]:
    """Prefer the team sprint plan (story-level), then the task sprint
    plan (`SprintPlan.items`), then auto sprint plan (one tile)."""
    tiles: List[DeliverySprintTile] = []

    if project.team_sprint_plan and project.team_sprint_plan.sprints:
        for s in project.team_sprint_plan.sprints:
            tiles.append(
                DeliverySprintTile(
                    label=s.label or f"Sprint {s.sprint_number}",
                    number=int(s.sprint_number or len(tiles) + 1),
                    weeks=float(s.weeks or _SPRINT_WEEKS_DEFAULT),
                    planned_points=int(s.planned_points or 0),
                    goal=s.goal or "",
                )
            )
        return tiles

    if project.sprint_plan and project.sprint_plan.items:
        for s in project.sprint_plan.items:
            tiles.append(
                DeliverySprintTile(
                    label=f"Sprint {s.sprint_number}",
                    number=int(s.sprint_number or len(tiles) + 1),
                    weeks=float(s.weeks or _SPRINT_WEEKS_DEFAULT),
                    planned_points=int(s.total_points or 0),
                    goal=s.goal or "",
                )
            )
        return tiles

    if project.auto_sprint_plan and project.auto_sprint_plan.tasks:
        plan = project.auto_sprint_plan
        tiles.append(
            DeliverySprintTile(
                label=plan.suggested_sprint or "Sprint 1",
                number=int(plan.suggested_sprint_number or 1),
                weeks=_SPRINT_WEEKS_DEFAULT,
                planned_points=int(plan.total_story_points or 0),
                goal=plan.rationale[:80] if plan.rationale else "",
            )
        )
    return tiles


# --------------------------------------------------------------------- #
# Effort & cost
# --------------------------------------------------------------------- #


def _total_points(project: Project) -> int:
    if project.team_sprint_plan and project.team_sprint_plan.total_points:
        return int(project.team_sprint_plan.total_points)
    if project.sprint_plan and project.sprint_plan.total_points:
        return int(project.sprint_plan.total_points)
    if project.auto_sprint_plan and project.auto_sprint_plan.total_story_points:
        return int(project.auto_sprint_plan.total_story_points)
    return sum(int(t.estimate_points or 0) for t in (project.tasks or []))


def _total_hours(project: Project) -> float:
    direct = sum(float(t.estimate_hours or 0) for t in (project.tasks or []))
    if direct > 0:
        return direct
    # Fall back: derive from story points.
    return float(_total_points(project)) * _HOURS_PER_POINT


def _projected_cost(total_hours: float) -> float:
    return round(total_hours * _BLENDED_HOURLY_RATE, 2)


def _estimated_delivery_weeks(project: Project, sprints: Iterable[DeliverySprintTile]) -> float:
    weeks = sum(s.weeks for s in sprints)
    if weeks > 0:
        return round(weeks, 1)
    if project.team_sprint_plan and project.team_sprint_plan.total_weeks:
        return round(float(project.team_sprint_plan.total_weeks), 1)
    if project.sprint_plan and project.sprint_plan.total_weeks:
        return round(float(project.sprint_plan.total_weeks), 1)
    # Pure fallback: points / velocity * 2 weeks
    points = _total_points(project)
    if points:
        sprints_needed = max(1, -(-points // int(_VELOCITY_POINTS_PER_SPRINT)))
        return round(sprints_needed * _SPRINT_WEEKS_DEFAULT, 1)
    return 0.0


# --------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------- #


def _compute_verdict(
    *,
    readiness: int,
    quality: int,
    critical_risks: int,
    sprints: int,
    apis: int,
    stories: int,
) -> tuple[DeliveryVerdict, str, List[str], List[str]]:
    reasons: List[str] = []
    blockers: List[str] = []

    if stories == 0:
        blockers.append("No user stories generated yet.")
    if sprints == 0:
        blockers.append("Sprint plan not generated.")
    if apis == 0:
        blockers.append("API contracts not generated.")
    if readiness < 50:
        blockers.append(f"Readiness score is {readiness}/100 (< 50).")

    # Positive signals (always shown when present)
    if readiness >= 80:
        reasons.append(f"Readiness {readiness}/100 — above 80 threshold.")
    if quality >= 70:
        reasons.append(f"Quality {quality}/100 — above 70 threshold.")
    if critical_risks == 0:
        reasons.append("No critical/high risks blocking delivery.")
    elif critical_risks <= 1:
        reasons.append(f"{critical_risks} high-severity risk(s) flagged with mitigation.")
    if sprints >= 1:
        reasons.append(f"{sprints} sprint(s) planned with capacity allocation.")

    if blockers:
        return DeliveryVerdict.NO_GO, "NO-GO", reasons, blockers

    if readiness >= 80 and quality >= 70 and critical_risks == 0:
        return DeliveryVerdict.GO, "GO", reasons, blockers

    if readiness >= 60 and critical_risks <= 1:
        return DeliveryVerdict.GO_WITH_CAVEATS, "GO with caveats", reasons, blockers

    return DeliveryVerdict.NO_GO, "NO-GO", reasons, blockers


# --------------------------------------------------------------------- #
# Hero tiles (UI render shortcut)
# --------------------------------------------------------------------- #


def _build_headline_metrics(summary: DeliverySummary) -> List[DeliveryHeadlineMetric]:
    """The exact tile order shown on the Executive Delivery dashboard."""
    return [
        DeliveryHeadlineMetric(
            key="requirements",
            label="Requirements",
            value=summary.requirements_count,
            detail="extracted clauses",
            severity="ok" if summary.requirements_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="epics",
            label="Epics",
            value=summary.epics_count,
            detail="inferred from stories",
            severity="ok" if summary.epics_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="stories",
            label="Stories",
            value=summary.stories_count,
            detail="user stories",
            severity="ok" if summary.stories_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="tasks",
            label="Tasks",
            value=summary.tasks_count,
            detail="engineering work items",
            severity="ok" if summary.tasks_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="apis",
            label="APIs",
            value=summary.apis_count,
            detail="REST contracts",
            severity="ok" if summary.apis_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="tests",
            label="Test Cases",
            value=summary.test_cases_count,
            detail="auto-generated",
            severity="ok" if summary.test_cases_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="risks",
            label="Risks",
            value=summary.risks_count,
            detail="categorised",
            severity="warn" if summary.risks_count else "ok",
        ),
        DeliveryHeadlineMetric(
            key="ambiguities",
            label="Ambiguities",
            value=summary.ambiguities_count,
            detail="flagged",
            severity="warn" if summary.ambiguities_count else "ok",
        ),
        DeliveryHeadlineMetric(
            key="architecture",
            label="Architecture Components",
            value=summary.architecture_components_count,
            detail="layers + nodes",
            severity="ok" if summary.architecture_components_count else "warn",
        ),
        DeliveryHeadlineMetric(
            key="readiness",
            label="Readiness Score",
            value=summary.readiness_score,
            detail="out of 100",
            severity=(
                "ok"
                if summary.readiness_score >= 80
                else "warn"
                if summary.readiness_score >= 60
                else "crit"
            ),
        ),
    ]


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #


def build_delivery_summary(project: Project) -> DeliverySummary:
    """Build the one-screen delivery verdict for ``project``.

    Pure computation — no DB writes, no LLM calls. Safe to call on
    every workspace load.
    """
    sprints = _collect_sprints(project)
    readiness = _readiness_score(project)
    quality = _quality_score(project)
    confidence = _confidence_score(project)
    critical_risks = _critical_risk_count(project)
    stories_count = len(project.stories or [])
    tasks_count = len(project.tasks or [])
    apis_count = _apis_count(project)
    tests_count = len(project.test_cases or [])
    risks_count = len(project.risks or [])
    amb_count = len(project.ambiguities or [])
    clauses_count = len(project.source_clauses or [])
    arch_count = _architecture_components_count(project)
    epics_count = _epic_count(project)

    total_hours = _total_hours(project)
    total_points = _total_points(project)
    weeks = _estimated_delivery_weeks(project, sprints)
    projected_cost = _projected_cost(total_hours)

    # Manual effort baseline (what a human-only team would burn)
    manual_hours = (
        clauses_count * _MANUAL_HOURS_PER_CLAUSE
        + stories_count * _MANUAL_HOURS_PER_STORY
        + tests_count * _MANUAL_HOURS_PER_TEST
    )
    cost_saved = round(manual_hours * _BLENDED_HOURLY_RATE, 2)
    weeks_saved = round(manual_hours / 40.0, 1) if manual_hours else 0.0

    verdict, verdict_label, reasons, blockers = _compute_verdict(
        readiness=readiness,
        quality=quality,
        critical_risks=critical_risks,
        sprints=len(sprints),
        apis=apis_count,
        stories=stories_count,
    )

    summary = DeliverySummary(
        project_id=project.id,
        project_name=project.name,
        requirements_count=clauses_count,
        epics_count=epics_count,
        stories_count=stories_count,
        tasks_count=tasks_count,
        apis_count=apis_count,
        test_cases_count=tests_count,
        risks_count=risks_count,
        ambiguities_count=amb_count,
        architecture_components_count=arch_count,
        readiness_score=readiness,
        quality_score=quality,
        confidence_score=confidence,
        sprints=sprints,
        sprint_count=len(sprints),
        estimated_delivery_weeks=weeks,
        estimated_total_hours=round(total_hours, 1),
        estimated_total_points=total_points,
        projected_cost_usd=projected_cost,
        blended_hourly_rate_usd=_BLENDED_HOURLY_RATE,
        verdict=verdict,
        verdict_label=verdict_label,
        verdict_reasons=reasons,
        blocking_items=blockers,
        hours_saved_vs_manual=int(round(manual_hours)),
        cost_saved_usd=cost_saved,
        weeks_saved_vs_manual=weeks_saved,
    )
    summary.headline_metrics = _build_headline_metrics(summary)
    return summary
