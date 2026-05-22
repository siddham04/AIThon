from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import get_db
from ...services.export_filter import slice_for_export
from ...services.github_service import export_project_to_github_issues
from ...services.jira_service import export_project_to_jira
from ...sqla_models import User
from ..deps import get_current_user
from ..exporters import export_csv, export_jira_csv, export_markdown
from ..route_helpers import get_owned_project_row, load_project_graph

logger = logging.getLogger("helix.export")

router = APIRouter()


@router.post("/jira/{project_id}")
async def export_jira(
    project_id: str,
    approved_only: bool = Query(
        False,
        description="If true, only stories/tasks marked approved_for_export are sent.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    project = slice_for_export(project, approved_only=approved_only)
    settings = get_settings()
    # Prefer JIRA REST when JIRA_TOKEN + base URL + project are set
    if (settings.jira_token or "").strip() and (settings.jira_base_url or "").strip() and (settings.jira_project_key or "").strip():
        rest = await export_project_to_jira(project)
        return {
            "mode": "rest",
            "delivered": bool(rest.get("ok")),
            "created_keys": rest.get("created_keys") or [],
            "epic_key": rest.get("epic_key"),
            "errors": rest.get("errors") or [],
            "detail": rest.get("detail"),
        }
    body = export_jira_csv(project)
    raw = body.encode("utf-8")
    url = settings.jira_webhook_url.strip()
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
            logger.warning("Jira export POST failed: %s", exc)
            delivered = False
    return {
        "mode": "webhook",
        "delivered": delivered,
        "target": url or None,
        "csv_bytes": len(raw),
        "http_status": status_code,
    }


@router.post("/github/{project_id}")
async def export_github(
    project_id: str,
    approved_only: bool = Query(
        False,
        description="If true, only stories/tasks marked approved_for_export are sent.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    st = get_settings()
    if not (st.github_token or "").strip() or not (st.github_repo or "").strip():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "GITHUB_TOKEN and GITHUB_REPO (owner/name) must be set for GitHub export.",
        )
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    project = slice_for_export(project, approved_only=approved_only)
    result = await export_project_to_github_issues(project)
    return {
        "ok": bool(result.get("ok")),
        "issue_urls": result.get("issue_urls") or [],
        "errors": result.get("errors") or [],
        "detail": result.get("detail"),
    }


@router.get("/csv/{project_id}")
def export_project_csv(
    project_id: str,
    approved_only: bool = Query(
        False,
        description="If true, only stories/tasks marked approved_for_export are exported.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    project = slice_for_export(project, approved_only=approved_only)
    csv_body = export_csv(project)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="helix-export.csv"'},
    )


@router.get("/markdown/{project_id}")
def export_project_markdown(
    project_id: str,
    approved_only: bool = Query(
        False,
        description="If true, only stories/tasks marked approved_for_export are exported.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    project = slice_for_export(project, approved_only=approved_only)
    settings = get_settings()
    model_label = (settings.helix_export_model_label or "").strip() or (
        settings.azure_openai_deployment or "Helix"
    )
    if settings.helix_production:
        user_label = f"user-{user.id}"
    else:
        user_label = (user.email or "").strip() or f"user-{user.id}"
    body = export_markdown(project, audit=(user_label, model_label))
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="helix-export.md"'},
    )


@router.get("/json/{project_id}")
def export_project_json(
    project_id: str,
    approved_only: bool = Query(
        False,
        description="If true, only stories/tasks marked approved_for_export are exported.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    project = slice_for_export(project, approved_only=approved_only)
    payload = project.model_dump(mode="json")
    return Response(
        content=json.dumps(payload, default=str, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="helix-export.json"'},
    )
