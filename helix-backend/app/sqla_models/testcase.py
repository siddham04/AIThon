from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .project import ProjectRecord


class TestCaseRecord(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    tc_type: Mapped[str] = mapped_column(String(64), default="unit")
    given: Mapped[str] = mapped_column(Text)
    when: Mapped[str] = mapped_column(Text)
    then: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")

    project: Mapped["ProjectRecord"] = relationship(
        "ProjectRecord", back_populates="test_cases"
    )
