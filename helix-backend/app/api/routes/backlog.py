"""Automatic Jira Backlog Generator API.

POST /api/backlog/{project_id}/generate   — generate Epic→Story→Task→Subtask hierarchy
GET  /api/backlog/{project_id}            — most-recent persisted backlog
GET  /api/backlog/{project_id}/json       — download as canonical JSON shape
GET  /api/backlog/{project_id}/jira-csv   — download Jira-importable CSV (4 levels)
GET  /api/backlog/{project_id}/ado-csv    — download Azure DevOps CSV (4 levels)
POST /api/backlog/{project_id}/jira-push  — push 4 levels to Jira REST
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import JiraBacklog
from ...services.backlog_export import (
    export_backlog_to_jira,
    to_azure_devops_csv,
    to_jira_csv,
)
from ...services.backlog_generator import generate_backlog, to_simple_json
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

logger = logging.getLogger("helix.backlog_api")

router = APIRouter()


async def _ensure_backlog_fresh(
    db: Session,
    row,
    project,
    *,
    use_ai: bool = False,
) -> JiraBacklog:
    """Regenerate backlog when missing or built before tasks existed."""
    stale = project.jira_backlog is None or (
        bool(project.tasks) and not (project.jira_backlog.tasks or [])
    )
    if stale:
        project.jira_backlog = await generate_backlog(project, use_ai=use_ai)
        save_project_to_db(db, row, project)
        db.commit()
    if project.jira_backlog is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Backlog has not been generated yet for this project.",
        )
    return project.jira_backlog


@router.post("/{project_id}/generate", response_model=JiraBacklog)
async def generate_for_project(
    project_id: str,
    use_ai: bool = Query(True, description="Use Azure OpenAI for richer epic/subtasks."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JiraBacklog:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if not project.stories and not project.tasks:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Generate stories + tasks first — backlog needs the SDLC pipeline output.",
        )
    backlog = await generate_backlog(project, use_ai=use_ai)
    project.jira_backlog = backlog
    save_project_to_db(db, row, project)
    db.commit()
    return backlog


@router.get("/{project_id}", response_model=JiraBacklog)
def get_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JiraBacklog:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.jira_backlog is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Backlog has not been generated yet for this project.",
        )
    return project.jira_backlog


@router.get("/{project_id}/json")
async def download_simple_json(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    backlog = await _ensure_backlog_fresh(db, row, project)
    payload = to_simple_json(backlog)
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-backlog-{project.id[:8]}.json"'
            )
        },
    )


@router.get("/{project_id}/jira-csv/preview")
async def preview_jira_csv(
    project_id: str,
    limit: int = 24,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """First N rows of the Jira CSV for in-app preview (P2)."""
    import csv
    import io

    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    backlog = await _ensure_backlog_fresh(db, row, project)
    text = to_jira_csv(backlog)
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = []
    for i, r in enumerate(reader):
        if i >= max(1, min(limit, 100)):
            break
        rows.append(dict(r))
    return {
        "headers": headers,
        "rows": rows,
        "total_preview": len(rows),
        "truncated": len(rows) >= limit,
    }


@router.get("/{project_id}/jira-csv")
async def download_jira_csv(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    backlog = await _ensure_backlog_fresh(db, row, project)
    csv_body = to_jira_csv(backlog)
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-backlog-{project.id[:8]}.csv"'
            )
        },
    )


@router.get("/{project_id}/ado-csv")
async def download_ado_csv(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    backlog = await _ensure_backlog_fresh(db, row, project)
    csv_body = to_azure_devops_csv(backlog)
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-backlog-ado-{project.id[:8]}.csv"'
            )
        },
    )


@router.post("/{project_id}/jira-push")
async def push_to_jira(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.jira_backlog is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Generate the backlog before pushing to Jira.",
        )
    result = await export_backlog_to_jira(project.jira_backlog)
    if result.get("ok") or any(
        i.jira_key for i in (project.jira_backlog.subtasks or [])
    ):
        save_project_to_db(db, row, project)
        db.commit()
    return result
