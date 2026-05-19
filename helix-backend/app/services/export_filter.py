"""Slice a project graph for export (e.g. human-approved rows only)."""
from __future__ import annotations

from ..models import Project


def slice_for_export(project: Project, *, approved_only: bool) -> Project:
    """Return a shallow copy with filtered stories/tasks when ``approved_only``.

    Approved tasks whose parent story is not approved are omitted so Jira
    parent links stay consistent.
    """
    if not approved_only:
        return project
    stories = [s for s in project.stories if s.approved_for_export]
    approved_story_ids = {s.id for s in stories}
    tasks = [
        t
        for t in project.tasks
        if t.approved_for_export
        and (not t.story_id or t.story_id in approved_story_ids)
    ]
    return project.model_copy(update={"stories": stories, "tasks": tasks})
