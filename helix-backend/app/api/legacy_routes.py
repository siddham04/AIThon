"""Public REST API for Helix."""
from __future__ import annotations

import json
import logging
from typing import List

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..agents.chat import ChatAgent
from ..agents.orchestrator import run_pipeline
from ..config import get_settings
from ..models import (
    AppendNotesRequest,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    IngestRequest,
    Project,
    ProjectPatch,
)
from ..services.ingestion import extract_text, split_into_clauses
from ..services.snapshots import save_project_snapshot
from ..services.store import get_store
from .deps import helix_auth_gate
from .exporters import (
    export_azure_devops_json,
    export_csv,
    export_github_issues_json,
    export_jira_csv,
    export_markdown,
)

logger = logging.getLogger("helix.api")

router = APIRouter(
    prefix="/api",
    tags=["helix"],
    dependencies=[Depends(helix_auth_gate)],
)


# --------------------------- health & meta -------------------------------- #


@router.get("/health")
async def health() -> dict:
    from ..services.llm import get_llm

    llm = get_llm()
    return {
        "status": "ok",
        "llm_configured": llm.enabled,
        "version": "0.1.0",
    }


# --------------------------- ingestion ------------------------------------ #


@router.post("/projects/ingest-text")
async def ingest_text(payload: IngestRequest) -> Project:
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(400, "Empty input text")
    project = Project(
        name=payload.name or "Untitled initiative",
        raw_input=text,
        source_clauses=split_into_clauses(text),
    )
    await get_store().create(project)
    return project


@router.post("/projects/ingest-file")
async def ingest_file(file: UploadFile = File(...)) -> Project:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    text = extract_text(file.filename or "input.txt", data)
    if not text.strip():
        raise HTTPException(400, "Could not extract any text from the file")
    project = Project(
        name=(file.filename or "Uploaded document").rsplit(".", 1)[0],
        raw_input=text,
        source_clauses=split_into_clauses(text),
    )
    await get_store().create(project)
    return project


# --------------------------- analysis pipeline ---------------------------- #


@router.post("/projects/{project_id}/analyze")
async def analyze(project_id: str) -> Project:
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    async for _ in run_pipeline(project):
        pass
    await get_store().update(project)
    save_project_snapshot(project, label="analyze")
    return project


@router.get("/projects/{project_id}/analyze/stream")
async def analyze_stream(project_id: str) -> StreamingResponse:
    """Server-Sent Events stream of pipeline progress."""

    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    async def event_gen():
        try:
            async for evt in run_pipeline(project):
                yield f"data: {json.dumps(evt)}\n\n"
            await get_store().update(project)
            save_project_snapshot(project, label="analyze-stream")
            yield (
                "event: done\ndata: "
                + json.dumps(project.model_dump(mode="json"), default=str)
                + "\n\n"
            )
        except Exception as exc:
            logger.exception("Pipeline failed")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------- read / mutate -------------------------------- #


@router.get("/projects")
async def list_projects() -> List[Project]:
    return await get_store().list()


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> Project:
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/projects/{project_id}")
async def patch_project(project_id: str, patch: ProjectPatch) -> Project:
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    data = patch.model_dump(exclude_unset=True)
    if not data:
        return project
    for key, value in data.items():
        setattr(project, key, value)
    await get_store().update(project)
    save_project_snapshot(project, label="patch")
    return project


@router.post("/projects/{project_id}/append-notes")
async def append_notes(project_id: str, payload: AppendNotesRequest) -> Project:
    extra = (payload.text or "").strip()
    if not extra:
        raise HTTPException(400, "Empty notes")
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    new_clauses = split_into_clauses(extra)
    start = len(project.source_clauses)
    for i, c in enumerate(new_clauses):
        c.index = start + i
    project.source_clauses.extend(new_clauses)
    project.raw_input = (project.raw_input.rstrip() + "\n\n" + extra).strip()
    await get_store().update(project)
    save_project_snapshot(project, label="append-notes")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> dict:
    ok = await get_store().delete(project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    return {"deleted": project_id}


# --------------------------- integrations --------------------------------- #


@router.post("/projects/{project_id}/integrations/jira-stub")
async def jira_publish_stub(project_id: str) -> dict:
    """POST Jira-import CSV to HELIX_JIRA_WEBHOOK_URL when set (enterprise demo stub)."""
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    body = export_jira_csv(project)
    raw = body.encode("utf-8")
    url = get_settings().jira_webhook_url.strip()
    delivered = False
    status_code: int | None = None
    if url:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    url,
                    content=raw,
                    headers={"Content-Type": "text/csv; charset=utf-8"},
                )
                status_code = resp.status_code
                delivered = resp.status_code < 400
        except Exception as exc:
            logger.warning("Jira stub POST failed: %s", exc)
            delivered = False
    return {
        "delivered": delivered,
        "target": url or None,
        "csv_bytes": len(raw),
        "http_status": status_code,
    }


# --------------------------- chat ----------------------------------------- #


@router.post("/projects/{project_id}/chat")
async def chat(project_id: str, payload: ChatRequest) -> ChatResponse:
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not payload.message.strip():
        raise HTTPException(400, "Empty message")

    user_msg = ChatMessage(role="user", content=payload.message.strip())
    project.chat_history.append(user_msg)

    agent = ChatAgent()
    reply = await agent.reply(project, payload.message)
    project.chat_history.append(reply)
    await get_store().update(project)
    return ChatResponse(message=reply)


# --------------------------- export --------------------------------------- #


@router.get("/projects/{project_id}/export/{fmt}")
async def export(project_id: str, fmt: str):
    project = await get_store().get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    fmt = fmt.lower()
    if fmt == "json":
        return project
    if fmt == "markdown":
        return _text_response(export_markdown(project), "text/markdown", "helix.md")
    if fmt == "csv":
        return _text_response(export_csv(project), "text/csv", "helix-tasks.csv")
    if fmt == "jira":
        return _text_response(export_jira_csv(project), "text/csv", "helix-jira.csv")
    if fmt == "ado":
        return _text_response(
            json.dumps(export_azure_devops_json(project), indent=2),
            "application/json",
            "helix-ado.json",
        )
    if fmt == "github":
        return _text_response(
            json.dumps(export_github_issues_json(project), indent=2),
            "application/json",
            "helix-github.json",
        )
    raise HTTPException(400, f"Unsupported format: {fmt}")


def _text_response(content: str, media: str, filename: str):
    from fastapi.responses import Response

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
