"""Regression tests for the Executive Delivery Summary builder.

The verdict logic is judge-facing — it powers the GO / GO-WITH-CAVEATS
/ NO-GO badge on the Approve & Export hero panel. These tests pin it
down so a refactor cannot silently flip the verdict.
"""
from __future__ import annotations

from app.models import (
    APIContract,
    APIContractSuite,
    AmbiguityIssue,
    AmbiguityKind,
    ArchitectureDiagram,
    ArchitectureLayerGroup,
    DeliveryReadinessCenter,
    DeliveryVerdict,
    Project,
    QualityRadarScores,
    QualityScoreReport,
    Risk,
    RiskCategory,
    Severity,
    SourceClause,
    SprintItem,
    SprintPlan,
    Task,
    TaskType,
    UserStory,
)
from app.services.delivery_summary import build_delivery_summary


def _make_project(
    *,
    clauses: int = 20,
    stories: int = 6,
    tasks_per_story: int = 7,
    apis: int = 10,
    tests: int = 30,
    ambiguities: int = 5,
    risks: list[Severity] | None = None,
    architecture_components: int = 12,
    readiness: int = 90,
    quality: int = 82,
    sprint_items: int = 3,
    points_per_task: int = 5,
    hours_per_task: float = 8.0,
) -> Project:
    """Fabricate a Project with the exact counts we want to assert on.

    Using full Pydantic models (not mocks) so we exercise the same
    field access path as production code.
    """
    risks = risks or []
    project = Project(name="Acme Test PRD", raw_input="...")

    project.source_clauses = [
        SourceClause(index=i, text=f"clause {i}") for i in range(clauses)
    ]

    project.stories = [
        UserStory(
            id=f"story_{i:04d}",
            title=f"Story {i} title",
            persona="customer",
            goal=f"do thing {i}",
            benefit="value",
        )
        for i in range(stories)
    ]

    project.tasks = [
        Task(
            title=f"Task {i}.{j}",
            description="",
            type=TaskType.FEATURE,
            priority=Severity.MEDIUM,
            story_id=project.stories[i].id,
            estimate_points=points_per_task,
            estimate_hours=hours_per_task,
        )
        for i in range(stories)
        for j in range(tasks_per_story)
    ]

    project.api_contract_suite = APIContractSuite(
        title="APIs",
        contracts=[
            APIContract(
                endpoint=f"/api/resource{i}",
                method="GET",
                summary="x",
                description="x",
            )
            for i in range(apis)
        ],
    )

    project.test_cases = []  # tests count handled via len(); skip building full TestCase
    # build minimal TestCase entries
    from app.models import TestCase, TestType

    project.test_cases = [
        TestCase(
            title=f"TC {i}",
            type=TestType.UNIT,
            given="g",
            when="w",
            then="t",
        )
        for i in range(tests)
    ]

    project.ambiguities = [
        AmbiguityIssue(
            kind=AmbiguityKind.UNDEFINED_TERM,
            severity=Severity.MEDIUM,
            excerpt=f"vague {i}",
            explanation=f"issue {i}",
            suggested_question=f"What does '{i}' mean?",
        )
        for i in range(ambiguities)
    ]

    project.risks = [
        Risk(
            category=RiskCategory.SECURITY,
            severity=sev,
            title=f"risk {i}",
            description="d",
            mitigation="m",
        )
        for i, sev in enumerate(risks)
    ]

    layers: list[ArchitectureLayerGroup] = []
    remaining = architecture_components
    layer_count = 4
    per_layer = max(1, architecture_components // layer_count)
    for i in range(layer_count):
        take = min(per_layer, remaining)
        if take <= 0:
            break
        layers.append(
            ArchitectureLayerGroup(
                name=f"Layer {i}",
                items=[f"Component {i}.{k}" for k in range(take)],
            )
        )
        remaining -= take
    if remaining > 0 and layers:
        layers[-1].items.extend(
            f"Component extra {k}" for k in range(remaining)
        )
    project.architecture_diagram = ArchitectureDiagram(
        title="Arch",
        layers=layers,
        tree_text="",
        mermaid="graph TD\n",
        mermaid_layers="graph LR\n",
    )

    project.delivery_readiness_center = DeliveryReadinessCenter(
        readiness=readiness,
        status_label="PROJECT READY",
        headline="ready",
    )

    project.quality_score_report = QualityScoreReport(
        overall_score=quality,
        radar=QualityRadarScores(),
    )

    project.sprint_plan = SprintPlan(
        velocity_points_per_sprint=20.0,
        total_sprints=sprint_items,
        total_weeks=float(sprint_items) * 2.0,
        items=[
            SprintItem(
                sprint_number=i + 1,
                goal=f"Sprint {i + 1} goal",
                task_ids=[],
                total_points=15,
                weeks=2.0,
            )
            for i in range(sprint_items)
        ],
    )

    return project


# --------------------------------------------------------------------- #
# Counts
# --------------------------------------------------------------------- #


def test_counts_match_artifacts() -> None:
    project = _make_project(
        clauses=40,
        stories=11,
        tasks_per_story=7,
        apis=24,
        tests=183,
        ambiguities=12,
        risks=[Severity.MEDIUM, Severity.MEDIUM],
        architecture_components=18,
    )
    summary = build_delivery_summary(project)

    assert summary.requirements_count == 40
    assert summary.stories_count == 11
    assert summary.tasks_count == 11 * 7  # 77
    assert summary.apis_count == 24
    assert summary.test_cases_count == 183
    assert summary.ambiguities_count == 12
    assert summary.risks_count == 2
    assert summary.architecture_components_count == 18
    assert summary.epics_count >= 1


# --------------------------------------------------------------------- #
# Verdict transitions
# --------------------------------------------------------------------- #


def test_verdict_go_when_readiness_and_quality_high_with_no_critical_risks() -> None:
    project = _make_project(
        readiness=92,
        quality=85,
        risks=[],
    )
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.GO
    assert summary.verdict_label == "GO"
    assert not summary.blocking_items


def test_verdict_caveats_when_one_high_risk_present() -> None:
    project = _make_project(
        readiness=85,
        quality=78,
        risks=[Severity.HIGH],
    )
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.GO_WITH_CAVEATS
    assert "GO with caveats" == summary.verdict_label


def test_verdict_no_go_when_readiness_too_low() -> None:
    project = _make_project(
        readiness=35,
        quality=70,
        risks=[],
    )
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.NO_GO
    assert any("Readiness" in b for b in summary.blocking_items)


def test_verdict_no_go_when_apis_missing() -> None:
    project = _make_project(apis=0)
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.NO_GO
    assert any("API contracts" in b for b in summary.blocking_items)


# --------------------------------------------------------------------- #
# Cost & effort
# --------------------------------------------------------------------- #


def test_cost_derives_from_estimate_hours_when_available() -> None:
    project = _make_project(
        stories=10,
        tasks_per_story=5,
        hours_per_task=4.0,
        points_per_task=3,
    )
    summary = build_delivery_summary(project)
    expected_hours = 10 * 5 * 4.0
    assert summary.estimated_total_hours == expected_hours
    # Cost = hours * blended_rate ($150)
    assert summary.projected_cost_usd == expected_hours * 150.0


def test_cost_falls_back_to_points_when_hours_missing() -> None:
    project = _make_project(
        stories=5,
        tasks_per_story=4,
        hours_per_task=0.0,
        points_per_task=3,
    )
    summary = build_delivery_summary(project)
    # 20 tasks * 3 pts = 60 pts -> 360 hours @ 6h/pt -> $54,000
    assert summary.estimated_total_points == 60
    assert summary.estimated_total_hours == 360.0
    assert summary.projected_cost_usd == 54_000.0


# --------------------------------------------------------------------- #
# Headline metrics
# --------------------------------------------------------------------- #


def test_headline_metrics_have_all_judge_facing_tiles() -> None:
    project = _make_project()
    summary = build_delivery_summary(project)
    keys = {m.key for m in summary.headline_metrics}
    # The exact tile order is judge-facing — pin every required key.
    assert keys == {
        "requirements",
        "epics",
        "stories",
        "tasks",
        "apis",
        "tests",
        "risks",
        "ambiguities",
        "architecture",
        "readiness",
    }


# --------------------------------------------------------------------- #
# Phase 2 additions — upgrade recs, wow metrics, agent contributions
# --------------------------------------------------------------------- #


def test_upgrade_recommendations_emitted_when_verdict_is_caveats() -> None:
    """When the verdict is GO_WITH_CAVEATS, the dashboard MUST tell
    judges the specific actions that flip it to GO."""
    project = _make_project(
        readiness=72,
        quality=68,
        risks=[Severity.HIGH],
    )
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.GO_WITH_CAVEATS
    recs = summary.upgrade_recommendations
    assert len(recs) >= 2
    joined = " ".join(recs).lower()
    assert "readiness" in joined
    assert "quality" in joined
    assert "risk" in joined


def test_upgrade_recommendations_empty_when_verdict_is_go() -> None:
    project = _make_project(readiness=92, quality=85, risks=[])
    summary = build_delivery_summary(project)
    assert summary.verdict is DeliveryVerdict.GO
    assert summary.upgrade_recommendations == []


def test_agent_contributions_attribute_artifacts_to_agents() -> None:
    """The per-agent breakdown is the receipts for the time-saved number.
    Each agent listed must have produced >0 artifacts and have a
    positive displaced-minutes count."""
    project = _make_project(
        stories=10,
        tasks_per_story=5,
        tests=40,
        ambiguities=8,
        clauses=30,
        risks=[Severity.MEDIUM, Severity.LOW],
        architecture_components=14,
        apis=15,
    )
    summary = build_delivery_summary(project)

    contributions = summary.agent_contributions
    assert contributions, "Expected non-empty agent contributions list"
    agents = {row.agent for row in contributions}
    # All eight production-tracked agents should appear once each
    # storied artifacts are present.
    assert "Product Manager" in agents
    assert "Scrum Master" in agents
    assert "QA Engineer" in agents
    assert "Solution Architect" in agents
    assert "API Designer" in agents
    for row in contributions:
        assert row.artifacts_produced > 0
        assert row.human_minutes_displaced > 0


def test_wow_metrics_populate_when_pipeline_timings_present() -> None:
    """Wall-clock vs manual + speedup multiplier must populate when the
    pipeline captured timings on the Project — this is the 'AI Delivery
    Manager wow factor' the dashboard renders front and centre."""
    project = _make_project()
    # Simulate a pipeline that took 18 seconds across 11 steps.
    project.last_pipeline_timings_ms = {f"step_{i}": 1600 for i in range(11)}
    summary = build_delivery_summary(project)

    assert summary.helix_wall_clock_minutes > 0
    assert summary.manual_equivalent_weeks > 0
    assert summary.speedup_multiplier >= 1.0
    assert summary.equivalent_team_size >= 1
    # ROI = cost_saved / projected_cost. For a 5pt 8h/task project
    # with the default fabricated counts this must be >= 0 (sometimes
    # 0 when manual hours < project hours, that's OK).
    assert summary.roi_multiplier >= 0


# --------------------------------------------------------------------- #
# Sprint planner — team-aware velocity & meaningful goals
# --------------------------------------------------------------------- #


def test_sprint_planner_keeps_sprint_count_under_seven_for_normal_backlog() -> None:
    """Judges flagged 17-sprint plans as unrealistic. The team-aware
    velocity must cap normal backlogs at <= 7 sprints (heuristic
    target is 6, +1 tolerance for dependency-forced overflow)."""
    from app.agents.sprint_planner import _heuristic_plan
    from app.agents.scrum_master import _build_lane_tasks

    project = _make_project(
        stories=11,
        tasks_per_story=0,  # we'll use lane fanout to build tasks instead
    )
    project.tasks = []
    for s in project.stories:
        project.tasks.extend(_build_lane_tasks(project, s))

    plan = _heuristic_plan(project.tasks, velocity=20.0)
    assert len(plan.items) <= 7, (
        f"Expected <= 7 sprints from team-aware velocity, got "
        f"{len(plan.items)} (total_points={plan.total_points})"
    )
    assert plan.velocity_points_per_sprint >= 48.0
    # Goal text must not be the legacy "deliver next N tasks" string.
    legacy = [i for i in plan.items if "deliver next" in (i.goal or "")]
    assert not legacy, f"Found {len(legacy)} sprints with legacy 'deliver next' goal"


def test_sprint_planner_respects_lane_dependencies() -> None:
    """Database tasks must land before backend; backend before frontend;
    frontend before QA — never the other way around."""
    from app.agents.sprint_planner import _heuristic_plan
    from app.agents.scrum_master import _build_lane_tasks

    project = _make_project(stories=3, tasks_per_story=0)
    project.tasks = []
    for s in project.stories:
        project.tasks.extend(_build_lane_tasks(project, s))

    plan = _heuristic_plan(project.tasks, velocity=20.0)
    by_id = {t.id: t for t in project.tasks}
    sprint_index = {}
    for s in plan.items:
        for tid in s.task_ids:
            sprint_index[tid] = s.sprint_number

    for t in project.tasks:
        for dep in t.dependencies:
            if dep in sprint_index and t.id in sprint_index:
                assert sprint_index[dep] <= sprint_index[t.id], (
                    f"Task {t.title} (sprint {sprint_index[t.id]}) "
                    f"scheduled before its dep {by_id[dep].title} "
                    f"(sprint {sprint_index[dep]})"
                )


# --------------------------------------------------------------------- #
# Lane fan-out — AC subtasks
# --------------------------------------------------------------------- #


def test_lane_fanout_adds_ac_verification_subtasks() -> None:
    from app.agents.scrum_master import _build_lane_tasks

    project = _make_project(stories=1, tasks_per_story=0)
    story = project.stories[0]
    story.acceptance_criteria = [
        "Given a valid order, When the customer submits it, Then it is accepted.",
        "Given KYC fails, When the order is created, Then it is rejected.",
        "Given network is unavailable, When provisioning runs, Then it retries.",
    ]
    tasks = _build_lane_tasks(project, story)

    base_lanes = [t for t in tasks if not t.title.startswith("QA: verify ")]
    ac_subtasks = [t for t in tasks if t.title.startswith("QA: verify ")]
    assert len(base_lanes) >= 6, "Expected at least 6 base-lane tasks"
    assert len(ac_subtasks) == 3, (
        f"Expected one verification subtask per AC, got {len(ac_subtasks)}"
    )
    # Each lane task must have an estimate (the seeded heuristic).
    for t in tasks:
        assert t.estimate_points is not None and t.estimate_points > 0
        assert t.estimate_hours is not None and t.estimate_hours > 0


def test_lane_fanout_stamps_dependency_chain() -> None:
    """DB → Backend domain → Backend API → Frontend → QA wiring must
    be present so the sprint planner can respect ordering without
    the LLM."""
    from app.agents.scrum_master import _build_lane_tasks

    project = _make_project(stories=1, tasks_per_story=0)
    story = project.stories[0]
    story.acceptance_criteria = []  # focus on base lanes only
    tasks = _build_lane_tasks(project, story)
    by_title_prefix = {}
    for t in tasks:
        prefix = t.title.split(":", 1)[0]
        by_title_prefix.setdefault(prefix, []).append(t)

    db = by_title_prefix["Database"][0]
    be_domain = next(t for t in tasks if t.title.startswith("Backend: design"))
    be_api = next(t for t in tasks if t.title.startswith("Backend: implement"))
    fe_state = next(t for t in tasks if t.title.startswith("Frontend: wire"))
    qa = next(t for t in tasks if t.title.startswith("QA: test plan"))

    # Backend domain depends on DB
    assert db.id in be_domain.dependencies
    # Backend API depends on backend domain
    assert be_domain.id in be_api.dependencies
    # Frontend state depends on backend API
    assert be_api.id in fe_state.dependencies
    # QA depends on backend API (and frontend UI)
    assert be_api.id in qa.dependencies
