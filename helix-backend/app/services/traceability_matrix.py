"""Traceability Matrix.

Walk the project artifacts and emit a row per requirement clause showing
the full chain:

    Requirement → Story → Task → Test Case

Example tree::

    REQ-001
     ├── US-001
     ├── TASK-001
     └── TC-001

Coverage statistics tell the user where the chain is broken.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..models import (
    Project,
    TraceabilityCoverage,
    TraceabilityGraph,
    TraceabilityGraphEdge,
    TraceabilityGraphNode,
    TraceabilityMatrix,
    TraceabilityRow,
)

NODE_W = 172.0
NODE_H = 50.0
ROW_INNER_GAP = 22.0
REQ_BLOCK_GAP = 36.0
LANE_X = {
    "requirement": 48.0,
    "story": 268.0,
    "task": 488.0,
    "test": 708.0,
}
def _short(text: str, n: int = 140) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _label(prefix: str, index: int) -> str:
    return f"{prefix}-{index:03d}"


def _labels_for_ids(ids: List[str], prefix: str) -> List[str]:
    return [_label(prefix, i + 1) for i in range(len(ids))]


def format_row_tree(
    req_label: str,
    story_labels: List[str],
    task_labels: List[str],
    test_labels: List[str],
) -> str:
    """Single requirement chain as ASCII tree."""
    lines = [req_label]
    children: List[Tuple[str, str]] = []
    for lbl in story_labels:
        children.append(("story", lbl))
    for lbl in task_labels:
        children.append(("task", lbl))
    for lbl in test_labels:
        children.append(("test", lbl))

    if not children:
        lines.append(" └── (no downstream links)")
        return "\n".join(lines)

    for i, (_kind, lbl) in enumerate(children):
        branch = "└──" if i == len(children) - 1 else "├──"
        lines.append(f" {branch} {lbl}")
    return "\n".join(lines)


def build_traceability_graph(matrix: TraceabilityMatrix) -> TraceabilityGraph:
    """Layout interactive graph from matrix rows — four lanes left to right."""
    nodes: List[TraceabilityGraphNode] = []
    edges: List[TraceabilityGraphEdge] = []
    y_cursor = 56.0
    max_y = 0.0

    for row_index, row in enumerate(matrix.rows):
        block_start = y_cursor
        row_nodes: dict[str, List[str]] = {
            "requirement": [],
            "story": [],
            "task": [],
            "test": [],
        }

        req_id = f"req:{row.requirement_id}"
        nodes.append(
            TraceabilityGraphNode(
                id=req_id,
                label=row.requirement_label or "REQ",
                title=row.requirement_text,
                kind="requirement",
                row_index=row_index,
                coverage=row.coverage,
                x=LANE_X["requirement"],
                y=y_cursor,
            )
        )
        row_nodes["requirement"].append(req_id)
        local_y = y_cursor

        def add_items(kind: str, labels: List[str], titles: List[str], ids: List[str]):
            nonlocal local_y, max_y
            prefix = {"story": "us", "task": "task", "test": "tc"}[kind]
            for i, lbl in enumerate(labels):
                nid = f"{prefix}:{row.requirement_id}:{i}"
                title = titles[i] if i < len(titles) else lbl
                artifact_id = ids[i] if i < len(ids) else lbl
                nodes.append(
                    TraceabilityGraphNode(
                        id=nid,
                        label=lbl,
                        title=title,
                        kind=kind,
                        row_index=row_index,
                        coverage=row.coverage,
                        x=LANE_X[kind],
                        y=local_y,
                    )
                )
                row_nodes[kind].append(nid)
                local_y += NODE_H + ROW_INNER_GAP
                max_y = max(max_y, local_y)

        add_items("story", row.story_labels, row.story_titles, row.story_ids)
        add_items("task", row.task_labels, row.task_titles, row.task_ids)
        add_items("test", row.test_labels, row.test_titles, row.test_ids)

        block_height = max(NODE_H, local_y - block_start)
        y_cursor = block_start + block_height + REQ_BLOCK_GAP

        req_nid = row_nodes["requirement"][0]
        stories = row_nodes["story"]
        tasks = row_nodes["task"]
        tests = row_nodes["test"]

        for sn in stories:
            edges.append(TraceabilityGraphEdge(source=req_nid, target=sn))
        for i, sn in enumerate(stories):
            if i < len(tasks):
                edges.append(
                    TraceabilityGraphEdge(source=sn, target=tasks[i], primary=i == 0)
                )
        for i, tn in enumerate(tasks):
            if not stories:
                edges.append(TraceabilityGraphEdge(source=req_nid, target=tn))
            if i < len(tests):
                edges.append(
                    TraceabilityGraphEdge(source=tn, target=tests[i], primary=i == 0)
                )
        for xn in tests:
            if not tasks and not stories:
                edges.append(TraceabilityGraphEdge(source=req_nid, target=xn))

        if stories and tasks and tests:
            edges.append(
                TraceabilityGraphEdge(
                    source=stories[0],
                    target=tasks[0],
                    primary=True,
                )
            )
            edges.append(
                TraceabilityGraphEdge(
                    source=tasks[0],
                    target=tests[0],
                    primary=True,
                )
            )

    height = max(480.0, max_y + 80.0)
    return TraceabilityGraph(
        nodes=nodes,
        edges=edges,
        width=920.0,
        height=height,
    )


def build_demo_traceability_graph() -> TraceabilityGraph:
    """Judge demo — two full chains when pipeline not run."""
    demo_rows = [
        TraceabilityRow(
            requirement_id="demo-1",
            requirement_label="REQ-001",
            requirement_text="User can log in with email and password",
            story_labels=["US-001"],
            story_titles=["As a user I can log in"],
            task_labels=["TASK-001"],
            task_titles=["Implement login API"],
            test_labels=["TC-001"],
            test_titles=["Verify valid credentials return JWT"],
            coverage=100,
        ),
        TraceabilityRow(
            requirement_id="demo-2",
            requirement_label="REQ-002",
            requirement_text="Password reset via secure email link",
            story_labels=["US-002"],
            story_titles=["As a user I can reset password"],
            task_labels=["TASK-002"],
            task_titles=["Password reset flow"],
            test_labels=["TC-002"],
            test_titles=["Expired token rejected"],
            coverage=100,
        ),
    ]
    matrix = TraceabilityMatrix(rows=demo_rows, coverage=TraceabilityCoverage(total_requirements=2))
    return build_traceability_graph(matrix)


def build_traceability(project: Project) -> TraceabilityMatrix:
    if not project.source_clauses:
        return TraceabilityMatrix(summary="No source clauses to trace.")

    stories_by_clause: Dict[str, List] = {}
    for story in project.stories or []:
        for cid in (story.source_clause_ids or []):
            stories_by_clause.setdefault(cid, []).append(story)

    tasks_by_clause: Dict[str, List] = {}
    tasks_by_story: Dict[str, List] = {}
    for task in project.tasks or []:
        for cid in (task.source_clause_ids or []):
            tasks_by_clause.setdefault(cid, []).append(task)
        if getattr(task, "story_id", None):
            tasks_by_story.setdefault(task.story_id, []).append(task)

    tests_by_clause: Dict[str, List] = {}
    tests_by_story: Dict[str, List] = {}
    tests_by_task: Dict[str, List] = {}
    for test in project.test_cases or []:
        for cid in (test.source_clause_ids or []):
            tests_by_clause.setdefault(cid, []).append(test)
        if getattr(test, "story_id", None):
            tests_by_story.setdefault(test.story_id, []).append(test)
        if getattr(test, "task_id", None):
            tests_by_task.setdefault(test.task_id, []).append(test)

    components_by_clause: Dict[str, List[str]] = {}
    if project.impact_report:
        for comp in project.impact_report.components or []:
            comp_name = getattr(comp, "component", "") or getattr(comp, "name", "")
            if not comp_name:
                continue
            for cid in (project.source_clauses or []):
                if comp_name.lower() in (cid.text or "").lower():
                    components_by_clause.setdefault(cid.id, []).append(comp_name)

    rows: List[TraceabilityRow] = []
    tree_blocks: List[str] = []

    for req_index, clause in enumerate(project.source_clauses):
        req_label = _label("REQ", req_index + 1)

        stories = stories_by_clause.get(clause.id, [])
        story_ids = [s.id for s in stories]
        story_titles = [s.title for s in stories]
        story_labels = _labels_for_ids(story_ids, "US")

        seen_task_ids: set[str] = set()
        ordered_tasks = []
        for t in tasks_by_clause.get(clause.id, []):
            if t.id not in seen_task_ids:
                seen_task_ids.add(t.id)
                ordered_tasks.append(t)
        for s in stories:
            for t in tasks_by_story.get(s.id, []):
                if t.id not in seen_task_ids:
                    seen_task_ids.add(t.id)
                    ordered_tasks.append(t)
        task_ids = [t.id for t in ordered_tasks]
        task_titles = [t.title for t in ordered_tasks]
        task_labels = _labels_for_ids(task_ids, "TASK")

        seen_test_ids: set[str] = set()
        ordered_tests = []
        for tc in tests_by_clause.get(clause.id, []):
            if tc.id not in seen_test_ids:
                seen_test_ids.add(tc.id)
                ordered_tests.append(tc)
        for s in stories:
            for tc in tests_by_story.get(s.id, []):
                if tc.id not in seen_test_ids:
                    seen_test_ids.add(tc.id)
                    ordered_tests.append(tc)
        for t in ordered_tasks:
            for tc in tests_by_task.get(t.id, []):
                if tc.id not in seen_test_ids:
                    seen_test_ids.add(tc.id)
                    ordered_tests.append(tc)
        test_ids = [tc.id for tc in ordered_tests]
        test_titles = [tc.title for tc in ordered_tests]
        test_labels = _labels_for_ids(test_ids, "TC")

        components = components_by_clause.get(clause.id, [])

        achieved = sum([bool(stories), bool(ordered_tasks), bool(ordered_tests), bool(components)])
        coverage = int(round(100 * achieved / 4))

        row_tree = format_row_tree(req_label, story_labels, task_labels, test_labels)
        tree_blocks.append(row_tree)

        rows.append(
            TraceabilityRow(
                requirement_id=clause.id,
                requirement_label=req_label,
                requirement_text=_short(clause.text),
                story_ids=story_ids,
                story_labels=story_labels,
                story_titles=[_short(t, 80) for t in story_titles],
                task_ids=task_ids,
                task_labels=task_labels,
                task_titles=[_short(t, 80) for t in task_titles],
                test_ids=test_ids,
                test_labels=test_labels,
                test_titles=[_short(t, 80) for t in test_titles],
                component_names=components,
                tree_text=row_tree,
                coverage=coverage,
            )
        )

    total = len(rows) or 1
    coverage = TraceabilityCoverage(
        requirements_with_stories=sum(1 for r in rows if r.story_ids),
        requirements_with_tasks=sum(1 for r in rows if r.task_ids),
        requirements_with_tests=sum(1 for r in rows if r.test_ids),
        requirements_with_components=sum(1 for r in rows if r.component_names),
        total_requirements=total,
    )

    pct_test = int(round(100 * coverage.requirements_with_tests / total))
    summary = (
        f"{total} requirement{'s' if total != 1 else ''} traced — "
        f"{pct_test}% have at least one test, "
        f"{coverage.requirements_with_components} link to a known component."
    )

    matrix = TraceabilityMatrix(
        rows=rows,
        coverage=coverage,
        tree_text="\n\n".join(tree_blocks),
        summary=summary,
    )
    matrix.graph = build_traceability_graph(matrix)
    return matrix


def to_csv(matrix: TraceabilityMatrix) -> str:
    """Render a flat CSV (one row per requirement)."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Requirement ID",
        "Requirement Label",
        "Requirement",
        "Story Labels",
        "Story IDs",
        "Stories",
        "Task Labels",
        "Task IDs",
        "Tasks",
        "Test Labels",
        "Test IDs",
        "Tests",
        "Components",
        "Coverage %",
    ])
    for r in matrix.rows:
        writer.writerow([
            r.requirement_id,
            r.requirement_label,
            r.requirement_text,
            "; ".join(r.story_labels),
            "; ".join(r.story_ids),
            "; ".join(r.story_titles),
            "; ".join(r.task_labels),
            "; ".join(r.task_ids),
            "; ".join(r.task_titles),
            "; ".join(r.test_labels),
            "; ".join(r.test_ids),
            "; ".join(r.test_titles),
            "; ".join(r.component_names),
            r.coverage,
        ])
    return buf.getvalue()


__all__ = [
    "build_traceability",
    "build_traceability_graph",
    "build_demo_traceability_graph",
    "format_row_tree",
    "to_csv",
]
