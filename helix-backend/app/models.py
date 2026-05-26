"""Pydantic models for the Helix SDLC Copilot.

Every artifact carries a stable id and links back to its source clause
(`source_clause_ids`) — this is what powers full SDLC traceability.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
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


# ---------- Control Tower briefs (Requirement Analyst, Solution Architect,
#            Sprint Planning) ------------------------------------------------ #


class RequirementEntity(BaseModel):
    name: str
    kind: str = Field(
        default="concept",
        description="actor | concept | system | external | data",
    )
    description: str = ""


class GlossaryTerm(BaseModel):
    term: str
    meaning: str


class ExtractedFeature(BaseModel):
    """Capability the requirement is asking for."""
    name: str
    description: str = ""
    priority: str = "medium"  # low | medium | high | critical


class ActorProfile(BaseModel):
    """Persona / role with goals — Requirement Analyst output."""
    name: str
    role: str = ""
    responsibilities: List[str] = Field(default_factory=list)


class BusinessRule(BaseModel):
    """Policy or validation the system must enforce."""
    description: str
    condition: str = ""
    outcome: str = ""


class RequirementBrief(BaseModel):
    """Output of the Requirement Analyst Agent.

    Extracts features, actors, and business rules from messy input.
    """
    cleaned_summary: str = ""
    features: List[ExtractedFeature] = Field(default_factory=list)
    actors: List[ActorProfile] = Field(default_factory=list)
    business_rules: List[BusinessRule] = Field(default_factory=list)
    entities: List[RequirementEntity] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    key_constraints: List[str] = Field(default_factory=list)
    glossary: List[GlossaryTerm] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class ProposedAPI(BaseModel):
    """API surface proposed by the Architect Agent."""
    method: str = "GET"
    path: str
    description: str = ""
    component: str = ""


class ArchitectureLayer(str, Enum):
    FRONTEND = "frontend"
    SERVICE = "service"
    DATA = "data"
    INFRA = "infra"
    INTEGRATION = "integration"


class ArchitectureComponent(BaseModel):
    name: str
    responsibility: str
    layer: ArchitectureLayer = ArchitectureLayer.SERVICE
    tech: List[str] = Field(default_factory=list)


class ArchitectureDecision(BaseModel):
    decision: str
    rationale: str
    trade_offs: Optional[str] = None


class ArchitectureBrief(BaseModel):
    """Output of the Architect Agent.

    APIs, DB entities, components, integrations, and architecture decisions.
    """
    overview: str = ""
    apis: List[ProposedAPI] = Field(default_factory=list)
    components: List[ArchitectureComponent] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    data_entities: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    suggested_stack: List[str] = Field(default_factory=list)
    decisions: List[ArchitectureDecision] = Field(default_factory=list)
    deployment: str = ""


class SprintItem(BaseModel):
    sprint_number: int
    goal: str = ""
    task_ids: List[str] = Field(default_factory=list)
    total_points: int = 0
    weeks: float = 2.0
    risk_callouts: List[str] = Field(default_factory=list)


class SprintPlan(BaseModel):
    """Output of the Sprint Planning Agent.

    Allocates estimated tasks into N two-week sprints by velocity, dependency
    order, and priority. Enterprise-friendly view of "when does this ship?".
    """
    velocity_points_per_sprint: float = 20.0
    total_sprints: int = 0
    total_points: int = 0
    total_weeks: float = 0.0
    items: List[SprintItem] = Field(default_factory=list)
    rationale: str = ""


# ---------- Multi-Agent Requirement Review Board -------------------------- #


class ReviewStoryItem(BaseModel):
    title: str
    acceptance_criteria: List[str] = Field(default_factory=list)


class APIChange(BaseModel):
    method: str = "GET"
    path: str
    description: str = ""
    is_new: bool = True


class DatabaseChange(BaseModel):
    entity: str
    change: str = "alter"  # "create" | "alter" | "migrate" | "delete"
    description: str = ""


class ArchitectureImpact(BaseModel):
    component: str
    impact: str = ""
    is_new: bool = False


class SecurityConcern(BaseModel):
    title: str
    severity: Severity = Severity.MEDIUM
    description: str = ""
    mitigation: str = ""


class ComplianceConcern(BaseModel):
    title: str
    framework: str = ""  # GDPR / SOC2 / PCI / HIPAA / etc.
    severity: Severity = Severity.MEDIUM
    description: str = ""
    mitigation: str = ""


class PMObservation(BaseModel):
    title: str
    severity: Severity = Severity.MEDIUM
    description: str = ""


class AgentReview(BaseModel):
    """Single agent's review on the Requirement Review Board."""
    agent: str  # "ba" | "architect" | "qa" | "security" | "pm"
    role: str
    score: float = 0.0  # 0..100 — this agent's confidence in the requirement
    summary: str = ""
    findings: dict = Field(default_factory=dict)  # agent-specific structured payload
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class ReviewBoardReport(BaseModel):
    """Aggregate output of the Requirement Review Board.

    Five specialized agents (BA, Architect, QA, Security, PM) review the
    requirement in parallel; the headline `confidence` is a weighted blend
    of their individual scores so the team sees at a glance whether this
    requirement is buildable as-is.
    """
    project_id: str
    confidence: float = 0.0  # 0..100
    grade: str = "D"  # "A" | "B" | "C" | "D"
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    reviews: List[AgentReview] = Field(default_factory=list)


# ---------- Requirement Quality Score ------------------------------------ #


class QualityDimension(str, Enum):
    ROLES = "roles"  # actors / personas
    SUCCESS_CRITERIA = "success_criteria"  # acceptance criteria
    BUSINESS_RULES = "business_rules"
    EDGE_CASES = "edge_cases"
    SCOPE = "scope"
    ERROR_HANDLING = "error_handling"
    NON_FUNCTIONAL = "non_functional"
    DATA = "data"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    DEPENDENCIES = "dependencies"
    DEPLOYMENT = "deployment"
    OTHER = "other"


class MissingInformation(BaseModel):
    """A specific gap the requirement needs to fill before build-ready."""
    dimension: QualityDimension = QualityDimension.OTHER
    title: str  # human-readable gap, e.g. "User roles missing"
    severity: Severity = Severity.MEDIUM
    explanation: str = ""
    suggested_question: str = ""


class VaguePhrase(BaseModel):
    """A specific quoted phrase that introduces ambiguity."""
    phrase: str
    suggestion: str = ""
    category: str = "vague_term"  # vague_term | unquantified | passive | undefined
    flagged_term: str = ""  # e.g. "fast" from "fast login"
    questions: List[str] = Field(default_factory=list)  # e.g. "What is fast?"


class QualityRadarScores(BaseModel):
    """Screen 4 — six-axis requirement quality radar (0..100, higher is better)."""
    clarity: float = 0.0
    completeness: float = 0.0
    testability: float = 0.0
    security: float = 0.0
    business_value: float = 0.0
    maintainability: float = 0.0


class QualityScoreReport(BaseModel):
    """Output of the Requirement Quality scorer.

    Enterprise-facing shape (also exposed at top level):
        {
          "clarity": 82,
          "completeness": 70,
          "testability": 90,
          "ambiguity": 65,
          "overall_score": 77
        }

    Legacy aliases: `quality_score` == `overall_score`;
    `ambiguity_score` == `ambiguity` (higher = more ambiguous / worse).
    """
    clarity: float = 0.0
    completeness: float = 0.0
    testability: float = 0.0
    radar: QualityRadarScores = Field(default_factory=QualityRadarScores)
    ambiguity: float = 0.0
    overall_score: float = 0.0
    quality_score: float = 0.0
    ambiguity_score: float = 0.0
    grade: str = "F"
    method: str = "heuristic"  # "heuristic" | "ai" | "hybrid"
    highlight_gaps: List[str] = Field(default_factory=list)
    breakdown: dict = Field(default_factory=dict)
    stats: dict = Field(default_factory=dict)
    missing_information: List[MissingInformation] = Field(default_factory=list)
    vague_phrases: List[VaguePhrase] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Requirement-to-Code Impact Analysis -------------------------- #


class ImpactChangeType(str, Enum):
    NEW = "new"
    MODIFY = "modify"
    EXTEND = "extend"
    REPLACE = "replace"
    REMOVE = "remove"
    UNKNOWN = "unknown"


class BlastLabel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SWEEPING = "sweeping"


class ComponentImpact(BaseModel):
    component: str
    layer: ArchitectureLayer = ArchitectureLayer.SERVICE
    change_type: ImpactChangeType = ImpactChangeType.MODIFY
    is_new: bool = False
    rationale: str = ""
    confidence: float = 0.7  # 0..1


class APIImpact(BaseModel):
    method: str = "GET"
    path: str
    change_type: ImpactChangeType = ImpactChangeType.NEW
    description: str = ""


class DataImpact(BaseModel):
    entity: str
    change_type: ImpactChangeType = ImpactChangeType.MODIFY
    fields: List[str] = Field(default_factory=list)
    description: str = ""


class FileImpact(BaseModel):
    path: str
    change_type: ImpactChangeType = ImpactChangeType.MODIFY
    description: str = ""


class DependencyImpact(BaseModel):
    name: str
    kind: str = "library"  # library | service | saas | protocol
    is_new: bool = True
    description: str = ""


class ImpactRisk(BaseModel):
    title: str
    severity: Severity = Severity.MEDIUM
    description: str = ""
    mitigation: str = ""


class ImpactGraphNode(BaseModel):
    id: str
    label: str
    layer: ArchitectureLayer = ArchitectureLayer.SERVICE
    change_type: ImpactChangeType = ImpactChangeType.MODIFY
    is_new: bool = False


class ImpactGraphEdge(BaseModel):
    source: str
    target: str
    label: str = ""


class ImpactGraph(BaseModel):
    nodes: List[ImpactGraphNode] = Field(default_factory=list)
    edges: List[ImpactGraphEdge] = Field(default_factory=list)


class RolloutStep(BaseModel):
    order: int
    title: str
    description: str = ""
    component_ids: List[str] = Field(default_factory=list)


# ---------- Defect Prediction (12) ------------------------------------- #


class DefectModule(BaseModel):
    name: str
    risk_score: int = 0  # 0-100
    risk_level: str = "low"  # low | medium | high | critical
    drivers: List[str] = Field(default_factory=list)
    notes: str = ""


class DefectPrediction(BaseModel):
    high_risk_modules: List[str] = Field(default_factory=list)
    modules: List[DefectModule] = Field(default_factory=list)
    overall_risk: int = 0
    summary: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Delivery Readiness (16) ------------------------------------ #


class ReadinessSignal(BaseModel):
    label: str
    weight: int = 5
    achieved: bool = False
    description: str = ""


class DeliveryReadiness(BaseModel):
    readiness: int = 0  # 0-100
    status: str = "not_ready"  # not_ready | preparing | ready_with_caveats | ready
    blocking_items: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    signals: List[ReadinessSignal] = Field(default_factory=list)
    summary: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Delivery Readiness Center (Screen 10) ----------------------- #


class ReadinessChecklistItem(BaseModel):
    """One row on the demo-ending readiness checklist."""

    key: str  # requirements | stories | tasks | tests | risks | architecture
    label: str
    complete: bool = False
    detail: str = ""


class DeliveryReadinessCenter(BaseModel):
    """Screen 10 — final SDLC gate summary before handoff."""

    checklist: List[ReadinessChecklistItem] = Field(default_factory=list)
    readiness: int = 0  # 0-100
    status_label: str = "PROJECT READY"  # PROJECT READY | IN PROGRESS | NOT READY
    headline: str = ""
    blocking_items: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Meeting Extractor (13) ------------------------------------ #


class ExtractedRequirement(BaseModel):
    text: str
    persona: str = ""
    confidence: float = 0.7


class ExtractedStory(BaseModel):
    title: str
    persona: str = ""
    goal: str = ""
    benefit: str = ""


class ExtractedTask(BaseModel):
    title: str
    owner: str = ""
    estimate_hours: Optional[float] = None


class ExtractedRisk(BaseModel):
    description: str
    severity: Severity = Severity.MEDIUM


class ActionItem(BaseModel):
    description: str
    owner: str = ""
    due: Optional[str] = None


class MeetingExtraction(BaseModel):
    source_type: str = "transcript"  # transcript | notes | mixed
    title: str = ""
    summary: str = ""
    attendees: List[str] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    requirements: List[ExtractedRequirement] = Field(default_factory=list)
    stories: List[ExtractedStory] = Field(default_factory=list)
    tasks: List[ExtractedTask] = Field(default_factory=list)
    risks: List[ExtractedRisk] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Requirement Diff (14) ------------------------------------- #


class DiffEntry(BaseModel):
    kind: str = "added"  # added | removed | changed
    text: str = ""
    before: str = ""
    after: str = ""


class RequirementDiffReport(BaseModel):
    title_a: str = "Version A"
    title_b: str = "Version B"
    summary: str = ""
    added: List[DiffEntry] = Field(default_factory=list)
    removed: List[DiffEntry] = Field(default_factory=list)
    changed: List[DiffEntry] = Field(default_factory=list)
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Traceability Matrix (15) ---------------------------------- #


class TraceabilityRow(BaseModel):
    requirement_id: str
    requirement_label: str = ""  # e.g. REQ-001
    requirement_text: str = ""
    story_ids: List[str] = Field(default_factory=list)
    story_labels: List[str] = Field(default_factory=list)
    story_titles: List[str] = Field(default_factory=list)
    task_ids: List[str] = Field(default_factory=list)
    task_labels: List[str] = Field(default_factory=list)
    task_titles: List[str] = Field(default_factory=list)
    test_ids: List[str] = Field(default_factory=list)
    test_labels: List[str] = Field(default_factory=list)
    test_titles: List[str] = Field(default_factory=list)
    component_names: List[str] = Field(default_factory=list)
    tree_text: str = ""  # ASCII chain for this requirement
    coverage: int = 0  # 0-100 — % of chain links present


class TraceabilityCoverage(BaseModel):
    requirements_with_stories: int = 0
    requirements_with_tasks: int = 0
    requirements_with_tests: int = 0
    requirements_with_components: int = 0
    total_requirements: int = 0


class TraceabilityGraphNode(BaseModel):
    """Screen 7 — interactive traceability graph node."""
    id: str
    label: str
    title: str = ""
    kind: str = "requirement"  # requirement | story | task | test
    row_index: int = 0
    coverage: int = 0
    x: float = 0.0
    y: float = 0.0


class TraceabilityGraphEdge(BaseModel):
    source: str
    target: str
    primary: bool = False


class TraceabilityGraph(BaseModel):
    """REQ → US → TASK → TC lanes for the visual graph."""
    nodes: List[TraceabilityGraphNode] = Field(default_factory=list)
    edges: List[TraceabilityGraphEdge] = Field(default_factory=list)
    lanes: List[str] = Field(
        default_factory=lambda: [
            "Requirement",
            "User Story",
            "Task",
            "Test Case",
        ]
    )
    width: float = 1000.0
    height: float = 520.0


class TraceabilityMatrix(BaseModel):
    rows: List[TraceabilityRow] = Field(default_factory=list)
    coverage: TraceabilityCoverage = Field(default_factory=TraceabilityCoverage)
    tree_text: str = ""  # Full matrix as ASCII trees
    graph: TraceabilityGraph = Field(default_factory=TraceabilityGraph)
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- AI Risk Center (Screen 8) ----------------------------------- #


class RiskCenterItem(BaseModel):
    """One clickable cell in the severity-band heat map."""

    id: str
    title: str
    risk: str = Field(description="Primary risk label, e.g. External dependency")
    probability: int = Field(ge=0, le=100, description="Likelihood 0–100%")
    severity: str = "high"  # high | medium | low
    category: str = ""
    mitigation: str = ""
    source: str = "pipeline"  # pipeline | prediction | module


class RiskCenterBand(BaseModel):
    """HIGH / MEDIUM / LOW row with block count matching items."""

    level: str  # high | medium | low
    label: str  # HIGH | MEDIUM | LOW
    items: List[RiskCenterItem] = Field(default_factory=list)


class RiskCenterHeatmap(BaseModel):
    """Screen 8 — severity-band heat map with drill-down items."""

    bands: List[RiskCenterBand] = Field(default_factory=list)
    total_items: int = 0
    headline: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Conversational Assistant (17) ----------------------------- #


class AssistantCitation(BaseModel):
    artifact_type: str  # story | task | test | risk | ambiguity | component | api | requirement
    artifact_id: str = ""
    label: str = ""
    snippet: str = ""


class AssistantTurn(BaseModel):
    question: str
    answer: str
    citations: List[AssistantCitation] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- PRD Generator (18) ---------------------------------------- #


class PRDStory(BaseModel):
    id: str = Field(default_factory=lambda: f"prd_st_{uuid4().hex[:6]}")
    title: str
    persona: str = ""
    goal: str = ""
    benefit: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)
    priority: Severity = Severity.MEDIUM


class PRDRisk(BaseModel):
    title: str
    severity: Severity = Severity.MEDIUM
    mitigation: str = ""


class PRDDependency(BaseModel):
    name: str
    kind: str = "external"  # external | internal | infra | team
    description: str = ""


class ProductRequirementsDocument(BaseModel):
    title: str = ""
    one_liner: str = ""
    executive_summary: str = ""
    problem_statement: str = ""
    goals: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    user_stories: List[PRDStory] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    risks: List[PRDRisk] = Field(default_factory=list)
    dependencies: List[PRDDependency] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    timeline: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- SDLC Digital Twin (19) ----------------------------------- #


class TwinArtifact(BaseModel):
    """A single artifact rendered inside a digital-twin stage card."""
    kind: str  # story | task | test | risk | api | component | metric | note
    label: str
    detail: str = ""
    icon: str = ""  # short single-glyph hint for the UI
    severity: Optional[Severity] = None


class TwinStage(BaseModel):
    id: str  # requirement | analysis | design | development | testing | deployment
    label: str
    status: str = "pending"  # pending | in_progress | complete | blocked
    progress: int = 0  # 0..100
    summary: str = ""
    artifacts: List[TwinArtifact] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class DigitalTwinReport(BaseModel):
    project_id: str
    title: str = ""
    stages: List[TwinStage] = Field(default_factory=list)
    overall_progress: int = 0  # 0..100
    headline: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- AI Project Manager Agent (20) ---------------------------- #


class CriticalPathStep(BaseModel):
    name: str
    duration_days: float = 0.0
    depends_on: List[str] = Field(default_factory=list)
    rationale: str = ""


class PMMilestone(BaseModel):
    name: str
    week: int
    description: str = ""


class ProjectManagerForecast(BaseModel):
    project_id: str = ""
    timeline: str = ""  # canonical, e.g. "4 weeks"
    timeline_weeks: float = 0.0
    critical_path: List[str] = Field(default_factory=list)
    critical_path_detail: List[CriticalPathStep] = Field(default_factory=list)
    release_risk: str = "Low"  # Low | Medium | High | Critical
    risk_score: int = 0  # 0..100
    risk_drivers: List[str] = Field(default_factory=list)
    milestones: List[PMMilestone] = Field(default_factory=list)
    workstreams: List[str] = Field(default_factory=list)
    summary: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Dev Studio: API / Schema / Tests ---------------------------- #


class APIField(BaseModel):
    name: str
    type: str = "string"  # string | integer | number | boolean | object | array | datetime | uuid
    required: bool = True
    description: str = ""
    example: Optional[Any] = None


class APIContract(BaseModel):
    """A single endpoint contract."""
    endpoint: str  # e.g. "/login/otp"
    method: str = "POST"  # GET | POST | PUT | PATCH | DELETE
    summary: str = ""
    description: str = ""
    request_fields: List[APIField] = Field(default_factory=list)
    response_fields: List[APIField] = Field(default_factory=list)
    request_example: Dict[str, Any] = Field(default_factory=dict)
    response_example: Dict[str, Any] = Field(default_factory=dict)
    status_codes: List[Dict[str, str]] = Field(default_factory=list)
    auth_required: bool = True
    tags: List[str] = Field(default_factory=list)


class APIContractSuite(BaseModel):
    """Output of the API Contract Generator."""
    title: str = ""
    base_path: str = "/api"
    contracts: List[APIContract] = Field(default_factory=list)
    method: str = "heuristic"  # "heuristic" | "hybrid"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Database schema ---


class SchemaField(BaseModel):
    name: str
    type: str = "string"  # uuid | string | text | integer | bigint | boolean | datetime | decimal | json | enum
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None  # e.g. "users.id"
    indexed: bool = False
    unique: bool = False
    default: Optional[str] = None
    description: str = ""


class SchemaTable(BaseModel):
    name: str  # snake_case table name
    label: str = ""  # PascalCase friendly label
    description: str = ""
    fields: List[SchemaField] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)


class SchemaRelationship(BaseModel):
    from_table: str
    to_table: str
    cardinality: str = "many_to_one"  # one_to_one | one_to_many | many_to_one | many_to_many
    via_field: str = ""
    description: str = ""


class DatabaseSchema(BaseModel):
    """Output of the Database Schema Suggestions feature."""
    title: str = ""
    summary: str = ""
    tables: List[SchemaTable] = Field(default_factory=list)
    relationships: List[SchemaRelationship] = Field(default_factory=list)
    sql_ddl: str = ""
    mermaid_er: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Test suite ---


class TestCategory(str, Enum):
    FUNCTIONAL = "functional"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    SECURITY = "security"
    REGRESSION = "regression"


class GeneratedTest(BaseModel):
    id: str = Field(default_factory=lambda: f"gtc_{uuid4().hex[:8]}")
    title: str
    category: TestCategory = TestCategory.FUNCTIONAL
    given: str = ""
    when: str = ""
    then: str = ""
    severity: Severity = Severity.MEDIUM
    tags: List[str] = Field(default_factory=list)
    expected_result: str = ""


class TestCategoryGroup(BaseModel):
    category: TestCategory
    description: str = ""
    tests: List[GeneratedTest] = Field(default_factory=list)


class GeneratedTestSuite(BaseModel):
    """Output of the Automated Test Generation feature."""
    title: str = ""
    summary: str = ""
    groups: List[TestCategoryGroup] = Field(default_factory=list)
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- AI Studio: Effort / Risk / Architecture --------------------- #


class EffortComplexity(str, Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EffortEstimate(BaseModel):
    """Auto-estimate for a requirement / story / task."""
    story_points: int = 0
    complexity: EffortComplexity = EffortComplexity.MEDIUM
    estimated_hours: float = 0.0
    confidence: float = 0.6  # 0..1
    drivers: List[str] = Field(default_factory=list)
    rationale: str = ""
    method: str = "heuristic"  # "heuristic" | "hybrid"
    # Management rollup (project or scaled requirement view)
    total_story_points: int = 0
    developers: int = 4
    estimated_weeks: float = 0.0
    estimated_cost_usd: float = 0.0
    cost_currency: str = "USD"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAlert(BaseModel):
    """Enterprise-facing risk callout (shown with warning icon in UI)."""
    message: str
    severity: str = "medium"  # low | medium | high | critical


class RiskPrediction(BaseModel):
    """Predicted risk profile of a requirement."""
    risk_level: RiskLevel = RiskLevel.LOW
    score: int = 0  # 0-100
    alerts: List[RiskAlert] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)  # security, integration, etc.
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ArchitectureLayerGroup(BaseModel):
    """One tier in the generated architecture tree (Frontend, Backend, …)."""
    name: str
    items: List[str] = Field(default_factory=list)


class ArchitectureGraphNode(BaseModel):
    """Interactive graph node for Screen 5 — Architecture Visualizer."""
    id: str
    label: str
    tier: str = "service"  # frontend | gateway | service | data | integration
    layer: str = ""
    kind: str = "component"  # stack | component | tier
    x: float = 0.0
    y: float = 0.0


class ArchitectureGraphEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    kind: str = "flow"  # flow | internal


class ArchitectureGraph(BaseModel):
    """Nodes + edges for the interactive architecture canvas."""
    nodes: List[ArchitectureGraphNode] = Field(default_factory=list)
    edges: List[ArchitectureGraphEdge] = Field(default_factory=list)
    stack: List[str] = Field(
        default_factory=list,
        description="Linear wow stack e.g. Frontend → API Gateway → Auth Service → Database",
    )


class ArchitectureDiagram(BaseModel):
    """Architecture Generator output — layer tree + Mermaid diagrams."""
    title: str = ""
    layers: List[ArchitectureLayerGroup] = Field(default_factory=list)
    tree_text: str = ""
    mermaid: str = ""  # system flow (flowchart TD)
    mermaid_layers: str = ""  # layered subgraph view
    graph: ArchitectureGraph = Field(default_factory=ArchitectureGraph)
    nodes_count: int = 0
    edges_count: int = 0
    description: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Auto Sprint Planning (task-level, from raw requirement) ----- #


class SprintPlanTaskRow(BaseModel):
    """One row in the manager-facing sprint plan table."""
    task: str
    story_points: int = 0
    category: str = ""  # api | ui | auth | data | testing | infra | other


class SprintKanbanCard(BaseModel):
    """One draggable card on the Screen 6 sprint board."""
    id: str = Field(default_factory=lambda: f"card_{uuid4().hex[:8]}")
    title: str
    story_points: int = 0
    category: str = ""  # api | ui | auth | data | testing
    status: str = "todo"  # todo | in_progress | done (within sprint)


class SprintKanbanColumn(BaseModel):
    """Sprint column — e.g. Sprint 1, Sprint 2."""
    id: str
    title: str
    sprint_number: int = 1
    goal: str = ""
    capacity_points: int = 20
    cards: List[SprintKanbanCard] = Field(default_factory=list)


class SprintKanbanBoard(BaseModel):
    """Screen 6 — multi-sprint Kanban with drag-and-drop persistence."""
    columns: List[SprintKanbanColumn] = Field(default_factory=list)
    total_points: int = 0
    velocity_per_sprint: int = 20
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AutoSprintPlan(BaseModel):
    """Auto Sprint Planning — decompose a requirement into tasks + points.

    Example output for "Build user authentication":
        Login API · 3 | Registration API · 3 | JWT Auth · 2 | …
        Total: 13 story points → Suggested Sprint: Sprint 1
    """
    requirement: str = ""
    tasks: List[SprintPlanTaskRow] = Field(default_factory=list)
    total_story_points: int = 0
    suggested_sprint: str = "Sprint 1"
    suggested_sprint_number: int = 1
    sprint_capacity: int = 20
    utilization_pct: int = 0
    fits_in_sprint: bool = True
    rationale: str = ""
    method: str = "heuristic"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Interactive Sprint Planning ---------------------------------- #


class StorySprintItem(BaseModel):
    """A story slot inside a planned sprint."""
    story_id: str
    story_title: str
    persona: str = ""
    points: int = 0
    tasks_count: int = 0
    has_risk: bool = False


class StorySprint(BaseModel):
    """One sprint's allocation in a story-level sprint plan."""
    sprint_number: int
    label: str = ""  # e.g. "Sprint 1"
    goal: str = ""
    weeks: float = 2.0
    capacity_points: float = 0.0
    planned_points: int = 0
    utilization_pct: int = 0
    stories: List[StorySprintItem] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class TeamSprintPlan(BaseModel):
    """Story-level sprint plan derived from interactive team-size + sprint-length input.

    Distinct from the Control-Tower-stage `SprintPlan` (which works at the
    Task level). This plan is the deliverable view a Scrum Master /
    Engineering Manager actually wants for a kickoff: which STORIES land in
    which sprint, given THIS team's capacity.
    """
    project_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    method: str = "heuristic"  # "heuristic" | "hybrid"
    team_size: int = 6
    sprint_weeks: float = 2.0
    points_per_engineer_per_sprint: float = 6.0
    velocity_points_per_sprint: float = 0.0
    total_stories: int = 0
    total_points: int = 0
    total_sprints: int = 0
    total_weeks: float = 0.0
    sprints: List[StorySprint] = Field(default_factory=list)
    unscheduled_stories: List[StorySprintItem] = Field(default_factory=list)
    rationale: str = ""


# ---------- Automatic Jira Backlog ---------------------------------------- #


class BacklogEpic(BaseModel):
    """Top of the backlog hierarchy (one per generated backlog)."""
    id: str = Field(default_factory=lambda: f"epic_{uuid4().hex[:8]}")
    title: str
    description: str = ""
    key_results: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    jira_key: Optional[str] = None


class BacklogSubtask(BaseModel):
    """An implementation step under a Task (4th level in Jira)."""
    id: str = Field(default_factory=lambda: f"sub_{uuid4().hex[:8]}")
    title: str
    description: str = ""
    parent_task_id: str
    estimate_hours: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    jira_key: Optional[str] = None


class BacklogStoryRef(BaseModel):
    """Story-shaped row used in the Jira Backlog hierarchy."""
    id: str
    title: str
    persona: str = ""
    goal: str = ""
    benefit: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)
    task_ids: List[str] = Field(default_factory=list)
    jira_key: Optional[str] = None


class BacklogTaskRef(BaseModel):
    """Task-shaped row used in the Jira Backlog hierarchy."""
    id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.FEATURE
    priority: Severity = Severity.MEDIUM
    story_id: Optional[str] = None
    estimate_points: Optional[int] = None
    estimate_hours: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    subtask_ids: List[str] = Field(default_factory=list)
    jira_key: Optional[str] = None


class JiraBacklog(BaseModel):
    """Hierarchical Epic → Stories → Tasks → Subtasks structure ready for export."""
    project_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    method: str = "heuristic"  # "heuristic" | "ai" | "hybrid"
    epic: BacklogEpic
    stories: List[BacklogStoryRef] = Field(default_factory=list)
    tasks: List[BacklogTaskRef] = Field(default_factory=list)
    subtasks: List[BacklogSubtask] = Field(default_factory=list)
    summary: str = ""


class AffectedItem(BaseModel):
    """Copilot-style affected surface (API, service, app, tests, …)."""
    name: str
    kind: str = "component"  # api | service | frontend | test | data | integration
    change_type: str = "modify"
    detail: str = ""


class ImpactAnalysisReport(BaseModel):
    """Predicted impact of a requirement on an existing system."""
    requirement: str = ""
    project_id: Optional[str] = None
    blast_radius: float = 0.0  # 0..100
    blast_label: BlastLabel = BlastLabel.LOW
    summary: str = ""
    method: str = "heuristic"  # "heuristic" | "ai"
    affected: List[AffectedItem] = Field(default_factory=list)
    components: List[ComponentImpact] = Field(default_factory=list)
    apis: List[APIImpact] = Field(default_factory=list)
    data: List[DataImpact] = Field(default_factory=list)
    files: List[FileImpact] = Field(default_factory=list)
    dependencies: List[DependencyImpact] = Field(default_factory=list)
    risks: List[ImpactRisk] = Field(default_factory=list)
    rollout: List[RolloutStep] = Field(default_factory=list)
    graph: ImpactGraph = Field(default_factory=ImpactGraph)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: f"proj_{uuid4().hex[:8]}")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_input: str
    source_clauses: List[SourceClause] = Field(default_factory=list)
    requirement_brief: Optional[RequirementBrief] = None
    pipeline_epic: Optional[BacklogEpic] = None
    summary: Optional[RequirementSummary] = None
    architecture_brief: Optional[ArchitectureBrief] = None
    stories: List[UserStory] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    ambiguities: List[AmbiguityIssue] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    sprint_plan: Optional[SprintPlan] = None
    team_sprint_plan: Optional[TeamSprintPlan] = None
    auto_sprint_plan: Optional[AutoSprintPlan] = None
    sprint_kanban: Optional[SprintKanbanBoard] = None
    review_board_report: Optional[ReviewBoardReport] = None
    quality_score_report: Optional[QualityScoreReport] = None
    impact_report: Optional[ImpactAnalysisReport] = None
    jira_backlog: Optional[JiraBacklog] = None
    requirement_estimate: Optional[EffortEstimate] = None
    requirement_risk: Optional[RiskPrediction] = None
    architecture_diagram: Optional[ArchitectureDiagram] = None
    api_contract_suite: Optional[APIContractSuite] = None
    database_schema: Optional[DatabaseSchema] = None
    generated_test_suite: Optional[GeneratedTestSuite] = None
    defect_prediction: Optional[DefectPrediction] = None
    delivery_readiness: Optional[DeliveryReadiness] = None
    delivery_readiness_center: Optional[DeliveryReadinessCenter] = None
    meeting_extraction: Optional[MeetingExtraction] = None
    traceability_matrix: Optional[TraceabilityMatrix] = None
    risk_center: Optional[RiskCenterHeatmap] = None
    prd_document: Optional[ProductRequirementsDocument] = None
    digital_twin: Optional[DigitalTwinReport] = None
    pm_forecast: Optional[ProjectManagerForecast] = None
    metrics: Optional[ProductivityMetrics] = None
    chat_history: List["ChatMessage"] = Field(default_factory=list)
    last_pipeline_timings_ms: Optional[dict[str, int]] = Field(
        default=None,
        description="Wall time per pipeline stage from the last analyze run (stage label → ms).",
    )


class CommandCenterMetric(BaseModel):
    """One KPI tile on the SDLC Command Center."""
    key: str
    label: str
    value: str = ""
    subvalue: str = ""
    status: str = "pending"  # pending | ok | warn | crit
    href: str = ""


class ExecutiveKpis(BaseModel):
    requirements_processed: int = 0
    stories_generated: int = 0
    test_cases_generated: int = 0
    hours_saved: int = 0
    risky_requirements: int = 0


class ExecutiveHealth(BaseModel):
    requirement_quality_score: int = 0
    readiness_score: int = 0
    readiness_label: str = "Ready For Development"


class ExecutiveDashboard(BaseModel):
    """Screen 1 — org-wide executive view after login."""
    kpis: ExecutiveKpis = Field(default_factory=ExecutiveKpis)
    health: ExecutiveHealth = Field(default_factory=ExecutiveHealth)
    projects_count: int = 0
    method: str = "aggregated"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DeliveryVerdict(str, Enum):
    """Three-state GO/NO-GO verdict surfaced on the Approve & Export panel."""
    GO = "GO"
    GO_WITH_CAVEATS = "GO_WITH_CAVEATS"
    NO_GO = "NO_GO"


class DeliverySprintTile(BaseModel):
    """One sprint tile rendered on the Executive Delivery dashboard."""
    label: str = "Sprint 1"
    number: int = 1
    weeks: float = 2.0
    planned_points: int = 0
    goal: str = ""


class DeliveryHeadlineMetric(BaseModel):
    """A single hero KPI on the Executive Delivery dashboard."""
    key: str
    label: str
    value: int = 0
    detail: str = ""
    severity: str = "info"  # info | ok | warn | crit


class DeliverySummary(BaseModel):
    """One-screen 'AI Delivery Manager' verdict surfaced on Approve & Export.

    Aggregates every artifact the multi-agent pipeline produced into a
    single counts-plus-verdict view so a judge can answer
    'is this project ready to ship?' in under five seconds.
    """
    project_id: str
    project_name: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # ----- Headline counts (matches the user's wishlist) -----
    requirements_count: int = 0
    epics_count: int = 0
    stories_count: int = 0
    tasks_count: int = 0
    apis_count: int = 0
    test_cases_count: int = 0
    risks_count: int = 0
    ambiguities_count: int = 0
    architecture_components_count: int = 0

    # ----- Quality & readiness -----
    readiness_score: int = 0
    quality_score: int = 0
    confidence_score: int = 0  # review board confidence

    # ----- Plan -----
    sprints: List[DeliverySprintTile] = Field(default_factory=list)
    sprint_count: int = 0
    estimated_delivery_weeks: float = 0.0
    estimated_total_hours: float = 0.0
    estimated_total_points: int = 0

    # ----- Cost -----
    projected_cost_usd: float = 0.0
    blended_hourly_rate_usd: float = 150.0

    # ----- GO / NO-GO verdict -----
    verdict: DeliveryVerdict = DeliveryVerdict.GO_WITH_CAVEATS
    verdict_label: str = "GO with caveats"
    verdict_reasons: List[str] = Field(default_factory=list)
    blocking_items: List[str] = Field(default_factory=list)

    # ----- Value narrative -----
    hours_saved_vs_manual: int = 0
    cost_saved_usd: float = 0.0
    weeks_saved_vs_manual: float = 0.0

    # ----- Wow-factor delivery comparison -----
    helix_wall_clock_minutes: float = 0.0  # actual pipeline run time
    manual_equivalent_weeks: float = 0.0  # what a human team would take
    speedup_multiplier: float = 0.0       # manual / helix
    equivalent_team_size: int = 0          # FTEs a human team would need
    roi_multiplier: float = 0.0            # cost_saved / projected_cost

    # ----- Per-agent productivity multiplier breakdown -----
    # Shows judges WHERE the savings come from (which agent replaced
    # how many human-hours). Empty list when no agents have produced
    # artifacts yet.
    agent_contributions: List["AgentContribution"] = Field(default_factory=list)

    # ----- Verdict upgrade path -----
    # When verdict is GO_WITH_CAVEATS or NO_GO, list the specific
    # actions that would flip the verdict to GO. Empty when verdict
    # is already GO.
    upgrade_recommendations: List[str] = Field(default_factory=list)

    # Pre-built hero tiles for the UI (key+label+value+severity) — keeps
    # the React component dumb (one .map render) and lets us update the
    # tile order/labels without re-shipping the frontend.
    headline_metrics: List[DeliveryHeadlineMetric] = Field(default_factory=list)


class AgentContribution(BaseModel):
    """One per-agent row on the productivity-multiplier breakdown.

    Lets judges see "where did the time savings come from?" instead
    of one anonymous hours-saved number.
    """
    agent: str  # "Product Manager", "Architect", "QA Engineer", ...
    artifacts_produced: int = 0  # stories or tasks or tests created
    artifact_label: str = "artifacts"  # "stories" / "tasks" / "tests"
    human_minutes_per_artifact: float = 0.0
    human_minutes_displaced: int = 0  # artifacts_produced * minutes/artifact
    pipeline_seconds: float = 0.0   # what Helix took to do the work
    speedup_multiplier: float = 0.0  # human_minutes * 60 / pipeline_seconds


DeliverySummary.model_rebuild()


class CommandCenterSnapshot(BaseModel):
    """Single-screen SDLC health for a project."""
    project_id: str
    project_name: str = ""
    metrics: List[CommandCenterMetric] = Field(default_factory=list)
    requirement_score: Optional[int] = None
    ambiguities_count: int = 0
    tasks_count: int = 0
    test_cases_count: int = 0
    stories_count: int = 0
    risks_count: int = 0
    risk_score: Optional[int] = None
    total_story_points: int = 0
    estimated_weeks: float = 0.0
    estimated_cost_usd: float = 0.0
    suggested_sprint: str = ""
    pipeline_done: int = 0
    pipeline_total: int = 5
    generated_at: datetime = Field(default_factory=datetime.utcnow)


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
