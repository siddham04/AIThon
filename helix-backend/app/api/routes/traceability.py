"""Traceability Matrix API.

POST /api/traceability/{project_id}/run    → build + persist + return
GET  /api/traceability/{project_id}        → cached
GET  /api/traceability/{project_id}/csv    → flat CSV download
GET  /api/traceability/{project_id}/tree   → ASCII REQ → US → TASK → TC trees
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import TraceabilityGraph, TraceabilityMatrix
from ...services.project_bridge import save_project_to_db
from ...services.traceability_matrix import (
    build_demo_traceability_graph,
    build_traceability,
    build_traceability_graph,
    to_csv,
)
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()


@router.post("/{project_id}/run", response_model=TraceabilityMatrix)
def run_traceability(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TraceabilityMatrix:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    matrix = build_traceability(project)
    project.traceability_matrix = matrix
    save_project_to_db(db, row, project)
    db.commit()
    return matrix


@router.get("/{project_id}", response_model=TraceabilityMatrix)
def get_traceability(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TraceabilityMatrix:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    if project.traceability_matrix is None:
        # Build on-demand so this endpoint is always useful.
        return build_traceability(project)
    return project.traceability_matrix


@router.get("/{project_id}/csv")
def download_csv(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    matrix = project.traceability_matrix or build_traceability(project)
    if not matrix.rows:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No traceability rows could be assembled for this project.",
        )
    csv_text = to_csv(matrix)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="traceability-{project_id}.csv"',
        },
    )


@router.get("/graph/demo", response_model=TraceabilityGraph)
def get_demo_graph() -> TraceabilityGraph:
    """Demo graph for Screen 7 — REQ → US → TASK → TC."""
    return build_demo_traceability_graph()


@router.get("/{project_id}/graph", response_model=TraceabilityGraph)
def get_traceability_graph(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TraceabilityGraph:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    matrix = project.traceability_matrix
    if matrix is None:
        matrix = build_traceability(project)
    if matrix.graph and matrix.graph.nodes:
        return matrix.graph
    graph = build_traceability_graph(matrix)
    matrix.graph = graph
    project.traceability_matrix = matrix
    save_project_to_db(db, row, project)
    db.commit()
    return graph


@router.get("/{project_id}/tree")
def download_tree(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    matrix = project.traceability_matrix or build_traceability(project)
    body = matrix.tree_text or "No traceability tree available."
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="traceability-tree-{project_id}.txt"',
        },
    )


__all__ = ["router"]
