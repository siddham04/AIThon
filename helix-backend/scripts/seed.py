"""Idempotent seed: demo@demo.com / demo123 and a project with pre-built artifacts."""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

_here = Path(__file__).resolve()
ROOT = _here.parent.parent
if not (ROOT / "app").is_dir():
    raise RuntimeError(
        "Cannot locate Helix app package (run from helix-backend or Docker /app)."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("helix.seed")

# Canonical hackathon backup — bookmark /project/proj_demo_seed01/ai-workspace
SEED_PROJECT_ID = "proj_demo_seed01"
SEED_PROJECT_NAME = "Showcase — Checkout & OTP (pre-baked)"


def _wait_for_db(engine, attempts: int = 45, delay_sec: float = 1.0) -> None:
    from sqlalchemy import text

    for i in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as e:
            log.warning("Database not ready (%s/%s): %s", i + 1, attempts, e)
            time.sleep(delay_sec)
    raise RuntimeError("Could not connect to database after retries")


def _build_demo_project():
    from datetime import datetime

    from app.models import (
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

    c1 = SourceClause(id="clause_demo_001", index=0, text="Customers must pay with card or wallet within 10 seconds.")
    c2 = SourceClause(id="clause_demo_002", index=1, text="Inventory must decrement atomically when an order is confirmed.")
    c3 = SourceClause(id="clause_demo_003", index=2, text="SLA: p95 checkout API latency under 300ms for 1k concurrent users.")

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

    amb = AmbiguityIssue(
        id="amb_demo_001",
        kind=AmbiguityKind.UNQUANTIFIED,
        severity=Severity.MEDIUM,
        excerpt="1k concurrent users",
        explanation="Peak vs sustained load not specified.",
        suggested_question="Is 1k concurrent checkout sessions or total active users?",
        source_clause_ids=[c3.id],
    )

    risk = Risk(
        id="risk_demo_001",
        category=RiskCategory.SCALABILITY,
        severity=Severity.HIGH,
        title="Hot SKU contention",
        description="High concurrency may bottleneck row locks.",
        mitigation="Partition inventory or queue reservations.",
        source_clause_ids=[c2.id],
    )

    metrics = ProductivityMetrics(
        manual_minutes=240,
        helix_minutes=12,
        minutes_saved=228,
        hours_saved=3.8,
        cost_saved_usd=380.0,
        artifacts_generated=12,
        coverage_score=0.86,
        citation_item_rate=0.92,
    )

    return Project(
        id=SEED_PROJECT_ID,
        name=SEED_PROJECT_NAME,
        created_at=datetime.utcnow(),
        raw_input=raw,
        source_clauses=[c1, c2, c3],
        summary=summary,
        stories=[story, story2],
        tasks=[t1, t2, t3],
        test_cases=[tc],
        ambiguities=[amb],
        risks=[risk],
        metrics=metrics,
        last_pipeline_timings_ms={
            "Requirement Analyst": 540,
            "Product Manager": 1200,
            "Architect": 980,
            "QA Agent": 1500,
            "Scrum Master": 1100,
        },
    )


def main() -> None:
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import SessionLocal, engine, init_db
    from app.services.project_bridge import ensure_project_row
    from app.services.rag_service import embed_requirements
    from app.services.security import hash_password
    from app.services.store import get_store
    from app.sqla_models import ProjectRecord, User

    _wait_for_db(engine)
    init_db()
    settings = get_settings()
    demo_email = (settings.helix_demo_email or "").strip()
    demo_password = settings.helix_demo_password or ""
    if not demo_email or not demo_password:
        log.error("Set HELIX_DEMO_EMAIL and HELIX_DEMO_PASSWORD in .env before running seed.")
        raise SystemExit(1)

    db = SessionLocal()
    try:
        user = db.scalars(select(User).where(User.email == demo_email)).first()
        if user is None:
            user = User(email=demo_email, hashed_password=hash_password(demo_password))
            db.add(user)
            db.commit()
            db.refresh(user)
            log.info("Created demo user %s (id=%s)", demo_email, user.id)
        else:
            log.info("Demo user already exists: %s (id=%s)", demo_email, user.id)

        existing = db.get(ProjectRecord, SEED_PROJECT_ID)
        if existing is not None and existing.owner_id == user.id:
            log.info("Seed project %s already present; skipping graph insert.", SEED_PROJECT_ID)
            return

        proj = _build_demo_project()
        try:
            from app.services.prd_generator import generate_prd_for_project

            proj.prd_document = asyncio.run(
                generate_prd_for_project(proj, use_ai=False)
            )
        except Exception as e:
            log.warning("PRD pre-bake skipped: %s", e)

        row = ProjectRecord(
            id=proj.id,
            name=proj.name,
            owner_id=user.id,
            pipeline_json=None,
        )
        db.add(row)
        db.flush()
        ensure_project_row(db, proj, user.id)
        db.commit()

        asyncio.run(get_store().create(proj))
        try:
            embed_requirements(proj.id, [c.text for c in proj.source_clauses])
        except Exception as e:  # noqa: BLE001 — never fail seed on embeddings
            log.warning("embed_requirements skipped: %s", e)
        log.info("Seeded project %s (%s)", proj.id, proj.name)
    finally:
        db.close()


if __name__ == "__main__":
    main()
