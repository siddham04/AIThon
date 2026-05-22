"""Analyzer Agent — produces the high-level RequirementSummary.

Acts like a senior PM reading a brief: distills the objective, scope,
personas, success metrics, and assumptions.
"""
from __future__ import annotations

from typing import Any, Dict

from ..models import Project, RequirementSummary
from ..services.ingestion import render_clauses
from .base import Agent


SYSTEM = """You are a Principal Product Manager and Staff Engineer.
You read raw, often messy, requirement input (emails, docs, meeting notes,
user stories) and distill it into a structured product brief.

Be precise, neutral, and grounded ONLY in what the input actually says.
Do NOT invent features or scope. If something is unclear, omit it (the
Ambiguity agent will catch it separately).
""".strip()


SCHEMA = """{
  "title": "string — short product/feature title (<= 8 words)",
  "one_liner": "string — single sentence summary",
  "objective": "string — 2-3 sentence objective and value",
  "in_scope": ["string", "..."],
  "out_of_scope": ["string", "..."],
  "primary_personas": ["string", "..."],
  "success_metrics": ["string — measurable KPI"],
  "assumptions": ["string", "..."]
}"""


class AnalyzerAgent(Agent):
    name = "analyzer"
    stage = "Business Analyst"

    async def run(self, project: Project) -> Dict[str, Any]:
        clauses = render_clauses(project.source_clauses)
        user = (
            "Source clauses (each prefixed with its stable id):\n\n"
            f"{clauses}\n\n"
            "Produce the structured product brief."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name, project, SYSTEM, user, schema_hint=SCHEMA
        )
        summary = RequirementSummary(
            title=data.get("title") or (project.name or "Untitled Initiative"),
            one_liner=data.get("one_liner", ""),
            objective=data.get("objective", ""),
            in_scope=list(data.get("in_scope") or []),
            out_of_scope=list(data.get("out_of_scope") or []),
            primary_personas=list(data.get("primary_personas") or []),
            success_metrics=list(data.get("success_metrics") or []),
            assumptions=list(data.get("assumptions") or []),
        )
        return {"summary": summary}
