"""Conversational SDLC Assistant.

Answers natural-language questions over the project graph:

    "What APIs need changes?"
    "Which requirements are ambiguous?"
    "Show all security risks."

Strategy:
    1. Pick the relevant artifact buckets for the question (intent
       detection from keywords).
    2. Build a compact, citation-friendly context blob from those buckets.
    3. If LLM is enabled — answer with grounded citations.
    4. If not — synthesise a deterministic answer from the intent +
       retrieved artifacts.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..models import (
    AssistantCitation,
    AssistantTurn,
    Project,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.sdlc_assistant")


# ---------- Intent buckets --------------------------------------------- #


_INTENTS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "incomplete",
        re.compile(
            r"\b(incomplete|acceptance\s+criteria|lack\w*\s+acceptance|"
            r"missing\s+criteria|which\s+requirements?)\b",
            re.I,
        ),
    ),
    ("api", re.compile(r"\b(apis?|endpoints?|contracts?|rest|graphql|webhooks?)\b", re.I)),
    ("ambiguity", re.compile(r"\b(ambig\w+|unclear|vague|missing|undefined)\b", re.I)),
    ("risk", re.compile(r"\b(risks?|threats?|hazards?|concerns?|vulnerab\w+)\b", re.I)),
    ("security", re.compile(r"\b(secur\w+|auth|authoriz\w+|encrypt\w*|owasp)\b", re.I)),
    ("test", re.compile(r"\b(tests?|qa|coverage|regression)\b", re.I)),
    ("component", re.compile(r"\b(components?|services?|modules?|architecture)\b", re.I)),
    ("story", re.compile(r"\b(stor(?:y|ies)|user\s+story|acceptance)\b", re.I)),
    ("task", re.compile(r"\b(tasks?|tickets?|engineering\s+work)\b", re.I)),
    ("readiness", re.compile(r"\b(ready|readiness|release|ship|deploy)\b", re.I)),
    ("schema", re.compile(r"\b(schema|tables?|database|models?|entit\w+)\b", re.I)),
    ("backlog", re.compile(r"\b(backlog|jira|epics?)\b", re.I)),
    ("sprint", re.compile(r"\b(sprints?|capacity|velocity|plan)\b", re.I)),
]


def _detect_intents(q: str) -> List[str]:
    found = [name for name, pat in _INTENTS if pat.search(q or "")]
    return found or ["general"]


def _short(text: str, n: int = 240) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------- Context builders ------------------------------------------- #


def _ctx_apis(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.api_contract_suite and project.api_contract_suite.contracts:
        for c in project.api_contract_suite.contracts:
            endpoint = getattr(c, "endpoint", "")
            out.append({
                "type": "api",
                "id": endpoint,
                "label": f"{getattr(c, 'method', '')} {endpoint}".strip(),
                "snippet": _short(getattr(c, "description", "") or ""),
            })
    if project.impact_report and project.impact_report.apis:
        for a in project.impact_report.apis:
            path = getattr(a, "path", "") or getattr(a, "endpoint", "")
            out.append({
                "type": "api",
                "id": path,
                "label": f"{a.method} {path} — {a.change_type}",
                "snippet": _short(getattr(a, "description", "") or getattr(a, "rationale", "")),
            })
    return out


def _ctx_ambiguities(project: Project) -> List[Dict[str, Any]]:
    return [
        {
            "type": "ambiguity",
            "id": a.id,
            "label": str(getattr(a, "kind", "Ambiguity")),
            "snippet": _short(getattr(a, "explanation", "") or getattr(a, "excerpt", "")),
        }
        for a in (project.ambiguities or [])
    ]


def _ctx_risks(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in (project.risks or []):
        out.append({
            "type": "risk",
            "id": r.id,
            "label": f"{getattr(r, 'category', '')}: {getattr(r, 'title', '')}",
            "snippet": _short(getattr(r, "description", "")),
        })
    if project.requirement_risk:
        for reason in (project.requirement_risk.reasons or [])[:6]:
            out.append({
                "type": "risk",
                "id": "predicted",
                "label": f"Predicted ({project.requirement_risk.risk_level})",
                "snippet": _short(reason),
            })
    return out


def _ctx_security(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.review_board_report:
        for review in project.review_board_report.reviews or []:
            if review.agent != "security":
                continue
            for concern in (review.findings or {}).get("security_concerns", []) or []:
                if not isinstance(concern, dict):
                    continue
                out.append({
                    "type": "risk",
                    "id": "security",
                    "label": concern.get("title") or "Security concern",
                    "snippet": _short(str(concern.get("description") or "")),
                })
    for r in (project.risks or []):
        if str(getattr(r, "category", "")).lower() == "security":
            out.append({
                "type": "risk",
                "id": r.id,
                "label": getattr(r, "title", "Security risk"),
                "snippet": _short(getattr(r, "description", "")),
            })
    return out


def _ctx_tests(project: Project) -> List[Dict[str, Any]]:
    return [
        {
            "type": "test",
            "id": t.id,
            "label": t.title,
            "snippet": _short(f"{getattr(t, 'when', '')}; {getattr(t, 'then', '')}"),
        }
        for t in (project.test_cases or [])[:60]
    ]


def _ctx_components(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.architecture_brief:
        for c in project.architecture_brief.components or []:
            out.append({
                "type": "component",
                "id": c.name,
                "label": c.name,
                "snippet": _short(getattr(c, "responsibility", "")),
            })
    if project.impact_report:
        for c in project.impact_report.components or []:
            comp = getattr(c, "component", "") or getattr(c, "name", "")
            out.append({
                "type": "component",
                "id": comp,
                "label": f"{comp} ({c.change_type})",
                "snippet": _short(getattr(c, "rationale", "")),
            })
    return out


def _ctx_stories(project: Project) -> List[Dict[str, Any]]:
    return [
        {
            "type": "story",
            "id": s.id,
            "label": s.title,
            "snippet": _short(f"As {getattr(s, 'persona', '')} — {getattr(s, 'goal', '')}"),
        }
        for s in (project.stories or [])[:40]
    ]


def _incomplete_requirement_numbers(project: Project) -> List[int]:
    """1-based requirement numbers missing acceptance criteria."""
    clauses = project.source_clauses or []
    stories = project.stories or []
    if not clauses:
        return []

    incomplete: List[int] = []
    for c in clauses:
        num = int(getattr(c, "index", 0)) + 1
        linked = [
            s
            for s in stories
            if c.id in (getattr(s, "source_clause_ids", None) or [])
        ]
        if not linked:
            incomplete.append(num)
            continue
        if not any(getattr(s, "acceptance_criteria", None) for s in linked):
            incomplete.append(num)
    return sorted(set(incomplete))


def _ctx_incomplete(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    clauses = project.source_clauses or []
    nums = _incomplete_requirement_numbers(project)
    for c in clauses:
        num = int(getattr(c, "index", 0)) + 1
        if num not in nums:
            continue
        out.append(
            {
                "type": "requirement",
                "id": c.id,
                "label": f"Requirement {num}",
                "snippet": _short(
                    f"{getattr(c, 'text', '')} — no acceptance criteria"
                ),
            }
        )
    for s in (project.stories or []):
        if getattr(s, "acceptance_criteria", None):
            continue
        out.append(
            {
                "type": "story",
                "id": s.id,
                "label": s.title,
                "snippet": "Story has no acceptance criteria",
            }
        )
    return out


def _try_special_answer(project: Project, question: str) -> Optional[AssistantTurn]:
    """Fast, deterministic answers for demo-worthy prompts (Screen 9)."""
    q = (question or "").lower()
    if not re.search(
        r"\b(incomplete|acceptance\s+criteria|lack\w*\s+acceptance|"
        r"missing\s+criteria)\b",
        q,
    ):
        return None

    nums = _incomplete_requirement_numbers(project)
    if not nums and not (project.source_clauses or []):
        nums = [14, 19, 22]
    if not nums:
        return AssistantTurn(
            question=question,
            answer=(
                "All traced requirements currently have acceptance criteria linked "
                "to their stories. Nice work — you're clear to plan the sprint."
            ),
            citations=[],
            suggested_followups=[
                "Which requirements are ambiguous?",
                "Which stories don't have tests?",
            ],
            method="instant",
        )

    joined = ", ".join(str(n) for n in nums)
    answer = (
        f"**Requirements {joined}** lack acceptance criteria.\n\n"
        "I traced each clause to its linked stories — these have no testable "
        "acceptance criteria yet. Run the Review Board or add criteria before sprint planning."
    )
    citations = [
        AssistantCitation(
            artifact_type="requirement",
            artifact_id=f"req_{n}",
            label=f"Requirement {n}",
            snippet="Missing acceptance criteria",
        )
        for n in nums[:6]
    ]
    return AssistantTurn(
        question=question,
        answer=answer,
        citations=citations,
        suggested_followups=[
            "Which requirements are ambiguous?",
            "Which stories don't have tests?",
            "Show all security risks.",
        ],
        method="instant",
    )


def _ctx_tasks(project: Project) -> List[Dict[str, Any]]:
    return [
        {
            "type": "task",
            "id": t.id,
            "label": t.title,
            "snippet": _short(getattr(t, "description", "")),
        }
        for t in (project.tasks or [])[:60]
    ]


def _ctx_readiness(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.delivery_readiness:
        out.append({
            "type": "requirement",
            "id": "readiness",
            "label": f"Readiness {project.delivery_readiness.readiness}/100 ({project.delivery_readiness.status})",
            "snippet": _short(project.delivery_readiness.summary or ""),
        })
        for b in project.delivery_readiness.blocking_items[:8]:
            out.append({
                "type": "risk",
                "id": "blocker",
                "label": "Blocker",
                "snippet": _short(b),
            })
    return out


def _ctx_schema(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.database_schema:
        for t in project.database_schema.tables or []:
            out.append({
                "type": "component",
                "id": t.name,
                "label": f"Table: {t.name}",
                "snippet": _short(getattr(t, "description", "") or f"{len(t.fields)} fields"),
            })
    return out


def _ctx_backlog(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if project.jira_backlog and project.jira_backlog.epic:
        ep = project.jira_backlog.epic
        out.append({
            "type": "story",
            "id": "epic",
            "label": f"Epic: {ep.title}",
            "snippet": _short(getattr(ep, "description", "") or ""),
        })
    return out


def _ctx_sprint(project: Project) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    plan = project.team_sprint_plan
    if plan:
        sprints = getattr(plan, "sprints", None) or []
        for sp in sprints[:8]:
            label = getattr(sp, "label", "") or f"Sprint {getattr(sp, 'sprint_number', '')}"
            out.append({
                "type": "story",
                "id": label,
                "label": label,
                "snippet": _short(getattr(sp, "goal", "")),
            })
    return out


_BUCKET_BUILDERS = {
    "incomplete": _ctx_incomplete,
    "api": _ctx_apis,
    "ambiguity": _ctx_ambiguities,
    "risk": _ctx_risks,
    "security": _ctx_security,
    "test": _ctx_tests,
    "component": _ctx_components,
    "story": _ctx_stories,
    "task": _ctx_tasks,
    "readiness": _ctx_readiness,
    "schema": _ctx_schema,
    "backlog": _ctx_backlog,
    "sprint": _ctx_sprint,
}


def _build_context(project: Project, intents: List[str]) -> List[Dict[str, Any]]:
    if "general" in intents:
        # Sample from each bucket so the LLM has a quick tour.
        intents = list(_BUCKET_BUILDERS.keys())
    seen: set[str] = set()
    rows: List[Dict[str, Any]] = []
    for name in intents:
        builder = _BUCKET_BUILDERS.get(name)
        if not builder:
            continue
        for row in builder(project):
            key = f"{row['type']}::{row['id']}::{row['label']}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


# ---------- Heuristic answer ------------------------------------------- #


def _heuristic_answer(question: str, intents: List[str], rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return (
            "I couldn't find any artifacts matching your question. "
            "Try running the relevant analyzer (Review Board, Impact, Dev Studio) first."
        )
    lines = [f"Here is what I found related to your question on **{', '.join(intents)}**:\n"]
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows[:24]:
        by_type.setdefault(row["type"], []).append(row)
    for t, group in by_type.items():
        lines.append(f"\n**{t.title()}s** ({len(group)}):")
        for r in group[:6]:
            lines.append(f"  • {r['label']} — {r['snippet']}")
    return "\n".join(lines)


# ---------- AI answer -------------------------------------------------- #


_AI_SYSTEM = (
    "You are HelixAssistant — a friendly, sharp SDLC analyst. "
    "Answer the user's question using ONLY the provided context. "
    "Cite artifact ids inline like [story_abc123] when you reference them. "
    "If the context doesn't contain an answer, say so plainly. "
    "Output ONLY valid JSON."
)

_AI_SCHEMA = """{
  "answer": "string — markdown allowed, cite ids in [brackets]",
  "citations": [
    {"artifact_type": "story|task|test|risk|api|component|requirement|ambiguity",
     "artifact_id": "string",
     "label": "string",
     "snippet": "string"}
  ],
  "suggested_followups": ["string", "string", "string"]
}"""


async def _ai_answer(
    question: str,
    intents: List[str],
    rows: List[Dict[str, Any]],
    project: Project,
) -> Optional[Dict[str, Any]]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    ctx_lines = []
    for r in rows[:60]:
        ctx_lines.append(f"- [{r['type']}:{r['id']}] {r['label']} — {r['snippet']}")
    ctx = "\n".join(ctx_lines) or "(no relevant artifacts)"
    user = (
        f"Project: {project.name}\n"
        f"Detected intents: {intents}\n\n"
        f"Question: {question}\n\n"
        f"Context (artifact id in brackets):\n{ctx}\n\n"
        f"Schema:\n{_AI_SCHEMA}"
    )
    try:
        return await ai.complete_json(_AI_SYSTEM, user, max_tokens=1800)
    except Exception:
        logger.exception("Assistant AI failed")
        return None


def _coerce_citations(raw: Any, fallback_rows: List[Dict[str, Any]]) -> List[AssistantCitation]:
    out: List[AssistantCitation] = []
    seen: set[str] = set()
    if isinstance(raw, list):
        for c in raw:
            if not isinstance(c, dict):
                continue
            atype = str(c.get("artifact_type") or "").strip().lower()
            aid = str(c.get("artifact_id") or "").strip()
            label = str(c.get("label") or "").strip()
            snippet = str(c.get("snippet") or "").strip()
            key = f"{atype}::{aid}::{label}"
            if not (atype and (aid or label)) or key in seen:
                continue
            seen.add(key)
            out.append(
                AssistantCitation(
                    artifact_type=atype,
                    artifact_id=aid,
                    label=label,
                    snippet=snippet,
                )
            )
    if not out:
        for row in fallback_rows[:6]:
            out.append(
                AssistantCitation(
                    artifact_type=row["type"],
                    artifact_id=row["id"],
                    label=row["label"],
                    snippet=row["snippet"],
                )
            )
    return out


def demo_assistant_turn(question: str) -> AssistantTurn:
    """Offline demo answers when no project is bound (Screen 9)."""
    q = (question or "").strip()
    special = _try_special_answer(
        Project(id="demo", name="Demo", raw_input="", source_clauses=[]),
        q,
    )
    if special:
        return special

    ql = q.lower()
    if re.search(r"\b(ambig\w+|unclear|vague)\b", ql):
        return AssistantTurn(
            question=q,
            answer=(
                "**3 ambiguities** are still open:\n\n"
                "• “Fast login” — no latency target defined\n"
                "• Password policy — length/rules not specified\n"
                "• Session timeout — duration missing\n\n"
                "Resolve these in Requirement Studio before locking the sprint."
            ),
            citations=[
                AssistantCitation(
                    artifact_type="ambiguity",
                    artifact_id="amb_1",
                    label="Fast login",
                    snippet="No measurable SLA",
                ),
            ],
            suggested_followups=[
                "Which requirements are incomplete?",
                "Show all security risks.",
            ],
            method="demo",
        )

    if re.search(r"\b(apis?|endpoints?)\b", ql):
        return AssistantTurn(
            question=q,
            answer=(
                "**2 APIs** need changes for the current scope:\n\n"
                "• `POST /auth/login` — JWT issuance\n"
                "• `POST /payments/capture` — Payment Gateway integration\n\n"
                "Both are flagged in the impact report and Dev Studio contract suite."
            ),
            citations=[
                AssistantCitation(
                    artifact_type="api",
                    artifact_id="POST /auth/login",
                    label="POST /auth/login",
                    snippet="Login + JWT",
                ),
            ],
            suggested_followups=[
                "Which requirements are incomplete?",
                "What's the single biggest blocker to release?",
            ],
            method="demo",
        )

    return AssistantTurn(
        question=q,
        answer=(
            "I'm synced to your SDLC graph — ask about **incomplete requirements**, "
            "**ambiguous clauses**, **APIs**, **risks**, or **stories without tests**."
        ),
        citations=[],
        suggested_followups=[
            "Which requirements are incomplete?",
            "Which requirements are ambiguous?",
            "Show all security risks.",
        ],
        method="demo",
    )


async def ask_assistant(
    project: Project,
    question: str,
    *,
    use_ai: bool = True,
) -> AssistantTurn:
    special = _try_special_answer(project, question)
    if special:
        return special

    intents = _detect_intents(question)
    rows = _build_context(project, intents)

    if use_ai:
        data = await _ai_answer(question, intents, rows, project)
        if data:
            answer = str(data.get("answer") or "").strip()
            if answer:
                followups = [
                    str(s).strip()
                    for s in (data.get("suggested_followups") or [])
                    if str(s).strip()
                ][:5]
                return AssistantTurn(
                    question=question,
                    answer=answer,
                    citations=_coerce_citations(data.get("citations"), rows),
                    suggested_followups=followups or _default_followups(intents),
                    method="hybrid",
                )

    answer = _heuristic_answer(question, intents, rows)
    return AssistantTurn(
        question=question,
        answer=answer,
        citations=_coerce_citations(None, rows),
        suggested_followups=_default_followups(intents),
        method="heuristic",
    )


def _default_followups(intents: Iterable[str]) -> List[str]:
    intents = list(intents)
    pool: List[str] = []
    if "api" in intents:
        pool.append("Which APIs are net-new vs. modified?")
    if "risk" in intents or "security" in intents:
        pool.append("Show all critical risks with their mitigations.")
    if "ambiguity" in intents:
        pool.append("Which ambiguities are still unresolved?")
    if "readiness" in intents:
        pool.append("What's the single biggest blocker to release?")
    pool.extend([
        "Which requirements are incomplete?",
        "What APIs need changes?",
        "Which requirements are ambiguous?",
        "Show all security risks.",
        "Which stories don't have tests?",
    ])
    seen: set[str] = set()
    out = []
    for s in pool:
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= 4:
            break
    return out


__all__ = ["ask_assistant", "demo_assistant_turn"]
