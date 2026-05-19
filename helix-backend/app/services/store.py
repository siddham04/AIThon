"""Process-local project store.

Trivially swappable for Postgres/Redis later — all access goes through
this interface. Thread/async-safe enough for the prototype scale.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from ..models import Project


class ProjectStore:
    def __init__(self) -> None:
        self._projects: Dict[str, Project] = {}
        self._lock = asyncio.Lock()

    async def create(self, project: Project) -> Project:
        async with self._lock:
            self._projects[project.id] = project
            return project

    async def get(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    async def update(self, project: Project) -> Project:
        async with self._lock:
            self._projects[project.id] = project
            return project

    async def list(self) -> List[Project]:
        return list(self._projects.values())

    async def delete(self, project_id: str) -> bool:
        async with self._lock:
            return self._projects.pop(project_id, None) is not None


_store: Optional[ProjectStore] = None


def get_store() -> ProjectStore:
    global _store
    if _store is None:
        _store = ProjectStore()
    return _store
