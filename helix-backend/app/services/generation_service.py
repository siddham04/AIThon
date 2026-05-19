from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from ..agents.orchestrator import run_pipeline
from ..agents.test_architect import TestArchitectAgent
from ..database import SessionLocal
from ..models import Project
from ..services.project_bridge import ensure_project_row, pydantic_from_db_row
from ..services.store import get_store
from ..services.task_progress import set_task_progress
from ..sqla_models import ProjectRecord

logger = logging.getLogger("helix.generation")


async def _run_pipeline_with_progress(project: Project, task_id: str) -> None:
    step = 0
    async for evt in run_pipeline(project):
        step += 1
        pct = min(95, 10 + step * 6)
        stage = evt.get("stage") if isinstance(evt, dict) else str(evt)
        st = evt.get("status") if isinstance(evt, dict) else "running"
        set_task_progress(task_id, pct, str(st), str(stage))


async def generate_artifacts_async(project_id: str, user_id: int, task_id: str) -> None:
    set_task_progress(task_id, 2, "running", "Loading project")
    db: Session = SessionLocal()
    try:
        row = db.get(ProjectRecord, project_id)
        if row is None or row.owner_id != user_id:
            set_task_progress(task_id, 100, "error", "Project not found")
            return
        project = pydantic_from_db_row(row)
        if project is None:
            project = Project(id=row.id, name=row.name, raw_input="", source_clauses=[])
        store = get_store()
        if await store.get(project_id):
            await store.update(project)
        else:
            await store.create(project)
        await _run_pipeline_with_progress(project, task_id)
        ensure_project_row(db, project, user_id)
        db.commit()
        await get_store().update(project)
        set_task_progress(task_id, 100, "done", "Artifacts ready")
    except Exception as exc:  # pragma: no cover
        logger.exception("Artifact generation failed")
        set_task_progress(task_id, 100, "error", str(exc))
        db.rollback()
    finally:
        db.close()


def generate_artifacts_blocking(project_id: str, user_id: int, task_id: str) -> None:
    asyncio.run(generate_artifacts_async(project_id, user_id, task_id))


async def generate_testcases_async(project_id: str, user_id: int, task_id: str) -> None:
    set_task_progress(task_id, 5, "running", "Loading project")
    db: Session = SessionLocal()
    try:
        row = db.get(ProjectRecord, project_id)
        if row is None or row.owner_id != user_id:
            set_task_progress(task_id, 100, "error", "Project not found")
            return
        project = pydantic_from_db_row(row)
        if project is None:
            project = Project(id=row.id, name=row.name, raw_input="", source_clauses=[])
        store = get_store()
        if await store.get(project_id):
            await store.update(project)
        else:
            await store.create(project)
        set_task_progress(task_id, 20, "running", "Generating tests")
        agent = TestArchitectAgent()
        patch = await agent.run(project)
        for k, v in patch.items():
            setattr(project, k, v)
        ensure_project_row(db, project, user_id)
        db.commit()
        store = get_store()
        if await store.get(project_id):
            await store.update(project)
        else:
            await store.create(project)
        set_task_progress(task_id, 100, "done", "Test cases updated")
    except Exception as exc:  # pragma: no cover
        logger.exception("Test generation failed")
        set_task_progress(task_id, 100, "error", str(exc))
        db.rollback()
    finally:
        db.close()


def generate_testcases_blocking(project_id: str, user_id: int, task_id: str) -> None:
    asyncio.run(generate_testcases_async(project_id, user_id, task_id))
