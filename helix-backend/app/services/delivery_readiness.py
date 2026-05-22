"""Delivery Readiness Score.

Output (canonical):

    {
      "readiness": 83,
      "blocking_items": [
        "No performance criteria",
        "No rollback strategy"
      ]
    }

Implementation:
    * Score is a weighted sum of "delivery signals" — concrete things a
      release-ready feature should have. Each signal is binary
      (achieved / not achieved) so the breakdown is easy to defend.
    * Blocking items are the unmet HIGH-weight signals.
    * Recommendations are the unmet LOW/MEDIUM-weight signals.
    * The LLM (when enabled) refines wording and adds project-specific
      blockers; it cannot fabricate green signals.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import (
    DeliveryReadiness,
    Project,
    ReadinessSignal,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.delivery_readiness")


_PERF_PAT = re.compile(
    r"\b(p\d{2}|p99|latenc\w+|throughput|rps|qps|sla|slo|response\s+time|under\s+\d+\s*(ms|s))\b",
    re.I,
)
_ROLLBACK_PAT = re.compile(r"\b(rollback|revert|fall[- ]?back|kill\s*switch|feature\s+flag)\b", re.I)
_OBSERV_PAT = re.compile(r"\b(metric|alert|dashboard|observ\w+|log(ging)?|trace)\b", re.I)
_SECURITY_PAT = re.compile(r"\b(auth|authoriz|encrypt|secur\w+|threat|owasp|pci|gdpr|hipaa)\b", re.I)
_ACCEPTANCE_PAT = re.compile(r"\b(acceptance\s+criteria|definition\s+of\s+done|success\s+criteria)\b", re.I)


def _project_text(project: Project) -> str:
    blobs: List[str] = [project.raw_input or ""]
    if project.summary:
        blobs.append(getattr(project.summary, "one_liner", "") or "")
        blobs.append(getattr(project.summary, "objective", "") or "")
        blobs.extend(getattr(project.summary, "in_scope", []) or [])
        blobs.extend(getattr(project.summary, "out_of_scope", []) or [])
        blobs.extend(getattr(project.summary, "success_metrics", []) or [])
        blobs.extend(getattr(project.summary, "assumptions", []) or [])
    if project.requirement_brief:
        blobs.extend(getattr(project.requirement_brief, "business_outcomes", []) or [])
        blobs.extend(getattr(project.requirement_brief, "success_metrics", []) or [])
    if project.architecture_brief:
        blobs.append(getattr(project.architecture_brief, "overview", "") or "")
    return "\n".join(b for b in blobs if b)


def _build_signals(project: Project) -> List[ReadinessSignal]:
    text = _project_text(project)

    has_stories = bool(project.stories)
    has_acceptance = any(
        getattr(s, "acceptance_criteria", []) for s in project.stories
    )
    has_tasks = bool(project.tasks)
    has_tests = bool(project.test_cases)
    has_security_tests = any(
        getattr(t, "type", None) and str(t.type).endswith("security")
        for t in project.test_cases
    )
    has_perf = bool(_PERF_PAT.search(text)) or any(
        getattr(t, "type", None) and str(t.type).endswith("performance")
        for t in project.test_cases
    )
    has_rollback = bool(_ROLLBACK_PAT.search(text))
    has_observability = bool(_OBSERV_PAT.search(text))
    has_security_specs = bool(_SECURITY_PAT.search(text))
    has_arch = bool(project.architecture_brief and project.architecture_brief.components)
    has_risk_register = bool(project.risks)
    has_impact_done = bool(project.impact_report)
    has_review_board = bool(project.review_board_report)
    ambig_remaining = sum(1 for a in (project.ambiguities or []) if not getattr(a, "resolved", False))
    quality_ok = (
        project.quality_score_report is not None
        and getattr(project.quality_score_report, "quality_score", 0) >= 70
    )
    backlog_ok = bool(project.jira_backlog)
    sprint_ok = bool(project.team_sprint_plan or project.sprint_plan)

    signals: List[ReadinessSignal] = [
        ReadinessSignal(
            label="User stories defined",
            weight=8,
            achieved=has_stories,
            description="Stories with personas/goals are present.",
        ),
        ReadinessSignal(
            label="Acceptance criteria",
            weight=10,
            achieved=has_acceptance,
            description="At least one story has acceptance criteria — a release gate.",
        ),
        ReadinessSignal(
            label="Tasks broken down",
            weight=6,
            achieved=has_tasks,
            description="Engineering tasks exist for the stories.",
        ),
        ReadinessSignal(
            label="Test cases authored",
            weight=10,
            achieved=has_tests,
            description="Functional/integration test cases exist.",
        ),
        ReadinessSignal(
            label="Performance criteria",
            weight=10,
            achieved=has_perf,
            description="Latency/throughput targets or perf tests are specified.",
        ),
        ReadinessSignal(
            label="Rollback / kill-switch strategy",
            weight=10,
            achieved=has_rollback,
            description="Feature flag or rollback path called out — required for safe release.",
        ),
        ReadinessSignal(
            label="Observability defined",
            weight=7,
            achieved=has_observability,
            description="Metrics, logs, alerts, or dashboards mentioned.",
        ),
        ReadinessSignal(
            label="Security considerations",
            weight=8,
            achieved=has_security_specs or has_security_tests,
            description="Security/compliance is in scope or covered by tests.",
        ),
        ReadinessSignal(
            label="Architecture brief",
            weight=6,
            achieved=has_arch,
            description="Components & dependencies have been mapped.",
        ),
        ReadinessSignal(
            label="Risk register",
            weight=6,
            achieved=has_risk_register,
            description="Risks have been enumerated.",
        ),
        ReadinessSignal(
            label="Impact analysis run",
            weight=5,
            achieved=has_impact_done,
            description="Blast-radius analysis has been generated.",
        ),
        ReadinessSignal(
            label="Multi-agent review",
            weight=5,
            achieved=has_review_board,
            description="Cross-discipline review board has approved.",
        ),
        ReadinessSignal(
            label="Ambiguities resolved",
            weight=6,
            achieved=ambig_remaining == 0 and project.ambiguities is not None,
            description=f"Open ambiguities: {ambig_remaining}.",
        ),
        ReadinessSignal(
            label="Quality score ≥ 70",
            weight=6,
            achieved=quality_ok,
            description="Requirement quality score meets the release bar.",
        ),
        ReadinessSignal(
            label="Backlog generated",
            weight=4,
            achieved=backlog_ok,
            description="A Jira-style backlog exists.",
        ),
        ReadinessSignal(
            label="Sprint plan ready",
            weight=4,
            achieved=sprint_ok,
            description="Sprint capacity & sequencing have been planned.",
        ),
    ]
    return signals


def _score_status(score: int) -> str:
    if score >= 90:
        return "ready"
    if score >= 75:
        return "ready_with_caveats"
    if score >= 50:
        return "preparing"
    return "not_ready"


def _heuristic_readiness(project: Project) -> DeliveryReadiness:
    signals = _build_signals(project)
    if not signals:
        return DeliveryReadiness(summary="Project has no signals to evaluate.")

    total_w = sum(s.weight for s in signals) or 1
    earned = sum(s.weight for s in signals if s.achieved)
    score = int(round(100 * earned / total_w))

    blocking_items: List[str] = []
    recommendations: List[str] = []
    for s in signals:
        if s.achieved:
            continue
        # High-weight gaps block the release.
        if s.weight >= 8:
            blocking_items.append(f"No {s.label.lower()}")
        else:
            recommendations.append(s.label)

    summary = (
        f"Readiness {score}/100 — {len(blocking_items)} blocker"
        f"{'' if len(blocking_items) == 1 else 's'}, "
        f"{len(recommendations)} recommendation"
        f"{'' if len(recommendations) == 1 else 's'}."
    )

    return DeliveryReadiness(
        readiness=score,
        status=_score_status(score),
        blocking_items=blocking_items,
        recommendations=recommendations,
        signals=signals,
        summary=summary,
        method="heuristic",
    )


# ---------- AI augmentation -------------------------------------------- #


_AI_SYSTEM = (
    "You are a Release Manager. From the heuristic readiness signals "
    "and project context, rewrite blocking_items and recommendations "
    "with project-specific phrasing. NEVER fabricate green signals. "
    "Output ONLY valid JSON."
)

_AI_SCHEMA = """{
  "blocking_items": ["string — short, imperative"],
  "recommendations": ["string"],
  "summary": "string — 1-2 sentences"
}"""


async def _ai_augment(project: Project, baseline: DeliveryReadiness) -> Optional[DeliveryReadiness]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    signals_blob = "\n".join(
        f"  - [{'X' if s.achieved else ' '}] {s.label} (w={s.weight})"
        for s in baseline.signals
    )
    user = (
        f"Project: {project.name}\n"
        f"Requirement (truncated):\n---\n{(project.raw_input or '')[:2400]}\n---\n\n"
        f"Heuristic signals:\n{signals_blob}\n\n"
        f"Heuristic blocking items: {baseline.blocking_items}\n"
        f"Heuristic recommendations: {baseline.recommendations}\n\n"
        f"Return JSON in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=1400)
    except Exception:
        logger.exception("Readiness AI failed")
        return None

    blocking = [
        str(s).strip()
        for s in (data.get("blocking_items") or [])
        if str(s).strip()
    ]
    recs = [
        str(s).strip()
        for s in (data.get("recommendations") or [])
        if str(s).strip()
    ]
    summary = str(data.get("summary") or "").strip()

    return DeliveryReadiness(
        readiness=baseline.readiness,
        status=baseline.status,
        blocking_items=blocking or baseline.blocking_items,
        recommendations=recs or baseline.recommendations,
        signals=baseline.signals,
        summary=summary or baseline.summary,
        method="hybrid",
    )


async def assess_readiness(project: Project, *, use_ai: bool = True) -> DeliveryReadiness:
    baseline = _heuristic_readiness(project)
    if not use_ai:
        return baseline
    refined = await _ai_augment(project, baseline)
    return refined or baseline


def to_simple_json(r: DeliveryReadiness) -> Dict[str, Any]:
    return {
        "readiness": r.readiness,
        "blocking_items": list(r.blocking_items),
    }
