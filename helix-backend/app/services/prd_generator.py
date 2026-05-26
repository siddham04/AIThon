"""Auto PRD Generator (Feature 18).

Produce a Product Requirements Document from a raw requirement string.
Hybrid heuristic + LLM:

* Heuristic pass extracts likely scope/out-of-scope/risks/dependencies
  from keyword patterns so the doc is never empty.
* LLM pass refines wording, fills the executive summary, and authors
  user stories with acceptance criteria.

A Markdown export helper renders the PRD in a familiar format that
PMs can paste straight into Confluence / Notion.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import (
    PRDDependency,
    PRDRisk,
    PRDStory,
    ProductRequirementsDocument,
    Project,
    Severity,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.prd_generator")


# ---------- Heuristic helpers ---------------------------------------- #


_SCOPE_HINT = re.compile(
    r"\b(must|should|shall|will|need to|require[ds]?|support[s]?)\b",
    re.I,
)
_OUT_OF_SCOPE_HINT = re.compile(
    r"\b(out of scope|not covered|excluded|deferred|future|won['’]t|will not)\b",
    re.I,
)
_RISK_HINT = re.compile(
    r"\b(risk|threat|fail|breach|outage|downtime|unknown|unclear|missing|"
    r"no\s+rollback|irreversible|destructive|bottleneck|delay|legacy|"
    r"untested|deprecat\w+|vulnerab\w+)\b",
    re.I,
)
_DEP_HINT = re.compile(
    r"\b(stripe|twilio|sendgrid|aws|gcp|azure|kafka|rabbitmq|redis|postgres|mongo|elastic|firebase|github|jira|salesforce|sap)\b",
    re.I,
)


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+|;\s+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _heuristic_prd(text: str, *, title: str = "") -> ProductRequirementsDocument:
    text = (text or "").strip()
    if not text:
        return ProductRequirementsDocument(title=title or "Untitled PRD")

    sentences = _split_sentences(text)
    in_scope: List[str] = []
    out_of_scope: List[str] = []
    risks: List[PRDRisk] = []
    deps: Dict[str, str] = {}
    goals: List[str] = []

    for s in sentences:
        if _OUT_OF_SCOPE_HINT.search(s):
            out_of_scope.append(s)
            continue
        if _SCOPE_HINT.search(s):
            in_scope.append(s)
        if _RISK_HINT.search(s):
            risks.append(
                PRDRisk(
                    title=s if len(s) <= 90 else s[:87] + "…",
                    severity=Severity.HIGH if "fail" in s.lower() or "breach" in s.lower() else Severity.MEDIUM,
                    mitigation="Confirm during ambiguity / risk review.",
                )
            )
        for m in _DEP_HINT.finditer(s):
            name = m.group(0).title()
            if name not in deps:
                deps[name] = s

    # Goals heuristic — pull the first 3 in-scope sentences as headline goals.
    goals = in_scope[:3]
    if not goals and sentences:
        goals = sentences[:2]

    # User stories — convert in-scope sentences into As-a/I-want-to/So-that drafts.
    stories: List[PRDStory] = []
    for s in in_scope[:6]:
        stories.append(
            PRDStory(
                title=s if len(s) <= 90 else s[:87] + "…",
                persona="end user",
                goal=s,
                benefit="deliver the stated outcome",
                acceptance_criteria=[
                    f"Given the requirement scope, when implemented, then the behaviour described above is observable.",
                ],
                priority=Severity.MEDIUM,
            )
        )

    one_liner = sentences[0] if sentences else ""
    # If the heuristic extractor found nothing concrete (small / prose
    # PRDs like a case study), the old summary read like a failure
    # report — "X captures 0 in-scope items, 0 out-of-scope items, and
    # 0 risks". On stage that looks broken even when the rest of the
    # pipeline is fine. Use a graceful fallback that describes what we
    # *did* extract.
    parts: List[str] = []
    if in_scope:
        parts.append(
            f"{len(in_scope)} in-scope item{'' if len(in_scope) == 1 else 's'}"
        )
    if out_of_scope:
        parts.append(
            f"{len(out_of_scope)} explicit out-of-scope item"
            f"{'' if len(out_of_scope) == 1 else 's'}"
        )
    if risks:
        parts.append(
            f"{len(risks)} risk callout{'' if len(risks) == 1 else 's'}"
        )

    subject = title or "This requirement"
    if parts:
        summary = f"{subject} captures " + ", ".join(parts[:-1])
        if len(parts) > 1:
            summary += f", and {parts[-1]}"
        else:
            summary += parts[0] if not summary.endswith(parts[0]) else ""
        summary += " from the source text."
    else:
        # Honest no-data wording — invites the user to enrich the PRD
        # rather than implying the analyzer broke.
        sample = ""
        if sentences:
            sample_text = sentences[0]
            if len(sample_text) > 140:
                sample_text = sample_text[:137].rstrip() + "…"
            sample = f' Source one-liner: "{sample_text}".'
        summary = (
            f"{subject} was ingested as free-form prose; no explicit "
            f"in-scope / out-of-scope / risk callouts were detected."
            f"{sample} Add bullet-style requirements or an Acceptance "
            f"Criteria section to unlock the full executive summary."
        )

    return ProductRequirementsDocument(
        title=title or (one_liner[:60] + ("…" if len(one_liner) > 60 else "")),
        one_liner=one_liner,
        executive_summary=summary,
        problem_statement=one_liner,
        goals=goals,
        success_metrics=[],
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        target_users=[],
        user_stories=stories,
        acceptance_criteria=[s for st in stories for s in st.acceptance_criteria][:10],
        risks=risks,
        dependencies=[
            PRDDependency(name=n, kind="external", description=d)
            for n, d in list(deps.items())[:8]
        ],
        open_questions=[],
        timeline="",
        method="heuristic",
    )


# ---------- AI augmentation ------------------------------------------ #


_AI_SYSTEM = """You are a Senior Product Manager writing a Product
Requirements Document (PRD) from a raw requirement. Be concise,
specific, and write so engineers can build from it. Never invent
business facts, but you may infer reasonable defaults (e.g. an
authentication feature implies "session expiry" as a goal). Output
ONLY valid JSON.""".strip()


_AI_SCHEMA = """{
  "title": "string",
  "one_liner": "string — a single-sentence elevator pitch",
  "executive_summary": "string — 3-5 sentences",
  "problem_statement": "string — what hurts today and why",
  "goals": ["string"],
  "success_metrics": ["string"],
  "in_scope": ["string"],
  "out_of_scope": ["string"],
  "target_users": ["string"],
  "user_stories": [
    {
      "title": "string",
      "persona": "string",
      "goal": "string",
      "benefit": "string",
      "acceptance_criteria": ["string"],
      "priority": "low|medium|high|critical"
    }
  ],
  "acceptance_criteria": ["string"],
  "risks": [
    {"title": "string", "severity": "low|medium|high|critical", "mitigation": "string"}
  ],
  "dependencies": [
    {"name": "string", "kind": "external|internal|infra|team", "description": "string"}
  ],
  "open_questions": ["string"],
  "timeline": "string"
}"""


async def _ai_augment(text: str, baseline: ProductRequirementsDocument) -> Optional[ProductRequirementsDocument]:
    ai = get_ai_service()
    if not ai.enabled:
        return None

    user = (
        f"Raw requirement:\n---\n{(text or '')[:6000]}\n---\n\n"
        f"Heuristic baseline (refine, don't ignore):\n"
        f"  in_scope: {baseline.in_scope[:6]}\n"
        f"  out_of_scope: {baseline.out_of_scope[:6]}\n"
        f"  risks: {[r.title for r in baseline.risks[:6]]}\n"
        f"  deps: {[d.name for d in baseline.dependencies[:6]]}\n\n"
        f"Return JSON in this schema:\n{_AI_SCHEMA}"
    )

    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=4500)
    except Exception:
        logger.exception("PRD AI failed")
        return None

    def _str_list(key: str) -> List[str]:
        return [str(x).strip() for x in (data.get(key) or []) if str(x).strip()]

    stories: List[PRDStory] = []
    for raw in (data.get("user_stories") or []):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        try:
            sev = Severity(str(raw.get("priority") or "medium").lower())
        except ValueError:
            sev = Severity.MEDIUM
        stories.append(
            PRDStory(
                title=title,
                persona=str(raw.get("persona") or "").strip(),
                goal=str(raw.get("goal") or "").strip(),
                benefit=str(raw.get("benefit") or "").strip(),
                acceptance_criteria=[
                    str(c).strip()
                    for c in (raw.get("acceptance_criteria") or [])
                    if str(c).strip()
                ],
                priority=sev,
            )
        )

    risks: List[PRDRisk] = []
    for raw in (data.get("risks") or []):
        if not isinstance(raw, dict):
            continue
        t = str(raw.get("title") or "").strip()
        if not t:
            continue
        try:
            sev = Severity(str(raw.get("severity") or "medium").lower())
        except ValueError:
            sev = Severity.MEDIUM
        risks.append(PRDRisk(title=t, severity=sev, mitigation=str(raw.get("mitigation") or "")))

    deps: List[PRDDependency] = []
    for raw in (data.get("dependencies") or []):
        if not isinstance(raw, dict):
            continue
        n = str(raw.get("name") or "").strip()
        if not n:
            continue
        kind = str(raw.get("kind") or "external").strip().lower()
        if kind not in ("external", "internal", "infra", "team"):
            kind = "external"
        deps.append(PRDDependency(name=n, kind=kind, description=str(raw.get("description") or "")))

    return ProductRequirementsDocument(
        title=str(data.get("title") or baseline.title).strip(),
        one_liner=str(data.get("one_liner") or baseline.one_liner).strip(),
        executive_summary=str(data.get("executive_summary") or baseline.executive_summary).strip(),
        problem_statement=str(data.get("problem_statement") or baseline.problem_statement).strip(),
        goals=_str_list("goals") or baseline.goals,
        success_metrics=_str_list("success_metrics"),
        in_scope=_str_list("in_scope") or baseline.in_scope,
        out_of_scope=_str_list("out_of_scope") or baseline.out_of_scope,
        target_users=_str_list("target_users"),
        user_stories=stories or baseline.user_stories,
        acceptance_criteria=_str_list("acceptance_criteria") or baseline.acceptance_criteria,
        risks=risks or baseline.risks,
        dependencies=deps or baseline.dependencies,
        open_questions=_str_list("open_questions"),
        timeline=str(data.get("timeline") or "").strip(),
        method="hybrid",
    )


async def generate_prd(
    text: str,
    *,
    title: str = "",
    use_ai: bool = True,
) -> ProductRequirementsDocument:
    baseline = _heuristic_prd(text, title=title)
    if not use_ai:
        return baseline
    refined = await _ai_augment(text, baseline)
    return refined or baseline


async def generate_prd_for_project(project: Project, *, use_ai: bool = True) -> ProductRequirementsDocument:
    """Convenience entry — pull the requirement straight from the project."""
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)
    title = project.name or ""
    return await generate_prd(text, title=title, use_ai=use_ai)


# ---------- Markdown export ------------------------------------------ #


def to_markdown(prd: ProductRequirementsDocument) -> str:
    lines: List[str] = []
    lines.append(f"# {prd.title or 'Product Requirements Document'}")
    if prd.one_liner:
        lines.append(f"\n> {prd.one_liner}")
    lines.append("\n## Executive Summary")
    lines.append(prd.executive_summary or "_(none)_")
    if prd.problem_statement:
        lines.append("\n## Problem Statement")
        lines.append(prd.problem_statement)
    if prd.goals:
        lines.append("\n## Goals")
        lines.extend(f"- {g}" for g in prd.goals)
    if prd.success_metrics:
        lines.append("\n## Success Metrics")
        lines.extend(f"- {m}" for m in prd.success_metrics)
    lines.append("\n## In Scope")
    if prd.in_scope:
        lines.extend(f"- {s}" for s in prd.in_scope)
    else:
        lines.append("_(none)_")
    lines.append("\n## Out of Scope")
    if prd.out_of_scope:
        lines.extend(f"- {s}" for s in prd.out_of_scope)
    else:
        lines.append("_(none)_")
    if prd.target_users:
        lines.append("\n## Target Users")
        lines.extend(f"- {u}" for u in prd.target_users)
    if prd.user_stories:
        lines.append("\n## User Stories")
        for st in prd.user_stories:
            lines.append(f"\n### {st.title}  · _{st.priority.value if hasattr(st.priority, 'value') else st.priority}_")
            if st.persona or st.goal or st.benefit:
                lines.append(
                    f"As **{st.persona or 'user'}**, I want to **{st.goal or '…'}** "
                    f"so that **{st.benefit or '…'}**."
                )
            if st.acceptance_criteria:
                lines.append("\n**Acceptance Criteria**")
                lines.extend(f"- {c}" for c in st.acceptance_criteria)
    if prd.acceptance_criteria:
        lines.append("\n## Global Acceptance Criteria")
        lines.extend(f"- {c}" for c in prd.acceptance_criteria)
    if prd.risks:
        lines.append("\n## Risks")
        for r in prd.risks:
            sev = r.severity.value if hasattr(r.severity, "value") else r.severity
            lines.append(f"- **[{sev.upper()}]** {r.title} — _Mitigation:_ {r.mitigation or 'TBD'}")
    if prd.dependencies:
        lines.append("\n## Dependencies")
        for d in prd.dependencies:
            lines.append(f"- **{d.name}** ({d.kind}) — {d.description or '—'}")
    if prd.open_questions:
        lines.append("\n## Open Questions")
        lines.extend(f"- {q}" for q in prd.open_questions)
    if prd.timeline:
        lines.append("\n## Timeline")
        lines.append(prd.timeline)
    lines.append(f"\n---\n_Generated by Helix · method: {prd.method}_")
    return "\n".join(lines)


__all__ = ["generate_prd", "generate_prd_for_project", "to_markdown"]
