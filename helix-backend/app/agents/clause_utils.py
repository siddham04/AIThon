"""Validate traceability fields against the project clause graph."""
from __future__ import annotations

import logging
from typing import Iterable, Set

from ..models import Project

logger = logging.getLogger("helix.agents")


def valid_clause_ids(project: Project) -> Set[str]:
    return {c.id for c in (project.source_clauses or []) if getattr(c, "id", None)}


def valid_story_ids(project: Project) -> Set[str]:
    return {s.id for s in (project.stories or []) if getattr(s, "id", None)}


def filter_clause_ids(
    project: Project,
    clause_ids: Iterable[str] | None,
    *,
    agent: str,
    context: str = "",
) -> list[str]:
    """Keep only clause ids that exist on the project; log drops."""
    allowed = valid_clause_ids(project)
    if not allowed:
        return list(clause_ids or [])
    kept: list[str] = []
    for cid in clause_ids or []:
        raw = str(cid or "").strip()
        if not raw:
            continue
        if raw in allowed:
            kept.append(raw)
        else:
            logger.warning(
                "%s dropped unknown source_clause_id %r%s",
                agent,
                raw,
                f" ({context})" if context else "",
            )
    return kept


def resolve_story_id(
    project: Project,
    story_id: str | None,
    *,
    agent: str,
    title: str = "",
) -> str | None:
    """Return story_id if valid; log and return None otherwise."""
    allowed = valid_story_ids(project)
    if not allowed:
        return story_id
    sid = str(story_id or "").strip()
    if not sid:
        logger.warning("%s skipped task/test — missing story_id (%s)", agent, title[:60])
        return None
    if sid in allowed:
        return sid
    logger.warning(
        "%s skipped row — story_id %r not in project (%s)",
        agent,
        sid,
        title[:60],
    )
    return None
