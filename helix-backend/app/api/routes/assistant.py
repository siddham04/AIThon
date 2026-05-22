"""Conversational SDLC Assistant API.

POST /api/assistant/{project_id}/ask     → AssistantTurn
GET  /api/assistant/{project_id}/suggested → quick prompt suggestions
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import AssistantTurn
from ...services.sdlc_assistant import (
    _default_followups,
    _detect_intents,
    ask_assistant,
    demo_assistant_turn,
)
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph


router = APIRouter()

_DEMO_SUGGESTIONS = [
    "Which requirements are incomplete?",
    "What APIs need changes?",
    "Which requirements are ambiguous?",
    "Show all security risks.",
    "Which stories don't have tests?",
]


class _AskBody(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    use_ai: bool = True


@router.post("/demo/ask", response_model=AssistantTurn)
async def ask_demo(
    body: _AskBody,
    _user: User = Depends(get_current_user),
) -> AssistantTurn:
    """Instant demo replies — authenticated (no open LLM proxy)."""
    return demo_assistant_turn(body.question)


@router.get("/demo/suggested")
def demo_suggested() -> dict:
    return {
        "suggestions": _DEMO_SUGGESTIONS,
        "intents": _detect_intents(""),
        "followups": _default_followups(["incomplete", "general"]),
    }


@router.post("/{project_id}/ask", response_model=AssistantTurn)
async def ask(
    project_id: str,
    body: _AskBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssistantTurn:
    row = get_owned_project_row(db, user, project_id)
    project = load_project_graph(db, row)
    return await ask_assistant(project, body.question, use_ai=body.use_ai)


@router.get("/{project_id}/suggested")
def suggested_prompts(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = get_owned_project_row(db, user, project_id)
    load_project_graph(db, row)
    suggestions = list(_DEMO_SUGGESTIONS) + [
        "What's the single biggest blocker to release?",
        "Summarise the architecture in one paragraph.",
    ]
    return {
        "suggestions": suggestions,
        "intents": _detect_intents(""),
        "followups": _default_followups(["general"]),
    }


__all__ = ["router"]
