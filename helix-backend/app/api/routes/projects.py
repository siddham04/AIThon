from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Project
from ...schemas.project import ProjectCreate, ProjectResponse
from ...services.project_bridge import ensure_project_row, new_project_id
from ...services.rag_service import embed_requirements, search
from ...services.sensitive_scan import enforce_no_secrets_in_prompt, scan_sensitive_hints
from ...services.store import get_store
from ...sqla_models import ProjectRecord, User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    rows = db.scalars(select(ProjectRecord).where(ProjectRecord.owner_id == user.id)).all()
    return [
        ProjectResponse(
            id=r.id,
            name=r.name,
            owner_id=r.owner_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    pid = new_project_id()
    raw = (payload.raw_text or "").strip()
    if raw:
        enforce_no_secrets_in_prompt(raw)
    proj = Project(id=pid, name=payload.name, raw_input=raw, source_clauses=[])
    if raw:
        from ...services.ingestion import split_into_clauses

        proj.source_clauses = split_into_clauses(raw)
    row = ProjectRecord(id=pid, name=payload.name, owner_id=user.id, pipeline_json=None)
    db.add(row)
    db.flush()
    ensure_project_row(db, proj, user.id)
    db.commit()
    db.refresh(row)
    await get_store().create(proj)
    embed_requirements(pid, [c.text for c in proj.source_clauses])
    hints = scan_sensitive_hints(raw)
    return ProjectResponse(
        id=row.id,
        name=row.name,
        owner_id=row.owner_id,
        created_at=row.created_at,
        sensitive_hints=hints,
    )


@router.get("/{project_id}/rag/search")
def rag_search_project(
    project_id: str,
    q: str = Query(..., min_length=1, description="Natural language query"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_owned_project_row(db, user, project_id)
    return {"query": q, "chunks": search(q, project_id)}


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.get(ProjectRecord, project_id)
    if row is None or row.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    graph = load_project_graph(db, row)
    raw = (graph.raw_input or "").strip()
    hints = scan_sensitive_hints(raw) if raw else []
    return ProjectResponse(
        id=row.id,
        name=row.name,
        owner_id=row.owner_id,
        created_at=row.created_at,
        sensitive_hints=hints,
    )
