"""Architecture Diagram Generator.

Outputs a Mermaid `flowchart TD` for a requirement. Hybrid: a
deterministic skeleton always produces something renderable; the LLM
(when enabled) replaces the body with a richer, requirement-specific
diagram.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from ..models import ArchitectureDiagram
from .ai_service import get_ai_service

logger = logging.getLogger("helix.diagram_generator")


# ---------- Heuristic skeleton ----------------------------------------- #


_LAYER_HINTS: List[tuple[re.Pattern[str], str, str, str]] = [
    # (pattern, layer_id, label, parent_after)
    (
        re.compile(r"\b(notif|email|sms|push)\b", re.I),
        "Notif", "Notification Service", "Service",
    ),
    (
        re.compile(r"\b(otp|2fa|mfa|two[- ]?factor)\b", re.I),
        "OTPSvc", "OTP Service", "Service",
    ),
    (
        re.compile(r"\b(payment|billing|invoice|stripe|razorpay)\b", re.I),
        "Pay", "Payment Service", "Service",
    ),
    (
        re.compile(r"\b(report|dashboard|analytics)\b", re.I),
        "Analytics", "Analytics Service", "Service",
    ),
    (
        re.compile(r"\b(search|elastic|index)\b", re.I),
        "Search", "Search Service", "Service",
    ),
    (
        re.compile(r"\b(file\s+upload|attach(ment)?|s3|object\s+store)\b", re.I),
        "Storage", "Object Storage", "DB",
    ),
    (
        re.compile(r"\b(third[- ]?party|external\s+api|webhook)\b", re.I),
        "ExtAPI", "External API", "Service",
    ),
    (
        re.compile(r"\b(machine\s+learning|llm|inference|embedding)\b", re.I),
        "ML", "ML / LLM Inference", "Service",
    ),
    (
        re.compile(r"\b(queue|kafka|rabbitmq|sqs|background\s+job|worker)\b", re.I),
        "Queue", "Message Queue", "Service",
    ),
    (
        re.compile(r"\b(cache|redis|memcache)\b", re.I),
        "Cache", "Cache (Redis)", "Service",
    ),
]


def _safe_label(s: str) -> str:
    """Mermaid labels can't contain unescaped quotes/brackets."""
    return s.replace('"', "'").replace("[", "(").replace("]", ")").strip()


_AUTH_FLOW = """flowchart TD
  classDef ui fill:#ede9fe,stroke:#6d28d9,color:#3b0764;
  classDef svc fill:#dbeafe,stroke:#1d4ed8,color:#0c2657;
  classDef db fill:#dcfce7,stroke:#15803d,color:#14532d;
  User(["User"]):::ui
  Login["Login"]:::ui
  Dashboard["Dashboard"]:::ui
  AuthSvc["Auth Service"]:::svc
  UserSvc["User Service"]:::svc
  Users[("Users")]:::db
  Sessions[("Sessions")]:::db
  User --> Login
  User --> Dashboard
  Login --> AuthSvc
  Dashboard --> UserSvc
  AuthSvc --> Users
  AuthSvc --> Sessions
  UserSvc --> Users"""


def _heuristic_diagram(text: str, *, title: str = "") -> ArchitectureDiagram:
    text = (text or "").strip()
    if not text:
        return ArchitectureDiagram(
            title=title or "Architecture diagram",
            mermaid="flowchart TD\n  empty[\"No requirement provided\"]",
            nodes_count=1,
            edges_count=0,
            description="Empty requirement.",
            method="heuristic",
        )

    if re.search(
        r"\b(authentication|authorize|login|sign[- ]?up|register|jwt|session|"
        r"password|otp|mfa|oauth)\b",
        text,
        re.I,
    ):
        nodes, edges = _count_nodes_edges(_AUTH_FLOW)
        return ArchitectureDiagram(
            title=title or "User authentication architecture",
            mermaid=_AUTH_FLOW,
            nodes_count=nodes,
            edges_count=edges,
            description="Auth-specific system flow (heuristic).",
            method="heuristic",
        )

    # Pick services that match the requirement.
    extras: List[tuple[str, str]] = []  # (id, label)
    seen: set[str] = set()
    for pat, nid, label, _parent in _LAYER_HINTS:
        if nid in seen:
            continue
        if pat.search(text):
            extras.append((nid, label))
            seen.add(nid)

    has_db = bool(re.search(r"\b(database|db|postgres|mysql|mongo|sql)\b", text, re.I))
    has_external = any(nid == "ExtAPI" for nid, _ in extras)

    title_label = _safe_label(title or "Architecture")

    lines: List[str] = ["flowchart TD"]
    lines.append('  classDef ext fill:#fef3c7,stroke:#d97706,color:#7c2d12;')
    lines.append('  classDef db  fill:#dcfce7,stroke:#15803d,color:#14532d;')
    lines.append('  classDef ui  fill:#ede9fe,stroke:#6d28d9,color:#3b0764;')
    lines.append('  classDef svc fill:#dbeafe,stroke:#1d4ed8,color:#0c2657;')

    lines.append('  User(["User"]):::ui')
    lines.append('  FE["Frontend"]:::ui')
    lines.append('  GW["API Gateway"]:::svc')
    lines.append('  Service["Application Service"]:::svc')

    edges = [
        "User --> FE",
        "FE --> GW",
        "GW --> Service",
    ]

    nodes_count = 4

    for nid, label in extras:
        lines.append(f'  {nid}["{_safe_label(label)}"]:::svc')
        edges.append(f"Service --> {nid}")
        nodes_count += 1

    if has_db or extras:
        lines.append('  DB[("Database")]:::db')
        edges.append("Service --> DB")
        nodes_count += 1
        # Some services typically WRITE to DB
        for nid, _label in extras:
            if nid in {"OTPSvc", "Pay", "Analytics", "Search"}:
                edges.append(f"{nid} --> DB")

    if has_external and "ExtAPI" not in seen:
        lines.append('  ExtAPI["External API"]:::ext')
        edges.append("Service --> ExtAPI")
        nodes_count += 1

    for e in edges:
        lines.append(f"  {e}")

    return ArchitectureDiagram(
        title=title_label,
        mermaid="\n".join(lines),
        nodes_count=nodes_count,
        edges_count=len(edges),
        description=(
            f"Heuristic skeleton with {nodes_count} nodes and "
            f"{len(edges)} edges, derived from keywords."
        ),
        method="heuristic",
    )


# ---------- AI Mermaid generation -------------------------------------- #


_AI_SYSTEM = """You generate ARCHITECTURE diagrams in Mermaid. RULES:

1. Output ONLY a Mermaid flowchart in `flowchart TD` syntax — no
   prose, no markdown fences, no commentary.
2. Nodes are real architectural building blocks: User, Frontend / UI,
   Gateway, individual Services, External APIs, Queues, Cache,
   Database. Use NAMES from the requirement when possible.
3. Each node id is short PascalCase (no spaces). Labels go in
   square brackets with double quotes.
4. Apply the provided classDef styles to every node:
     classDef ui  fill:#ede9fe,stroke:#6d28d9;
     classDef svc fill:#dbeafe,stroke:#1d4ed8;
     classDef ext fill:#fef3c7,stroke:#d97706;
     classDef db  fill:#dcfce7,stroke:#15803d;
5. 6-12 nodes is ideal.
6. ALWAYS include a User node and a clear top-down flow.
7. Use --> for sync calls and -.-> for async / events. Label edges
   sparingly with |"label"| only when necessary.
""".strip()


def _looks_like_mermaid(s: str) -> bool:
    s = s.strip()
    return bool(s) and (s.startswith("flowchart") or s.startswith("graph"))


def _strip_fences(s: str) -> str:
    s = s.strip()
    # Remove ```mermaid ... ``` or ``` ... ``` fences if the LLM ignored rule 1.
    m = re.match(r"^```(?:mermaid)?\s*(.*?)```$", s, flags=re.DOTALL | re.I)
    if m:
        return m.group(1).strip()
    return s


def _count_nodes_edges(mermaid: str) -> tuple[int, int]:
    body = mermaid.splitlines()
    edges = 0
    node_ids: set[str] = set()
    for line in body:
        line = line.strip()
        if line.startswith(("flowchart", "graph", "classDef", "click", "%%")):
            continue
        # Edges
        if "-->" in line or "-.->" in line or "==>" in line:
            edges += 1
            for tok in re.split(r"-+\.?->|==>", line):
                tok = tok.strip()
                m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)", tok)
                if m:
                    node_ids.add(m.group(1))
        else:
            m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)", line)
            if m:
                node_ids.add(m.group(1))
    return len(node_ids), edges


async def _ai_diagram(text: str, *, title: str) -> Optional[ArchitectureDiagram]:
    ai = get_ai_service()
    if not ai.enabled:
        return None

    user = (
        f"Requirement to diagram:\n---\n{text[:3500]}\n---\n\n"
        "Output ONLY the Mermaid flowchart TD body (no fences, no prose)."
    )
    try:
        # We deliberately use raw chat (NOT JSON) here — Mermaid is a
        # text format, not JSON, so JSON-mode isn't applicable.
        out = await ai.complete_text(_AI_SYSTEM, user, max_tokens=1400)
    except Exception:  # pragma: no cover
        logger.exception("Diagram AI generation failed")
        return None

    if not out:
        return None

    body = _strip_fences(out)
    if not _looks_like_mermaid(body):
        # Sometimes the model leads with a header like "Here is the diagram:"
        # — try to grab the first flowchart block.
        m = re.search(r"(flowchart\s+TD[\s\S]+)$", body, flags=re.I | re.M)
        if not m:
            return None
        body = m.group(1).strip()

    nodes, edges = _count_nodes_edges(body)
    if nodes == 0:
        return None

    return ArchitectureDiagram(
        title=title or "Architecture diagram",
        mermaid=body,
        nodes_count=nodes,
        edges_count=edges,
        description=f"AI-generated flowchart with {nodes} nodes and {edges} edges.",
        method="hybrid",
    )


# ---------- Public API ------------------------------------------------- #


async def generate_diagram(
    text: str,
    *,
    title: str = "",
    use_ai: bool = True,
) -> ArchitectureDiagram:
    if use_ai:
        ai_out = await _ai_diagram(text, title=title)
        if ai_out is not None:
            return ai_out
    return _heuristic_diagram(text, title=title)
