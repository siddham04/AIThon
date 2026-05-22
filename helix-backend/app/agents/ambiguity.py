"""Ambiguity Agent — detects unclear, missing, or conflicting requirements.

Returns severity-scored issues, each citing the source clause(s) and
proposing a clarifying question to send back to the PM.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai.prompts.ambiguity_prompt import AMBIGUITY_SYSTEM, ambiguity_user_message

from ..models import AmbiguityIssue, AmbiguityKind, Project, Severity
from ..services.ai_service import get_ai_service
from ..services.ingestion import render_clauses
from .base import Agent

_KIND_FROM_LLM = {
    "passive_voice": AmbiguityKind.MISSING_CRITERIA,
    "vague_quantifier": AmbiguityKind.UNQUANTIFIED,
    "missing_actor": AmbiguityKind.MISSING_CRITERIA,
    "undefined_acronym": AmbiguityKind.UNDEFINED_TERM,
    "contradiction": AmbiguityKind.CONFLICTING,
    "other": AmbiguityKind.MISSING_CRITERIA,
}

SYSTEM = """You are a Staff Engineer reviewing requirements for clarity
before development begins. Your job is to surface ambiguity that, if left
unresolved, would cause defects, scope creep, or rework.

For every issue you find:
  - Quote the offending text exactly (excerpt)
  - Classify the kind: undefined_term | missing_criteria | conflicting |
    unquantified | out_of_scope | non_functional_gap
  - Score severity: low | medium | high | critical
  - Suggest a precise clarifying question for the PM
  - Optionally propose a sensible default resolution

Be selective. Avoid trivial nitpicks. Favor issues that actually impact
implementation, security, performance, or UX.
""".strip()


SCHEMA = """{
  "issues": [
    {
      "kind": "undefined_term|missing_criteria|conflicting|unquantified|out_of_scope|non_functional_gap",
      "severity": "low|medium|high|critical",
      "excerpt": "string — exact quote from the requirement",
      "explanation": "string — why this is ambiguous",
      "suggested_question": "string — clarifying question",
      "suggested_resolution": "string — optional default",
      "source_clause_ids": ["clause_xxxx", "..."]
    }
  ]
}"""


class AmbiguityAgent(Agent):
    name = "ambiguity"
    stage = "Risk & Ambiguity · Ambiguity"

    async def run(self, project: Project) -> Dict[str, Any]:
        clauses_txt = render_clauses(project.source_clauses)
        ai = get_ai_service()
        if ai.enabled:
            data = await ai.complete_json(
                AMBIGUITY_SYSTEM,
                ambiguity_user_message(clauses_txt),
                max_tokens=6000,
            )
        else:
            user = (
                "Source clauses:\n\n"
                f"{clauses_txt}\n\n"
                "Identify ambiguities. Cite source_clause_ids for each."
            )
            data = await self.llm.chat_json_with_fallback(
                self.name, project, SYSTEM, user, schema_hint=SCHEMA
            )
        issues_raw = data.get("issues") or []
        issues: List[AmbiguityIssue] = []
        for it in issues_raw:
            try:
                raw_kind = str(it.get("kind", "missing_criteria")).lower().strip()
                kind = _KIND_FROM_LLM.get(raw_kind)
                if kind is None:
                    try:
                        kind = AmbiguityKind(raw_kind)
                    except ValueError:
                        kind = AmbiguityKind.MISSING_CRITERIA
                issues.append(
                    AmbiguityIssue(
                        kind=kind,
                        severity=Severity(it.get("severity", "medium")),
                        excerpt=it.get("excerpt", "")[:500],
                        explanation=it.get("explanation", ""),
                        suggested_question=it.get("suggested_question", ""),
                        suggested_resolution=it.get("suggested_resolution"),
                        source_clause_ids=list(it.get("source_clause_ids") or []),
                        resolved=bool(it.get("resolved", False)),
                    )
                )
            except Exception:
                continue
        return {"ambiguities": issues}
