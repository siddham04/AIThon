"""Pydantic models for the Helix SDLC Copilot.

Every artifact carries a stable id and links back to its source clause
(`source_clause_ids`) — this is what powers full SDLC traceability.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------- Enums --------------------------------------------------------- #

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    CHORE = "chore"
    SPIKE = "spike"
    INFRA = "infra"


class TestType(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"


class RiskCategory(str, Enum):
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    DEPENDENCY = "dependency"
    DATA = "data"
    UX = "ux"


class AmbiguityKind(str, Enum):
    UNDEFINED_TERM = "undefined_term"
    MISSING_CRITERIA = "missing_criteria"
    CONFLICTING = "conflicting"
    UNQUANTIFIED = "unquantified"
    OUT_OF_SCOPE = "out_of_scope"
    NON_FUNCTIONAL_GAP = "non_functional_gap"


# ---------- Source clauses ------------------------------------------------ #

class SourceClause(BaseModel):
    """An atomic chunk of the original requirement text.

    Every downstream artifact references one or more clause ids so the user
    can trace any task or test back to the exact line of intent.
    """
    id: str = Field(default_factory=lambda: f"clause_{uuid4().hex[:8]}")
    index: int
    text: str


# ---------- Core artifacts ------------------------------------------------ #

class UserStory(BaseModel):
    id: str = Field(default_factory=lambda: f"story_{uuid4().hex[:8]}")
    title: str
    persona: str = Field(description="Who this is for, e.g. 'Returning customer'")
    goal: str = Field(description="What they want to accomplish")
    benefit: str = Field(description="Why it matters")
    acceptance_criteria: List[str] = Field(default_factory=list)
    source_clause_ids: List[str] = Field(default_factory=list)
    approved_for_export: bool = Field(
        default=False,
        description="Human gate: when true, story may be included in approved-only exports.",
    )


class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    title: str
    description: str
    type: TaskType = TaskType.FEATURE
    priority: Severity = Severity.MEDIUM
    story_id: Optional[str] = None
    estimate_hours: Optional[float] = None
    estimate_points: Optional[int] = None
    confidence: Optional[float] = Field(default=None, description="0.0–1.0")
    skills: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    source_clause_ids: List[str] = Field(default_factory=list)
    approved_for_export: bool = Field(
        default=False,
        description="Human gate: when true, task may be included in approved-only exports.",
    )


class TestCase(BaseModel):
    id: str = Field(default_factory=lambda: f"test_{uuid4().hex[:8]}")
    title: str
    type: TestType = TestType.UNIT
    given: str
    when: str
    then: str
    edge_cases: List[str] = Field(default_factory=list)
    story_id: Optional[str] = None
    task_id: Optional[str] = None
    source_clause_ids: List[str] = Field(default_factory=list)
    status: str = Field(default="pending", description="e.g. pending, passed, failed, blocked")


class AmbiguityIssue(BaseModel):
    id: str = Field(default_factory=lambda: f"amb_{uuid4().hex[:8]}")
    kind: AmbiguityKind
    severity: Severity
    excerpt: str = Field(description="Quoted text from the requirement")
    explanation: str
    suggested_question: str = Field(description="Clarifying question to ask the PM")
    suggested_resolution: Optional[str] = None
    source_clause_ids: List[str] = Field(default_factory=list)
    resolved: bool = False


class Risk(BaseModel):
    id: str = Field(default_factory=lambda: f"risk_{uuid4().hex[:8]}")
    category: RiskCategory
    severity: Severity
    title: str
    description: str
    mitigation: str
    source_clause_ids: List[str] = Field(default_factory=list)


# ---------- Top-level container ------------------------------------------ #

class RequirementSummary(BaseModel):
    title: str
    one_liner: str
    objective: str
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    primary_personas: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class ProductivityMetrics(BaseModel):
    """Estimated time/cost saved by Helix vs manual SDLC effort."""
    manual_minutes: int
    helix_minutes: int
    minutes_saved: int
    hours_saved: float
    cost_saved_usd: float
    artifacts_generated: int
    coverage_score: float = Field(description="0.0–1.0 estimated requirement coverage")
    citation_item_rate: float = Field(
        default=0.0,
        description="Share of stories+tasks+tests that cite at least one source clause (0–1).",
    )


class Project(BaseModel):
    id: str = Field(default_factory=lambda: f"proj_{uuid4().hex[:8]}")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_input: str
    source_clauses: List[SourceClause] = Field(default_factory=list)
    summary: Optional[RequirementSummary] = None
    stories: List[UserStory] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    ambiguities: List[AmbiguityIssue] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    metrics: Optional[ProductivityMetrics] = None
    chat_history: List["ChatMessage"] = Field(default_factory=list)
    last_pipeline_timings_ms: Optional[dict[str, int]] = Field(
        default=None,
        description="Wall time per pipeline stage from the last analyze run (stage label → ms).",
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: List[str] = Field(default_factory=list, description="Artifact ids referenced")


# ---------- Request / response DTOs --------------------------------------- #

class IngestRequest(BaseModel):
    name: Optional[str] = None
    text: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: ChatMessage


class AnalyzeProgress(BaseModel):
    stage: str
    status: Literal["pending", "running", "done", "error"]
    detail: Optional[str] = None
    elapsed_ms: Optional[int] = Field(
        default=None,
        description="Wall time for this stage when status is done or error.",
    )


class AppendNotesRequest(BaseModel):
    text: str


class ProjectPatch(BaseModel):
    """Partial update — only fields explicitly sent are replaced."""

    name: Optional[str] = None
    summary: Optional[RequirementSummary] = None
    stories: Optional[List[UserStory]] = None
    tasks: Optional[List[Task]] = None
    test_cases: Optional[List[TestCase]] = None
    ambiguities: Optional[List[AmbiguityIssue]] = None
    risks: Optional[List[Risk]] = None


Project.model_rebuild()
