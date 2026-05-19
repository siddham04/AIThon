from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Project, Severity
from ..services.project_bridge import pydantic_from_db_row
from ..sqla_models import ProjectRecord, User


def get_owned_project_row(db: Session, user: User, project_id: str) -> ProjectRecord:
    row = db.get(ProjectRecord, project_id)
    if row is None or row.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return row


def load_project_graph(db: Session, row: ProjectRecord) -> Project:
    p = pydantic_from_db_row(row)
    if p is None:
        return Project(id=row.id, name=row.name, raw_input="", source_clauses=[])
    return p


def severity_to_score(sev: Severity | str) -> float:
    if isinstance(sev, Severity):
        key = sev.value
    else:
        key = str(sev).lower()
    return {
        "critical": 1.0,
        "high": 0.85,
        "medium": 0.6,
        "low": 0.35,
    }.get(key, 0.5)
