"""Architect Agent — technical solution shape.

Third agent in the Multi-Agent SDLC Pipeline. Produces:

    - APIs (method, path, purpose)
    - DB / data entities
    - Components
    - Integrations, NFRs, stack, decisions

Output: `architecture_brief` on the Project.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import (
    ArchitectureBrief,
    ArchitectureComponent,
    ArchitectureDecision,
    ArchitectureLayer,
    Project,
    ProposedAPI,
)
from ..services.ingestion import render_clauses
from .base import Agent


SYSTEM = """You are a Solution Architect at a senior enterprise tier.

You have the requirement intake and Product Manager backlog (epic + stories).
Propose a CONCRETE, buildable first-pass architecture.

Be opinionated but grounded:
  - List REST (or GraphQL) APIs: method, path, description, owning component.
  - List major COMPONENTS (frontend / service / data / infra / integration).
  - Name the DATA ENTITIES (tables / aggregates) the system owns.
  - Name external INTEGRATIONS implied by the requirement.
  - Capture the NON-FUNCTIONAL REQUIREMENTS this design has to satisfy
    (security, scalability, performance, compliance, observability).
  - Suggest a STACK (concrete libraries / services).
  - Record 2-4 architecture DECISIONS with rationale and trade-offs the
    team should re-validate.
  - Propose a one-paragraph DEPLOYMENT topology.

Do not invent business scope. Only propose technology that the
requirement actually justifies.
""".strip()


SCHEMA = """{
  "overview": "string — 2-3 sentences: shape of the system",
  "apis": [
    {
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/resource",
      "description": "string",
      "component": "string — owning service"
    }
  ],
  "components": [
    {
      "name": "string",
      "responsibility": "string",
      "layer": "frontend|service|data|infra|integration",
      "tech": ["string"]
    }
  ],
  "integrations": ["string — external systems / APIs"],
  "data_entities": ["string — primary domain objects"],
  "non_functional_requirements": ["string — concrete NFR with target where possible"],
  "suggested_stack": ["string"],
  "decisions": [
    {
      "decision": "string",
      "rationale": "string",
      "trade_offs": "string"
    }
  ],
  "deployment": "string — runtime, region, scaling notes"
}"""


def _pm_block(project: Project) -> str:
    lines = []
    if project.pipeline_epic:
        e = project.pipeline_epic
        lines.append(f"Epic: {e.title} — {e.description}")
    if project.stories:
        lines.append(f"Stories: {len(project.stories)} user stories in backlog")
    return ("\n".join(lines) + "\n\n") if lines else ""


def _summary_block(project: Project) -> str:
    if not project.summary:
        return ""
    s = project.summary
    return (
        "Product Manager brief:\n"
        f"  Title: {s.title}\n"
        f"  One-liner: {s.one_liner}\n"
        f"  Objective: {s.objective}\n"
        f"  In-scope: {', '.join(s.in_scope) or '—'}\n"
        f"  Out-of-scope: {', '.join(s.out_of_scope) or '—'}\n"
        f"  Personas: {', '.join(s.primary_personas) or '—'}\n"
        f"  Success metrics: {', '.join(s.success_metrics) or '—'}\n\n"
    )


def _intake_block(project: Project) -> str:
    rb = project.requirement_brief
    if rb is None:
        return ""
    constraints = "\n    - ".join(rb.key_constraints) if rb.key_constraints else "—"
    return (
        "Requirement Analyst intake:\n"
        f"  Cleaned summary: {rb.cleaned_summary}\n"
        f"  Stakeholders: {', '.join(rb.stakeholders) or '—'}\n"
        f"  Target users: {', '.join(rb.target_users) or '—'}\n"
        f"  Constraints:\n    - {constraints}\n\n"
    )


class SolutionArchitectAgent(Agent):
    name = "solution_architect"
    stage = "Architect"

    async def run(self, project: Project) -> Dict[str, Any]:
        user = (
            f"{_intake_block(project)}"
            f"{_pm_block(project)}"
            f"{_summary_block(project)}"
            "Source clauses:\n\n"
            f"{render_clauses(project.source_clauses)}\n\n"
            "Produce the architecture brief. Concrete, opinionated, grounded."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=3500,
        )

        apis: List[ProposedAPI] = []
        for a in data.get("apis") or []:
            try:
                path = str(a.get("path") or "").strip()
                if not path:
                    continue
                apis.append(
                    ProposedAPI(
                        method=str(a.get("method") or "GET").upper().strip(),
                        path=path,
                        description=str(a.get("description") or "").strip(),
                        component=str(a.get("component") or "").strip(),
                    )
                )
            except Exception:
                continue

        components: List[ArchitectureComponent] = []
        for c in data.get("components") or []:
            try:
                layer_raw = str(c.get("layer") or "service").lower().strip()
                try:
                    layer = ArchitectureLayer(layer_raw)
                except ValueError:
                    layer = ArchitectureLayer.SERVICE
                components.append(
                    ArchitectureComponent(
                        name=str(c.get("name") or "Unnamed component").strip(),
                        responsibility=str(c.get("responsibility") or "").strip(),
                        layer=layer,
                        tech=[str(t).strip() for t in (c.get("tech") or []) if str(t).strip()],
                    )
                )
            except Exception:
                continue

        decisions: List[ArchitectureDecision] = []
        for d in data.get("decisions") or []:
            try:
                decisions.append(
                    ArchitectureDecision(
                        decision=str(d.get("decision") or "").strip(),
                        rationale=str(d.get("rationale") or "").strip(),
                        trade_offs=(str(d.get("trade_offs")).strip() or None)
                        if d.get("trade_offs")
                        else None,
                    )
                )
            except Exception:
                continue

        brief = ArchitectureBrief(
            overview=str(data.get("overview") or "").strip(),
            apis=apis,
            components=components,
            integrations=[str(s).strip() for s in (data.get("integrations") or []) if str(s).strip()],
            data_entities=[str(s).strip() for s in (data.get("data_entities") or []) if str(s).strip()],
            non_functional_requirements=[
                str(s).strip()
                for s in (data.get("non_functional_requirements") or [])
                if str(s).strip()
            ],
            suggested_stack=[
                str(s).strip()
                for s in (data.get("suggested_stack") or [])
                if str(s).strip()
            ],
            decisions=decisions,
            deployment=str(data.get("deployment") or "").strip(),
        )
        return {"architecture_brief": brief}
