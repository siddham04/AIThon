"""Dev Studio API — API contracts, DB schema suggestions, test generation.

Each feature exposes:
  - POST /<feature>/generate           ad-hoc text → result (no persistence)
  - POST /<feature>/{project_id}/run   uses project's saved requirement, persists
  - GET  /<feature>/{project_id}       most-recent persisted result
  - GET  /<feature>/{project_id}/<simple-export>

Simple exports:
  - /contract/{id}/json     → list of {endpoint, method, request, response}
  - /contract/{id}/openapi  → OpenAPI 3.0.3 JSON
  - /schema/{id}/sql        → SQL DDL (text/plain)
  - /schema/{id}/mermaid    → Mermaid ER (text/plain)
  - /tests/{id}/csv         → categorized test CSV
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import (
    APIContractSuite,
    DatabaseSchema,
    GeneratedTestSuite,
)
from ...services.api_contract_generator import (
    generate_contracts,
    to_openapi,
    to_simple_json as contract_simple,
)
from ...services.db_schema_generator import (
    generate_schema,
    to_simple_json as schema_simple,
)
from ...services.project_bridge import save_project_to_db
from ...services.test_suite_generator import (
    generate_test_suite,
    to_csv as tests_csv,
    to_simple_json as tests_simple,
)
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


class _TextBody(BaseModel):
    requirement: str = Field(..., min_length=1, max_length=8000)
    use_ai: bool = True
    title: Optional[str] = None


def _project_text(project) -> str:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    if not text and project.summary:
        text = (project.summary.objective or project.summary.one_liner or "").strip()
    return text


def _project_title(project) -> str:
    if project.summary and project.summary.title:
        return project.summary.title
    return project.name or ""


# ---------- API Contract ------------------------------------------------ #


@router.post("/contract/generate", response_model=APIContractSuite)
async def generate_contract_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> APIContractSuite:
    return await generate_contracts(
        body.requirement, title=body.title or "", use_ai=body.use_ai
    )


@router.post("/contract/{project_id}/run", response_model=APIContractSuite)
async def run_contract_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> APIContractSuite:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to derive a contract from.",
        )
    suite = await generate_contracts(text, title=_project_title(project), use_ai=use_ai)
    project.api_contract_suite = suite
    save_project_to_db(db, row, project)
    db.commit()
    return suite


@router.get("/contract/{project_id}", response_model=APIContractSuite)
def get_contract_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> APIContractSuite:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.api_contract_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "API contract has not been generated yet.",
        )
    return project.api_contract_suite


@router.get("/contract/{project_id}/json")
def get_contract_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.api_contract_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "API contract has not been generated yet.",
        )
    payload = contract_simple(project.api_contract_suite)
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-contracts-{project.id[:8]}.json"'
            )
        },
    )


@router.get("/contract/{project_id}/openapi")
def get_contract_openapi(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.api_contract_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "API contract has not been generated yet.",
        )
    payload = to_openapi(project.api_contract_suite)
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-openapi-{project.id[:8]}.json"'
            )
        },
    )


# ---------- DB Schema --------------------------------------------------- #


@router.post("/schema/generate", response_model=DatabaseSchema)
async def generate_schema_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> DatabaseSchema:
    return await generate_schema(
        body.requirement, title=body.title or "", use_ai=body.use_ai
    )


@router.post("/schema/{project_id}/run", response_model=DatabaseSchema)
async def run_schema_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatabaseSchema:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to derive a schema from.",
        )
    schema = await generate_schema(
        text, title=_project_title(project), use_ai=use_ai
    )
    project.database_schema = schema
    save_project_to_db(db, row, project)
    db.commit()
    return schema


@router.get("/schema/{project_id}", response_model=DatabaseSchema)
def get_schema_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatabaseSchema:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.database_schema is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Database schema has not been generated yet.",
        )
    return project.database_schema


@router.get("/schema/{project_id}/sql")
def get_schema_sql(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.database_schema is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Database schema has not been generated yet.",
        )
    return Response(
        content=project.database_schema.sql_ddl,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-schema-{project.id[:8]}.sql"'
            )
        },
    )


@router.get("/schema/{project_id}/mermaid")
def get_schema_mermaid(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.database_schema is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Database schema has not been generated yet.",
        )
    return Response(
        content=project.database_schema.mermaid_er,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-er-{project.id[:8]}.mmd"'
            )
        },
    )


# ---------- Test Suite -------------------------------------------------- #


@router.post("/tests/generate", response_model=GeneratedTestSuite)
async def generate_tests_text(
    body: _TextBody,
    _user: User = Depends(get_current_user),
) -> GeneratedTestSuite:
    return await generate_test_suite(
        body.requirement, title=body.title or "", use_ai=body.use_ai
    )


@router.post("/tests/{project_id}/run", response_model=GeneratedTestSuite)
async def run_tests_for_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GeneratedTestSuite:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    text = _project_text(project)
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project has no requirement text to derive tests from.",
        )
    suite = await generate_test_suite(
        text, title=_project_title(project), use_ai=use_ai
    )
    project.generated_test_suite = suite
    save_project_to_db(db, row, project)
    db.commit()
    return suite


@router.get("/tests/{project_id}", response_model=GeneratedTestSuite)
def get_tests_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GeneratedTestSuite:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.generated_test_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Test suite has not been generated yet.",
        )
    return project.generated_test_suite


@router.get("/tests/{project_id}/json")
def get_tests_simple(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.generated_test_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Test suite has not been generated yet.",
        )
    return tests_simple(project.generated_test_suite)


@router.get("/tests/{project_id}/csv")
def get_tests_csv(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.generated_test_suite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Test suite has not been generated yet.",
        )
    return Response(
        content=tests_csv(project.generated_test_suite),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="helix-tests-{project.id[:8]}.csv"'
            )
        },
    )
