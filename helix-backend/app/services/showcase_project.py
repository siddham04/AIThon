"""Idempotent pre-baked showcase project for hackathon backup demos."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    AmbiguityIssue,
    AmbiguityKind,
    ProductivityMetrics,
    Project,
    RequirementSummary,
    Risk,
    RiskCategory,
    Severity,
    SourceClause,
    Task,
    TaskType,
    TestCase,
    TestType,
    UserStory,
)
from ..services.project_bridge import ensure_project_row
from ..services.rag_service import embed_requirements
from ..services.store import get_store
from ..sqla_models import ProjectRecord, User

logger = logging.getLogger("helix.showcase")


def showcase_project_id() -> str:
    return (get_settings().helix_showcase_project_id or "proj_demo_seed01").strip()


def _build_showcase() -> Project:
    c1 = SourceClause(
        id="clause_demo_001",
        index=0,
        text="Customers must pay with card or wallet within 10 seconds.",
    )
    c2 = SourceClause(
        id="clause_demo_002",
        index=1,
        text="Inventory must decrement atomically when an order is confirmed.",
    )
    c3 = SourceClause(
        id="clause_demo_003",
        index=2,
        text="SLA: p95 checkout API latency under 300ms for 1k concurrent users.",
    )
    raw = "\n\n".join([c.text for c in (c1, c2, c3)])

    summary = RequirementSummary(
        title="One-click checkout & stock integrity",
        one_liner="Fast checkout with consistent inventory under load.",
        objective="Increase conversion while preventing overselling.",
        in_scope=["Card/wallet payments", "Inventory reservation", "Latency SLO"],
        out_of_scope=["Tax jurisdictions outside EU", "Offline mode"],
        primary_personas=["Returning shopper", "Ops analyst"],
        success_metrics=["Checkout completion rate", "Oversell incidents = 0"],
        assumptions=["Payment provider SLA 99.9%", "Single-region deploy"],
    )

    story = UserStory(
        id="story_demo_001",
        title="Pay and confirm order",
        persona="Returning shopper",
        goal="Complete purchase quickly",
        benefit="Fewer abandoned carts",
        acceptance_criteria=[
            "Given items in cart, when user pays, then order is confirmed",
            "Receipt shown within 2s of provider callback",
        ],
        source_clause_ids=[c1.id],
    )
    story2 = UserStory(
        id="story_demo_002",
        title="Show delivery date before payment",
        persona="Shopper",
        goal="See accurate delivery estimate",
        benefit="Reduce cart abandonment",
        acceptance_criteria=[
            "Given cart with address, when viewing checkout, then delivery date displays",
            "Estimate renders within 200ms P95",
        ],
        source_clause_ids=[c3.id],
    )

    t1 = Task(
        id="task_demo_001",
        title="Integrate payment webhook idempotency",
        description="Handle duplicate callbacks without double charge.",
        type=TaskType.FEATURE,
        priority=Severity.HIGH,
        story_id=story.id,
        estimate_hours=6.0,
        estimate_points=5,
        confidence=0.82,
        skills=["FastAPI", "webhooks"],
        source_clause_ids=[c1.id],
    )
    t2 = Task(
        id="task_demo_002",
        title="Atomic inventory decrement",
        description="Use transaction / compare-and-swap to prevent oversell.",
        type=TaskType.FEATURE,
        priority=Severity.CRITICAL,
        story_id=story.id,
        estimate_hours=8.0,
        estimate_points=8,
        confidence=0.75,
        skills=["PostgreSQL", "transactions"],
        source_clause_ids=[c2.id],
    )
    t3 = Task(
        id="task_demo_003",
        title="Delivery estimate API",
        description="Compute shipping ETA from warehouse + carrier rules.",
        type=TaskType.FEATURE,
        priority=Severity.HIGH,
        story_id=story2.id,
        estimate_hours=5.0,
        estimate_points=5,
        confidence=0.8,
        skills=["FastAPI", "caching"],
        source_clause_ids=[c3.id],
    )

    tc = TestCase(
        id="test_demo_001",
        title="Successful checkout deducts stock once",
        type=TestType.INTEGRATION,
        given="SKU A has qty 1",
        when="Two parallel checkouts race",
        then="Exactly one succeeds; the other gets sold-out",
        edge_cases=["retry same payment intent"],
        story_id=story.id,
        task_id=t2.id,
        source_clause_ids=[c2.id],
    )

    return Project(
        id=showcase_project_id(),
        name="Showcase — Checkout & OTP (pre-baked)",
        created_at=datetime.utcnow(),
        raw_input=raw,
        source_clauses=[c1, c2, c3],
        summary=summary,
        stories=[story, story2],
        tasks=[t1, t2, t3],
        test_cases=[tc],
        ambiguities=[
            AmbiguityIssue(
                id="amb_demo_001",
                kind=AmbiguityKind.UNQUANTIFIED,
                severity=Severity.MEDIUM,
                excerpt="1k concurrent users",
                explanation="Peak vs sustained load not specified.",
                suggested_question="Is 1k concurrent checkout sessions or total active users?",
                source_clause_ids=[c3.id],
            )
        ],
        risks=[
            Risk(
                id="risk_demo_001",
                category=RiskCategory.SCALABILITY,
                severity=Severity.HIGH,
                title="Hot SKU contention",
                description="High concurrency may bottleneck row locks.",
                mitigation="Partition inventory or queue reservations.",
                source_clause_ids=[c2.id],
            )
        ],
        metrics=ProductivityMetrics(
            manual_minutes=240,
            helix_minutes=12,
            minutes_saved=228,
            hours_saved=3.8,
            cost_saved_usd=380.0,
            artifacts_generated=12,
            coverage_score=0.86,
            citation_item_rate=0.92,
        ),
    )


def ensure_showcase_project(db: Session) -> str | None:
    """Create showcase project for demo user if missing. Returns project id or None."""
    settings = get_settings()
    email = (settings.helix_demo_email or "").strip()
    if not email:
        return None

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        return None

    pid = showcase_project_id()
    existing = db.get(ProjectRecord, pid)
    if existing is not None and existing.owner_id == user.id:
        return pid

    proj = _build_showcase()
    try:
        from .prd_generator import generate_prd_for_project

        proj.prd_document = asyncio.run(
            generate_prd_for_project(proj, use_ai=False)
        )
    except Exception:
        logger.exception("Showcase PRD pre-bake skipped")

    row = ProjectRecord(id=proj.id, name=proj.name, owner_id=user.id, pipeline_json=None)
    db.add(row)
    db.flush()
    ensure_project_row(db, proj, user.id)
    db.commit()

    try:
        asyncio.run(get_store().create(proj))
        embed_requirements(proj.id, [c.text for c in proj.source_clauses])
    except Exception:
        logger.exception("Showcase store/RAG bootstrap failed")

    logger.info("Pre-baked showcase project %s for %s", pid, email)
    return pid
