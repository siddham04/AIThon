"""Export project artifacts to formats compatible with PM tools."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from ..models import Project


def markdown_audit_footer(*, user_label: str, model_label: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "\n\n---\n\n"
        f"_Generated at {ts} · model {model_label} · user {user_label}_\n"
    )


def export_markdown(
    p: Project,
    *,
    audit: Tuple[str, str] | None = None,
) -> str:
    lines: List[str] = []
    s = p.summary
    lines.append(f"# {s.title if s else p.name}")
    lines.append("")
    if s:
        lines.append(f"_{s.one_liner}_")
        lines.append("")
        lines.append("## Objective")
        lines.append(s.objective)
        lines.append("")
        if s.in_scope:
            lines.append("## In scope")
            lines.extend(f"- {x}" for x in s.in_scope)
            lines.append("")
        if s.out_of_scope:
            lines.append("## Out of scope")
            lines.extend(f"- {x}" for x in s.out_of_scope)
            lines.append("")
        if s.success_metrics:
            lines.append("## Success metrics")
            lines.extend(f"- {x}" for x in s.success_metrics)
            lines.append("")

    if p.stories:
        lines.append("## User Stories")
        for st in p.stories:
            lines.append(f"### {st.title}  `{st.id}`")
            lines.append(
                f"**As a** {st.persona}, **I want** {st.goal}, **so that** {st.benefit}."
            )
            if st.acceptance_criteria:
                lines.append("")
                lines.append("**Acceptance criteria:**")
                lines.extend(f"- {a}" for a in st.acceptance_criteria)
            lines.append("")

    if p.tasks:
        lines.append("## Engineering Tasks")
        for t in p.tasks:
            est = (
                f" — {t.estimate_points}sp / {t.estimate_hours}h"
                if t.estimate_points
                else ""
            )
            lines.append(f"- **[{t.type.value}]** {t.title} `{t.id}`{est}")
            if t.description:
                lines.append(f"  - {t.description}")
        lines.append("")

    if p.test_cases:
        lines.append("## Test Plan")
        for tc in p.test_cases:
            lines.append(f"- **[{tc.type.value}]** {tc.title} `{tc.id}`")
            lines.append(f"  - Given {tc.given}")
            lines.append(f"  - When {tc.when}")
            lines.append(f"  - Then {tc.then}")
        lines.append("")

    if p.ambiguities:
        lines.append("## Ambiguities")
        for a in p.ambiguities:
            lines.append(
                f"- **[{a.severity.value}/{a.kind.value}]** {a.explanation}"
            )
            lines.append(f"  - Excerpt: _{a.excerpt}_")
            lines.append(f"  - Ask: {a.suggested_question}")
        lines.append("")

    if p.risks:
        lines.append("## Risks")
        for r in p.risks:
            lines.append(f"- **[{r.severity.value}/{r.category.value}]** {r.title}")
            lines.append(f"  - {r.description}")
            lines.append(f"  - Mitigation: {r.mitigation}")
        lines.append("")

    body = "\n".join(lines)
    if audit:
        u, m = audit
        body += markdown_audit_footer(user_label=u, model_label=m)
    return body


def export_csv(p: Project) -> str:
    """Generic CSV of tasks for any tool."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "task_id", "title", "type", "priority", "story_id",
        "estimate_points", "estimate_hours", "confidence",
        "skills", "description", "approved_for_export",
    ])
    for t in p.tasks:
        w.writerow([
            t.id, t.title, t.type.value, t.priority.value, t.story_id or "",
            t.estimate_points or "", t.estimate_hours or "",
            t.confidence or "",
            ";".join(t.skills),
            t.description.replace("\n", " "),
            "yes" if t.approved_for_export else "no",
        ])
    return buf.getvalue()


def export_jira_csv(p: Project) -> str:
    """Jira CSV import format with Epic / Story / Task hierarchy."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "Issue Type", "Summary", "Description", "Priority",
        "Story Points", "Original Estimate", "Labels", "Epic Link",
        "Helix approved",
    ])
    epic_summary = (p.summary.title if p.summary else p.name)
    w.writerow(["Epic", epic_summary,
                p.summary.objective if p.summary else "",
                "Medium", "", "", "helix", "", "yes"])
    story_lookup = {s.id: s.title for s in p.stories}
    for s in p.stories:
        w.writerow([
            "Story", s.title,
            f"As a {s.persona}, I want {s.goal}, so that {s.benefit}.\n\nAC:\n- "
            + "\n- ".join(s.acceptance_criteria),
            "Medium", "", "", "helix", epic_summary,
            "yes" if s.approved_for_export else "no",
        ])
    for t in p.tasks:
        story_title = story_lookup.get(t.story_id or "", epic_summary)
        seconds = int((t.estimate_hours or 0) * 3600)
        w.writerow([
            "Task", t.title, t.description,
            t.priority.value.capitalize(),
            t.estimate_points or "",
            f"{seconds}s" if seconds else "",
            ";".join(["helix", t.type.value]),
            story_title,
            "yes" if t.approved_for_export else "no",
        ])
    return buf.getvalue()


def export_azure_devops_json(p: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in p.stories:
        out.append({
            "workItemType": "User Story",
            "id": s.id,
            "title": s.title,
            "description": (
                f"As a {s.persona}, I want {s.goal}, so that {s.benefit}."
            ),
            "acceptanceCriteria": s.acceptance_criteria,
            "tags": ["helix"],
        })
    for t in p.tasks:
        out.append({
            "workItemType": "Task",
            "id": t.id,
            "parent": t.story_id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority.value,
            "originalEstimateHours": t.estimate_hours,
            "storyPoints": t.estimate_points,
            "tags": ["helix", t.type.value, *t.skills],
        })
    return out


def export_github_issues_json(p: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in p.stories:
        body = (
            f"**As a** {s.persona}, **I want** {s.goal}, **so that** {s.benefit}.\n\n"
            "**Acceptance criteria:**\n"
            + "\n".join(f"- [ ] {a}" for a in s.acceptance_criteria)
            + f"\n\n_Helix story id: `{s.id}`_"
        )
        out.append({
            "title": f"[Story] {s.title}",
            "body": body,
            "labels": ["helix", "user-story"],
        })
    for t in p.tasks:
        body = (
            f"{t.description}\n\n"
            f"- Type: `{t.type.value}`\n"
            f"- Priority: `{t.priority.value}`\n"
            f"- Estimate: {t.estimate_points or '?'} sp / {t.estimate_hours or '?'} h\n"
            f"- Skills: {', '.join(t.skills) or '—'}\n\n"
            f"_Helix task id: `{t.id}` (story `{t.story_id or '—'}`)_"
        )
        labels = ["helix", t.type.value, f"priority:{t.priority.value}"]
        out.append({"title": t.title, "body": body, "labels": labels})
    return out
