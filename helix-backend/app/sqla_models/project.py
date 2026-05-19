from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .artifact import Artifact
    from .requirement import Requirement
    from .testcase import TestCaseRecord
    from .user import User


class ProjectRecord(Base):
    """Persisted project shell + serialized Helix pipeline graph."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    pipeline_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    requirements: Mapped[list["Requirement"]] = relationship(
        "Requirement", back_populates="project", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact", back_populates="project", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCaseRecord"]] = relationship(
        "TestCaseRecord", back_populates="project", cascade="all, delete-orphan"
    )
