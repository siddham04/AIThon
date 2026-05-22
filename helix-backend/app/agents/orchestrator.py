"""Multi-Agent SDLC Pipeline — orchestration.

Five specialized agents — each a focused LLM pass, not one monolithic call:

    Requirement
        ↓
    Requirement Analyst Agent     → Features · Actors · Business rules
        ↓
    Product Manager Agent         → Epic · Stories · Acceptance criteria
        ↓
    Architect Agent               → APIs · DB entities · Components
        ↓
    QA Agent                      → Test cases · Edge · Negative scenarios
        ↓
    Scrum Master Agent            → Sprint tasks · Priorities · Dependencies

Streams progress events for the Control Tower UI.
Developer Copilot (chat) is available separately via /chat.
"""
from __future__ import annotations

import logging
import time
from typing import AsyncIterator, Dict

from ..models import AnalyzeProgress, Project, ProductivityMetrics
from .product_manager import ProductManagerAgent
from .requirement_analyst import RequirementAnalystAgent
from .scrum_master import ScrumMasterAgent
from .solution_architect import SolutionArchitectAgent
from .test_architect import TestArchitectAgent

logger = logging.getLogger("helix.orchestrator")

ENGINEER_MIN_COST_USD = 1.25

# Stable stage ids for the Control Tower frontend.
CONTROL_TOWER_STAGES: tuple[str, ...] = (
    "Requirement Analyst",
    "Product Manager",
    "Architect",
    "QA Agent",
    "Scrum Master",
)

# What each agent produces (shown in UI tooltips).
PIPELINE_AGENT_OUTPUTS: dict[str, str] = {
    "Requirement Analyst": "Features · Actors · Business rules",
    "Product Manager": "Epic · Stories · Acceptance criteria",
    "Architect": "APIs · DB entities · Components",
    "QA Agent": "Test cases · Edge cases · Negative scenarios",
    "Scrum Master": "Sprint tasks · Priorities · Dependencies",
}

# First activity line shown in the Screen 3 live workflow UI.
PIPELINE_ACTIVITY: dict[str, str] = {
    "Requirement Analyst": "Thinking...",
    "Product Manager": "Generating stories...",
    "Architect": "Designing APIs...",
    "QA Agent": "Generating test cases...",
    "Scrum Master": "Analyzing dependencies...",
}


def _estimate_metrics(project: Project) -> ProductivityMetrics:
    manual = (
        12 * len(project.source_clauses)
        + 18 * len(project.stories)
        + 12 * len(project.tasks)
        + 10 * len(project.test_cases)
        + 8 * len(project.ambiguities)
        + 10 * len(project.risks)
    )
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
    """Yield pipeline progress events; mutates `project` in place."""

    agents = (
        RequirementAnalystAgent(),
        ProductManagerAgent(),
        SolutionArchitectAgent(),
        TestArchitectAgent(),
        ScrumMasterAgent(),
    )

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

    yield AnalyzeProgress(stage="Ingesting input", status="done").model_dump()

    for agent in agents:
        label = agent.stage
        yield AnalyzeProgress(
            stage=label,
            status="running",
            detail=PIPELINE_ACTIVITY.get(label, "Thinking..."),
        ).model_dump()
        yield (await collect(agent, label)).model_dump()

    project.last_pipeline_timings_ms = dict(pipeline_timings_ms)
    project.metrics = _estimate_metrics(project)
    yield AnalyzeProgress(stage="Computing impact metrics", status="done").model_dump()
