"""Winning Demo Flow — single-shot SSE orchestrator.

Endpoints:

    GET  /api/demo/steps                   → static metadata (skeleton for UI)
    POST /api/demo/run                     → ad-hoc run on raw text (no persistence)
    POST /api/demo/{project_id}/run        → run + persist on project
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import SessionLocal, get_db
from ...models import Project
from ...services.demo_orchestrator import (
    DEMO_STEPS,
    ensure_project_prd,
    finalize_demo_project,
    run_demo,
)
from ...services.ingestion import split_into_clauses
from ...services.project_bridge import (
    ensure_project_row,
    new_project_id,
    save_project_to_db,
)
from ...services.store import get_store
from ...sqla_models import ProjectRecord, User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

logger = logging.getLogger("helix.demo.route")


router = APIRouter()


class _AdHocBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=20000)
    name: Optional[str] = None
    use_ai: bool = True


class _ProjectRunBody(BaseModel):
    use_ai: Optional[bool] = None


def _resolve_use_ai(requested: Optional[bool]) -> bool:
    if requested is not None:
        return requested
    return not get_settings().helix_demo_fast


SAMPLE_DEMO = (
    "We need to roll out OTP-based login for our B2B portal next quarter. "
    "End users will receive a 6-digit code via SMS through Twilio; on success "
    "we mint a 24h JWT and rotate the refresh token. Admins must enable MFA "
    "for everyone in the Finance org by Q3. The new flow has to integrate "
    "Stripe for the upcoming Premium tier (monthly + annual). Rollback plan "
    "is unclear today. Out of scope: WhatsApp delivery, biometric login, "
    "and the legacy LDAP integration. The system must support 10k concurrent "
    "sessions, p99 < 500ms, and meet GDPR — user data deleted within 30 days "
    "of account closure. Reporting and analytics for OTP delivery are TBD."
)


@router.get("/steps")
def get_steps() -> dict:
    settings = get_settings()
    return {
        "steps": DEMO_STEPS,
        "sample": SAMPLE_DEMO,
        "demo_fast": settings.helix_demo_fast,
        "showcase_project_id": settings.helix_showcase_project_id,
    }


@router.get("/showcase")
def get_showcase() -> dict:
    settings = get_settings()
    return {
        "project_id": settings.helix_showcase_project_id,
        "path": f"/project/{settings.helix_showcase_project_id}/ai-workspace",
        "demo_email": settings.helix_demo_email,
    }


def _format_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/run")
async def run_adhoc(
    body: _AdHocBody,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a demo run on raw requirement text — no persistence.

    A throwaway in-memory `Project` is built so all the analyzers can
    do their work; the project is NOT saved.
    """
    text = body.requirement.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty requirement")

    project = Project(
        id=new_project_id(),
        name=body.name or "Demo run",
        raw_input=text,
        source_clauses=split_into_clauses(text),
    )

    use_ai = _resolve_use_ai(body.use_ai)

    async def events() -> AsyncIterator[str]:
        try:
            async for evt in run_demo(project, use_ai=use_ai):
                yield _format_event(evt)
        except Exception as exc:
            logger.exception("Demo run failed")
            yield _format_event({"step": "error", "status": "error", "detail": str(exc), "percent": 100})
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{project_id}/run")
async def run_for_project(
    project_id: str,
    body: _ProjectRunBody,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a demo run against an existing project, persisting every artifact."""
    uid = user.id
    db0 = SessionLocal()
    try:
        u0 = db0.merge(user)
        row = get_owned_project_row(db0, u0, project_id)
        project = load_project_graph(db0, row)
    finally:
        db0.close()

    use_ai = _resolve_use_ai(body.use_ai)

    async def events() -> AsyncIterator[str]:
        held_complete: dict | None = None
        try:
            async for evt in run_demo(project, use_ai=use_ai):
                if evt.get("step") == "complete" and evt.get("status") == "done":
                    held_complete = evt
                    continue
                yield _format_event(evt)
        except Exception as exc:
            logger.exception("Demo run failed")
            yield _format_event({"step": "error", "status": "error", "detail": str(exc), "percent": 100})
            yield "event: done\ndata: {}\n\n"
            return

        # Persist before complete — workspace PRD/tasks must exist when UI navigates.
        dbw = SessionLocal()
        try:
            u2 = dbw.get(User, uid)
            if u2 is None:
                yield _format_event({"step": "persist", "status": "error", "detail": "user missing", "percent": 100})
                return
            row2 = get_owned_project_row(dbw, u2, project_id)
            finalize_demo_project(project)
            await ensure_project_prd(project, use_ai=use_ai)
            ensure_project_row(dbw, project, uid)
            save_project_to_db(dbw, row2, project)
            dbw.commit()
            yield _format_event(
                {
                    "step": "persist",
                    "status": "done",
                    "percent": 99,
                    "headline": "Artifacts saved",
                    "detail": f"PRD={'yes' if project.prd_document else 'no'} · tasks={len(project.tasks or [])}",
                }
            )
        except Exception as exc:
            logger.exception("Persist after demo failed")
            yield _format_event({"step": "persist", "status": "error", "detail": str(exc), "percent": 100})
            return
        finally:
            dbw.close()
        try:
            store = get_store()
            if await store.get(project_id):
                await store.update(project)
            else:
                await store.create(project)
        except Exception:
            logger.exception("Store update failed")

        if held_complete:
            yield _format_event(held_complete)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
