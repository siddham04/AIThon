from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...services.requirement_snapshot_service import append_snapshot, list_snapshots
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row

router = APIRouter()


class SnapshotCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500_000)


class SnapshotItem(BaseModel):
    id: str
    text: str
    created_at: str


@router.get("/{project_id}/requirement-versions", response_model=list[SnapshotItem])
async def get_versions(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SnapshotItem]:
    get_owned_project_row(db, user, project_id)
    if not get_settings_mongo_url():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "MongoDB not configured (MONGO_URL). Version history requires MongoDB.",
        )
    rows = await list_snapshots(project_id)
    return [SnapshotItem(**r) for r in rows]


def get_settings_mongo_url() -> str:
    from ...config import get_settings

    return (get_settings().mongo_url or "").strip()


@router.post("/{project_id}/requirement-versions", response_model=SnapshotItem)
async def post_version(
    project_id: str,
    payload: SnapshotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SnapshotItem:
    get_owned_project_row(db, user, project_id)
    if not get_settings_mongo_url():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "MongoDB not configured (MONGO_URL).",
        )
    doc = await append_snapshot(project_id, payload.text)
    if doc is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not save snapshot")
    ts = doc.get("created_at")
    return SnapshotItem(
        id=str(doc.get("_id", "")),
        text=payload.text,
        created_at=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
    )
