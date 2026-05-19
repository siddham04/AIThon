"""Conversational refinement agent.

Has full context of every artifact in the project and answers grounded
questions, citing artifact ids so the UI can deep-link.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..models import ChatMessage, Project
from ..services.ai_service import get_ai_service
from .base import Agent


SYSTEM = """You are Helix, an SDLC copilot embedded in a workspace.
You have full context of the requirement: the brief, the user stories,
the engineering tasks, the test plan, ambiguities, and risks.

Answer the user's question concisely and accurately.
- Always ground your answer in the provided artifacts.
- When you reference a story, task, test, or risk, mention its id (e.g.
  "task_a1b2c3d4") so the UI can deep-link.
- If something is not in the workspace, say so plainly.
- Prefer short answers with bullet points over long prose.
""".strip()


def _project_context(project: Project) -> str:
    payload: Dict[str, Any] = {
        "summary": project.summary.model_dump() if project.summary else None,
        "stories": [s.model_dump() for s in project.stories],
        "tasks": [t.model_dump(mode="json") for t in project.tasks],
        "test_cases": [t.model_dump(mode="json") for t in project.test_cases],
        "ambiguities": [a.model_dump(mode="json") for a in project.ambiguities],
        "risks": [r.model_dump(mode="json") for r in project.risks],
        "metrics": project.metrics.model_dump() if project.metrics else None,
    }
    return json.dumps(payload, default=str)[:18000]


class ChatAgent(Agent):
    name = "chat"
    stage = "Chat"

    async def reply(self, project: Project, user_message: str) -> ChatMessage:
        ai = get_ai_service()
        if ai.enabled:
            system = ai.chat_system_with_context(_project_context(project))
            messages: List[Dict[str, str]] = [
                {"role": m.role, "content": m.content} for m in project.chat_history[:-1]
            ]
            messages.append({"role": "user", "content": user_message})
            parts: List[str] = []
            async for chunk in ai.stream_chat(system=system, messages=messages):
                parts.append(chunk)
            text = "".join(parts)
        else:
            history: List[Dict[str, str]] = []
            for m in project.chat_history[-8:]:
                history.append({"role": m.role, "content": m.content})

            context_block = (
                "Workspace artifacts (JSON):\n"
                f"{_project_context(project)}\n\n"
                "Now answer the user."
            )
            history = [{"role": "system", "content": context_block}, *history]

            text = await self.llm.chat_text_with_fallback(
                project, SYSTEM, user_message, history=history
            )
        citations = list(
            set(re.findall(r"(?:story|task|test|amb|risk|clause)_[a-z0-9]{4,}", text))
        )
        return ChatMessage(role="assistant", content=text, citations=citations)
