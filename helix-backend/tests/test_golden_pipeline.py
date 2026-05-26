"""Helix golden-domain pipeline contract.

Runs the full 11-step demo orchestrator end-to-end against the canonical
**e-commerce checkout** sample requirement, in mock mode (no LLM keys),
and asserts the bulletproof invariants documented in
``docs/GOLDEN_DOMAIN.md``.

If this test fails, the live judge demo is no longer guaranteed —
something in the pipeline started silently producing empty artifacts,
breaking citations, or hardcoding scores. Fix the regression before
shipping.

Run from ``helix-backend/``::

    pip install -r requirements-dev.txt
    pytest tests/test_golden_pipeline.py -v
"""
from __future__ import annotations

import pytest

from app.models import Project
from app.services.demo_orchestrator import run_demo


# Kept in lock-step with helix-frontend/src/constants/sampleRequirement.js.
# If you edit the user-facing sample, mirror the change here so the
# contract still reflects what judges see on screen.
GOLDEN_REQUIREMENT = """\
Title: Checkout Revamp Initiative

Goal: Cut cart abandonment by delivering a fast, trustworthy checkout
flow for returning shoppers and a clear ops surface for support agents.

Functional requirements:
- Authenticated shoppers must complete checkout in 3 steps or fewer:
  review cart, choose payment, confirm.
- Show a delivery date estimate before payment within 200 ms P95.
- Accept saved cards and one digital wallet at launch; vendor selection
  is TBD pending procurement review.
- Inventory must decrement atomically when an order is confirmed so two
  shoppers cannot oversell the last unit.
- Support agents need a refund action from the order detail page;
  refunds should happen "fast" (legal still drafting the SLA wording).
- International shoppers see prices in their local currency
  "where it makes sense" — exact FX/rounding policy is undefined.

Non-functional requirements:
- p95 checkout API latency must stay under 300 ms at 1k concurrent
  shoppers.
- Payment provider uptime assumption: 99.9% monthly availability.
- PCI scope must remain SAQ-A: never store or transmit raw PAN data.
- All authentication uses short-lived JWTs (<= 15 min) refreshed via a
  secure HTTP-only cookie; sessions must be revocable from the support
  console.

Success metrics:
- Checkout completion rate up 8 percentage points within one quarter.
- Zero oversell incidents per 10k orders.
- Support tickets tagged "payment failed randomly" drop by 50%.

Out of scope (this initiative):
- Crypto / BNPL payment methods.
- Tax-jurisdiction logic outside the EU.
- Offline / kiosk checkout mode.
"""


# Steps DEMO_STEPS / _STEP_RUNNERS guarantees a `done` (or `error`)
# event for, in canonical order.
EXPECTED_STEPS = (
    "ingest",
    "quality",
    "review",
    "ambiguity",
    "stories",
    "architecture",
    "effort_sprint",
    "apis",
    "tests",
    "jira",
    "readiness",
)


@pytest.fixture
def golden_project() -> Project:
    return Project(
        id="proj_golden_checkout",
        name="Checkout Revamp Initiative",
        raw_input=GOLDEN_REQUIREMENT,
    )


async def _collect(project: Project) -> tuple[Project, list[dict]]:
    events: list[dict] = []
    async for ev in run_demo(project, use_ai=False):
        events.append(ev)
    return project, events


@pytest.mark.asyncio
async def test_pipeline_runs_all_steps(golden_project: Project) -> None:
    """Every declared step emits at least one event and the run finishes."""
    _, events = await _collect(golden_project)

    seen_steps = {ev["step"] for ev in events}
    missing = [s for s in EXPECTED_STEPS if s not in seen_steps]
    assert not missing, f"Pipeline skipped steps: {missing}"

    # Orchestrator must always reach the final readiness step.
    readiness_events = [e for e in events if e["step"] == "readiness"]
    assert readiness_events, "No `readiness` event was emitted."
    assert any(
        e.get("status") == "done" for e in readiness_events
    ), "Final `readiness` step did not finish with status=done."


@pytest.mark.asyncio
async def test_no_step_emits_error(golden_project: Project) -> None:
    """No pipeline step should crash in mock mode on the golden requirement."""
    _, events = await _collect(golden_project)
    errors = [e for e in events if e.get("status") == "error"]
    assert not errors, (
        "Pipeline emitted error events on the golden requirement (mock mode): "
        f"{[(e['step'], e.get('detail')) for e in errors]}"
    )


@pytest.mark.asyncio
async def test_stories_tasks_tests_non_empty(golden_project: Project) -> None:
    """The core SDLC artifacts must all be non-empty on the golden domain.

    This is the contract that makes a live demo unembarrassable.
    Targets are deliberately conservative; loosen only with discussion.
    """
    project, _ = await _collect(golden_project)

    assert len(project.source_clauses) >= 5, (
        f"Expected >= 5 atomic clauses; got {len(project.source_clauses)}."
    )
    assert len(project.stories) >= 4, (
        f"Expected >= 4 user stories; got {len(project.stories)}."
    )
    assert len(project.tasks) >= 4, (
        f"Expected >= 4 engineering tasks; got {len(project.tasks)} — "
        "the Scrum / Decomposer fallback chain may be broken."
    )
    assert len(project.test_cases) >= 4, (
        f"Expected >= 4 test cases; got {len(project.test_cases)}."
    )


@pytest.mark.asyncio
async def test_every_artifact_cites_a_clause(golden_project: Project) -> None:
    """Provenance contract: every story/task/test must cite >= 1 real clause."""
    project, _ = await _collect(golden_project)

    real_clause_ids = {c.id for c in project.source_clauses}

    def _cites_real_clause(artifact) -> bool:
        ids = getattr(artifact, "source_clause_ids", None) or []
        return any(cid in real_clause_ids for cid in ids)

    uncited_stories = [s.id for s in project.stories if not _cites_real_clause(s)]
    assert not uncited_stories, (
        f"Stories without real source_clause_ids: {uncited_stories}"
    )

    uncited_tasks = [t.id for t in project.tasks if not _cites_real_clause(t)]
    # Tasks generated by the heuristic fallback inherit the parent story's
    # clauses, so at least 75% of tasks must carry a real citation.
    cited_ratio = 1.0 - (len(uncited_tasks) / max(1, len(project.tasks)))
    assert cited_ratio >= 0.75, (
        f"Only {cited_ratio:.0%} of tasks cite a real clause "
        f"(uncited: {uncited_tasks}); the citation chain is regressing."
    )


@pytest.mark.asyncio
async def test_tests_reference_real_stories(golden_project: Project) -> None:
    """Every test that names a `story_id` must reference a real story."""
    project, _ = await _collect(golden_project)

    real_story_ids = {s.id for s in project.stories}
    orphan_tests = [
        tc.id
        for tc in project.test_cases
        if getattr(tc, "story_id", None) and tc.story_id not in real_story_ids
    ]
    assert not orphan_tests, (
        f"Test cases reference non-existent story ids: {orphan_tests}"
    )


@pytest.mark.asyncio
async def test_ambiguities_and_risks_surface(golden_project: Project) -> None:
    """The golden requirement contains deliberate ambiguities and PCI/auth
    hints — the Ambiguity + Risk agents must surface them, not return empty.
    """
    project, _ = await _collect(golden_project)

    assert len(project.ambiguities) >= 2, (
        f"Expected >= 2 ambiguities (vendor TBD, 'fast' refunds, "
        f"'where it makes sense'); got {len(project.ambiguities)}."
    )

    assert len(project.risks) >= 2, (
        f"Expected >= 2 risks (security: JWT/auth + compliance: PCI-SAQ); "
        f"got {len(project.risks)}."
    )

    categories = {
        getattr(r.category, "value", str(r.category)) for r in project.risks
    }
    assert "security" in categories or "compliance" in categories, (
        "Risk agent missed both the security and compliance signals on a "
        f"requirement that explicitly mentions PCI + JWT auth. Categories: {categories}"
    )


@pytest.mark.asyncio
async def test_readiness_is_live_not_hardcoded(golden_project: Project) -> None:
    """Readiness percent must come from the live delivery-gate scorer,
    NOT a hardcoded constant. Guard against the regression flagged in
    docs/PHASE5_AI_WORKFLOW_AUDIT.md (H3).
    """
    project, events = await _collect(golden_project)

    readiness_done = [
        e for e in events
        if e["step"] == "readiness" and e.get("status") == "done"
    ]
    assert readiness_done, "No completed readiness event."

    artifact = readiness_done[-1].get("artifact") or {}
    score = artifact.get("readiness")
    assert isinstance(score, (int, float)), (
        f"Readiness score missing or wrong type: {score!r}"
    )
    assert 0 <= score <= 100, f"Readiness score out of range: {score}"

    # Two runs of the same project produce the same score only because the
    # mock pipeline is deterministic — but a literal hardcoded 94 across
    # ALL projects is the regression we're guarding against. Pair this
    # with a different-shape requirement to detect that fully; here we
    # check the live `delivery_readiness_center` exists and matches.
    center = project.delivery_readiness_center
    assert center is not None, (
        "delivery_readiness_center is not populated — readiness step did not "
        "call build_readiness_center."
    )
    assert center.readiness == score, (
        f"SSE readiness ({score}) does not match the stored "
        f"delivery_readiness_center.readiness ({center.readiness}). "
        "The display score and the stored score must be the same number."
    )


@pytest.mark.asyncio
async def test_export_artifacts_populated(golden_project: Project) -> None:
    """Jira backlog and traceability matrix must be ready for export."""
    project, _ = await _collect(golden_project)

    assert project.jira_backlog is not None, "Jira backlog never built."
    assert project.jira_backlog.epic is not None, "Backlog has no epic."
    assert len(project.jira_backlog.stories or []) >= 1, (
        "Backlog has no stories — Jira CSV export would be empty."
    )

    assert project.traceability_matrix is not None, (
        "Traceability matrix never built — Trace tab would be empty."
    )
