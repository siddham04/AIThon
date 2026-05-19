from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    tc_type: str = Field(serialization_alias="type")
    given: str
    when: str
    then: str
    status: str
    extra: dict[str, Any] = Field(default_factory=dict)


class TestCaseStatusPatch(BaseModel):
    status: str = Field(min_length=1, max_length=64)
