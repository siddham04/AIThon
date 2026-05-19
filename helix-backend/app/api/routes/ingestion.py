from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Project
from ...schemas.ingest import IngestTextBody, IngestUrlBody
from ...services.ingestion import split_into_clauses
from ...services.ingestion_service import IngestSource, extract_clean_chunk_and_store, extract_text, extract_text_from_url
from ...services.project_bridge import ensure_project_row, new_project_id
from ...services.rag_service import embed_requirements
from ...services.sensitive_scan import scan_sensitive_hints
from ...services.store import get_store
from ...sqla_models import ProjectRecord, User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


async def _apply_text_to_project(
    db: Session,
    user: User,
    project_id: str | None,
    name: str | None,
    text: str,
) -> str:
    text = text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty text")
    clauses = split_into_clauses(text)
    if project_id:
        row = get_owned_project_row(db, user, project_id)
        proj = load_project_graph(db, row)
        proj.raw_input = text
        proj.source_clauses = clauses
        if name:
            proj.name = name
            row.name = name
        ensure_project_row(db, proj, user.id)
        db.commit()
        embed_requirements(row.id, [c.text for c in proj.source_clauses])
        if await get_store().get(project_id):
            await get_store().update(proj)
        else:
            await get_store().create(proj)
        return row.id
    pid = new_project_id()
    proj = Project(
        id=pid,
        name=name or "Ingested document",
        raw_input=text,
        source_clauses=clauses,
    )
    row = ProjectRecord(id=pid, name=proj.name, owner_id=user.id)
    db.add(row)
    db.flush()
    ensure_project_row(db, proj, user.id)
    db.commit()
    embed_requirements(pid, [c.text for c in proj.source_clauses])
    await get_store().create(proj)
    return pid


@router.post("/text")
async def ingest_text(
    body: IngestTextBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    pid = await _apply_text_to_project(
        db, user, body.project_id, body.name, body.text
    )
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="text", text=body.text), pid
    )
    return {
        "project_id": pid,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(body.text),
    }


@router.post("/file")
async def ingest_file(
    file: UploadFile = File(...),
    project_id: str | None = Form(None),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    fname = file.filename or "upload.bin"
    extracted = await extract_text(
        IngestSource(kind="bytes", filename=fname, data=data)
    )
    pid = await _apply_text_to_project(db, user, project_id, name, extracted)
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="bytes", filename=fname, data=data), pid
    )
    return {
        "project_id": pid,
        "filename": fname,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(extracted),
    }


@router.post("/url")
async def ingest_url(
    body: IngestUrlBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    url = str(body.url)
    text = await extract_text_from_url(url)
    pid = await _apply_text_to_project(db, user, body.project_id, body.name, text)
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="url", url=url), pid
    )
    return {
        "project_id": pid,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(text),
    }
