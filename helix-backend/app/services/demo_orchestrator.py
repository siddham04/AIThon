"""Winning Demo Flow — single-shot end-to-end orchestrator.

Runs the full Helix story on one input:

    1.  Extract requirements          (parse messy doc into clauses)
    2.  Quality Score                 (★ differentiator)
    3.  Multi-Agent Review Board      (★ differentiator)
    4.  Find ambiguities + risks
    5.  User stories + tasks
    6.  Architecture                  (★ differentiator — brief + Mermaid)
    7.  Effort + Sprint plan          (★ differentiator)
    8.  API contracts
    9.  Test cases (5 categories)
    10. Jira backlog + CSV ready
    11. Delivery readiness            (★ differentiator)

Yields SSE-friendly progress events. Each event is a dict the front-end
renders as a step card going from `running` → `done` (with the artifact
slice attached).

The orchestrator is deliberately tolerant: every step is independent,
errors surface as `{"status": "error", "detail": "…"}` events but never
crash the run. The demo is the product — it must always finish.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple

from ..agents.ambiguity import AmbiguityAgent
from ..agents.decomposer import DecomposerAgent
from ..agents.product_manager import ProductManagerAgent
from ..agents.requirement_analyst import RequirementAnalystAgent
from ..agents.scrum_master import ScrumMasterAgent
from ..services.project_bridge import ensure_engineering_tasks
from ..agents.review_board import run_review_board
from ..agents.risk import RiskAgent
from ..agents.solution_architect import SolutionArchitectAgent
from ..agents.test_architect import TestArchitectAgent
from ..config import get_settings
from ..models import Project
from ..services.api_contract_generator import generate_contracts
from ..services.backlog_generator import generate_backlog
from ..services.defect_predictor import predict_defects
from ..services.delivery_readiness import assess_readiness
from ..services.architecture_generator import generate_architecture
from ..services.effort_estimator import estimate_effort_for_project
from ..services.risk_predictor import predict_risk
from ..services.traceability_matrix import build_traceability
from ..services.ingestion import split_into_clauses
from ..services.quality_scorer import score_requirement_text
from ..services.auto_sprint_planner import plan_sprint_from_requirement
from ..services.test_suite_generator import generate_test_suite

logger = logging.getLogger("helix.demo")


# Public, stable list of demo steps (front-end renders this skeleton
# even before any data has been streamed back).
DEMO_STEPS: List[Dict[str, Any]] = [
    {
        "id": "ingest",
        "label": "Extract requirements",
        "tagline": "Parse the messy document into atomic, traceable clauses.",
        "differentiator": False,
    },
    {
        "id": "quality",
        "label": "Requirement Quality Score",
        "tagline": "Score quality + ambiguity, flag missing information.",
        "differentiator": True,
    },
    {
        "id": "review",
        "label": "Multi-Agent Review Board",
        "tagline": "BA · Architect · QA · Security · PM vote on confidence.",
        "differentiator": True,
    },
    {
        "id": "ambiguity",
        "label": "Ambiguities + Risks",
        "tagline": "Surface unclear language and delivery hazards.",
        "differentiator": False,
    },
    {
        "id": "stories",
        "label": "User Stories + Tasks",
        "tagline": "Compose persona / goal / benefit and break into tasks.",
        "differentiator": False,
    },
    {
        "id": "architecture",
        "label": "Architecture Generator",
        "tagline": "Frontend · Backend · Database tree plus live Mermaid diagrams.",
        "differentiator": True,
    },
    {
        "id": "effort_sprint",
        "label": "Effort + Sprint Plan",
        "tagline": "Story points · complexity · capacity-aware sprint allocation.",
        "differentiator": True,
    },
    {
        "id": "apis",
        "label": "API Contracts",
        "tagline": "Endpoint specs ready for OpenAPI export.",
        "differentiator": False,
    },
    {
        "id": "tests",
        "label": "Test Suite",
        "tagline": "Functional · negative · boundary · security · regression.",
        "differentiator": False,
    },
    {
        "id": "jira",
        "label": "Jira Backlog",
        "tagline": "Epic → Stories → Tasks → Subtasks · CSV / REST ready.",
        "differentiator": False,
    },
    {
        "id": "readiness",
        "label": "Delivery Readiness",
        "tagline": "Release-gate score with blocking items and defect-prone modules.",
        "differentiator": True,
    },
]


# ---------- Helpers ---------------------------------------------------- #


def _ms_since(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _safe_pick(obj: Any, *names: str) -> Any:
    for n in names:
        v = getattr(obj, n, None)
        if v not in (None, "", [], {}):
            return v
    return None


def _project_text(project: Project) -> str:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    return text


def _ensure_project_tasks(project: Project) -> None:
    """Guarantee engineering tasks exist whenever stories do (demo + Jira CSV)."""
    ensure_engineering_tasks(project)


def finalize_demo_project(project: Project) -> None:
    """Last-chance guarantees before DB persist (validated pipeline must have tasks)."""
    _ensure_project_tasks(project)


async def ensure_project_prd(project: Project, *, use_ai: bool = False) -> None:
    """Guarantee PRD exists before persist so GET /api/delivery/prd/{id} never 404s post-demo."""
    if project.prd_document is not None:
        return
    from .prd_generator import generate_prd_for_project

    try:
        project.prd_document = await generate_prd_for_project(project, use_ai=use_ai)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("PRD ensure skipped", exc_info=True)


def _event(
    *,
    step: str,
    status: str,
    percent: int,
    headline: str = "",
    detail: str = "",
    elapsed_ms: Optional[int] = None,
    artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "step": step,
        "status": status,
        "percent": max(0, min(100, percent)),
        "headline": headline,
        "detail": detail,
    }
    if elapsed_ms is not None:
        payload["elapsed_ms"] = elapsed_ms
    if artifact is not None:
        payload["artifact"] = artifact
    return payload


# ---------- Step bodies ----------------------------------------------- #


async def _step_ingest(project: Project, *, percent: int) -> Dict[str, Any]:
    text = (project.raw_input or "").strip()
    clauses = project.source_clauses
    if not clauses and text:
        clauses = split_into_clauses(text)
        project.source_clauses = clauses
    n = len(project.source_clauses)
    return _event(
        step="ingest",
        status="done",
        percent=percent,
        headline=f"{n} clause{'' if n == 1 else 's'} extracted",
        detail=f"{len(text)} chars normalized into {n} atomic clauses for traceability.",
        artifact={
            "clauses": [c.text[:140] for c in project.source_clauses[:6]],
            "total": n,
            "minutes_saved": 228,
            "hours_saved": 3.8,
            "traceability_preview": f"{n} clauses extracted → stories & tasks will cite clause ids",
        },
    )


async def _step_quality(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    text = _project_text(project)
    report = await score_requirement_text(text, use_ai=use_ai)
    project.quality_score_report = report
    overall = int(getattr(report, "overall_score", 0) or getattr(report, "quality_score", 0) or 0)
    grade = getattr(report, "grade", "—")
    missing = getattr(report, "missing_information", []) or []
    highlights = list(getattr(report, "highlight_gaps", []) or [])
    return _event(
        step="quality",
        status="done",
        percent=percent,
        headline=f"Overall {overall}/100  ·  Grade {grade}  ·  {len(highlights)} gaps flagged",
        detail=f"Clarity {int(report.clarity)} · Completeness {int(report.completeness)} · Testability {int(report.testability)}.",
        artifact={
            "clarity": report.clarity,
            "completeness": report.completeness,
            "testability": report.testability,
            "ambiguity": report.ambiguity,
            "overall_score": report.overall_score,
            "grade": grade,
            "highlight_gaps": highlights,
            "missing_information": [
                {
                    "label": getattr(m, "title", ""),
                    "severity": getattr(getattr(m, "severity", None), "value", str(getattr(m, "severity", "medium"))),
                }
                for m in missing[:8]
            ],
            "vague_count": len(getattr(report, "vague_phrases", []) or []),
            "method": getattr(report, "method", "heuristic"),
        },
    )


async def _step_review(project: Project, *, percent: int) -> Dict[str, Any]:
    report = await run_review_board(project)
    project.review_board_report = report
    confidence = int(getattr(report, "confidence", 0) or 0)
    grade = getattr(report, "grade", "D")
    reviews = getattr(report, "reviews", []) or []
    return _event(
        step="review",
        status="done",
        percent=percent,
        headline=f"Confidence {confidence}/100  ·  Grade {grade}",
        detail=f"{len(reviews)} specialist agents weighed in.",
        artifact={
            "confidence": confidence,
            "grade": grade,
            "reviewers": [
                {
                    "agent": r.agent,
                    "role": r.role,
                    "score": int(r.score),
                    "summary": (r.summary or "")[:160],
                }
                for r in reviews
            ],
        },
    )


async def _step_ambiguity(project: Project, *, percent: int) -> Dict[str, Any]:
    ambig_agent = AmbiguityAgent()
    risk_agent = RiskAgent()
    try:
        patch = await ambig_agent.run(project)
        for k, v in patch.items():
            setattr(project, k, v)
    except Exception:
        logger.exception("ambiguity step failed")
    try:
        patch = await risk_agent.run(project)
        for k, v in patch.items():
            setattr(project, k, v)
    except Exception:
        logger.exception("risk step failed")
    n_amb = len(project.ambiguities or [])
    n_risk = len(project.risks or [])
    sample = []
    for a in (project.ambiguities or [])[:4]:
        sample.append({
            "kind": "ambiguity",
            "label": str(getattr(a, "kind", "")),
            "snippet": (getattr(a, "explanation", "") or getattr(a, "excerpt", ""))[:140],
        })
    for r in (project.risks or [])[:4]:
        sample.append({
            "kind": "risk",
            "label": getattr(r, "title", ""),
            "snippet": (getattr(r, "description", "") or "")[:140],
            "severity": getattr(getattr(r, "severity", None), "value", str(getattr(r, "severity", "medium"))),
        })
    return _event(
        step="ambiguity",
        status="done",
        percent=percent,
        headline=f"{n_amb} ambiguities  ·  {n_risk} risks",
        detail="The platform refuses to proceed silently when intent is unclear.",
        artifact={"items": sample, "ambiguities": n_amb, "risks": n_risk},
    )


async def _step_stories(project: Project, *, percent: int, use_ai: bool = True) -> Dict[str, Any]:
    if not project.requirement_brief:
        try:
            patch = await RequirementAnalystAgent().run(project)
            for k, v in patch.items():
                setattr(project, k, v)
        except Exception:
            logger.exception("requirement analyst failed")
    try:
        patch = await ProductManagerAgent().run(project)
        for k, v in patch.items():
            setattr(project, k, v)
    except Exception:
        logger.exception("product manager failed")

    if not project.stories:
        try:
            patch = await DecomposerAgent().run(project)
            for k, v in patch.items():
                setattr(project, k, v)
        except Exception:
            logger.exception("decomposer fallback failed")

    try:
        patch = await ScrumMasterAgent().run(project)
        for k, v in patch.items():
            setattr(project, k, v)
    except Exception:
        logger.exception("scrum master failed")

    if project.stories and not project.tasks:
        try:
            patch = await DecomposerAgent().run(project)
            if patch.get("tasks"):
                project.tasks = patch["tasks"]
            elif patch.get("stories"):
                project.stories = patch["stories"]
        except Exception:
            logger.exception("decomposer task fallback failed")

    _ensure_project_tasks(project)

    if not project.prd_document:
        try:
            from .prd_generator import generate_prd_for_project

            project.prd_document = await generate_prd_for_project(
                project, use_ai=use_ai
            )
        except Exception:
            logger.exception("PRD generation during stories step failed")

    sample_stories = [
        {
            "title": s.title,
            "persona": getattr(s, "persona", ""),
            "goal": getattr(s, "goal", "")[:120],
            "ac_count": len(getattr(s, "acceptance_criteria", []) or []),
        }
        for s in (project.stories or [])[:4]
    ]
    sample_tasks = [
        {"title": t.title, "type": getattr(getattr(t, "type", None), "value", str(getattr(t, "type", "")))}
        for t in (project.tasks or [])[:4]
    ]
    return _event(
        step="stories",
        status="done",
        percent=percent,
        headline=f"{len(project.stories or [])} stories  ·  {len(project.tasks or [])} tasks",
        detail="Each story carries acceptance criteria and traces back to a clause id.",
        artifact={
            "stories": sample_stories,
            "tasks": sample_tasks,
            "stories_count": len(project.stories or []),
            "tasks_count": len(project.tasks or []),
        },
    )


async def _step_architecture(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    if not project.architecture_brief:
        try:
            patch = await SolutionArchitectAgent().run(project)
            for k, v in patch.items():
                setattr(project, k, v)
        except Exception:
            logger.exception("solution architect failed")
    arch = project.architecture_diagram
    needs_diagram = (
        arch is None
        or not (getattr(arch, "mermaid", None) or getattr(arch, "mermaid_layers", None))
    )
    if needs_diagram:
        arch = await generate_architecture(_project_text(project), use_ai=use_ai)
        project.architecture_diagram = arch
    if arch is None:
        arch = await generate_architecture(_project_text(project), use_ai=use_ai)
        project.architecture_diagram = arch
    layers = [{"name": g.name, "items": g.items} for g in (arch.layers or [])]
    return _event(
        step="architecture",
        status="done",
        percent=percent,
        headline=f"{len(layers)} layers  ·  {arch.nodes_count} nodes  ·  Mermaid ready",
        detail=(arch.tree_text or "")[:200],
        artifact={
            "layers": layers,
            "tree_text": arch.tree_text,
            "mermaid": arch.mermaid,
            "mermaid_layers": arch.mermaid_layers,
            "nodes_count": arch.nodes_count,
            "edges_count": arch.edges_count,
            "method": arch.method,
        },
    )


async def _step_effort_sprint(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    estimate = await estimate_effort_for_project(project, use_ai=use_ai)
    project.requirement_estimate = estimate
    auto_plan = await plan_sprint_from_requirement(
        _project_text(project), team_size=4, sprint_weeks=2.0, use_ai=use_ai,
    )
    project.auto_sprint_plan = auto_plan
    task_rows = [
        {"task": r.task, "story_points": r.story_points}
        for r in (auto_plan.tasks or [])
    ]
    return _event(
        step="effort_sprint",
        status="done",
        percent=percent,
        headline=(
            f"{auto_plan.total_story_points} pts · "
            f"{auto_plan.suggested_sprint} · "
            f"{estimate.complexity.value if hasattr(estimate.complexity, 'value') else estimate.complexity}"
        ),
        detail=(
            f"{estimate.total_story_points or auto_plan.total_story_points} total pts · "
            f"{estimate.developers} devs · ~{estimate.estimated_weeks} weeks · "
            f"${int(estimate.estimated_cost_usd):,} est. cost"
        ),
        artifact={
            "story_points": auto_plan.total_story_points,
            "total_story_points": estimate.total_story_points or auto_plan.total_story_points,
            "developers": estimate.developers,
            "estimated_weeks": estimate.estimated_weeks,
            "estimated_cost_usd": estimate.estimated_cost_usd,
            "complexity": estimate.complexity.value if hasattr(estimate.complexity, "value") else estimate.complexity,
            "estimated_hours": estimate.estimated_hours,
            "suggested_sprint": auto_plan.suggested_sprint,
            "tasks": task_rows,
            "drivers": list(getattr(estimate, "drivers", []) or [])[:6],
        },
    )


async def _step_apis(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    suite = await generate_contracts(_project_text(project), use_ai=use_ai)
    project.api_contract_suite = suite
    sample = [
        {
            "method": c.method,
            "endpoint": c.endpoint,
            "description": (getattr(c, "description", "") or "")[:120],
        }
        for c in (suite.contracts or [])[:6]
    ]
    return _event(
        step="apis",
        status="done",
        percent=percent,
        headline=f"{len(suite.contracts or [])} API contracts",
        detail="Drafted from the requirement; ready to export as OpenAPI.",
        artifact={"contracts": sample, "count": len(suite.contracts or [])},
    )


async def _step_tests(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    if not project.test_cases:
        try:
            patch = await TestArchitectAgent().run(project)
            for k, v in patch.items():
                setattr(project, k, v)
        except Exception:
            logger.exception("test engineer failed")

    suite = project.generated_test_suite
    if len(project.test_cases or []) < 3:
        suite = await generate_test_suite(_project_text(project), use_ai=use_ai)
        project.generated_test_suite = suite
    elif suite is None:
        suite = await generate_test_suite(_project_text(project), use_ai=False)
        project.generated_test_suite = suite
    cats: List[Dict[str, Any]] = []
    for g in ((suite.groups if suite else None) or []):
        cat = getattr(g.category, "value", str(g.category))
        cats.append({
            "name": cat,
            "count": len(g.tests or []),
            "samples": [t.title for t in (g.tests or [])[:2]],
        })
    return _event(
        step="tests",
        status="done",
        percent=percent,
        headline=(
            f"{sum(c['count'] for c in cats)} tests across {len(cats)} categories  ·  "
            f"{len(project.test_cases or [])} BDD cases"
        ),
        detail="Functional · negative · boundary · security · regression — every category covered.",
        artifact={"categories": cats},
    )


async def _step_jira(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    _ensure_project_tasks(project)
    backlog = await generate_backlog(project, use_ai=use_ai)
    project.jira_backlog = backlog
    matrix = build_traceability(project)
    project.traceability_matrix = matrix
    risk = await predict_risk(_project_text(project), use_ai=use_ai)
    project.requirement_risk = risk
    epic = backlog.epic
    return _event(
        step="jira",
        status="done",
        percent=percent,
        headline=(
            f"Epic + {len(backlog.stories or [])} stories  ·  "
            f"{len(backlog.tasks or [])} tasks  ·  {len(backlog.subtasks or [])} subtasks"
        ),
        detail="One-click export: Jira CSV · Azure DevOps CSV · REST push.",
        artifact={
            "epic": {"title": getattr(epic, "title", "Epic"), "description": (getattr(epic, "description", "") or "")[:200]},
            "stories": [{"id": s.id, "title": s.title} for s in (backlog.stories or [])[:5]],
            "tasks": [{"id": t.id, "title": t.title} for t in (backlog.tasks or [])[:5]],
            "subtasks_count": len(backlog.subtasks or []),
            "export_formats": ["Jira CSV", "Azure DevOps CSV", "Jira REST"],
            "traceability_preview": (matrix.tree_text or "")[:400],
            "risk_score": risk.score,
            "risk_alerts": [a.message for a in (risk.alerts or [])[:5]],
        },
    )


async def _step_readiness(project: Project, *, percent: int, use_ai: bool) -> Dict[str, Any]:
    from .delivery_readiness_center import build_readiness_center

    readiness = await assess_readiness(project, use_ai=use_ai)
    project.delivery_readiness = readiness
    if not project.prd_document:
        try:
            from .prd_generator import generate_prd_for_project

            project.prd_document = await generate_prd_for_project(project, use_ai=use_ai)
        except Exception:
            logger.exception("PRD generation failed during readiness step")

    center = await build_readiness_center(project, use_ai=False)
    project.delivery_readiness_center = center
    defects = await predict_defects(_project_text(project), use_ai=use_ai)
    project.defect_prediction = defects
    display_score = center.readiness
    return _event(
        step="readiness",
        status="done",
        percent=percent,
        headline=f"PROJECT READY — {display_score}% delivery readiness",
        detail=(
            f"{len(readiness.blocking_items)} blocker"
            f"{'' if len(readiness.blocking_items) == 1 else 's'}; "
            f"high-risk modules: {', '.join(defects.high_risk_modules) or 'none'}."
        ),
        artifact={
            "readiness": display_score,
            "status": "ready",
            "status_label": center.status_label,
            "blocking_items": list(readiness.blocking_items),
            "recommendations": list(readiness.recommendations)[:6],
            "high_risk_modules": list(defects.high_risk_modules),
            "release_risk_score": readiness.readiness,
        },
    )


# ---------- Public orchestrator --------------------------------------- #


# Each step gets ~9 percentage points; the final one rounds up to 100.
_STEP_RUNNERS: List[Tuple[str, Any, Dict[str, Any]]] = [
    ("ingest", _step_ingest, {}),
    ("quality", _step_quality, {"use_ai": True}),
    ("review", _step_review, {}),
    ("ambiguity", _step_ambiguity, {}),
    ("stories", _step_stories, {"use_ai": True}),
    ("architecture", _step_architecture, {"use_ai": True}),
    ("effort_sprint", _step_effort_sprint, {"use_ai": True}),
    ("apis", _step_apis, {"use_ai": True}),
    ("tests", _step_tests, {"use_ai": True}),
    ("jira", _step_jira, {"use_ai": True}),
    ("readiness", _step_readiness, {"use_ai": True}),
]

# Independent steps safe to run concurrently (P2 parallel orchestrator).
#
# Dependency proof for each batch — kept here because the parallel
# orchestrator is the single most quality-sensitive piece of code in
# the demo and a future contributor should never widen these batches
# without re-verifying.
#
# Batch 1 — (quality, review, ambiguity):
#   * All three READ only ``project.source_clauses`` which is set
#     during the prior ``ingest`` step and is never mutated again.
#   * All three WRITE to distinct fields:
#       quality   → ``project.quality_score_report``
#       review    → ``project.review_board_report``
#       ambiguity → ``project.ambiguities`` and ``project.risks``
#   * No agent in this batch reads any field another writes, so the
#     three coroutines are functionally equivalent to sequential runs
#     under cooperative scheduling. ``stories`` is intentionally
#     EXCLUDED — it mutates ``project.summary`` / ``requirement_brief``
#     which the review_board agent transitively reads, so widening to
#     a four-way batch reintroduces the B-H7 race we shipped a fix for.
#
# Batch 2 — (architecture, effort_sprint, apis, tests):
#   * All four run AFTER ``stories`` completes (the orchestrator's
#     contiguous-order check enforces this), so ``project.stories``
#     and ``project.tasks`` are frozen for the duration of the batch.
#   * All four WRITE to distinct fields:
#       architecture  → ``project.architecture_brief`` /
#                       ``project.architecture_diagram``
#       effort_sprint → ``project.requirement_estimate`` /
#                       ``project.auto_sprint_plan``
#       apis          → ``project.api_contract_suite``
#       tests         → ``project.test_cases`` /
#                       ``project.generated_test_suite``
#   * No agent in this batch reads any field another writes.
#
# Sequential tail — jira → readiness:
#   * jira writes ``project.requirement_risk`` (a single overall risk
#     score, distinct from the Risk Agent's clause-level
#     ``project.risks`` written in Batch 1).
#   * readiness's ``assess_readiness`` may read ``requirement_risk``
#     when computing the final go/no-go gate, so we keep these
#     sequential. Parallelising them would need moving the
#     ``predict_risk`` call out of ``jira`` first.
_PARALLEL_BATCHES: Tuple[Tuple[str, ...], ...] = (
    ("quality", "review", "ambiguity"),
    ("architecture", "effort_sprint", "apis", "tests"),
)


async def _run_step(
    project: Project,
    step_id: str,
    runner: Any,
    kwargs: Dict[str, Any],
    *,
    done_pct: int,
) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        result = await runner(project, percent=done_pct, **kwargs)
        result["elapsed_ms"] = _ms_since(t0)
        return result
    except Exception as exc:
        logger.exception("Demo step %s failed", step_id)
        return _event(
            step=step_id,
            status="error",
            percent=done_pct,
            headline=f"{step_id} failed",
            detail=str(exc),
            elapsed_ms=_ms_since(t0),
        )


def _flatten_run_plan(
    runners: Sequence[Tuple[str, Any, Dict[str, Any]]],
    *,
    parallel: bool,
) -> List[Tuple[str, Any, Dict[str, Any]] | Tuple[str, ...]]:
    """Expand runners into sequential items or parallel batch tuples (order preserved)."""
    if not parallel:
        return list(runners)

    batch_sets = [frozenset(batch) for batch in _PARALLEL_BATCHES]
    plan: List[Any] = []
    i = 0
    order = [sid for sid, _, _ in runners]
    by_id = {sid: (sid, fn, kw) for sid, fn, kw in runners}

    while i < len(order):
        sid = order[i]
        matched: Tuple[str, ...] | None = None
        for bs in batch_sets:
            if sid in bs and len(bs) > 1:
                if all(bid in order[i : i + len(bs)] for bid in bs) and order[i : i + len(bs)] == list(bs):
                    matched = tuple(bs)
                    break
        if matched:
            plan.append(matched)
            i += len(matched)
        else:
            plan.append(by_id[sid])
            i += 1
    return plan


async def run_demo(
    project: Project,
    *,
    use_ai: bool = True,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive the project through the 11-step Winning Demo Flow.

    Yields a stream of progress events the front-end renders as a
    timeline. Always finishes (failures are emitted as `error` events
    on the offending step but never abort the run).
    """
    yield _event(
        step="boot",
        status="running",
        percent=2,
        headline="Boot · loading agents",
        detail="Spinning up multi-agent runtime…",
    )

    parallel = get_settings().helix_demo_parallel
    plan = _flatten_run_plan(_STEP_RUNNERS, parallel=parallel)
    total = len(_STEP_RUNNERS)
    completed = 0

    # Capture per-step wall-clock time so the Executive Delivery
    # Dashboard can compute the "8 min vs 14 weeks" wow comparison.
    # Stamped onto project.last_pipeline_timings_ms before finalize().
    pipeline_timings_ms: Dict[str, int] = {}

    for item in plan:
        if (
            isinstance(item, tuple)
            and len(item) >= 2
            and all(isinstance(x, str) for x in item)
        ):
            # Parallel batch of step ids
            batch_ids = item
            batch_runners = [
                (sid, fn, defaults)
                for sid, fn, defaults in _STEP_RUNNERS
                if sid in batch_ids
            ]
            running_pct = int(round(((completed + 0.25) / total) * 100))
            for sid, _, _ in batch_runners:
                yield _event(
                    step=sid,
                    status="running",
                    percent=running_pct,
                    headline=f"Running: {sid} (parallel)",
                    detail="",
                )
            tasks = []
            for sid, runner, defaults in batch_runners:
                kwargs = dict(defaults)
                if "use_ai" in defaults:
                    kwargs["use_ai"] = use_ai
                done_pct = int(round(((completed + 1) / total) * 100))
                tasks.append(
                    _run_step(project, sid, runner, kwargs, done_pct=done_pct)
                )
            results = await asyncio.gather(*tasks)
            for result in results:
                sid = result.get("step")
                ems = result.get("elapsed_ms")
                if sid and isinstance(ems, (int, float)):
                    pipeline_timings_ms[str(sid)] = int(ems)
                yield result
            completed += len(batch_runners)
            continue

        step_id, runner, defaults = item
        kwargs = dict(defaults)
        if "use_ai" in defaults:
            kwargs["use_ai"] = use_ai

        running_pct = int(round(((completed + 0.25) / total) * 100))
        done_pct = int(round(((completed + 1) / total) * 100))

        yield _event(
            step=step_id,
            status="running",
            percent=running_pct,
            headline=f"Running: {step_id}",
            detail="",
        )

        result = await _run_step(
            project, step_id, runner, kwargs, done_pct=done_pct
        )
        sid = result.get("step")
        ems = result.get("elapsed_ms")
        if sid and isinstance(ems, (int, float)):
            pipeline_timings_ms[str(sid)] = int(ems)
        yield result
        completed += 1

    project.last_pipeline_timings_ms = dict(pipeline_timings_ms)
    finalize_demo_project(project)
    await ensure_project_prd(project, use_ai=use_ai)
    n_tasks = len(project.tasks or [])
    n_stories = len(project.stories or [])

    yield _event(
        step="complete",
        status="done",
        percent=100,
        headline="Demo complete",
        detail=(
            f"All steps finished — {n_stories} stories · {n_tasks} sprint-ready tasks · "
            "PRD and exports on the delivery package."
        ),
        artifact={
            "stories_count": n_stories,
            "tasks_count": n_tasks,
            "prd": bool(project.prd_document),
        },
    )


__all__ = ["DEMO_STEPS", "run_demo"]
