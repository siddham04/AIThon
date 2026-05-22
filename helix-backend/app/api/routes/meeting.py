"""Meeting-to-Requirement API.

POST /api/meeting/extract                    → {transcript, source_type?, use_ai?}
POST /api/meeting/{project_id}/extract       → persist on project + extract
GET  /api/meeting/{project_id}               → cached extraction
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import MeetingExtraction
from ...services.meeting_extractor import extract_meeting
from ...services.project_bridge import save_project_to_db
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class _MeetingBody(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=60000)
    source_type: Literal["transcript", "notes", "mixed"] = "transcript"
    use_ai: bool = True


@router.post("/extract", response_model=MeetingExtraction)
async def extract_text(
    body: _MeetingBody,
    _user: User = Depends(get_current_user),
) -> MeetingExtraction:
    return await extract_meeting(
        body.transcript,
        source_type=body.source_type,
        use_ai=body.use_ai,
    )


@router.post("/{project_id}/extract", response_model=MeetingExtraction)
async def extract_for_project(
    project_id: str,
    body: _MeetingBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeetingExtraction:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    extraction = await extract_meeting(
        body.transcript,
        source_type=body.source_type,
        use_ai=body.use_ai,
    )
    project.meeting_extraction = extraction
    save_project_to_db(db, row, project)
    db.commit()
    return extraction


@router.get("/{project_id}", response_model=MeetingExtraction)
def get_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeetingExtraction:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.meeting_extraction is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No meeting extraction has been recorded for this project.",
        )
    return project.meeting_extraction


__all__ = ["router"]
