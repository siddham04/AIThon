"""Requirement-to-Code Impact Analysis.

Given a single requirement (and optionally the project's existing system
catalog), predict how the change ripples through the codebase:

  - which COMPONENTS are affected (and whether each is new / modified /
    extended / replaced)
  - which APIs need to change or be added
  - which DATABASE entities need migrations
  - which FILES / modules will be touched
  - which external DEPENDENCIES come along (SMS provider, payment, etc.)
  - the RISKS this change introduces, with mitigations
  - a sequenced ROLLOUT plan
  - a small graph (nodes + edges) the UI can render

The catalog of "existing" components is derived from the project's
Architecture Brief (Solution Architect output) when available, so the AI
can correctly distinguish "modify the existing User Service" from "add a
new SMS Service".
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from ..models import (
    AffectedItem,
    APIImpact,
    ArchitectureLayer,
    BlastLabel,
    ComponentImpact,
    DataImpact,
    DependencyImpact,
    FileImpact,
    ImpactAnalysisReport,
    ImpactChangeType,
    ImpactGraph,
    ImpactGraphEdge,
    ImpactGraphNode,
    ImpactRisk,
    Project,
    RolloutStep,
    Severity,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.impact_analysis")


# --------------------------------------------------------------------- #
# Catalog from project
# --------------------------------------------------------------------- #


def _catalog_from_project(project: Project) -> List[Dict[str, str]]:
    """Compact catalog the LLM can ground itself in.

    Pulls components from the Architecture Brief when present.
    """
    if project is None or project.architecture_brief is None:
        return []
    catalog: List[Dict[str, str]] = []
    for c in project.architecture_brief.components:
        catalog.append(
            {
                "name": c.name,
                "layer": c.layer.value
                if hasattr(c.layer, "value")
                else str(c.layer),
                "responsibility": c.responsibility,
            }
        )
    # Append data entities so the LLM can recognise existing ones
    for entity in project.architecture_brief.data_entities:
        catalog.append(
            {
                "name": entity,
                "layer": "data",
                "responsibility": "Existing data entity",
            }
        )
    return catalog


def _catalog_block(catalog: List[Dict[str, str]]) -> str:
    if not catalog:
        return (
            "(No system catalog provided. Treat the system as a fresh build "
            "and mark every component as 'new' unless the requirement implies "
            "a clearly existing piece.)\n"
        )
    lines = ["Existing system catalog (treat these as already in place):"]
    for c in catalog:
        lines.append(f"  - {c['name']}  [{c.get('layer', 'service')}] — {c.get('responsibility', '').strip()}")
    return "\n".join(lines)


# --------------------------------------------------------------------- #
# AI prompt
# --------------------------------------------------------------------- #


_SYSTEM = """You are an Impact Analysis assistant on a senior engineering team.

Given a requirement and (optionally) the existing system catalog, predict
the precise blast radius of the change. You must:

  - List every COMPONENT affected, with `change_type` ∈
    {new, modify, extend, replace, remove}. If the catalog has it, mark
    `is_new=false`. If the catalog does NOT have it, mark `is_new=true`.
  - Enumerate each new or modified API (method + path) and what changes.
  - Enumerate each database entity touched and the columns / tables.
  - Optionally enumerate the FILES (paths) you'd expect to edit.
  - List external DEPENDENCIES (libraries, SaaS, services) the change pulls in.
  - List the RISKS this change introduces with severity + mitigation.
  - Propose a ROLLOUT sequence (numbered steps) — what to ship first, last.
  - Build a small GRAPH: nodes = component ids you cited; edges =
    "calls" / "writes" / "reads" / "depends-on" relationships you implied.

Be specific. Don't invent components that aren't justified by the
requirement. If the catalog has a name that fits, USE IT verbatim.
""".strip()


_SCHEMA = """{
  "summary": "string — 1-2 sentence headline",
  "components": [
    {
      "component": "string",
      "layer": "frontend|service|data|infra|integration",
      "change_type": "new|modify|extend|replace|remove",
      "is_new": false,
      "rationale": "string",
      "confidence": 0.8
    }
  ],
  "apis": [
    {
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/example",
      "change_type": "new|modify|extend|remove",
      "description": "string"
    }
  ],
  "data": [
    {
      "entity": "string",
      "change_type": "new|modify|extend|remove",
      "fields": ["string"],
      "description": "string"
    }
  ],
  "files": [
    {"path": "string", "change_type": "new|modify|extend|remove", "description": "string"}
  ],
  "dependencies": [
    {"name": "string", "kind": "library|service|saas|protocol", "is_new": true, "description": "string"}
  ],
  "risks": [
    {"title": "string", "severity": "low|medium|high|critical", "description": "string", "mitigation": "string"}
  ],
  "rollout": [
    {"order": 1, "title": "string", "description": "string", "component_ids": ["string"]}
  ],
  "graph": {
    "edges": [
      {"source": "string — component name", "target": "string — component name", "label": "calls|writes|reads|depends-on"}
    ]
  }
}"""


# --------------------------------------------------------------------- #
# Heuristic fallback
# --------------------------------------------------------------------- #


# Demo-calibrated change sets (requirement phrase → affected surfaces)
_CHANGE_SCENARIOS: List[tuple[re.Pattern[str], List[tuple[str, str, str]]]] = [
    (
        re.compile(r"\b(add|enable|introduce)\s+otp\s+login\b|\botp\s+login\b", re.I),
        [
            ("Login API", "api", "modify"),
            ("User Service", "service", "modify"),
            ("Mobile App", "frontend", "modify"),
        ],
    ),
    (
        re.compile(r"\b(add|change|update)\s+.*\blogin\b|\blogin\s+flow\b", re.I),
        [
            ("Login API", "api", "modify"),
            ("User Service", "service", "modify"),
            ("Mobile App", "frontend", "modify"),
        ],
    ),
]


_VERB_HINTS: "OrderedDict[str, tuple[str, ...]]" = OrderedDict(
    (
        ("login", ("Login API", "User Service", "Mobile App", "Session Store")),
        ("auth", ("Authentication Middleware", "User Service", "Token Service")),
        ("otp", ("Login API", "User Service", "OTP Service", "SMS Service")),
        ("password", ("User Service", "Password Reset API", "Email Service")),
        ("notif", ("Notification Service", "Email Service", "User Service")),
        ("payment", ("Payment Service", "Billing API", "Transaction Store")),
        ("billing", ("Billing API", "Subscription Service", "Invoice Store")),
        ("upload", ("File Upload API", "Object Storage", "Virus Scanner")),
        ("search", ("Search Service", "Index Pipeline", "Search API")),
        ("dashboard", ("Dashboard UI", "Reporting API", "Analytics Service")),
        ("export", ("Export Service", "Reporting API")),
        ("import", ("Import Service", "Validation Pipeline")),
        ("admin", ("Admin UI", "Authorization Middleware", "Audit Log")),
        ("audit", ("Audit Log", "Event Bus")),
        ("sso", ("Identity Provider", "Authentication Middleware", "User Service")),
    )
)


def _match_test_cases(requirement: str, project: Optional[Project]) -> List[AffectedItem]:
    """Link existing test cases that likely need updates."""
    if not project or not project.test_cases:
        return []
    text = (requirement or "").lower()
    keys = []
    for token in ("otp", "login", "auth", "password", "session", "mfa"):
        if token in text:
            keys.append(token)
    if not keys:
        return []
    out: List[AffectedItem] = []
    for tc in project.test_cases:
        blob = f"{tc.title} {getattr(tc, 'description', '') or ''}".lower()
        if any(k in blob for k in keys):
            out.append(
                AffectedItem(
                    name=tc.title,
                    kind="test",
                    change_type="modify",
                    detail=tc.id,
                )
            )
    if not out and keys:
        out.append(
            AffectedItem(
                name="Test Cases",
                kind="test",
                change_type="modify",
                detail="Auth / login regression suite",
            )
        )
    return out[:12]


def _build_affected_list(
    requirement: str,
    components: List[ComponentImpact],
    project: Optional[Project],
) -> List[AffectedItem]:
    """Copilot-facing flat list: APIs, services, apps, tests."""
    text = (requirement or "").strip()
    affected: List[AffectedItem] = []
    seen: set[str] = set()

    for pat, items in _CHANGE_SCENARIOS:
        if pat.search(text):
            for name, kind, change in items:
                key = name.lower()
                if key not in seen:
                    seen.add(key)
                    affected.append(
                        AffectedItem(name=name, kind=kind, change_type=change)
                    )
            break

    if not affected:
        for c in components:
            key = c.component.lower()
            if key in seen:
                continue
            seen.add(key)
            kind = "api" if "api" in key else (
                "frontend" if c.layer == ArchitectureLayer.FRONTEND else "service"
            )
            affected.append(
                AffectedItem(
                    name=c.component,
                    kind=kind,
                    change_type=c.change_type.value,
                    detail=(c.rationale or "")[:120],
                )
            )

    for tc_item in _match_test_cases(text, project):
        key = tc_item.name.lower()
        if key not in seen:
            seen.add(key)
            affected.append(tc_item)

    if re.search(r"\botp\b|\blogin\b", text, re.I) and not any(
        a.kind == "test" for a in affected
    ):
        affected.append(
            AffectedItem(
                name="Test Cases",
                kind="test",
                change_type="modify",
                detail="Auth / OTP regression suite",
            )
        )

    return affected


def _heuristic_report(
    requirement: str,
    catalog: List[Dict[str, str]],
) -> Dict[str, Any]:
    text = (requirement or "").strip()
    if not text:
        return {
            "summary": "No requirement text was provided.",
            "components": [],
            "apis": [],
            "data": [],
            "files": [],
            "dependencies": [],
            "risks": [],
            "rollout": [],
            "graph": {"edges": []},
        }

    catalog_names = {c["name"].lower() for c in catalog}
    proposed: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    txt_low = text.lower()
    for verb, components in _VERB_HINTS.items():
        if verb in txt_low:
            for comp in components:
                key = comp.lower()
                is_known = any(comp.lower() == n for n in catalog_names)
                if comp not in proposed:
                    proposed[comp] = {
                        "component": comp,
                        "layer": "service" if "api" not in comp.lower() else "service",
                        "change_type": "modify" if is_known else "new",
                        "is_new": not is_known,
                        "rationale": f"Heuristic: keyword '{verb}' typically touches {comp}.",
                        "confidence": 0.55,
                    }

    if not proposed:
        proposed["Application Service"] = {
            "component": "Application Service",
            "layer": "service",
            "change_type": "modify",
            "is_new": False,
            "rationale": "Default heuristic — no specific keyword matched.",
            "confidence": 0.4,
        }

    return {
        "summary": (
            f"Heuristic blast radius — {len(proposed)} component(s) likely "
            "touched. Run AI analysis for higher fidelity."
        ),
        "components": list(proposed.values()),
        "apis": [],
        "data": [],
        "files": [],
        "dependencies": [],
        "risks": [],
        "rollout": [],
        "graph": {"edges": []},
    }


# --------------------------------------------------------------------- #
# Coercion helpers
# --------------------------------------------------------------------- #


def _coerce_layer(raw: Any) -> ArchitectureLayer:
    s = str(raw or "service").lower().strip()
    try:
        return ArchitectureLayer(s)
    except ValueError:
        return ArchitectureLayer.SERVICE


def _coerce_change(raw: Any) -> ImpactChangeType:
    s = str(raw or "modify").lower().strip()
    try:
        return ImpactChangeType(s)
    except ValueError:
        return ImpactChangeType.MODIFY


def _coerce_severity(raw: Any) -> Severity:
    s = str(raw or "medium").lower().strip()
    try:
        return Severity(s)
    except ValueError:
        return Severity.MEDIUM


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "node"


# --------------------------------------------------------------------- #
# Blast radius
# --------------------------------------------------------------------- #


def _blast_radius(
    components: List[ComponentImpact],
    risks: List[ImpactRisk],
    dependencies: List[DependencyImpact],
    apis: List[APIImpact],
    data: List[DataImpact],
) -> tuple[float, BlastLabel]:
    """0..100 score representing how big this change is."""
    # Component impact: new > replace > extend > modify
    weight_change = {
        ImpactChangeType.NEW: 14,
        ImpactChangeType.REPLACE: 12,
        ImpactChangeType.EXTEND: 8,
        ImpactChangeType.MODIFY: 6,
        ImpactChangeType.REMOVE: 7,
        ImpactChangeType.UNKNOWN: 5,
    }
    score = sum(weight_change[c.change_type] for c in components)
    score += 4 * len(apis)
    score += 5 * len(data)
    score += 3 * sum(1 for d in dependencies if d.is_new)

    sev_w = {"low": 2, "medium": 5, "high": 9, "critical": 14}
    score += sum(sev_w[r.severity.value] for r in risks)

    score = max(0.0, min(100.0, score))
    if score >= 75:
        label = BlastLabel.SWEEPING
    elif score >= 55:
        label = BlastLabel.HIGH
    elif score >= 30:
        label = BlastLabel.MEDIUM
    else:
        label = BlastLabel.LOW
    return round(score, 1), label


# --------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------- #


async def analyze_impact(
    requirement: str,
    project: Optional[Project] = None,
    *,
    use_ai: bool = True,
) -> ImpactAnalysisReport:
    """Run impact analysis on a single requirement."""
    catalog = _catalog_from_project(project) if project else []
    payload: Dict[str, Any]

    ai = get_ai_service()
    method = "heuristic"
    if use_ai and ai.enabled and (requirement or "").strip():
        try:
            user = (
                f"{_catalog_block(catalog)}\n\n"
                f"Requirement: {requirement.strip()}\n\n"
                "Return ONLY valid JSON that matches this schema exactly:\n\n"
                f"{_SCHEMA}\n\n"
                "No prose, no markdown fences."
            )
            payload = await ai.complete_json(_SYSTEM, user, max_tokens=3500)
            method = "ai"
        except Exception:  # pragma: no cover — defensive
            logger.exception("Impact analysis AI call failed; using heuristics")
            payload = _heuristic_report(requirement, catalog)
    else:
        payload = _heuristic_report(requirement, catalog)

    components = _build_components(payload.get("components") or [], catalog)
    apis = _build_apis(payload.get("apis") or [])
    data = _build_data(payload.get("data") or [])
    files = _build_files(payload.get("files") or [])
    dependencies = _build_deps(payload.get("dependencies") or [])
    risks = _build_risks(payload.get("risks") or [])
    rollout = _build_rollout(payload.get("rollout") or [], components)
    graph = _build_graph(components, payload.get("graph") or {})
    score, label = _blast_radius(components, risks, dependencies, apis, data)
    affected = _build_affected_list(requirement, components, project)
    summary = str(payload.get("summary") or "").strip()
    if not summary and affected:
        summary = (
            f"Change touches {len(affected)} surface(s) including "
            f"{', '.join(a.name for a in affected[:4])}."
        )
    if not summary:
        summary = f"Touches {len(components)} component(s); blast radius {score}."

    return ImpactAnalysisReport(
        requirement=(requirement or "").strip(),
        project_id=(project.id if project else None),
        blast_radius=score,
        blast_label=label,
        summary=summary,
        method=method,
        affected=affected,
        components=components,
        apis=apis,
        data=data,
        files=files,
        dependencies=dependencies,
        risks=risks,
        rollout=rollout,
        graph=graph,
    )


# --------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------- #


def _build_components(
    raw: List[Dict[str, Any]],
    catalog: List[Dict[str, str]],
) -> List[ComponentImpact]:
    catalog_index = {c["name"].lower(): c for c in catalog}
    out: List[ComponentImpact] = []
    seen: set[str] = set()
    for entry in raw:
        try:
            name = str(entry.get("component") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            change = _coerce_change(entry.get("change_type"))
            existing = catalog_index.get(key)
            is_new_raw = entry.get("is_new")
            if existing is not None:
                is_new = False
            elif is_new_raw is not None:
                is_new = bool(is_new_raw)
            else:
                is_new = change == ImpactChangeType.NEW
            if is_new and change == ImpactChangeType.MODIFY:
                change = ImpactChangeType.NEW
            layer = _coerce_layer(
                entry.get("layer") or (existing.get("layer") if existing else "service")
            )
            confidence_raw = entry.get("confidence", 0.7)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.7
            confidence = max(0.0, min(1.0, confidence))
            out.append(
                ComponentImpact(
                    component=name,
                    layer=layer,
                    change_type=change,
                    is_new=is_new,
                    rationale=str(entry.get("rationale") or "").strip(),
                    confidence=round(confidence, 2),
                )
            )
        except Exception:
            continue
    return out


def _build_apis(raw: List[Dict[str, Any]]) -> List[APIImpact]:
    out: List[APIImpact] = []
    for entry in raw:
        try:
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            method = str(entry.get("method") or "GET").upper().strip()
            out.append(
                APIImpact(
                    method=method,
                    path=path,
                    change_type=_coerce_change(entry.get("change_type")),
                    description=str(entry.get("description") or "").strip(),
                )
            )
        except Exception:
            continue
    return out


def _build_data(raw: List[Dict[str, Any]]) -> List[DataImpact]:
    out: List[DataImpact] = []
    for entry in raw:
        try:
            entity = str(entry.get("entity") or "").strip()
            if not entity:
                continue
            out.append(
                DataImpact(
                    entity=entity,
                    change_type=_coerce_change(entry.get("change_type")),
                    fields=[str(f).strip() for f in (entry.get("fields") or []) if str(f).strip()],
                    description=str(entry.get("description") or "").strip(),
                )
            )
        except Exception:
            continue
    return out


def _build_files(raw: List[Dict[str, Any]]) -> List[FileImpact]:
    out: List[FileImpact] = []
    for entry in raw:
        try:
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            out.append(
                FileImpact(
                    path=path,
                    change_type=_coerce_change(entry.get("change_type")),
                    description=str(entry.get("description") or "").strip(),
                )
            )
        except Exception:
            continue
    return out


def _build_deps(raw: List[Dict[str, Any]]) -> List[DependencyImpact]:
    out: List[DependencyImpact] = []
    for entry in raw:
        try:
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            out.append(
                DependencyImpact(
                    name=name,
                    kind=str(entry.get("kind") or "library").strip().lower(),
                    is_new=bool(entry.get("is_new", True)),
                    description=str(entry.get("description") or "").strip(),
                )
            )
        except Exception:
            continue
    return out


def _build_risks(raw: List[Dict[str, Any]]) -> List[ImpactRisk]:
    out: List[ImpactRisk] = []
    for entry in raw:
        try:
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            out.append(
                ImpactRisk(
                    title=title,
                    severity=_coerce_severity(entry.get("severity")),
                    description=str(entry.get("description") or "").strip(),
                    mitigation=str(entry.get("mitigation") or "").strip(),
                )
            )
        except Exception:
            continue
    return out


def _build_rollout(
    raw: List[Dict[str, Any]],
    components: List[ComponentImpact],
) -> List[RolloutStep]:
    valid_components = {c.component.lower() for c in components}
    out: List[RolloutStep] = []
    for i, entry in enumerate(raw):
        try:
            order_val = entry.get("order", i + 1)
            try:
                order = int(order_val)
            except (TypeError, ValueError):
                order = i + 1
            ids = [
                str(s).strip()
                for s in (entry.get("component_ids") or [])
                if str(s).strip().lower() in valid_components
            ]
            out.append(
                RolloutStep(
                    order=order,
                    title=str(entry.get("title") or f"Step {order}").strip(),
                    description=str(entry.get("description") or "").strip(),
                    component_ids=ids,
                )
            )
        except Exception:
            continue
    out.sort(key=lambda r: r.order)
    return out


def _build_graph(
    components: List[ComponentImpact],
    raw_graph: Dict[str, Any],
) -> ImpactGraph:
    if not components:
        return ImpactGraph()
    nodes: List[ImpactGraphNode] = []
    name_to_id: Dict[str, str] = {}
    used_ids: set[str] = set()
    for c in components:
        base = _slug(c.component)
        node_id = base
        n = 2
        while node_id in used_ids:
            node_id = f"{base}-{n}"
            n += 1
        used_ids.add(node_id)
        name_to_id[c.component.lower()] = node_id
        nodes.append(
            ImpactGraphNode(
                id=node_id,
                label=c.component,
                layer=c.layer,
                change_type=c.change_type,
                is_new=c.is_new,
            )
        )

    edges: List[ImpactGraphEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in (raw_graph.get("edges") or []) if raw_graph else []:
        try:
            src = name_to_id.get(str(entry.get("source") or "").strip().lower())
            dst = name_to_id.get(str(entry.get("target") or "").strip().lower())
            if not src or not dst or src == dst:
                continue
            label = str(entry.get("label") or "").strip()
            key = (src, dst, label)
            if key in seen:
                continue
            seen.add(key)
            edges.append(ImpactGraphEdge(source=src, target=dst, label=label))
        except Exception:
            continue

    return ImpactGraph(nodes=nodes, edges=edges)
