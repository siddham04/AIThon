from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Project
from ...schemas.ingest import IngestTextBody, IngestUrlBody
from ...services.ingestion import (
    split_into_clauses,
    _strip_team_config_preamble,
    _looks_like_header,
    _looks_like_noise,
)
from ...services.ingestion_service import IngestSource, extract_clean_chunk_and_store, extract_text, extract_text_from_url
from ...services.project_bridge import ensure_project_row, new_project_id, save_project_to_db
from ...services.quality_scorer import score_requirement_text
from ...services.rag_service import embed_requirements
from ...config import get_settings
from ...services.sensitive_scan import enforce_no_secrets_in_prompt, scan_sensitive_hints
from ...services.url_safety import validate_public_http_url
from ...services.store import get_store
from ...sqla_models import ProjectRecord, User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


def _quality_summary(report) -> dict:
    """Compact shape returned right after ingestion."""
    return {
        "clarity": report.clarity,
        "completeness": report.completeness,
        "testability": report.testability,
        "ambiguity": report.ambiguity,
        "overall_score": report.overall_score,
        "grade": report.grade,
        "highlight_gaps": list(report.highlight_gaps or []),
        "vague_phrase_count": len(report.vague_phrases or []),
    }


def _derive_project_name(text: str, fallback: str = "Ingested document") -> str:
    """Best-effort project name from the first substantive line.

    Mission Control sometimes posts the PRD without a name (the form
    field is optional). The old behaviour was to default to the literal
    string ``"Ingested document"``, which then bubbled up to the Jira
    epic title — embarrassing on demo day. We now lift the first non-
    trivial line (≤ 14 words after trimming) as the title, and only
    fall back to the generic default if no candidate is found.

    Defensive: also strips the Mission Control team-config preamble
    in case the caller forgot to do it (the ``/ingest/text`` route
    does, but stand-alone scripts / future callers may not).

    Uses the same header / noise classifiers as the clause splitter so
    a section header like ``"Our Solution and Approach"`` can never be
    promoted to a project title.
    """
    if not text:
        return fallback
    text, _ = _strip_team_config_preamble(text)
    for raw in text.splitlines():
        line = raw.strip().rstrip(":.")
        if not line:
            continue
        if line.startswith("[Helix team configuration]"):
            continue
        if _looks_like_noise(line) or _looks_like_header(line):
            continue
        if len(line) < 6:
            continue
        # Accept long lines but clip to a readable title length —
        # the previous "reject >120 chars" rule meant the PRD's own
        # marketing title (often the best candidate) was silently
        # passed over in favour of the next section header.
        words = line.split()
        if len(words) > 14:
            line = " ".join(words[:14]).rstrip(",;:") + "…"
        elif len(line) > 140:
            line = line[:137].rstrip() + "…"
        return line
    return fallback


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
    enforce_no_secrets_in_prompt(text)
    # Strip the Mission Control team-config preamble *before* deriving
    # the project name OR persisting raw_input. Otherwise the team-
    # config block ends up in:
    #   - the project title  ("[Helix team configuration]")
    #   - the Jira epic description (entire 5-line block prepended)
    #   - any LLM prompt that interpolates raw_input.
    # The team-config values are not lost; the planners take team_size
    # and sprint_weeks as explicit parameters, not from raw_input.
    text_clean, _ = _strip_team_config_preamble(text)
    text_clean = text_clean.strip() or text
    clauses = split_into_clauses(text_clean)
    if project_id:
        row = get_owned_project_row(db, user, project_id)
        proj = load_project_graph(db, row)
        proj.raw_input = text_clean
        proj.source_clauses = clauses
        if name:
            proj.name = name
            row.name = name
        quality = await score_requirement_text(text, use_ai=False)
        proj.quality_score_report = quality
        ensure_project_row(db, proj, user.id)
        save_project_to_db(db, row, proj)
        db.commit()
        embed_requirements(row.id, [c.text for c in proj.source_clauses])
        if await get_store().get(project_id):
            await get_store().update(proj)
        else:
            await get_store().create(proj)
        return row.id, quality
    pid = new_project_id()
    derived = (name or "").strip() or _derive_project_name(text_clean)
    proj = Project(
        id=pid,
        name=derived,
        raw_input=text_clean,
        source_clauses=clauses,
    )
    row = ProjectRecord(id=pid, name=proj.name, owner_id=user.id)
    db.add(row)
    db.flush()
    quality = await score_requirement_text(text, use_ai=False)
    proj.quality_score_report = quality
    ensure_project_row(db, proj, user.id)
    save_project_to_db(db, row, proj)
    db.commit()
    embed_requirements(pid, [c.text for c in proj.source_clauses])
    await get_store().create(proj)
    return pid, quality


@router.post("/text")
async def ingest_text(
    body: IngestTextBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    pid, quality = await _apply_text_to_project(
        db, user, body.project_id, body.name, body.text
    )
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="text", text=body.text), pid
    )
    return {
        "project_id": pid,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(body.text),
        "quality": _quality_summary(quality),
    }


@router.post("/file")
async def ingest_file(
    file: UploadFile = File(...),
    project_id: str | None = Form(None),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    data = await file.read()
    if len(data) > settings.helix_max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.helix_max_upload_bytes // (1024 * 1024)} MB limit",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    fname = file.filename or "upload.bin"
    extracted = await extract_text(
        IngestSource(kind="bytes", filename=fname, data=data)
    )
    pid, quality = await _apply_text_to_project(db, user, project_id, name, extracted)
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="bytes", filename=fname, data=data), pid
    )
    return {
        "project_id": pid,
        "filename": fname,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(extracted),
        "quality": _quality_summary(quality),
    }


@router.post("/url")
async def ingest_url(
    body: IngestUrlBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        url = validate_public_http_url(str(body.url))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    text = await extract_text_from_url(url)
    enforce_no_secrets_in_prompt(text)
    pid, quality = await _apply_text_to_project(db, user, body.project_id, body.name, text)
    _, _, n = await extract_clean_chunk_and_store(
        IngestSource(kind="url", url=url), pid
    )
    return {
        "project_id": pid,
        "mongo_chunks": n,
        "sensitive_hints": scan_sensitive_hints(text),
        "quality": _quality_summary(quality),
    }
