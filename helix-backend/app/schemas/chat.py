from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequestBody(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatHistoryTurn] = Field(default_factory=list)
