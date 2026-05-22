"""Effort Estimation Engine.

Outputs:

    {
      "story_points": 8,
      "complexity": "medium",
      "estimated_hours": 24
    }

Hybrid: a deterministic heuristic ALWAYS produces a baseline (so the
endpoint never returns nothing), and the LLM refines/overrides when it
is enabled and confident.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import EffortComplexity, EffortEstimate, Project
from .ai_service import get_ai_service
from .delivery_cost import attach_delivery_rollup, sum_project_story_points

logger = logging.getLogger("helix.effort_estimator")


# ---------- Fibonacci helpers --------------------------------------------- #

_FIB = [1, 2, 3, 5, 8, 13, 21]


def _to_fib(n: float) -> int:
    n = max(1.0, float(n))
    best = _FIB[0]
    best_diff = abs(best - n)
    for f in _FIB[1:]:
        d = abs(f - n)
        if d < best_diff:
            best, best_diff = f, d
    return best


# ---------- Complexity drivers (keyword-based heuristic) ----------------- #


_COMPLEXITY_KEYWORDS: List[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(otp|two[- ]?factor|2fa|mfa)\b", re.I), 2, "Multi-factor / OTP flow"),
    (re.compile(r"\b(oauth|sso|saml|openid)\b", re.I), 3, "Federated auth / SSO"),
    (re.compile(r"\b(authentication|authoriz(ation|e)|login|sign[- ]?up)\b", re.I), 1, "Authentication"),
    (re.compile(r"\b(payment|billing|invoice|subscription|stripe|razorpay)\b", re.I), 3, "Payments"),
    (re.compile(r"\b(third[- ]?party|external\s+api|integrat(e|ion)|webhook)\b", re.I), 2, "External integration"),
    (re.compile(r"\b(real[- ]?time|websocket|streaming|sse)\b", re.I), 2, "Real-time"),
    (re.compile(r"\b(scal(e|ing|ability)|throughput|concurren(t|cy))\b", re.I), 2, "Scalability"),
    (re.compile(r"\b(migrat(e|ion)|backfill|data[- ]?move|re[- ]?architect)\b", re.I), 3, "Data migration"),
    (re.compile(r"\b(gdpr|hipaa|pci|sox|compliance|audit\s+trail)\b", re.I), 2, "Compliance"),
    (re.compile(r"\b(machine\s+learning|ml\s+model|llm|inference|embedding)\b", re.I), 3, "ML / inference"),
    (re.compile(r"\b(report|dashboard|analytics|kpi)\b", re.I), 1, "Reporting / dashboards"),
    (re.compile(r"\b(notification|email|sms|push)\b", re.I), 1, "Notifications"),
    (re.compile(r"\b(file\s+upload|attach(ment)?|s3|object\s+store)\b", re.I), 1, "File handling"),
    (re.compile(r"\b(role|rbac|permission|access\s+control)\b", re.I), 2, "Access control"),
    (re.compile(r"\b(search|elastic|index(ing)?)\b", re.I), 2, "Search"),
    (re.compile(r"\b(localiz(ation|e)|i18n|multi[- ]?tenant)\b", re.I), 2, "i18n / multi-tenancy"),
]


_COMPLEXITY_FROM_POINTS = [
    (1, EffortComplexity.TRIVIAL),
    (2, EffortComplexity.LOW),
    (5, EffortComplexity.MEDIUM),
    (8, EffortComplexity.HIGH),
    (21, EffortComplexity.VERY_HIGH),
]


def _complexity_from_points(points: int) -> EffortComplexity:
    for cap, comp in _COMPLEXITY_FROM_POINTS:
        if points <= cap:
            return comp
    return EffortComplexity.VERY_HIGH


def _heuristic_estimate(text: str) -> EffortEstimate:
    text = (text or "").strip()
    if not text:
        return EffortEstimate(
            story_points=0,
            complexity=EffortComplexity.TRIVIAL,
            estimated_hours=0.0,
            confidence=0.0,
            drivers=[],
            rationale="No requirement text provided.",
        )

    # Base score from text length: small = 1, paragraph = 3, doc = 5
    length = len(text)
    if length < 80:
        base = 1
    elif length < 180:
        base = 2
    elif length < 400:
        base = 3
    elif length < 800:
        base = 5
    else:
        base = 8

    # Sentence-count nudge — long requirements often hide more scope.
    sentences = max(1, len(re.findall(r"[.!?]+\s", text)))
    if sentences >= 6:
        base += 1

    drivers: List[str] = []
    bumps = 0
    seen: set[str] = set()
    for pat, weight, label in _COMPLEXITY_KEYWORDS:
        if pat.search(text) and label not in seen:
            seen.add(label)
            drivers.append(label)
            bumps += weight
    raw = base + bumps
    points = _to_fib(raw)
    complexity = _complexity_from_points(points)

    # Hours: ~3.5h per point, scaled by complexity.
    multipliers = {
        EffortComplexity.TRIVIAL: 2.5,
        EffortComplexity.LOW: 3.0,
        EffortComplexity.MEDIUM: 3.5,
        EffortComplexity.HIGH: 4.5,
        EffortComplexity.VERY_HIGH: 5.5,
    }
    hours = round(points * multipliers[complexity], 1)

    rationale_parts = [
        f"Base {base} sp from requirement length",
    ]
    if drivers:
        rationale_parts.append(
            f"+{bumps} sp from drivers: {', '.join(drivers[:5])}"
        )
    rationale_parts.append(f"Snapped to Fibonacci → {points} sp ({complexity.value}).")

    confidence = 0.45 + min(0.35, 0.05 * len(drivers)) + (0.05 if length > 400 else 0)

    return EffortEstimate(
        story_points=points,
        complexity=complexity,
        estimated_hours=hours,
        confidence=round(min(1.0, confidence), 2),
        drivers=drivers,
        rationale=" · ".join(rationale_parts),
        method="heuristic",
    )


# ---------- AI refinement ------------------------------------------------- #


_AI_SYSTEM = """You are a Tech Lead estimating effort. Be calibrated:
small CRUD = 1-2 sp, real feature = 3-5 sp, multi-component =
8 sp, system-shaping = 13 sp, multi-team = 21 sp. Return ONLY valid
JSON. story_points MUST be a Fibonacci number from this set:
1, 2, 3, 5, 8, 13, 21.""".strip()


_AI_SCHEMA = """{
  "story_points": 8,
  "complexity": "trivial|low|medium|high|very_high",
  "estimated_hours": 24,
  "confidence": 0.7,
  "drivers": ["string — the top 2-5 cost drivers"],
  "rationale": "string — 1-2 sentence justification"
}"""


_VALID_FIB = set(_FIB)
_VALID_COMPLEXITY = {c.value for c in EffortComplexity}


async def _ai_estimate(text: str, baseline: EffortEstimate) -> Optional[EffortEstimate]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    user = (
        "Requirement to estimate:\n"
        f"---\n{text[:4000]}\n---\n\n"
        "Heuristic baseline (you may agree, override, or refine):\n"
        f"  story_points: {baseline.story_points}\n"
        f"  complexity: {baseline.complexity.value}\n"
        f"  estimated_hours: {baseline.estimated_hours}\n"
        f"  drivers: {', '.join(baseline.drivers) or 'none'}\n\n"
        f"Return ONLY JSON in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=900)
    except Exception:  # pragma: no cover — defensive
        logger.exception("Effort AI estimation failed")
        return None

    try:
        sp_raw = int(data.get("story_points") or 0)
    except (TypeError, ValueError):
        return None
    if sp_raw not in _VALID_FIB:
        sp_raw = _to_fib(sp_raw or baseline.story_points)

    complexity_raw = str(data.get("complexity") or "").strip().lower()
    if complexity_raw not in _VALID_COMPLEXITY:
        complexity = _complexity_from_points(sp_raw)
    else:
        complexity = EffortComplexity(complexity_raw)

    try:
        hours = float(data.get("estimated_hours") or 0)
    except (TypeError, ValueError):
        hours = baseline.estimated_hours
    hours = max(0.5, round(hours, 1))

    try:
        confidence = float(data.get("confidence") or baseline.confidence)
    except (TypeError, ValueError):
        confidence = baseline.confidence
    confidence = max(0.0, min(1.0, confidence))

    drivers = [
        str(d).strip()
        for d in (data.get("drivers") or [])
        if str(d).strip()
    ][:6] or baseline.drivers

    rationale = str(data.get("rationale") or "").strip() or baseline.rationale

    return EffortEstimate(
        story_points=sp_raw,
        complexity=complexity,
        estimated_hours=hours,
        confidence=round(confidence, 2),
        drivers=drivers,
        rationale=rationale,
        method="hybrid",
    )


# ---------- Public API ---------------------------------------------------- #


async def estimate_effort(
    text: str,
    *,
    use_ai: bool = True,
    total_story_points: Optional[int] = None,
    developers: Optional[int] = None,
) -> EffortEstimate:
    baseline = _heuristic_estimate(text)
    if use_ai:
        refined = await _ai_estimate(text, baseline)
        est = refined or baseline
    else:
        est = baseline
    pts = total_story_points if total_story_points is not None else est.story_points
    return attach_delivery_rollup(est, total_story_points=pts, developers=developers)


async def estimate_effort_for_project(
    project: Project,
    *,
    use_ai: bool = True,
    developers: Optional[int] = None,
) -> EffortEstimate:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    total_pts = sum_project_story_points(project)
    return await estimate_effort(
        text,
        use_ai=use_ai,
        total_story_points=total_pts or None,
        developers=developers,
    )


def to_simple_json(est: EffortEstimate) -> Dict[str, Any]:
    """Render the canonical user-facing shape."""
    return {
        "story_points": est.story_points,
        "complexity": est.complexity.value,
        "estimated_hours": est.estimated_hours,
        "total_story_points": est.total_story_points or est.story_points,
        "developers": est.developers,
        "estimated_weeks": est.estimated_weeks,
        "estimated_cost_usd": est.estimated_cost_usd,
    }
