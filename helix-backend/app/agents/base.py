"""Shared agent helpers.

Each agent is a small, focused class:
  - declares its name & stage label
  - exposes `run(project) -> patch`
  - returns the slice of artifacts it produced (no side-effects)
The orchestrator merges patches into the Project.
"""
from __future__ import annotations

from typing import Any, Dict

from ..models import Project
from ..services.llm import get_llm


class Agent:
    name: str = "agent"
    stage: str = "Stage"

    def __init__(self) -> None:
        self.llm = get_llm()

    async def run(self, project: Project) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError
