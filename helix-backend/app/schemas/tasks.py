from __future__ import annotations

from pydantic import BaseModel


class CeleryTaskAccepted(BaseModel):
    task_id: str
    mode: str = "async"
