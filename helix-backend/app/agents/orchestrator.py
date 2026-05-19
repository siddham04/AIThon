"""Pipeline orchestration.

Runs agents in dependency order:
  Analyzer & Ambiguity (parallel)  →  Decomposer  →  Tests + Estimator + Risk (parallel)

Streams progress events the UI can render as a live timeline.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncIterator, Dict

from ..models import (
    AnalyzeProgress,
    Project,
    ProductivityMetrics,
)
from .ambiguity import AmbiguityAgent
from .analyzer import AnalyzerAgent
from .decomposer import DecomposerAgent
from .estimator import EstimatorAgent
from .risk import RiskAgent
from .test_architect import TestArchitectAgent

logger = logging.getLogger("helix.orchestrator")


# Tunable assumption: average cost of an engineer-minute (USD).
ENGINEER_MIN_COST_USD = 1.25


def _estimate_metrics(project: Project) -> ProductivityMetrics:
    """Heuristic productivity savings calc.

    Manual baseline: rough industry rules of thumb for grooming a brief.
      - 12 min per source clause to read & discuss
      - 18 min per user story to write & refine
      - 12 min per task to draft
      - 10 min per test case
      - 8 min per ambiguity surfaced in review
      - 10 min per risk discovered later
    """
    manual = (
        12 * len(project.source_clauses)
        + 18 * len(project.stories)
        + 12 * len(project.tasks)
        + 10 * len(project.test_cases)
        + 8 * len(project.ambiguities)
        + 10 * len(project.risks)
    )
    # Helix wallclock ~ 1 min ingestion + ~30s per agent stage on average.
    helix = 4
    saved = max(manual - helix, 0)
    artifacts = (
        len(project.stories)
        + len(project.tasks)
        + len(project.test_cases)
        + len(project.ambiguities)
        + len(project.risks)
    )
    coverage = 0.0
    if project.source_clauses:
        cited = set()
        for collection in (
            project.stories,
            project.tasks,
            project.test_cases,
            project.ambiguities,
            project.risks,
        ):
            for item in collection:
                cited.update(getattr(item, "source_clause_ids", []) or [])
        coverage = round(
            min(1.0, len(cited) / max(1, len(project.source_clauses))), 2
        )

    traceable = (
        list(project.stories) + list(project.tasks) + list(project.test_cases)
    )
    if traceable:
        with_clause = sum(
            1
            for item in traceable
            if len(getattr(item, "source_clause_ids", []) or []) > 0
        )
        citation_item_rate = round(with_clause / len(traceable), 3)
    else:
        citation_item_rate = 0.0

    return ProductivityMetrics(
        manual_minutes=manual,
        helix_minutes=helix,
        minutes_saved=saved,
        hours_saved=round(saved / 60, 1),
        cost_saved_usd=round(saved * ENGINEER_MIN_COST_USD, 2),
        artifacts_generated=artifacts,
        coverage_score=coverage,
        citation_item_rate=citation_item_rate,
    )


async def run_pipeline(project: Project) -> AsyncIterator[Dict]:
    """Yield progress events as JSON-friendly dicts; mutates `project` in place."""

    analyzer = AnalyzerAgent()
    ambiguity = AmbiguityAgent()
    decomposer = DecomposerAgent()
    tests = TestArchitectAgent()
    estimator = EstimatorAgent()
    risk = RiskAgent()

    # --- Phase 1: analyze + ambiguity in parallel ---
    yield AnalyzeProgress(stage="Ingesting input", status="done").model_dump()
    yield AnalyzeProgress(stage=analyzer.stage, status="running").model_dump()
    yield AnalyzeProgress(stage=ambiguity.stage, status="running").model_dump()

    pipeline_timings_ms: Dict[str, int] = {}

    async def collect(agent, label: str):
        t0 = time.monotonic()
        try:
            patch = await agent.run(project)
            for k, v in patch.items():
                setattr(project, k, v)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            pipeline_timings_ms[label] = elapsed_ms
            return AnalyzeProgress(stage=label, status="done", elapsed_ms=elapsed_ms)
        except Exception as exc:
            logger.exception("Agent %s failed", agent.name)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            pipeline_timings_ms[label] = elapsed_ms
            return AnalyzeProgress(
                stage=label, status="error", detail=str(exc), elapsed_ms=elapsed_ms
            )

    p1 = await asyncio.gather(
        collect(analyzer, analyzer.stage),
        collect(ambiguity, ambiguity.stage),
    )
    for p in p1:
        yield p.model_dump()

    # --- Phase 2: decomposer (needs summary) ---
    yield AnalyzeProgress(stage=decomposer.stage, status="running").model_dump()
    p2 = await collect(decomposer, decomposer.stage)
    yield p2.model_dump()

    # --- Phase 3: tests + estimator + risk in parallel ---
    yield AnalyzeProgress(stage=tests.stage, status="running").model_dump()
    yield AnalyzeProgress(stage=estimator.stage, status="running").model_dump()
    yield AnalyzeProgress(stage=risk.stage, status="running").model_dump()
    p3 = await asyncio.gather(
        collect(tests, tests.stage),
        collect(estimator, estimator.stage),
        collect(risk, risk.stage),
    )
    for p in p3:
        yield p.model_dump()

    # --- Phase 4: metrics ---
    project.last_pipeline_timings_ms = dict(pipeline_timings_ms)
    project.metrics = _estimate_metrics(project)
    yield AnalyzeProgress(stage="Computing impact metrics", status="done").model_dump()
