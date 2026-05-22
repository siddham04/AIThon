"""Multi-Agent Requirement Review Board.

Five specialized agents review the requirement IN PARALLEL — each from
their own functional lens — then a coordinator aggregates their scores
into a single headline `Requirement Confidence`. This is intentionally a
DIFFERENT shape from the Control Tower pipeline: instead of producing
downstream artifacts, every agent returns a critique + score so a team
can decide "is this requirement buildable as-is?".

Agents
------
  - BA Agent          → user stories + acceptance criteria
  - Architect Agent   → components affected + APIs + DB changes
  - QA Agent          → test scenarios + edge cases
  - Security Agent    → security concerns + compliance concerns
  - PM Agent          → business risks + missing requirements

The aggregate score is a weighted blend of the five sub-scores; a grade
(A/B/C/D) is attached for at-a-glance reporting.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

from ..models import AgentReview, Project, ReviewBoardReport
from ..services.ingestion import render_clauses
from .base import Agent

logger = logging.getLogger("helix.review_board")


# ---------- Agent prompts -------------------------------------------------- #


_BA_SYSTEM = """You are a Senior Business Analyst on a requirement review board.

For the requirement under review, draft the user stories and acceptance
criteria you would expect to see. Be concrete and grounded in the input.
Then critique whether the input gives you enough signal to write
high-quality stories — that critique drives your confidence score.
""".strip()

_BA_SCHEMA = """{
  "stories": [
    {"title": "string", "acceptance_criteria": ["string", "..."]}
  ],
  "summary": "string — one sentence: how clear is this requirement from a BA lens?",
  "concerns": ["string — vague or missing pieces a BA would push back on"]
}"""


_ARCH_SYSTEM = """You are a Solution Architect reviewing a requirement.

Identify the system surface this requirement will touch. Specifically:
  - which existing or new COMPONENTS are affected
  - which APIs (new or changed) are needed, with method + path
  - which DATABASE entities will be created / altered / migrated

Be specific. If the input is too vague to commit to any of these, say so
in your `summary` and reflect that in your concerns.
""".strip()

_ARCH_SCHEMA = """{
  "components_affected": [
    {"component": "string", "impact": "string", "is_new": false}
  ],
  "apis": [
    {"method": "GET|POST|PUT|PATCH|DELETE", "path": "/example", "description": "string", "is_new": true}
  ],
  "database_changes": [
    {"entity": "string", "change": "create|alter|migrate|delete", "description": "string"}
  ],
  "summary": "string — one sentence: how implementable is this from an architect's lens?",
  "concerns": ["string — gaps an architect would block on"]
}"""


_QA_SYSTEM = """You are a Senior QA Engineer reviewing a requirement.

For the requirement, list the test scenarios you would write (happy
path, integration, performance / security / accessibility where
relevant) and the edge cases that worry you. Your confidence score
reflects how testable the requirement is.
""".strip()

_QA_SCHEMA = """{
  "scenarios": [
    {"title": "string", "type": "functional|edge|negative|performance|security|accessibility", "description": "string"}
  ],
  "edge_cases": ["string"],
  "summary": "string — one sentence: how testable is this requirement?",
  "concerns": ["string — what is missing for QA to write a real test plan?"]
}"""


_SEC_SYSTEM = """You are a Security & Compliance reviewer.

Surface the SECURITY concerns (auth, authz, input validation, data
exposure, abuse vectors) and the COMPLIANCE concerns (GDPR / SOC2 / PCI
/ HIPAA / regional data residency / audit) that this requirement would
trigger. Each concern needs a severity (low|medium|high|critical) and a
concrete mitigation an engineer can act on. Your score is highest when
the requirement is unambiguous and has no critical gaps.
""".strip()

_SEC_SCHEMA = """{
  "security_concerns": [
    {"title": "string", "severity": "low|medium|high|critical", "description": "string", "mitigation": "string"}
  ],
  "compliance_concerns": [
    {"title": "string", "framework": "string", "severity": "low|medium|high|critical", "description": "string", "mitigation": "string"}
  ],
  "summary": "string — one sentence: is this requirement secure & compliant by design?",
  "concerns": ["string — short list of the top blockers"]
}"""


_PM_SYSTEM = """You are a Senior Product Manager reviewing a requirement
for a stakeholder briefing. Your job is to surface BUSINESS RISKS the
team is taking on (market, monetization, user adoption, dependency on
unowned partners, time-to-value) and the MISSING REQUIREMENTS the brief
glosses over (success metrics, non-functional targets, rollback plan,
support model). Score reflects how much you trust this requirement
without further work.
""".strip()

_PM_SCHEMA = """{
  "business_risks": [
    {"title": "string", "severity": "low|medium|high|critical", "description": "string"}
  ],
  "missing_requirements": [
    {"title": "string", "severity": "low|medium|high|critical", "description": "string"}
  ],
  "summary": "string — one sentence: would you green-light this for build?",
  "concerns": ["string — top 3 things the PM expects answers to before signing off"]
}"""


# ---------- Scoring helpers ----------------------------------------------- #


_SEV_PENALTY = {"low": 4, "medium": 10, "high": 20, "critical": 35}
_PM_SEV_PENALTY = {"low": 4, "medium": 8, "high": 16, "critical": 24}


def _coerce_severity(raw: Any) -> str:
    s = str(raw or "medium").strip().lower()
    return s if s in _SEV_PENALTY else "medium"


def _ba_score(d: Dict[str, Any]) -> float:
    stories = d.get("stories") or []
    if not stories:
        return 35.0
    avg_ac = sum(len(s.get("acceptance_criteria") or []) for s in stories) / max(
        1, len(stories)
    )
    raw = min(100.0, len(stories) * 12 + avg_ac * 6)
    # Each unresolved BA concern shaves points
    raw -= 4 * len(d.get("concerns") or [])
    return max(20.0, min(100.0, raw))


def _arch_score(d: Dict[str, Any]) -> float:
    score = 0.0
    if d.get("components_affected"):
        score += 35
    if d.get("apis"):
        score += 35
    if d.get("database_changes"):
        score += 25
    score = min(100.0, score + 10)
    score -= 5 * len(d.get("concerns") or [])
    return max(20.0, min(100.0, score))


def _qa_score(d: Dict[str, Any]) -> float:
    n_scen = len(d.get("scenarios") or [])
    n_edge = len(d.get("edge_cases") or [])
    score = min(100.0, n_scen * 12 + n_edge * 6)
    score -= 4 * len(d.get("concerns") or [])
    return max(20.0, min(100.0, score))


def _security_score(d: Dict[str, Any]) -> float:
    penalty = 0
    for c in (d.get("security_concerns") or []) + (d.get("compliance_concerns") or []):
        penalty += _SEV_PENALTY[_coerce_severity(c.get("severity"))]
    return max(20.0, min(100.0, 100.0 - penalty))


def _pm_score(d: Dict[str, Any]) -> float:
    penalty = 0
    for c in (d.get("business_risks") or []) + (d.get("missing_requirements") or []):
        penalty += _PM_SEV_PENALTY[_coerce_severity(c.get("severity"))]
    return max(20.0, min(100.0, 100.0 - penalty))


_AGENTS: Tuple[Tuple[str, str, str, str, str, Callable[[Dict[str, Any]], float]], ...] = (
    ("ba", "Business Analyst", _BA_SYSTEM, _BA_SCHEMA,
     "Draft the user stories and acceptance criteria for this requirement, then critique it.",
     _ba_score),
    ("architect", "Solution Architect", _ARCH_SYSTEM, _ARCH_SCHEMA,
     "Map this requirement to components, APIs, and database changes. Then critique it.",
     _arch_score),
    ("qa", "QA Engineer", _QA_SYSTEM, _QA_SCHEMA,
     "Build a test plan: scenarios + edge cases. Then critique testability.",
     _qa_score),
    ("security", "Security & Compliance", _SEC_SYSTEM, _SEC_SCHEMA,
     "Surface security and compliance concerns with severity and mitigation.",
     _security_score),
    ("pm", "Product Manager", _PM_SYSTEM, _PM_SCHEMA,
     "Identify business risks and missing requirements before sign-off.",
     _pm_score),
)


# Equal-weighted blend keeps the story honest.
_AGENT_WEIGHT: Dict[str, float] = {a[0]: 0.20 for a in _AGENTS}


def _grade_for(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _board_summary(reviews: List[AgentReview], confidence: float) -> str:
    lows = sorted(reviews, key=lambda r: r.score)[:2]
    if not lows:
        return ""
    low_part = ", ".join(f"{r.role.lower()} {r.score:.0f}" for r in lows)
    if confidence >= 80:
        return f"Requirement is buildable. Watch: {low_part}."
    if confidence >= 70:
        return f"Requirement is workable but soft on: {low_part}."
    return f"Requirement is not yet build-ready. Weakest reviews: {low_part}."


# ---------- Single-agent review runner ------------------------------------ #


class _ReviewAgent(Agent):
    """Common runner for one Review-Board agent.

    A single class parameterized on the prompt + scoring function keeps
    the LLM call shape identical across all five seats — the differences
    are pure data.
    """
    name = "review"
    stage = "Review"

    def __init__(self, key: str, role: str, system: str, schema: str,
                 task: str, scorer) -> None:
        super().__init__()
        self.key = key
        self.role = role
        self._system = system
        self._schema = schema
        self._task = task
        self._scorer = scorer

    async def run(self, project: Project) -> AgentReview:
        t0 = time.monotonic()
        try:
            user = (
                "Requirement under review (one clause per line, with stable ids):\n\n"
                f"{render_clauses(project.source_clauses)}\n\n"
                f"{self._task}"
            )
            data = await self.llm.chat_json_with_fallback(
                f"review_{self.key}",
                project,
                self._system,
                user,
                schema_hint=self._schema,
                max_completion_tokens=2500,
            )
            score = float(self._scorer(data))
            return AgentReview(
                agent=self.key,
                role=self.role,
                score=round(score, 1),
                summary=str(data.get("summary") or "").strip(),
                findings={k: v for k, v in data.items() if k != "summary"},
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("Review agent %s failed", self.key)
            return AgentReview(
                agent=self.key,
                role=self.role,
                score=40.0,
                summary="Agent failed to complete its review.",
                findings={},
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                error=str(exc),
            )


# ---------- Public coordinator ------------------------------------------- #


async def run_review_board(project: Project) -> ReviewBoardReport:
    """Run all five review agents in parallel and aggregate their scores."""

    runners = [
        _ReviewAgent(key, role, system, schema, task, scorer)
        for (key, role, system, schema, task, scorer) in _AGENTS
    ]
    reviews: List[AgentReview] = list(
        await asyncio.gather(*(r.run(project) for r in runners))
    )

    # Weighted blend
    if reviews:
        weighted = sum(_AGENT_WEIGHT.get(r.agent, 0.2) * r.score for r in reviews)
        total_weight = sum(_AGENT_WEIGHT.get(r.agent, 0.2) for r in reviews)
        confidence = round(weighted / max(total_weight, 1e-6), 1)
    else:
        confidence = 0.0

    return ReviewBoardReport(
        project_id=project.id,
        confidence=confidence,
        grade=_grade_for(confidence),
        summary=_board_summary(reviews, confidence),
        generated_at=datetime.utcnow(),
        reviews=reviews,
    )
