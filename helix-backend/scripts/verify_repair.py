"""End-to-end verification that repair_legacy_project.py actually heals
a broken project.

Builds a fresh project with the *old* broken behaviour (clauses include
the team-config preamble, name is "Ingested document", stories are
"Deliver: ..." templates), commits it to the DB, then calls the repair
script and prints before/after.
"""
from __future__ import annotations

import asyncio
import os
import sys

os.environ["HELIX_USE_AI"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite:///./helix_verify_repair.db")
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app.database import SessionLocal, init_db
from app.models import Project, SourceClause
from app.sqla_models import ProjectRecord, User as UserRow
from app.services.project_bridge import ensure_project_row, save_project_to_db
from sqlalchemy import select

# Force-import to reuse the repair logic
from scripts.repair_legacy_project import repair_one


PROJECT_ID = "proj_legacy_demo_test"
OWNER_EMAIL = "verify-repair@example.com"


RAW_INPUT_WITH_PREAMBLE = (
    "[Helix team configuration]\n"
    "Team size: 6 engineers\n"
    "Sprint length: 2 weeks\n"
    "Priority mode: delivery-first\n"
    "Tech stack: React · FastAPI · PostgreSQL\n"
    "---\n\n"
    "5-10% MAPE Accuracy: Optimizing Demand Forecasting for Cost "
    "Efficiency and Better Decisions for Retail and Professional "
    "Services Company\n"
    "\n"
    "Overview\n"
    "A leading retail and professional services company needed a "
    "predictive model to project residential operator demand based on "
    "recent momentum.\n"
    "Their goal was to make data-driven decisions on pricing, "
    "promotions, and demand planning.\n"
    "An accurate forecast would help align business performance with "
    "financial commitments and optimize sales strategies.\n"
    "\n"
    "rsystems.com\n"
    "All rights reserved. Internal\n"
)


# Simulate the OLD bad clauses — what would have been in the DB before
# my ingestion fixes. (Same first 8 lines the user pasted in their bug
# report, with stable clause ids.)
BAD_CLAUSES = [
    SourceClause(index=i, text=t)
    for i, t in enumerate([
        "[Helix team configuration] Team size: 6 engineers Sprint length: 2 weeks",
        "Priority mode: delivery-first",
        "Tech stack: React · FastAPI · PostgreSQL ---",
        "5-10% MAPE Accuracy: Optimizing Demand Forecasting for Cost Efficiency",
        "A leading retail and professional services company needed a predictive",
        "Their goal was to make data-driven decisions on pricing, promotions, an",
        "An accurate forecast would help align business performance with financi",
        "Our Solution and Approach Business Impact Technology Stack",
    ])
]


def _hr(title: str) -> None:
    print()
    print("=" * 76)
    print(f" {title}")
    print("=" * 76)


def _seed_broken_project() -> None:
    """Insert a project into the DB that looks like a pre-fix one."""
    init_db()
    db = SessionLocal()
    try:
        # Make sure we have a user row to own the project (FK).
        user = db.scalars(select(UserRow).where(UserRow.email == OWNER_EMAIL)).first()
        if user is None:
            user = UserRow(
                email=OWNER_EMAIL,
                hashed_password="not-a-real-hash-for-this-test",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        existing = db.get(ProjectRecord, PROJECT_ID)
        if existing is not None:
            db.delete(existing)
            db.commit()

        proj = Project(
            id=PROJECT_ID,
            name="Ingested document",
            raw_input=RAW_INPUT_WITH_PREAMBLE,
            source_clauses=BAD_CLAUSES,
        )
        row = ProjectRecord(id=PROJECT_ID, name=proj.name, owner_id=user.id)
        db.add(row)
        db.flush()
        ensure_project_row(db, proj, user.id)
        save_project_to_db(db, row, proj)
        db.commit()
    finally:
        db.close()


def _dump(label: str) -> None:
    from app.services.project_bridge import pydantic_from_db_row

    db = SessionLocal()
    try:
        row = db.get(ProjectRecord, PROJECT_ID)
        if row is None:
            print(f"[{label}] no row found")
            return
        proj = pydantic_from_db_row(row)
        print(f"  name:    {proj.name!r}")
        print(f"  clauses: {len(proj.source_clauses)}")
        for c in proj.source_clauses[:4]:
            print(f"    [{c.id}] {c.text[:90]}")
        if len(proj.source_clauses) > 4:
            print(f"    … +{len(proj.source_clauses) - 4} more")
        print(f"  stories: {len(proj.stories)}")
        for s in proj.stories[:4]:
            print(f"    - {s.title[:90]}")
        if len(proj.stories) > 4:
            print(f"    … +{len(proj.stories) - 4} more")
        print(f"  tasks:   {len(proj.tasks)}")
        for t in proj.tasks[:4]:
            print(f"    - {t.title[:90]}")
        if len(proj.tasks) > 4:
            print(f"    … +{len(proj.tasks) - 4} more")
    finally:
        db.close()


async def main() -> None:
    _seed_broken_project()

    _hr("BEFORE repair (broken state, as the user sees it today)")
    _dump("before")

    _hr("Running scripts/repair_legacy_project.py …")
    changed = await repair_one(PROJECT_ID)

    _hr("AFTER repair")
    _dump("after")

    print()
    print(f"Repair returned changed={changed}.")


if __name__ == "__main__":
    asyncio.run(main())
