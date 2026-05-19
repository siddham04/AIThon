"""Deterministic synthetic outputs when Azure OpenAI is not configured.

Clause-grounded mock data keeps traceability demonstrable on stage without keys.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

from ..models import Project

_VAGUE_RE = re.compile(
    r"\b(tbd|todo|to\s*do|later|maybe|asap|flexible|somehow|unclear|"
    r"nice\s*to\s*have|figure\s*out|needs\s*discussion)\b",
    re.I,
)
_QUANT_RE = re.compile(
    r"\b\d+\s*(ms|sec|s|min|minutes|hours|days|%|percent|users|rps|tps)\b",
    re.I,
)


def synthetic_json(agent: str, project: Project) -> Dict[str, Any]:
    handlers = {
        "analyzer": _analyzer_dict,
        "ambiguity": _ambiguity_dict,
        "decomposer": _decomposer_dict,
        "tests": _tests_dict,
        "estimator": _estimator_dict,
        "risk": _risk_dict,
    }
    fn = handlers.get(agent)
    if fn is None:
        return {}
    return fn(project)


def _clip(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _analyzer_dict(project: Project) -> Dict[str, Any]:
    clauses = project.source_clauses
    blob = " ".join(c.text for c in clauses)
    title = project.name.strip() or (
        _clip(clauses[0].text, 72) if clauses else "Untitled initiative"
    )
    one_liner = _clip(blob, 220) if blob else "No requirement text was provided."
    objective = (
        _clip(blob, 480)
        if blob
        else "Add substantive requirement text to generate a richer brief."
    )
    bullets = [c.text for c in clauses[:8] if len(c.text) > 12]
    personas = ["Primary user", "Internal operator"]
    if re.search(r"\b(admin|moderator|support)\b", blob, re.I):
        personas.append("Administrator")
    metrics = ["Requirement-to-artifact trace coverage ≥ 90% on cited clauses"]
    if _QUANT_RE.search(blob):
        metrics.append("Meet explicitly stated quantitative targets in source text")

    return {
        "title": title,
        "one_liner": one_liner,
        "objective": objective,
        "in_scope": bullets[:6] or ["Core capability described in source clauses"],
        "out_of_scope": [
            "Features not explicitly mentioned in the ingested requirement text"
        ],
        "primary_personas": personas[:4],
        "success_metrics": metrics[:5],
        "assumptions": [
            "Source clauses are authoritative for scope until clarified",
            "Human review validates LLM- or mock-generated artifacts before build",
        ],
    }


def _ambiguity_dict(project: Project) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for c in project.source_clauses:
        text = c.text
        if len(text) < 40 or _VAGUE_RE.search(text):
            issues.append(
                {
                    "kind": "missing_criteria",
                    "severity": "medium",
                    "excerpt": _clip(text, 280),
                    "explanation": (
                        "Clause is underspecified or contains vague language "
                        "that could drive rework without clarification."
                    ),
                    "suggested_question": (
                        "What concrete acceptance signals / metrics apply to this clause?"
                    ),
                    "suggested_resolution": (
                        "Add measurable acceptance criteria and explicit edge cases."
                    ),
                    "source_clause_ids": [c.id],
                }
            )
        if not _QUANT_RE.search(text) and re.search(
            r"\b(fast|scalable|secure|reliable|performance)\b", text, re.I
        ):
            issues.append(
                {
                    "kind": "unquantified",
                    "severity": "high",
                    "excerpt": _clip(text, 280),
                    "explanation": (
                        "Non-functional language without measurable thresholds."
                    ),
                    "suggested_question": (
                        "What numeric SLOs or bounds apply (latency, throughput, error rate)?"
                    ),
                    "suggested_resolution": (
                        "Define targets and measurement methodology for each NFR mention."
                    ),
                    "source_clause_ids": [c.id],
                }
            )

    if not issues and project.source_clauses:
        c0 = project.source_clauses[0]
        issues.append(
            {
                "kind": "undefined_term",
                "severity": "low",
                "excerpt": _clip(c0.text, 280),
                "explanation": (
                    "Mock/demo ambiguity pass: confirm stakeholders agree on definitions."
                ),
                "suggested_question": (
                    "Are there domain terms in this clause that need a shared glossary entry?"
                ),
                "suggested_resolution": "Attach glossary links or inline definitions.",
                "source_clause_ids": [c0.id],
            }
        )

    return {"issues": issues[:12]}


def _decomposer_dict(project: Project) -> Dict[str, Any]:
    clauses = project.source_clauses[:8]
    if not clauses:
        return {"stories": []}
    stories_raw: List[Dict[str, Any]] = []
    for i, c in enumerate(clauses):
        cid = c.id
        txt = c.text
        title = _clip(txt, 80)
        stories_raw.append(
            {
                "title": f"Deliver: {title}",
                "persona": "Primary stakeholder",
                "goal": f"Realize the capability described in [{cid}].",
                "benefit": "Reduces ambiguity and speeds delivery with traceable scope.",
                "acceptance_criteria": [
                    f"Given the requirement in [{cid}], when the feature is exercised, "
                    f"then behavior matches the clause intent.",
                    "Given invalid input, when handled, then users see safe feedback "
                    "without data corruption.",
                    "Given observability hooks, when operating in production, then teams "
                    "can trace failures to source intent.",
                ],
                "source_clause_ids": [cid],
                "tasks": [
                    {
                        "title": f"Implement core flow for clause [{cid}]",
                        "description": (
                            "Wire UI/API paths, validation, and persistence implied by the clause."
                        ),
                        "type": "feature",
                        "priority": "high",
                        "skills": ["typescript", "fastapi", "testing"],
                        "source_clause_ids": [cid],
                    },
                    {
                        "title": f"Add tests & telemetry for clause [{cid}]",
                        "description": (
                            "Cover happy path + critical edge cases; add structured logs/metrics."
                        ),
                        "type": "chore",
                        "priority": "medium",
                        "skills": ["pytest", "observability"],
                        "source_clause_ids": [cid],
                    },
                ],
            }
        )
        if i % 2 == 1:
            stories_raw[-1]["tasks"].append(
                {
                    "title": f"Security review checkpoint for [{cid}]",
                    "description": (
                        "Threat-model authz/data flows touching this clause; document mitigations."
                    ),
                    "type": "spike",
                    "priority": "medium",
                    "skills": ["security"],
                    "source_clause_ids": [cid],
                }
            )

    return {"stories": stories_raw}


def _tests_dict(project: Project) -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []
    for s in project.stories:
        sid = s.id
        clause_ids = list(s.source_clause_ids or [])
        tests.append(
            {
                "title": f"Happy path — {s.title}",
                "type": "integration",
                "given": "A user matching the story persona with valid permissions",
                "when": "They perform the primary flow described by the story goal",
                "then": "The system completes the flow and persists correct state",
                "edge_cases": ["Partial failure mid-flow", "Duplicate submissions"],
                "story_id": sid,
                "source_clause_ids": clause_ids[:3],
            }
        )
        tests.append(
            {
                "title": f"Negative path — {s.title}",
                "type": "unit",
                "given": "Inputs violate validation rules implied by acceptance criteria",
                "when": "The API/UI receives the invalid payload",
                "then": "Errors are surfaced safely without partial mutation",
                "edge_cases": ["Null fields", "Boundary values"],
                "story_id": sid,
                "source_clause_ids": clause_ids[:3],
            }
        )
        tests.append(
            {
                "title": f"Security posture — {s.title}",
                "type": "security",
                "given": "An authenticated but unauthorized actor",
                "when": "They attempt privileged actions tied to the story",
                "then": "Access is denied and an audit event is emitted",
                "edge_cases": ["Token replay", "Privilege escalation attempts"],
                "story_id": sid,
                "source_clause_ids": clause_ids[:3],
            }
        )
    return {"tests": tests}


_FIB = [1, 2, 3, 5, 8, 13]


def _fib_hours(points: int) -> float:
    return float(max(2, points * 2 + (points % 3)))


def _estimator_dict(project: Project) -> Dict[str, Any]:
    estimates = []
    for t in project.tasks:
        h = int(hashlib.sha256(t.id.encode()).hexdigest(), 16)
        pts = _FIB[h % len(_FIB)]
        conf = round(0.55 + (h % 40) / 100.0, 2)
        estimates.append(
            {
                "task_id": t.id,
                "estimate_points": pts,
                "estimate_hours": _fib_hours(pts),
                "confidence": conf,
            }
        )
    return {"estimates": estimates}


def _risk_dict(project: Project) -> Dict[str, Any]:
    blob = " ".join(c.text for c in project.source_clauses)
    cid = project.source_clauses[0].id if project.source_clauses else ""
    risks: List[Dict[str, Any]] = []

    def add(
        cat: str,
        sev: str,
        title: str,
        desc: str,
        mit: str,
        clause_ids: List[str],
    ) -> None:
        risks.append(
            {
                "category": cat,
                "severity": sev,
                "title": title,
                "description": desc,
                "mitigation": mit,
                "source_clause_ids": clause_ids,
            }
        )

    clauses_ids = [c.id for c in project.source_clauses[:3]]
    ref = clauses_ids or ([cid] if cid else [])

    if re.search(r"\b(password|auth|login|session|token)\b", blob, re.I):
        add(
            "security",
            "high",
            "Authentication/session hardening",
            "Credential flows often accumulate edge-case vulnerabilities.",
            "Enforce least-privilege RBAC, rotate secrets, add MFA where applicable.",
            ref,
        )
    if re.search(r"\b(gdpr|hipaa|pci|privacy|pii)\b", blob, re.I):
        add(
            "compliance",
            "high",
            "Data handling & residency",
            "Personal data touches amplify compliance obligations.",
            "Data inventory, retention limits, DPIA/privacy review before GA.",
            ref,
        )
    if re.search(r"\b(scale|million|throughput|rps|latency|performance)\b", blob, re.I):
        add(
            "performance",
            "medium",
            "Load & latency assumptions",
            "Performance targets without measurement plans risk late rework.",
            "Define SLOs, load tests on critical paths, caching strategy.",
            ref,
        )
    add(
        "dependency",
        "medium",
        "Third-party / LLM reliance",
        "External models/services introduce availability & correctness risk.",
        "Mock/offline path for demos; timeouts, fallbacks, eval harness for outputs.",
        ref,
    )
    add(
        "ux",
        "low",
        "Clarity of failure UX",
        "Users need actionable recovery when requirements are ambiguous.",
        "Surface ambiguity resolutions inline; progressive disclosure for errors.",
        ref,
    )

    return {"risks": risks[:8]}


def mock_chat_reply(project: Project, user_message: str) -> str:
    """Plain-text assistant reply for offline demos."""
    um = user_message.strip().lower()
    lines = [
        "**Helix (demo mode)** — Azure OpenAI is not configured; here's a grounded snapshot.",
        "",
        f"- **Project**: `{project.id}` · stories **{len(project.stories)}**, tasks **{len(project.tasks)}**, tests **{len(project.test_cases)}**",
        f"- **Ambiguities**: **{len(project.ambiguities)}** · **Risks**: **{len(project.risks)}**",
    ]
    ids = []
    for s in project.stories[:3]:
        ids.append(s.id)
    for t in project.tasks[:3]:
        ids.append(t.id)
    if ids:
        lines.append(f"- **Example artifact ids** you can trace: {', '.join(ids)}")

    if "risk" in um or "security" in um:
        r = next((x for x in project.risks if x.category.value == "security"), None)
        if r:
            lines.append(f"- Security risk **`{r.id}`**: {r.title}")

    if "test" in um or "qa" in um:
        tc = project.test_cases[:1]
        if tc:
            lines.append(
                f"- Sample test **`{tc[0].id}`** ({tc[0].type.value}): {tc[0].title}"
            )

    lines.append("")
    lines.append(
        "_Configure Azure OpenAI for full conversational reasoning; mock mode keeps "
        "the workspace populated for judging._"
    )
    return "\n".join(lines)
