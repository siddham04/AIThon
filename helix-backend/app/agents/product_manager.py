"""Product Manager Agent — backlog shaping.

Second agent in the Multi-Agent SDLC Pipeline. Turns the Requirement Analyst
intake into delivery-ready product artifacts:

    - Epic (one initiative container)
    - User stories (INVEST)
    - Acceptance criteria per story

Does NOT create engineering tasks — the Scrum Master Agent owns that.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..models import BacklogEpic, Project, RequirementSummary, UserStory
from ..services.ingestion import render_clauses
from ..services.story_voice import normalize_voice
from .base import Agent
from .clause_utils import filter_clause_ids

logger = logging.getLogger("helix.product_manager")


SYSTEM = """You are a Senior Product Manager on an enterprise delivery team.

You receive a cleaned requirement intake (features, actors, business rules)
and the raw source clauses. Your job is to shape the PRODUCT backlog:

  1. One EPIC that frames the initiative (title, description, 2-4 key results).
  2. User STORIES in INVEST form — each with persona, goal, benefit, and
     3-6 concrete acceptance criteria (Given/When/Then or "The system shall…").

Ground everything in the intake. Do not invent scope beyond what was stated.
Every story must cite source_clause_ids it derives from.
Do NOT output engineering tasks — only epics and stories.
""".strip()


SCHEMA = """{
  "epic": {
    "title": "string",
    "description": "string",
    "key_results": ["string — measurable outcomes for the epic"]
  },
  "product_title": "string — short initiative name",
  "one_liner": "string",
  "objective": "string — 2-3 sentences",
  "stories": [
    {
      "title": "string",
      "persona": "string",
      "goal": "string",
      "benefit": "string",
      "acceptance_criteria": ["string"],
      "source_clause_ids": ["clause_xxxx"]
    }
  ]
}"""


def _intake_block(project: Project) -> str:
    rb = project.requirement_brief
    if rb is None:
        return ""
    lines = [
        "Requirement Analyst intake:",
        f"  Summary: {rb.cleaned_summary}",
    ]
    if rb.features:
        lines.append("  Features:")
        for f in rb.features:
            lines.append(f"    - {f.name}: {f.description}")
    if rb.actors:
        lines.append("  Actors:")
        for a in rb.actors:
            lines.append(f"    - {a.name} ({a.role})")
    if rb.business_rules:
        lines.append("  Business rules:")
        for r in rb.business_rules:
            lines.append(f"    - {r.description}")
    return "\n".join(lines) + "\n\n"


class ProductManagerAgent(Agent):
    name = "product_manager"
    stage = "Product Manager"

    async def run(self, project: Project) -> Dict[str, Any]:
        user = (
            f"{_intake_block(project)}"
            "Source clauses:\n\n"
            f"{render_clauses(project.source_clauses)}\n\n"
            "Produce the epic and user stories with acceptance criteria."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=6000,
        )
        if not data:
            logger.warning("Product Manager: LLM returned empty JSON")

        epic_raw = data.get("epic") or {}
        epic = BacklogEpic(
            title=str(epic_raw.get("title") or project.name or "Epic").strip(),
            description=str(epic_raw.get("description") or "").strip(),
            key_results=[
                str(k).strip()
                for k in (epic_raw.get("key_results") or [])
                if str(k).strip()
            ],
        )

        stories: List[UserStory] = []
        skipped = 0
        for s in data.get("stories") or []:
            title = str(s.get("title") or "Untitled story").strip()
            if not title:
                skipped += 1
                continue
            try:
                # Normalise persona/goal/benefit so the template
                # "As a {persona}, I want {goal}, so that {benefit}."
                # reads cleanly even when the LLM returned "Place a service
                # order" or "to comply with X". See services/story_voice.py.
                persona_n, goal_n, benefit_n = normalize_voice(
                    s.get("persona", "User"),
                    s.get("goal", ""),
                    s.get("benefit", ""),
                )
                stories.append(
                    UserStory(
                        title=title,
                        persona=persona_n,
                        goal=goal_n,
                        benefit=benefit_n,
                        acceptance_criteria=list(s.get("acceptance_criteria") or []),
                        source_clause_ids=filter_clause_ids(
                            project,
                            s.get("source_clause_ids"),
                            agent="product_manager",
                            context=title[:40],
                        ),
                    )
                )
            except Exception as exc:
                skipped += 1
                logger.warning("Product Manager skipped story row: %s", exc)
        if skipped:
            logger.info("Product Manager: skipped %s invalid story row(s)", skipped)

        summary = RequirementSummary(
            title=str(data.get("product_title") or epic.title).strip(),
            one_liner=str(data.get("one_liner") or "").strip(),
            objective=str(data.get("objective") or "").strip(),
            in_scope=[f.name for f in (project.requirement_brief.features if project.requirement_brief else [])],
            primary_personas=[a.name for a in (project.requirement_brief.actors if project.requirement_brief else [])],
        )

        return {
            "pipeline_epic": epic,
            "stories": stories,
            "summary": summary,
        }
