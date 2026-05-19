"""Create JIRA Epic → Stories → Sub-tasks via REST API v3."""
from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from ..config import get_settings
from ..models import Project, Severity

logger = logging.getLogger("helix.jira")


def _jira_auth_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _severity_to_jira_priority(sev: Severity) -> str:
    m = {
        Severity.LOW: "Low",
        Severity.MEDIUM: "Medium",
        Severity.HIGH: "High",
        Severity.CRITICAL: "Highest",
    }
    return m.get(sev, "Medium")


def _adf_paragraph(text: str) -> dict[str, Any]:
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


async def export_project_to_jira(project: Project) -> dict[str, Any]:
    """POST issues to JIRA. Requires JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT_KEY."""
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
        return {"ok": False, "reason": "missing_email", "detail": "JIRA Cloud needs JIRA_EMAIL with JIRA_TOKEN."}

    headers = {
        "Authorization": _jira_auth_header(email, token),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    created: list[str] = []
    errors: list[str] = []

    epic_summary = (project.summary.title if project.summary else project.name)[:240]
    epic_desc = (project.summary.objective if project.summary else project.raw_input)[:30000]

    async with httpx.AsyncClient(timeout=45.0) as client:
        epic_body = {
            "fields": {
                "project": {"key": project_key},
                "summary": epic_summary,
                "description": _adf_paragraph(epic_desc),
                "issuetype": {"name": "Epic"},
            }
        }
        epic_key = ""
        try:
            r = await client.post(f"{base}/rest/api/3/issue", json=epic_body, headers=headers)
            if r.status_code >= 400:
                errors.append(f"epic:{r.status_code}:{r.text[:500]}")
            else:
                epic_key = str(r.json().get("key") or "")
                if epic_key:
                    created.append(epic_key)
        except Exception as exc:
            logger.warning("JIRA epic failed: %s", exc)
            errors.append(str(exc))

        story_keys: dict[str, str] = {}
        for st in project.stories:
            fields: dict[str, Any] = {
                "project": {"key": project_key},
                "summary": st.title[:240],
                "description": _adf_paragraph(
                    f"As a {st.persona}, I want {st.goal}, so that {st.benefit}.\n\n"
                    + "Acceptance criteria:\n- "
                    + "\n- ".join(st.acceptance_criteria)
                ),
                "issuetype": {"name": "Story"},
            }
            if epic_key:
                if epic_link_field:
                    fields[epic_link_field] = epic_key
                else:
                    fields["parent"] = {"key": epic_key}
            try:
                r2 = await client.post(f"{base}/rest/api/3/issue", json={"fields": fields}, headers=headers)
                if r2.status_code >= 400:
                    errors.append(f"story:{st.title[:40]}:{r2.status_code}")
                else:
                    sk = str(r2.json().get("key") or "")
                    if sk:
                        story_keys[st.id] = sk
                        created.append(sk)
            except Exception as exc:
                errors.append(f"story:{exc}")

        for t in project.tasks:
            parent_key = story_keys.get(t.story_id or "") or epic_key
            if not parent_key:
                errors.append(f"task_skip_no_parent:{t.id}")
                continue
            points = t.estimate_points
            sub_fields: dict[str, Any] = {
                "project": {"key": project_key},
                "summary": t.title[:240],
                "description": _adf_paragraph(
                    f"{t.description}\n\nType: {t.type.value}\nPriority: {t.priority.value}\n"
                    f"Story points (Helix): {points if points is not None else '—'}"
                ),
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": parent_key},
                "priority": {"name": _severity_to_jira_priority(t.priority)},
            }
            try:
                r3 = await client.post(
                    f"{base}/rest/api/3/issue",
                    json={"fields": sub_fields},
                    headers=headers,
                )
                if r3.status_code >= 400:
                    errors.append(f"subtask:{t.title[:30]}:{r3.status_code}")
                else:
                    tk = str(r3.json().get("key") or "")
                    if tk:
                        created.append(tk)
            except Exception as exc:
                errors.append(f"subtask:{exc}")

    return {
        "ok": not errors and bool(created),
        "created_keys": created,
        "errors": errors,
        "epic_key": epic_key or None,
    }
