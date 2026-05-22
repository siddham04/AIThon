"""Risk Agent — flags non-functional concerns the PM may have missed.

Categories: security, compliance, performance, scalability, dependency,
data, ux. Each risk has a mitigation a team can act on this sprint.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import Project, Risk, RiskCategory, Severity
from ..services.ingestion import render_clauses
from .base import Agent


SYSTEM = """You are a Principal Engineer reviewing a feature brief for
non-functional risk. Surface the risks that engineering will own — the
kind that cause incidents 3 sprints later if ignored.

Categories: security | compliance | performance | scalability | dependency
| data | ux.

Each risk includes: title, severity, description, and a concrete
mitigation that can begin this sprint.
""".strip()


SCHEMA = """{
  "risks": [
    {
      "category": "security|compliance|performance|scalability|dependency|data|ux",
      "severity": "low|medium|high|critical",
      "title": "string",
      "description": "string",
      "mitigation": "string",
      "source_clause_ids": ["clause_xxxx"]
    }
  ]
}"""


class RiskAgent(Agent):
    name = "risk"
    stage = "Risk & Ambiguity · Risk"

    async def run(self, project: Project) -> Dict[str, Any]:
        summary_block = ""
        if project.summary:
            summary_block = (
                f"Brief: {project.summary.one_liner}\n"
                f"Objective: {project.summary.objective}\n"
                f"Personas: {', '.join(project.summary.primary_personas)}\n\n"
            )
        user = (
            f"{summary_block}"
            "Source clauses:\n\n"
            f"{render_clauses(project.source_clauses)}\n\n"
            "Identify the top 4-8 non-functional risks."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=3000,
        )

        risks: List[Risk] = []
        for r in data.get("risks") or []:
            try:
                risks.append(
                    Risk(
                        category=RiskCategory(r.get("category", "dependency")),
                        severity=Severity(r.get("severity", "medium")),
                        title=r.get("title", "Untitled risk"),
                        description=r.get("description", ""),
                        mitigation=r.get("mitigation", ""),
                        source_clause_ids=list(r.get("source_clause_ids") or []),
                    )
                )
            except Exception:
                continue
        return {"risks": risks}
