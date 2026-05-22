"""SDLC Digital Twin (Feature 19).

Walks the project artifacts and assembles a 6-stage pipeline view
that mirrors a real software delivery lifecycle. Each stage is
graded "complete / in_progress / pending / blocked" based on which
artifacts have been generated; the front-end renders this as an
animated flow.

Stages:
    Requirement → Analysis → Design → Development → Testing → Deployment

This is intentionally read-only and deterministic (no LLM needed) —
the differentiator is the *visual* assembly of every artifact the
platform has already produced into a single mental model.
"""
from __future__ import annotations

from typing import List

from ..models import (
    DigitalTwinReport,
    Project,
    Severity,
    TwinArtifact,
    TwinStage,
)


def _short(text: str, n: int = 90) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def _status(progress: int) -> str:
    if progress >= 100:
        return "complete"
    if progress > 0:
        return "in_progress"
    return "pending"


def _stage_requirement(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    if p.raw_input:
        arts.append(TwinArtifact(
            kind="note",
            label="Source requirement captured",
            detail=_short(p.raw_input, 200),
            icon="◆",
        ))
    if p.source_clauses:
        arts.append(TwinArtifact(
            kind="metric",
            label=f"{len(p.source_clauses)} clauses parsed",
            detail="Each downstream artifact links back to a source clause for traceability.",
            icon="¶",
        ))
    if p.requirement_brief:
        arts.append(TwinArtifact(
            kind="note",
            label="Requirement brief written",
            detail=_short(getattr(p.requirement_brief, "summary", "") or "", 160),
            icon="✎",
        ))
    if p.summary:
        arts.append(TwinArtifact(
            kind="note",
            label=getattr(p.summary, "title", "") or "Requirement summary",
            detail=_short(getattr(p.summary, "objective", "") or getattr(p.summary, "one_liner", ""), 160),
            icon="✦",
        ))

    progress = 0
    if p.raw_input:
        progress = 40
    if p.source_clauses:
        progress = 70
    if p.summary or p.requirement_brief:
        progress = 100

    return TwinStage(
        id="requirement",
        label="Requirement",
        status=_status(progress),
        progress=progress,
        summary="Capture intent and parse it into traceable clauses.",
        artifacts=arts,
        metrics={"clauses": len(p.source_clauses or [])},
    )


def _stage_analysis(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    if p.ambiguities:
        unresolved = sum(1 for a in p.ambiguities if not getattr(a, "resolved", False))
        arts.append(TwinArtifact(
            kind="risk",
            label=f"{len(p.ambiguities)} ambiguities ({unresolved} open)",
            detail="Items the team must clarify before development.",
            icon="?",
            severity=Severity.MEDIUM if unresolved else Severity.LOW,
        ))
    if p.risks:
        worst = max(
            (getattr(r, "severity", Severity.MEDIUM) for r in p.risks),
            key=lambda s: ["low", "medium", "high", "critical"].index(
                s.value if hasattr(s, "value") else str(s)
            ),
            default=Severity.LOW,
        )
        arts.append(TwinArtifact(
            kind="risk",
            label=f"{len(p.risks)} risks identified",
            detail=f"Worst severity: {worst.value if hasattr(worst, 'value') else worst}",
            icon="⚠",
            severity=worst,
        ))
    if p.review_board_report:
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Review Board confidence {int(p.review_board_report.confidence)}/100",
            detail=f"Grade {p.review_board_report.grade} — five specialist agents.",
            icon="⚖",
        ))
    if p.quality_score_report:
        qs = p.quality_score_report
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Quality {int(getattr(qs, 'quality_score', 0))} · Ambiguity {int(getattr(qs, 'ambiguity_score', 0))}",
            detail="Hybrid heuristic + AI scoring of the requirement.",
            icon="✦",
        ))
    if p.defect_prediction and p.defect_prediction.high_risk_modules:
        arts.append(TwinArtifact(
            kind="risk",
            label=f"Defect-prone modules: {', '.join(p.defect_prediction.high_risk_modules[:3])}",
            detail="Predicted from requirement complexity.",
            icon="✺",
            severity=Severity.HIGH,
        ))

    progress = 0
    if p.ambiguities is not None or p.risks is not None:
        progress += 30 if (p.ambiguities or p.risks) else 0
    if p.review_board_report:
        progress += 35
    if p.quality_score_report:
        progress += 35
    progress = min(progress, 100)

    return TwinStage(
        id="analysis",
        label="Analysis",
        status=_status(progress),
        progress=progress,
        summary="Multi-agent review surfaces ambiguities, risks, and quality issues.",
        artifacts=arts,
        metrics={
            "ambiguities": len(p.ambiguities or []),
            "risks": len(p.risks or []),
        },
    )


def _stage_design(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    if p.architecture_brief:
        comp = len(p.architecture_brief.components or [])
        arts.append(TwinArtifact(
            kind="component",
            label=f"Architecture brief — {comp} components",
            detail=_short(getattr(p.architecture_brief, "overview", "") or "", 160),
            icon="◭",
        ))
    if p.architecture_diagram and p.architecture_diagram.mermaid:
        arts.append(TwinArtifact(
            kind="component",
            label=f"Architecture diagram ({p.architecture_diagram.nodes_count} nodes)",
            detail=_short(p.architecture_diagram.description or "", 140),
            icon="✦",
        ))
    if p.api_contract_suite and p.api_contract_suite.contracts:
        arts.append(TwinArtifact(
            kind="api",
            label=f"{len(p.api_contract_suite.contracts)} API contracts drafted",
            detail="Endpoints, request/response schemas, OpenAPI export ready.",
            icon="↔",
        ))
    if p.database_schema and p.database_schema.tables:
        arts.append(TwinArtifact(
            kind="component",
            label=f"DB schema — {len(p.database_schema.tables)} tables",
            detail="ER diagram + DDL generated from the requirement.",
            icon="▤",
        ))
    if p.impact_report:
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Blast radius {int(p.impact_report.blast_radius)}/100",
            detail=_short(p.impact_report.summary or "", 140),
            icon="⤳",
        ))

    progress = 0
    if p.architecture_brief:
        progress += 35
    if p.architecture_diagram:
        progress += 20
    if p.api_contract_suite:
        progress += 15
    if p.database_schema:
        progress += 15
    if p.impact_report:
        progress += 15
    progress = min(progress, 100)

    return TwinStage(
        id="design",
        label="Design",
        status=_status(progress),
        progress=progress,
        summary="Architecture, APIs, schemas and impact analysis crystallise the solution.",
        artifacts=arts,
        metrics={
            "components": len(p.architecture_brief.components if p.architecture_brief else []),
            "apis": len(p.api_contract_suite.contracts if p.api_contract_suite else []),
            "tables": len(p.database_schema.tables if p.database_schema else []),
        },
    )


def _stage_development(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    if p.stories:
        arts.append(TwinArtifact(
            kind="story",
            label=f"{len(p.stories)} user stories",
            detail="Persona / goal / benefit + acceptance criteria.",
            icon="✦",
        ))
    if p.tasks:
        arts.append(TwinArtifact(
            kind="task",
            label=f"{len(p.tasks)} engineering tasks",
            detail="Tasks broken down with estimates and dependencies.",
            icon="▣",
        ))
    if p.jira_backlog:
        ep_title = getattr(getattr(p.jira_backlog, "epic", None), "title", "") or "Epic"
        arts.append(TwinArtifact(
            kind="task",
            label=f"Jira backlog — {ep_title}",
            detail=f"{len(p.jira_backlog.stories or [])} stories · {len(p.jira_backlog.tasks or [])} tasks · {len(p.jira_backlog.subtasks or [])} subtasks",
            icon="▤",
        ))
    if p.team_sprint_plan and getattr(p.team_sprint_plan, "sprints", None):
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Sprint plan — {len(p.team_sprint_plan.sprints)} sprints",
            detail=f"Velocity {int(getattr(p.team_sprint_plan, 'velocity_points_per_sprint', 0))} pts/sprint",
            icon="⏱",
        ))
    if p.requirement_estimate:
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Estimate — {p.requirement_estimate.story_points} pts · {p.requirement_estimate.estimated_hours}h",
            detail=f"Complexity: {p.requirement_estimate.complexity.value if hasattr(p.requirement_estimate.complexity, 'value') else p.requirement_estimate.complexity}",
            icon="∑",
        ))

    progress = 0
    if p.stories:
        progress += 30
    if p.tasks:
        progress += 30
    if p.jira_backlog:
        progress += 20
    if p.team_sprint_plan:
        progress += 20
    progress = min(progress, 100)

    return TwinStage(
        id="development",
        label="Development",
        status=_status(progress),
        progress=progress,
        summary="Stories, tasks, sprint plan and Jira-ready backlog.",
        artifacts=arts,
        metrics={
            "stories": len(p.stories or []),
            "tasks": len(p.tasks or []),
        },
    )


def _stage_testing(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    by_type: dict[str, int] = {}
    for tc in (p.test_cases or []):
        t = str(getattr(tc, "type", "")).split(".")[-1].lower()
        by_type[t] = by_type.get(t, 0) + 1
    if p.test_cases:
        breakdown = " · ".join(f"{n} {t}" for t, n in by_type.items()) or f"{len(p.test_cases)} cases"
        arts.append(TwinArtifact(
            kind="test",
            label=f"{len(p.test_cases)} test cases authored",
            detail=breakdown,
            icon="✓",
        ))
    if p.generated_test_suite:
        ts = p.generated_test_suite
        total = sum(len(c.tests) for c in (ts.categories or []))
        arts.append(TwinArtifact(
            kind="test",
            label=f"Generated test suite — {total} cases",
            detail=f"{len(ts.categories or [])} categories (functional / negative / boundary / security / regression).",
            icon="⌘",
        ))
    if p.traceability_matrix:
        cov = p.traceability_matrix.coverage
        if cov.total_requirements:
            pct = int(round(100 * cov.requirements_with_tests / cov.total_requirements))
            arts.append(TwinArtifact(
                kind="metric",
                label=f"Test coverage {pct}%",
                detail=f"{cov.requirements_with_tests}/{cov.total_requirements} requirements with at least one test.",
                icon="⛓",
            ))

    progress = 0
    if p.test_cases:
        progress += 50
    if p.generated_test_suite:
        progress += 35
    if p.traceability_matrix:
        progress += 15
    progress = min(progress, 100)

    return TwinStage(
        id="testing",
        label="Testing",
        status=_status(progress),
        progress=progress,
        summary="Automated test suite plus traceability gives a confident gate.",
        artifacts=arts,
        metrics={"tests": len(p.test_cases or [])},
    )


def _stage_deployment(p: Project) -> TwinStage:
    arts: List[TwinArtifact] = []
    if p.delivery_readiness:
        rd = p.delivery_readiness
        sev = (
            Severity.CRITICAL if rd.readiness < 50 else
            Severity.HIGH if rd.readiness < 75 else
            Severity.MEDIUM if rd.readiness < 90 else
            Severity.LOW
        )
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Readiness {rd.readiness}/100 — {rd.status.replace('_', ' ')}",
            detail=_short(rd.summary or "", 140),
            icon="◎",
            severity=sev,
        ))
        for b in (rd.blocking_items or [])[:3]:
            arts.append(TwinArtifact(
                kind="risk",
                label=b,
                detail="Blocking the release until resolved.",
                icon="●",
                severity=Severity.HIGH,
            ))
    if p.pm_forecast:
        arts.append(TwinArtifact(
            kind="metric",
            label=f"Timeline {p.pm_forecast.timeline} · {p.pm_forecast.release_risk} risk",
            detail=" → ".join(p.pm_forecast.critical_path[:4]) if p.pm_forecast.critical_path else "Critical path: TBD",
            icon="↦",
        ))
    if p.requirement_risk:
        arts.append(TwinArtifact(
            kind="risk",
            label=f"Predicted release risk: {p.requirement_risk.risk_level.value if hasattr(p.requirement_risk.risk_level, 'value') else p.requirement_risk.risk_level}",
            detail=", ".join(p.requirement_risk.reasons[:3]) if p.requirement_risk.reasons else "",
            icon="⚠",
        ))

    progress = 0
    if p.delivery_readiness:
        progress = max(progress, p.delivery_readiness.readiness)
    if not progress and p.pm_forecast:
        progress = 40
    progress = min(progress, 100)

    return TwinStage(
        id="deployment",
        label="Deployment",
        status="blocked" if (p.delivery_readiness and p.delivery_readiness.blocking_items and p.delivery_readiness.readiness < 75)
        else _status(progress),
        progress=progress,
        summary="Release readiness, blockers, timeline and rollout risk.",
        artifacts=arts,
        metrics={},
    )


def build_digital_twin(project: Project) -> DigitalTwinReport:
    stages = [
        _stage_requirement(project),
        _stage_analysis(project),
        _stage_design(project),
        _stage_development(project),
        _stage_testing(project),
        _stage_deployment(project),
    ]
    overall = int(round(sum(s.progress for s in stages) / max(1, len(stages))))
    completed = sum(1 for s in stages if s.status == "complete")
    headline = f"{completed}/{len(stages)} stages complete · {overall}% overall progress"
    return DigitalTwinReport(
        project_id=project.id,
        title=project.name or "Project",
        stages=stages,
        overall_progress=overall,
        headline=headline,
        method="heuristic",
    )


__all__ = ["build_digital_twin"]
