from __future__ import annotations

import json
import os
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...agents.orchestrator import run_pipeline
from ...database import SessionLocal, get_db
from ...models import Project
from ...schemas.artifact import ApprovalBody, ArtifactsBundleResponse
from ...schemas.tasks import CeleryTaskAccepted
from ...services.ai_service import get_ai_service
from ...services.effort_service import calculate_project_estimate
from ...services.generation_service import generate_artifacts_blocking
from ...services.ingestion import render_clauses
from ...services.project_bridge import ensure_project_row, pydantic_from_db_row
from ...services.task_progress import set_task_progress
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


def _citation_item_rate(p: Project) -> float:
    if p.metrics is not None:
        return float(p.metrics.citation_item_rate)
    traceable = list(p.stories) + list(p.tasks) + list(p.test_cases)
    if not traceable:
        return 0.0
    cited = sum(1 for x in traceable if len(x.source_clause_ids or []) > 0)
    return round(cited / len(traceable), 3)

router = APIRouter()


def _requirements_blob(project: Project) -> str:
    raw = (project.raw_input or "").strip()
    if raw:
        return raw
    return render_clauses(project.source_clauses)


@router.post("/generate/{project_id}", response_model=CeleryTaskAccepted)
async def generate_artifacts(
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
            from celery_app import generate_artifacts_task

            generate_artifacts_task.apply_async(
                args=[project_id, user.id, task_id], task_id=task_id
            )
            return CeleryTaskAccepted(task_id=task_id, mode="celery")
        except ImportError:
            pass
        except Exception:
            pass
    background_tasks.add_task(
        generate_artifacts_blocking, project_id, user.id, task_id
    )
    return CeleryTaskAccepted(task_id=task_id, mode="background")


@router.post("/ai/json/{project_id}")
async def ai_artifact_json(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    ai = get_ai_service()
    if not ai.enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Anthropic API is not configured (set ANTHROPIC_API_KEY).",
        )
    try:
        return await ai.generate_artifacts(_requirements_blob(project))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Artifact generation failed: {exc}",
        ) from exc


@router.get("/ai/stream/{project_id}")
async def ai_artifact_stream(
    project_id: str,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    db0 = SessionLocal()
    try:
        u0 = db0.merge(user)
        row = get_owned_project_row(db0, u0, project_id)
        project = load_project_graph(db0, row)
    finally:
        db0.close()

    ai = get_ai_service()
    if not ai.enabled:

        async def err() -> AsyncIterator[str]:
            yield f"event: error\ndata: {json.dumps({'error': 'Anthropic API not configured'})}\n\n"

        return StreamingResponse(
            err(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    text_blob = _requirements_blob(project)

    async def events() -> AsyncIterator[str]:
        try:
            async for chunk in ai.stream_artifacts(text_blob):
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/estimate-summary/{project_id}")
def artifact_estimate_summary(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    payload = []
    for t in project.tasks:
        h = t.estimate_hours
        payload.append(
            {
                "story_points": t.estimate_points or 0,
                "hours_low": float(h or 0),
                "hours_high": float(h or 0),
                "confidence": t.confidence,
            }
        )
    return calculate_project_estimate(payload)


@router.get("/{project_id}", response_model=ArtifactsBundleResponse)
def get_artifacts(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ArtifactsBundleResponse:
    row = get_owned_project_row(db, user, project_id)
    p = pydantic_from_db_row(row)
    if p is None:
        return ArtifactsBundleResponse(
            project_id=project_id,
            stories=[],
            tasks=[],
            summary=None,
            citation_item_rate=0.0,
            last_pipeline_timings_ms=None,
        )
    summary = p.summary.model_dump(mode="json") if p.summary else None
    return ArtifactsBundleResponse(
        project_id=project_id,
        stories=[s.model_dump(mode="json") for s in p.stories],
        tasks=[t.model_dump(mode="json") for t in p.tasks],
        summary=summary,
        citation_item_rate=_citation_item_rate(p),
        last_pipeline_timings_ms=p.last_pipeline_timings_ms,
    )


@router.patch("/{project_id}/stories/{story_id}/approval")
def patch_story_export_approval(
    project_id: str,
    story_id: str,
    body: ApprovalBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    p = load_project_graph(db, row)
    for s in p.stories:
        if s.id == story_id:
            s.approved_for_export = body.approved_for_export
            ensure_project_row(db, p, user.id)
            db.commit()
            return {"ok": True, "story_id": story_id, "approved_for_export": s.approved_for_export}
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Story not found")


@router.patch("/{project_id}/tasks/{task_id}/approval")
def patch_task_export_approval(
    project_id: str,
    task_id: str,
    body: ApprovalBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    p = load_project_graph(db, row)
    for t in p.tasks:
        if t.id == task_id:
            t.approved_for_export = body.approved_for_export
            ensure_project_row(db, p, user.id)
            db.commit()
            return {"ok": True, "task_id": task_id, "approved_for_export": t.approved_for_export}
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")


@router.get("/stream/{project_id}")
async def stream_artifacts(
    project_id: str,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    uid = user.id
    db0 = SessionLocal()
    try:
        u0 = db0.merge(user)
        row = get_owned_project_row(db0, u0, project_id)
        project = load_project_graph(db0, row)
    finally:
        db0.close()

    async def events() -> AsyncIterator[str]:
        try:
            async for evt in run_pipeline(project):
                yield f"data: {json.dumps(evt, default=str)}\n\n"
            dbw = SessionLocal()
            try:
                u2 = dbw.get(User, uid)
                if u2 is None:
                    yield f"event: error\ndata: {json.dumps({'error': 'user missing'})}\n\n"
                    return
                from ...services.project_bridge import ensure_project_row

                ensure_project_row(dbw, project, uid)
                dbw.commit()
            finally:
                dbw.close()
            from ...services.store import get_store

            store = get_store()
            if await store.get(project_id):
                await store.update(project)
            else:
                await store.create(project)
            yield (
                "event: done\ndata: "
                + json.dumps(project.model_dump(mode="json"), default=str)
                + "\n\n"
            )
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
