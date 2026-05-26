"""Repair a legacy project whose source_clauses contain noise.

Usage (PowerShell, from helix-backend/):

    .\.venv\Scripts\python.exe scripts\repair_legacy_project.py <project_id>

Or for *every* project owned by the demo user:

    .\.venv\Scripts\python.exe scripts\repair_legacy_project.py --all

What it does
============

Projects created BEFORE the demo-day Jira-preview fix have these
problems persisted in their pipeline_json:

  - source_clauses include the "[Helix team configuration]" preamble
    as if it were a requirement.
  - The derived project name is the literal string "Ingested document".
  - Stories were generated against those bad clauses, so their titles
    read "Deliver: Team size: 6 engineers" and so on.

This script:

  1. Loads the project from the database.
  2. Re-splits the project's raw_input through the new clean
     splitter (which strips the team-config preamble + filters out
     headers, footers, page numbers, copyright lines, ...).
  3. Derives a real project name if the current one is "Ingested
     document" / "[Helix team configuration]" / etc.
  4. Wipes the stale generated artifacts (stories, tasks, test_cases,
     risks, summary, backlog, ...).
  5. Re-runs the demo orchestrator in mock mode so a fresh set of
     stories/tasks/tests/risks is generated from the cleaned clauses.
  6. Persists the rebuilt project graph back to the database.

The repaired project keeps its original ``id`` and ``owner_id`` so
existing UI bookmarks / sharing links still work.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Force the global kill-switch on so we never accidentally burn LLM
# credits when repairing — the orchestrator will use the deterministic
# mock fallback, which is exactly what we want for a quick fix-up.
os.environ["HELIX_USE_AI"] = "false"
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app.database import SessionLocal, init_db
from app.api.routes.ingestion import _derive_project_name
from app.services.ingestion import _strip_team_config_preamble, split_into_clauses
from app.services.demo_orchestrator import run_demo
from app.services.project_bridge import (
    ensure_project_row,
    save_project_to_db,
    pydantic_from_db_row,
)
from app.sqla_models import ProjectRecord


_GENERIC_NAMES = {
    "",
    "ingested document",
    "untitled initiative",
    "untitled project",
    "[helix team configuration]",
}


def _project_needs_repair(project) -> bool:
    """Heuristic: does this project still contain stale team-config noise?"""
    if (project.name or "").strip().lower() in _GENERIC_NAMES:
        return True
    for clause in project.source_clauses or []:
        txt = (clause.text or "").strip()
        if txt.startswith("[Helix team configuration]"):
            return True
        if txt.lower().startswith("team size:"):
            return True
        if txt.lower().startswith("priority mode:"):
            return True
        if txt.lower().startswith("tech stack:"):
            return True
    return False


async def repair_one(project_id: str) -> bool:
    """Repair a single project by id. Returns True if anything changed."""
    db = SessionLocal()
    try:
        row = db.get(ProjectRecord, project_id)
        if row is None:
            print(f"[skip] {project_id}: no such project in DB")
            return False
        project = pydantic_from_db_row(row)
        if project is None:
            print(f"[skip] {project_id}: no pipeline_json to rebuild from")
            return False

        if not _project_needs_repair(project):
            print(f"[ok]   {project_id} ({project.name!r}): already clean")
            return False

        original_name = project.name
        original_clause_count = len(project.source_clauses or [])
        raw = (project.raw_input or "").strip()
        if not raw:
            print(f"[skip] {project_id}: raw_input is empty, cannot rebuild")
            return False

        # 1. Re-split clauses through the new cleaning pipeline.
        cleaned_text, _ = _strip_team_config_preamble(raw)
        cleaned_text = cleaned_text.strip() or raw
        project.raw_input = cleaned_text
        project.source_clauses = split_into_clauses(cleaned_text)

        # 2. Promote a real project name if the stored one is generic.
        if (project.name or "").strip().lower() in _GENERIC_NAMES:
            project.name = _derive_project_name(cleaned_text)
            row.name = project.name

        # 3. Wipe the stale generated artifacts so the orchestrator
        #    regenerates them from the new clauses. We only blank the
        #    fields that demo_orchestrator.run_demo actually rebuilds;
        #    leave the rest (chat_history, metrics, ...) untouched.
        project.stories = []
        project.tasks = []
        project.test_cases = []
        project.risks = []
        project.ambiguities = []
        project.summary = None
        project.architecture_brief = None
        project.architecture_diagram = None
        project.api_contract_suite = None
        project.database_schema = None
        project.generated_test_suite = None
        project.delivery_readiness = None
        project.delivery_readiness_center = None
        project.quality_score_report = None
        project.review_board_report = None
        project.prd_document = None
        project.jira_backlog = None
        project.sprint_plan = None
        project.team_sprint_plan = None
        project.auto_sprint_plan = None
        project.sprint_kanban = None
        project.traceability_matrix = None
        project.risk_center = None
        project.requirement_brief = None
        project.pipeline_epic = None
        project.requirement_estimate = None
        project.requirement_risk = None
        project.defect_prediction = None
        project.impact_report = None
        project.pm_forecast = None

        # 4. Re-run the pipeline in mock mode against the cleaned clauses.
        async for _ev in run_demo(project, use_ai=False):
            pass

        # 5. Persist.
        ensure_project_row(db, project, row.owner_id)
        save_project_to_db(db, row, project)
        db.commit()

        print(
            f"[fix]  {project_id}: name {original_name!r} -> {project.name!r}, "
            f"clauses {original_clause_count} -> {len(project.source_clauses)}, "
            f"stories regenerated: {len(project.stories)}"
        )
        return True
    finally:
        db.close()


async def repair_all() -> None:
    db = SessionLocal()
    try:
        ids = [pid for (pid,) in db.query(ProjectRecord.id).all()]
    finally:
        db.close()
    if not ids:
        print("No projects in the database.")
        return
    print(f"Scanning {len(ids)} project(s)…")
    fixed = 0
    for pid in ids:
        if await repair_one(pid):
            fixed += 1
    print(f"\nDone. Repaired {fixed} of {len(ids)} project(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("project_id", nargs="?", help="project_id to repair")
    group.add_argument("--all", action="store_true", help="repair every project")
    args = parser.parse_args()

    init_db()

    if args.all:
        asyncio.run(repair_all())
    else:
        asyncio.run(repair_one(args.project_id))


if __name__ == "__main__":
    main()
