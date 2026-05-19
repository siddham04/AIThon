from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...agents.ambiguity import AmbiguityAgent
from ...database import get_db
from ...schemas.ambiguity import AmbiguityHit
from ...services.ingestion import render_clauses
from ...services.nlp_service import detect_ambiguities
from ...services.project_bridge import ensure_project_row
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph, severity_to_score

router = APIRouter()


@router.post("/analyze/{project_id}", response_model=list[AmbiguityHit])
async def analyze_ambiguity(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AmbiguityHit]:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    agent = AmbiguityAgent()
    patch = await agent.run(project)
    for k, v in patch.items():
        setattr(project, k, v)
    ensure_project_row(db, project, user.id)
    db.commit()
    hits: list[AmbiguityHit] = []
    for issue in project.ambiguities:
        hits.append(
            AmbiguityHit(
                span=issue.excerpt,
                score=severity_to_score(issue.severity),
                suggestion=issue.suggested_question,
            )
        )
    blob = (project.raw_input or "").strip()
    if not blob:
        blob = render_clauses(project.source_clauses)
    seen: set[str] = {h.span for h in hits}
    for h in detect_ambiguities(blob):
        span = str(h.get("span", ""))[:500]
        if not span or span in seen:
            continue
        seen.add(span)
        detail = str(h.get("detail", "Ambiguity cue"))
        hits.append(
            AmbiguityHit(
                span=span,
                score=0.45,
                suggestion=detail,
            )
        )
    return hits
