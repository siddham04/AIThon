"""Create GitHub issues from Helix project artifacts."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_settings
from ..models import Project, Severity

logger = logging.getLogger("helix.github")


def _priority_label(p: Severity) -> str:
    return f"priority:{p.value}"


async def export_project_to_github_issues(project: Project) -> dict[str, Any]:
    """POST /repos/{owner}/{repo}/issues for each story and task."""
    s = get_settings()
    token = (getattr(s, "github_token", None) or "").strip()
    repo = (getattr(s, "github_repo", None) or "").strip()
    if not token or not repo or "/" not in repo:
        return {
            "ok": False,
            "reason": "missing_config",
            "detail": "Set GITHUB_TOKEN and GITHUB_REPO (owner/name).",
        }

    owner, name = repo.split("/", 1)
    base = "https://api.github.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    urls: list[str] = []
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=45.0) as client:
        for st in project.stories:
            body = (
                f"**As a** {st.persona}, **I want** {st.goal}, **so that** {st.benefit}.\n\n"
                "**Acceptance criteria:**\n"
                + "\n".join(f"- [ ] {a}" for a in st.acceptance_criteria)
                + f"\n\n_Helix `{st.id}`_"
            )
            payload = {
                "title": f"[Story] {st.title}"[:240],
                "body": body[:65000],
                "labels": ["helix", "user-story"],
            }
            try:
                r = await client.post(
                    f"{base}/repos/{owner}/{name}/issues",
                    json=payload,
                    headers=headers,
                )
                if r.status_code >= 400:
                    errors.append(f"story:{r.status_code}:{r.text[:200]}")
                else:
                    urls.append(str(r.json().get("html_url") or ""))
            except Exception as exc:
                logger.warning("GitHub story issue failed: %s", exc)
                errors.append(str(exc))

        for t in project.tasks:
            body = (
                f"{t.description}\n\n"
                f"- Type: `{t.type.value}`\n"
                f"- Estimate: {t.estimate_points or '?'} sp / {t.estimate_hours or '?'} h\n"
                f"- Skills: {', '.join(t.skills) or '—'}\n\n"
                f"_Helix `{t.id}` (story `{t.story_id or '—'}`)_"
            )
            labels = ["helix", t.type.value, _priority_label(t.priority)]
            payload = {
                "title": t.title[:240],
                "body": body[:65000],
                "labels": labels,
            }
            try:
                r = await client.post(
                    f"{base}/repos/{owner}/{name}/issues",
                    json=payload,
                    headers=headers,
                )
                if r.status_code >= 400:
                    errors.append(f"task:{r.status_code}:{r.text[:200]}")
                else:
                    urls.append(str(r.json().get("html_url") or ""))
            except Exception as exc:
                errors.append(str(exc))

    return {
        "ok": not errors and bool(urls),
        "issue_urls": [u for u in urls if u],
        "errors": errors,
    }
