from __future__ import annotations

import json
from typing import Iterable
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import Project, SourceClause
from ..sqla_models import Artifact, ProjectRecord, Requirement, TestCaseRecord


def pydantic_from_db_row(row: ProjectRecord | None) -> Project | None:
    if row is None or not row.pipeline_json:
        return None
    return Project.model_validate_json(row.pipeline_json)


def save_project_to_db(db: Session, row: ProjectRecord, project: Project) -> None:
    row.name = project.name
    row.pipeline_json = project.model_dump_json()
    db.add(row)
    db.flush()


def sync_requirements_from_clauses(
    db: Session, row: ProjectRecord, clauses: Iterable[SourceClause]
) -> None:
    db.execute(delete(Requirement).where(Requirement.project_id == row.id))
    for c in clauses:
        db.add(
            Requirement(
                project_id=row.id,
                clause_id=c.id,
                body=c.text,
                sort_order=c.index,
            )
        )


def sync_artifacts_from_project(db: Session, row: ProjectRecord, project: Project) -> None:
    db.execute(delete(Artifact).where(Artifact.project_id == row.id))
    for s in project.stories:
        db.add(
            Artifact(
                id=s.id,
                project_id=row.id,
                kind="story",
                payload_json=json.dumps(s.model_dump(mode="json"), default=str),
            )
        )
    for t in project.tasks:
        db.add(
            Artifact(
                id=t.id,
                project_id=row.id,
                kind="task",
                payload_json=json.dumps(t.model_dump(mode="json"), default=str),
            )
        )


def sync_testcases_from_project(db: Session, row: ProjectRecord, project: Project) -> None:
    db.execute(delete(TestCaseRecord).where(TestCaseRecord.project_id == row.id))
    for tc in project.test_cases:
        extra = {
            "edge_cases": tc.edge_cases,
            "story_id": tc.story_id,
            "task_id": tc.task_id,
            "source_clause_ids": tc.source_clause_ids,
        }
        db.add(
            TestCaseRecord(
                id=tc.id,
                project_id=row.id,
                title=tc.title,
                tc_type=tc.type.value if hasattr(tc.type, "value") else str(tc.type),
                given=tc.given,
                when=tc.when,
                then=tc.then,
                status=tc.status,
                extra_json=json.dumps(extra, default=str),
            )
        )


def ensure_project_row(
    db: Session, project: Project, owner_id: int
) -> ProjectRecord:
    row = db.get(ProjectRecord, project.id)
    if row is None:
        row = ProjectRecord(id=project.id, name=project.name, owner_id=owner_id)
        db.add(row)
        db.flush()
    save_project_to_db(db, row, project)
    sync_requirements_from_clauses(db, row, project.source_clauses)
    sync_artifacts_from_project(db, row, project)
    sync_testcases_from_project(db, row, project)
    return row


def new_project_id() -> str:
    return f"proj_{uuid4().hex[:10]}"
