from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas.tasks import CeleryTaskAccepted
from ...schemas.testcase import TestCaseResponse, TestCaseStatusPatch
from ...services.generation_service import generate_testcases_blocking
from ...services.project_bridge import ensure_project_row
from ...services.task_progress import set_task_progress
from ...sqla_models import TestCaseRecord, User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.post("/generate/{project_id}", response_model=CeleryTaskAccepted)
async def generate_testcases(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CeleryTaskAccepted:
    row = get_owned_project_row(db, user, project_id)
    _ = load_project_graph(db, row)
    task_id = uuid.uuid4().hex
    set_task_progress(task_id, 0, "queued", "Queued")
    use_celery = os.environ.get("HELIX_USE_CELERY", "").lower() in ("1", "true", "yes")
    if use_celery:
        try:
            from celery_app import generate_testcases_task

            generate_testcases_task.apply_async(
                args=[project_id, user.id, task_id], task_id=task_id
            )
            return CeleryTaskAccepted(task_id=task_id, mode="celery")
        except ImportError:
            pass
        except Exception:
            pass
    background_tasks.add_task(
        generate_testcases_blocking, project_id, user.id, task_id
    )
    return CeleryTaskAccepted(task_id=task_id, mode="background")


@router.get(
    "/{project_id}",
    response_model=list[TestCaseResponse],
    response_model_by_alias=True,
)
def list_testcases(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TestCaseResponse]:
    get_owned_project_row(db, user, project_id)
    rows = db.scalars(
        select(TestCaseRecord).where(TestCaseRecord.project_id == project_id)
    ).all()
    out: list[TestCaseResponse] = []
    for r in rows:
        extra: dict = {}
        try:
            extra = json.loads(r.extra_json or "{}")
        except json.JSONDecodeError:
            extra = {}
        out.append(
            TestCaseResponse(
                id=r.id,
                title=r.title,
                tc_type=r.tc_type,
                given=r.given,
                when=r.when,
                then=r.then,
                status=r.status,
                extra=extra,
            )
        )
    return out


@router.patch(
    "/{tc_id}/status",
    response_model=TestCaseResponse,
    response_model_by_alias=True,
)
def patch_testcase_status(
    tc_id: str,
    body: TestCaseStatusPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TestCaseResponse:
    rec = db.get(TestCaseRecord, tc_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test case not found")
    row = get_owned_project_row(db, user, rec.project_id)
    proj = load_project_graph(db, row)
    updated = False
    for tc in proj.test_cases:
        if tc.id == tc_id:
            tc.status = body.status
            updated = True
            break
    if not updated:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Test case not present on project graph"
        )
    ensure_project_row(db, proj, user.id)
    db.commit()
    rec2 = db.get(TestCaseRecord, tc_id)
    if rec2 is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test case not found after sync")
    extra: dict = {}
    try:
        extra = json.loads(rec2.extra_json or "{}")
    except json.JSONDecodeError:
        extra = {}
    return TestCaseResponse(
        id=rec2.id,
        title=rec2.title,
        tc_type=rec2.tc_type,
        given=rec2.given,
        when=rec2.when,
        then=rec2.then,
        status=rec2.status,
        extra=extra,
    )
