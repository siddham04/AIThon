"""Backlog export — Jira-importable CSV + Jira REST 4-level push."""
from __future__ import annotations

import base64
import csv
import io
import logging
from typing import Any, Dict, List

import httpx

from ..config import get_settings
from ..models import JiraBacklog, Severity

logger = logging.getLogger("helix.backlog_export")


# ---------- CSV ---------------------------------------------------------- #


_CSV_FIELDS = (
    "Issue Type",
    "Issue ID",
    "Summary",
    "Description",
    "Parent",
    "Priority",
    "Story Points",
    "Estimate (h)",
    "Labels",
    "Helix ID",
)


def _priority_label(sev: Severity) -> str:
    return {
        Severity.LOW: "Low",
        Severity.MEDIUM: "Medium",
        Severity.HIGH: "High",
        Severity.CRITICAL: "Highest",
    }.get(sev, "Medium")


def to_jira_csv(backlog: JiraBacklog) -> str:
    """Render a Jira-importable CSV with all four levels.

    Issue Type column is one of: Epic | Story | Task | Sub-task. The
    Parent column links each row to the right parent so Jira's CSV
    importer can build the hierarchy in one shot.
    """
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(_CSV_FIELDS)

    # Epic (one row)
    w.writerow(
        [
            "Epic",
            backlog.epic.id,
            backlog.epic.title,
            backlog.epic.description,
            "",
            "Medium",
            "",
            "",
            ", ".join(backlog.epic.labels),
            backlog.epic.id,
        ]
    )

    # Stories — parent = epic
    for s in backlog.stories:
        as_a = (
            f"As a {s.persona}, I want {s.goal}, so that {s.benefit}.\n\n"
            "Acceptance criteria:\n"
            + "\n".join(f"- {c}" for c in (s.acceptance_criteria or []))
        )
        w.writerow(
            [
                "Story",
                s.id,
                s.title,
                as_a,
                backlog.epic.id,
                "Medium",
                "",
                "",
                "",
                s.id,
            ]
        )

    # Tasks — parent = story (or epic if orphaned)
    for t in backlog.tasks:
        priority = (
            _priority_label(t.priority)
            if isinstance(t.priority, Severity)
            else "Medium"
        )
        w.writerow(
            [
                "Task",
                t.id,
                t.title,
                t.description,
                t.story_id or backlog.epic.id,
                priority,
                t.estimate_points if t.estimate_points is not None else "",
                t.estimate_hours if t.estimate_hours is not None else "",
                ", ".join(t.skills),
                t.id,
            ]
        )

    # Subtasks — parent = task
    for st in backlog.subtasks:
        w.writerow(
            [
                "Sub-task",
                st.id,
                st.title,
                st.description,
                st.parent_task_id,
                "Medium",
                "",
                st.estimate_hours if st.estimate_hours is not None else "",
                ", ".join(st.skills),
                st.id,
            ]
        )

    return buf.getvalue()


_ADO_FIELDS = (
    "Work Item Type",
    "Title",
    "Description",
    "Parent",
    "Priority",
    "Story Points",
    "Remaining Work",
    "Tags",
    "Helix ID",
)


def to_azure_devops_csv(backlog: JiraBacklog) -> str:
    """Render an Azure DevOps bulk-import friendly CSV.

    Hierarchy: Epic → User Story → Task → Sub-task (maps to ADO work item types).
    """
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(_ADO_FIELDS)

    w.writerow(
        [
            "Epic",
            backlog.epic.title,
            backlog.epic.description,
            "",
            "2",
            "",
            "",
            ", ".join(backlog.epic.labels),
            backlog.epic.id,
        ]
    )

    for s in backlog.stories:
        as_a = (
            f"As a {s.persona}, I want {s.goal}, so that {s.benefit}.\n\n"
            "Acceptance criteria:\n"
            + "\n".join(f"- {c}" for c in (s.acceptance_criteria or []))
        )
        w.writerow(
            [
                "User Story",
                s.title,
                as_a,
                backlog.epic.id,
                "2",
                "",
                "",
                "",
                s.id,
            ]
        )

    for t in backlog.tasks:
        priority = (
            _priority_label(t.priority)
            if isinstance(t.priority, Severity)
            else "2"
        )
        ado_priority = {"Highest": "1", "High": "2", "Medium": "2", "Low": "3"}.get(
            priority, "2"
        )
        w.writerow(
            [
                "Task",
                t.title,
                t.description,
                t.story_id or backlog.epic.id,
                ado_priority,
                t.estimate_points if t.estimate_points is not None else "",
                t.estimate_hours if t.estimate_hours is not None else "",
                ", ".join(t.skills),
                t.id,
            ]
        )

    for st in backlog.subtasks:
        w.writerow(
            [
                "Sub-task",
                st.title,
                st.description,
                st.parent_task_id,
                "2",
                "",
                st.estimate_hours if st.estimate_hours is not None else "",
                ", ".join(st.skills),
                st.id,
            ]
        )

    return buf.getvalue()


# ---------- Jira REST push ---------------------------------------------- #


def _auth_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _adf(text: str) -> Dict[str, Any]:
    safe = (text or "").strip() or "—"
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": safe[:32000]}],
            }
        ],
    }


async def export_backlog_to_jira(backlog: JiraBacklog) -> Dict[str, Any]:
    """Push the 4-level backlog to Jira REST: Epic → Story → Task → Sub-task.

    The Epic / Story / Task / Sub-task issue types must exist in the
    target Jira project (the standard Software Cloud config already has
    all four).
    """
    s = get_settings()
    base = (getattr(s, "jira_base_url", None) or "").strip().rstrip("/")
    email = (getattr(s, "jira_email", None) or "").strip()
    token = (getattr(s, "jira_token", None) or "").strip()
    project_key = (getattr(s, "jira_project_key", None) or "").strip()
    epic_link_field = (getattr(s, "jira_epic_link_field", None) or "").strip()

    if not base or not token or not project_key:
        return {
            "ok": False,
            "reason": "missing_config",
            "detail": "Set JIRA_BASE_URL, JIRA_TOKEN, JIRA_PROJECT_KEY (and JIRA_EMAIL for Cloud).",
        }
    if not email:
        return {
            "ok": False,
            "reason": "missing_email",
            "detail": "JIRA Cloud needs JIRA_EMAIL with JIRA_TOKEN.",
        }

    headers = {
        "Authorization": _auth_header(email, token),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    created: List[str] = []
    errors: List[str] = []

    async with httpx.AsyncClient(timeout=45.0) as client:

        # 1. Epic
        epic_body = {
            "fields": {
                "project": {"key": project_key},
                "summary": backlog.epic.title[:240],
                "description": _adf(backlog.epic.description),
                "issuetype": {"name": "Epic"},
            }
        }
        if backlog.epic.labels:
            epic_body["fields"]["labels"] = list(backlog.epic.labels)
        epic_key = ""
        try:
            r = await client.post(
                f"{base}/rest/api/3/issue", json=epic_body, headers=headers
            )
            if r.status_code >= 400:
                errors.append(f"epic:{r.status_code}:{r.text[:300]}")
            else:
                epic_key = str(r.json().get("key") or "")
                if epic_key:
                    backlog.epic.jira_key = epic_key
                    created.append(epic_key)
        except Exception as exc:
            errors.append(f"epic:{exc}")

        # 2. Stories → parent = Epic
        story_keys: Dict[str, str] = {}
        for st in backlog.stories:
            fields: Dict[str, Any] = {
                "project": {"key": project_key},
                "summary": st.title[:240],
                "description": _adf(
                    f"As a {st.persona}, I want {st.goal}, so that {st.benefit}.\n\n"
                    + "Acceptance criteria:\n- "
                    + "\n- ".join(st.acceptance_criteria or [])
                ),
                "issuetype": {"name": "Story"},
            }
            if epic_key:
                if epic_link_field:
                    fields[epic_link_field] = epic_key
                else:
                    fields["parent"] = {"key": epic_key}
            try:
                r2 = await client.post(
                    f"{base}/rest/api/3/issue",
                    json={"fields": fields},
                    headers=headers,
                )
                if r2.status_code >= 400:
                    errors.append(f"story:{st.title[:30]}:{r2.status_code}")
                else:
                    sk = str(r2.json().get("key") or "")
                    if sk:
                        story_keys[st.id] = sk
                        st.jira_key = sk
                        created.append(sk)
            except Exception as exc:
                errors.append(f"story:{exc}")

        # 3. Tasks → parent = Story (or Epic if orphan)
        task_keys: Dict[str, str] = {}
        for t in backlog.tasks:
            parent = story_keys.get(t.story_id or "") or epic_key
            if not parent:
                errors.append(f"task_skip_no_parent:{t.id}")
                continue
            fields: Dict[str, Any] = {
                "project": {"key": project_key},
                "summary": t.title[:240],
                "description": _adf(
                    f"{t.description}\n\nType: {t.type.value}\nPriority: {t.priority.value}\n"
                    f"Story points (Helix): {t.estimate_points if t.estimate_points is not None else '—'}"
                ),
                "issuetype": {"name": "Task"},
                "parent": {"key": parent},
                "priority": {"name": _priority_label(t.priority)},
            }
            try:
                r3 = await client.post(
                    f"{base}/rest/api/3/issue",
                    json={"fields": fields},
                    headers=headers,
                )
                if r3.status_code >= 400:
                    errors.append(f"task:{t.title[:30]}:{r3.status_code}")
                else:
                    tk = str(r3.json().get("key") or "")
                    if tk:
                        task_keys[t.id] = tk
                        t.jira_key = tk
                        created.append(tk)
            except Exception as exc:
                errors.append(f"task:{exc}")

        # 4. Sub-tasks → parent = Task
        for sub in backlog.subtasks:
            parent = task_keys.get(sub.parent_task_id)
            if not parent:
                errors.append(f"subtask_skip_no_parent:{sub.id}")
                continue
            fields = {
                "project": {"key": project_key},
                "summary": sub.title[:240],
                "description": _adf(sub.description),
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": parent},
            }
            try:
                r4 = await client.post(
                    f"{base}/rest/api/3/issue",
                    json={"fields": fields},
                    headers=headers,
                )
                if r4.status_code >= 400:
                    errors.append(f"subtask:{sub.title[:30]}:{r4.status_code}")
                else:
                    sk = str(r4.json().get("key") or "")
                    if sk:
                        sub.jira_key = sk
                        created.append(sk)
            except Exception as exc:
                errors.append(f"subtask:{exc}")

    return {
        "ok": not errors and bool(created),
        "epic_key": backlog.epic.jira_key,
        "created_keys": created,
        "errors": errors,
        "summary": (
            f"Pushed {len(created)} issues to Jira "
            f"({1 if backlog.epic.jira_key else 0} epic · "
            f"{sum(1 for s in backlog.stories if s.jira_key)} stories · "
            f"{sum(1 for t in backlog.tasks if t.jira_key)} tasks · "
            f"{sum(1 for s in backlog.subtasks if s.jira_key)} subtasks)."
        ),
    }
