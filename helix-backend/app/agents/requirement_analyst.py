"""Requirement Analyst Agent — front-of-house intake pass.

First agent in the Multi-Agent SDLC Pipeline. Extracts:

    - Features
    - Actors
    - Business rules

Plus glossary, constraints, and open questions for downstream agents.

Output: `requirement_brief` on the Project.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import (
    ActorProfile,
    BusinessRule,
    ExtractedFeature,
    GlossaryTerm,
    Project,
    RequirementBrief,
    RequirementEntity,
)
from ..services.ingestion import render_clauses
from .base import Agent


SYSTEM = """You are a Requirement Analyst on an enterprise delivery team.

You are the FIRST agent in a multi-agent SDLC pipeline. Extract structured
intake from messy requirements:

  1. FEATURES — named capabilities the system must deliver.
  2. ACTORS — roles/personas (who does what, with responsibilities).
  3. BUSINESS RULES — policies, validations, if/then constraints.

Also provide a cleaned summary, entities, glossary, constraints, and
open_questions for anything implied but not stated.

Be faithful: ground EVERYTHING in the raw input. Do not invent scope.
""".strip()


SCHEMA = """{
  "cleaned_summary": "string — 3-5 sentence neutral restatement",
  "features": [
    {"name": "string", "description": "string", "priority": "low|medium|high|critical"}
  ],
  "actors": [
    {"name": "string", "role": "string", "responsibilities": ["string"]}
  ],
  "business_rules": [
    {"description": "string", "condition": "string", "outcome": "string"}
  ],
  "entities": [
    {"name": "string", "kind": "actor|concept|system|external|data", "description": "string"}
  ],
  "stakeholders": ["string"],
  "target_users": ["string"],
  "key_constraints": ["string"],
  "glossary": [{"term": "string", "meaning": "string"}],
  "open_questions": ["string"]
}"""


class RequirementAnalystAgent(Agent):
    name = "requirement_analyst"
    stage = "Requirement Analyst"

    async def run(self, project: Project) -> Dict[str, Any]:
        clauses = render_clauses(project.source_clauses)
        user = (
            "Raw incoming requirement (one clause per line, with stable ids):\n\n"
            f"{clauses}\n\n"
            "Extract features, actors, and business rules. Be concise and grounded."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=2500,
        )

        features: List[ExtractedFeature] = []
        for f in data.get("features") or []:
            try:
                features.append(
                    ExtractedFeature(
                        name=str(f.get("name") or "").strip() or "Feature",
                        description=str(f.get("description") or "").strip(),
                        priority=str(f.get("priority") or "medium").lower(),
                    )
                )
            except Exception:
                continue

        actors: List[ActorProfile] = []
        for a in data.get("actors") or []:
            try:
                actors.append(
                    ActorProfile(
                        name=str(a.get("name") or "").strip() or "Actor",
                        role=str(a.get("role") or "").strip(),
                        responsibilities=[
                            str(r).strip()
                            for r in (a.get("responsibilities") or [])
                            if str(r).strip()
                        ],
                    )
                )
            except Exception:
                continue

        business_rules: List[BusinessRule] = []
        for r in data.get("business_rules") or []:
            try:
                desc = str(r.get("description") or "").strip()
                if desc:
                    business_rules.append(
                        BusinessRule(
                            description=desc,
                            condition=str(r.get("condition") or "").strip(),
                            outcome=str(r.get("outcome") or "").strip(),
                        )
                    )
            except Exception:
                continue

        entities: List[RequirementEntity] = []
        for e in data.get("entities") or []:
            try:
                entities.append(
                    RequirementEntity(
                        name=str(e.get("name") or "").strip() or "Unnamed entity",
                        kind=str(e.get("kind") or "concept").lower().strip(),
                        description=str(e.get("description") or "").strip(),
                    )
                )
            except Exception:
                continue

        glossary: List[GlossaryTerm] = []
        for g in data.get("glossary") or []:
            try:
                term = str(g.get("term") or "").strip()
                meaning = str(g.get("meaning") or "").strip()
                if term and meaning:
                    glossary.append(GlossaryTerm(term=term, meaning=meaning))
            except Exception:
                continue

        brief = RequirementBrief(
            cleaned_summary=str(data.get("cleaned_summary") or "").strip(),
            features=features,
            actors=actors,
            business_rules=business_rules,
            entities=entities,
            stakeholders=[str(s).strip() for s in (data.get("stakeholders") or []) if str(s).strip()],
            target_users=[str(s).strip() for s in (data.get("target_users") or []) if str(s).strip()],
            key_constraints=[str(s).strip() for s in (data.get("key_constraints") or []) if str(s).strip()],
            glossary=glossary,
            open_questions=[str(s).strip() for s in (data.get("open_questions") or []) if str(s).strip()],
        )
        return {"requirement_brief": brief}
