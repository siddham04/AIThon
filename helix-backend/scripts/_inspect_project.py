"""Throwaway one-liner replacement for an `inspect` shell command that
Windows + PowerShell f-string quoting kept fighting with."""
from __future__ import annotations
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ABS_DB = os.path.join(_BACKEND_DIR, "helix.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_ABS_DB.replace(os.sep, '/')}"
sys.path.insert(0, _BACKEND_DIR)

from app.database import SessionLocal, engine
from app.sqla_models import ProjectRecord
from app.services.project_bridge import pydantic_from_db_row

print(f"(connecting to: {engine.url})")


def main(pid: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(ProjectRecord).filter(ProjectRecord.id == pid).first()
        if row is None:
            print(f"No project with id {pid!r}")
            return
        p = pydantic_from_db_row(row)
        if p is None:
            print(f"Project {pid} has no pipeline_json")
            return
        raw_chars = len(p.raw_input or "")
        print(f"name: {p.name!r}")
        print(f"raw_input chars: {raw_chars}")
        print(f"clauses: {len(p.source_clauses)}")
        print(f"stories: {len(p.stories)}")
        print(f"tasks: {len(p.tasks)}")
        print(f"test_cases: {len(p.test_cases)}")
        print(f"risks: {len(p.risks)}")
        print(f"ambiguities: {len(p.ambiguities)}")
        print(f"summary present: {p.summary is not None}")
        print(f"review_board_report: {p.review_board_report is not None}")
        print(f"requirement_risk: {p.requirement_risk is not None}")
        print(f"requirement_estimate: {p.requirement_estimate is not None}")
        print(f"auto_sprint_plan: {p.auto_sprint_plan is not None}")
        print(f"team_sprint_plan: {p.team_sprint_plan is not None}")
        print(f"jira_backlog: {p.jira_backlog is not None}")
        print(f"prd_document: {p.prd_document is not None}")
        print(f"quality_score_report: {p.quality_score_report is not None}")
        print()
        print("FIRST 6 STORIES:")
        for s in p.stories[:6]:
            print(f"  - {s.title}")
        print()
        print("FIRST 6 CLAUSES:")
        for c in p.source_clauses[:6]:
            print(f"  [{c.id}] {c.text[:120]}")
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "proj_demo_seed01")
