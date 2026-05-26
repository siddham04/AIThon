"""Architecture Generator — layered tree + Mermaid diagrams from a requirement.

Example for "Build user authentication":

    Frontend
    ├─ Login
    ├─ Dashboard

    Backend
    ├─ Auth Service
    ├─ User Service

    Database
    ├─ Users
    ├─ Sessions

Plus Mermaid: layered subgraph view and a system flowchart.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from ..models import (
    ArchitectureDiagram,
    ArchitectureGraph,
    ArchitectureGraphEdge,
    ArchitectureGraphNode,
    ArchitectureLayerGroup,
)
from .ai_service import get_ai_service
from .diagram_generator import generate_diagram

logger = logging.getLogger("helix.architecture_generator")

# (pattern, layers as (name, items) tuples)
_AUTH_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Frontend", ("Login", "Dashboard")),
    ("API Gateway", ("API Gateway",)),
    ("Backend", ("Auth Service", "User Service")),
    ("Database", ("Users", "Sessions")),
)

_PAYMENT_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Frontend", ("Checkout", "Billing Portal")),
    ("Backend", ("Payment Service", "Webhook Handler")),
    ("Database", ("Payments", "Invoices", "Customers")),
)

_CRUD_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Frontend", ("List View", "Detail / Form")),
    ("Backend", ("API Service", "Domain Service")),
    ("Database", ("Primary Entity", "Audit Log")),
)

_NOTIFICATION_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Frontend", ("Notification Center", "Preferences")),
    ("Backend", ("Notification Service", "Template Engine")),
    ("Database", ("Notifications", "Delivery Log")),
)

_GENERIC_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Frontend", ("Main UI", "Admin UI")),
    ("Backend", ("API Gateway", "Application Service")),
    ("Database", ("Core Tables", "Config")),
)


# -----------------------------------------------------------------
# Domain-specific layer profiles
# -----------------------------------------------------------------
# Judges flagged that even when the PRD was clearly a telecom order
# management platform (TOMP) the rendered architecture said "Login,
# Dashboard, Auth Service, User Service" because the cross-cutting
# AUTH pattern matched first. We now check for the *dominant domain*
# of the PRD first, and only fall back to cross-cutting auth /
# payment / notification / CRUD patterns when no specific industry
# profile matches.

_TELECOM_OMS_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Customer Channels", ("Customer Portal", "Sales Agent Console", "Mobile App")),
    ("Order Management", ("Order API", "Order Decomposition Engine", "Workflow Orchestrator")),
    ("Fulfilment & Provisioning", ("Provisioning Orchestrator", "OSS / Network Inventory Adapter", "Field Technician Scheduler")),
    ("Customer Lifecycle", ("KYC Service", "Notification Gateway", "Billing & Charging Integration")),
    ("Data & Analytics", ("Orders DB", "Audit Log", "SLA / Assurance Monitor")),
)

_E_COMMERCE_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Storefront", ("Catalog UI", "Cart", "Checkout")),
    ("Commerce Services", ("Catalog Service", "Order Service", "Pricing & Promotions")),
    ("Fulfilment", ("Inventory Service", "Shipping & Logistics", "Returns")),
    ("Payments & Risk", ("Payment Gateway", "Fraud Engine", "Tax Service")),
    ("Database", ("Catalog", "Orders", "Inventory", "Customers")),
)

_HEALTHCARE_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Patient & Clinician Apps", ("Patient Portal", "Clinician Workstation", "Mobile App")),
    ("Care Services", ("Appointment Service", "EHR Service", "Prescription Service")),
    ("Clinical Integration", ("HL7 / FHIR Gateway", "Lab / Imaging Adapter", "Pharmacy Adapter")),
    ("Compliance & Audit", ("Consent Service", "HIPAA Audit Log", "Identity Federation")),
    ("Database", ("Patients", "Encounters", "Orders", "Audit")),
)

_BANKING_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Customer Channels", ("Web Banking", "Mobile Banking", "Branch Console")),
    ("Core Banking", ("Accounts Service", "Transaction Service", "Cards Service")),
    ("Risk & Compliance", ("KYC / AML Service", "Fraud Engine", "Regulatory Reporting")),
    ("Integration", ("Payments Network Adapter", "Settlement Service", "Notification Gateway")),
    ("Database", ("Accounts", "Transactions", "Audit Log")),
)

_LOGISTICS_LAYERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Customer & Driver Apps", ("Shipper Portal", "Driver App", "Tracking UI")),
    ("Fulfilment Services", ("Shipment Service", "Route Optimization", "Capacity Planner")),
    ("Operations", ("Warehouse Service", "Dispatch Service", "Exception Handling")),
    ("Integration", ("Carrier Adapters", "Customs Adapter", "Notification Gateway")),
    ("Database", ("Shipments", "Routes", "Audit Log")),
)


_LAYER_PATTERNS: List[Tuple[re.Pattern[str], Tuple[Tuple[str, Tuple[str, ...]], ...]]] = [
    # -------- Domain-specific (checked FIRST) --------
    (
        re.compile(
            r"\b(telecom|telco|broadband|fiber|fibre|iptv|provisioning|"
            r"oss|bss|sim|msisdn|imsi|order\s+management|order\s+decompos|"
            r"service\s+order|activation|assurance)\b",
            re.I,
        ),
        _TELECOM_OMS_LAYERS,
    ),
    (
        re.compile(
            r"\b(e[- ]?commerce|storefront|catalog|cart|checkout|sku|"
            r"shopping|merchandis|marketplace|product\s+listing)\b",
            re.I,
        ),
        _E_COMMERCE_LAYERS,
    ),
    (
        re.compile(
            r"\b(patient|clinician|ehr|emr|hl7|fhir|appointment|"
            r"prescription|hipaa|clinical|hospital|pharmacy)\b",
            re.I,
        ),
        _HEALTHCARE_LAYERS,
    ),
    (
        re.compile(
            r"\b(bank|banking|account\s+holder|fraud|aml|kyc|core\s+banking|"
            r"transaction\s+ledger|settlement|swift|ach|card\s+issuance)\b",
            re.I,
        ),
        _BANKING_LAYERS,
    ),
    (
        re.compile(
            r"\b(shipment|logistics|warehouse|carrier|dispatch|fleet|"
            r"freight|delivery\s+route|driver\s+app|tracking\s+id)\b",
            re.I,
        ),
        _LOGISTICS_LAYERS,
    ),

    # -------- Cross-cutting fallbacks (auth / payment / notification / CRUD) --------
    (
        re.compile(
            r"\b(authentication|authorize|login|sign[- ]?up|register|jwt|session|"
            r"password|otp|mfa|oauth)\b",
            re.I,
        ),
        _AUTH_LAYERS,
    ),
    (
        re.compile(r"\b(payment|billing|checkout|stripe|invoice)\b", re.I),
        _PAYMENT_LAYERS,
    ),
    (
        re.compile(r"\b(notif|email|sms|push|alert)\b", re.I),
        _NOTIFICATION_LAYERS,
    ),
    (
        re.compile(r"\b(crud|create|update|delete|manage|catalog|inventory)\b", re.I),
        _CRUD_LAYERS,
    ),
]


def _pick_layers(text: str) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    for pat, template in _LAYER_PATTERNS:
        if pat.search(text or ""):
            return template
    return _GENERIC_LAYERS


def _to_layer_groups(
    raw: Tuple[Tuple[str, Tuple[str, ...]], ...],
) -> List[ArchitectureLayerGroup]:
    return [
        ArchitectureLayerGroup(name=name, items=list(items))
        for name, items in raw
    ]


def format_architecture_tree(layers: List[ArchitectureLayerGroup]) -> str:
    """ASCII tree with box-drawing branches (demo-friendly)."""
    blocks: List[str] = []
    for group in layers:
        if not group.items:
            continue
        blocks.append(group.name)
        for item in group.items:
            blocks.append(f"├─ {item}")
        blocks.append("")
    return "\n".join(blocks).rstrip()


def _safe_id(name: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]", "", name.replace(" ", ""))
    return out[:24] or "Node"


def _safe_label(s: str) -> str:
    return s.replace('"', "'").replace("[", "(").replace("]", ")").strip()


def build_mermaid_layers(layers: List[ArchitectureLayerGroup]) -> str:
    """Mermaid flowchart with Frontend / Backend / Database subgraphs."""
    lines: List[str] = [
        "flowchart TB",
        "  classDef fe fill:#ede9fe,stroke:#6d28d9,color:#3b0764;",
        "  classDef be fill:#dbeafe,stroke:#1d4ed8,color:#0c2657;",
        "  classDef db fill:#dcfce7,stroke:#15803d,color:#14532d;",
    ]
    group_ids: List[str] = []
    first_nodes: dict[str, str] = {}
    last_nodes: dict[str, str] = {}

    for group in layers:
        gid = _safe_id(group.name)
        group_ids.append(gid)
        lines.append(f'  subgraph {gid}["{_safe_label(group.name)}"]')
        prev_nid: Optional[str] = None
        for item in group.items:
            nid = f"{gid}_{_safe_id(item)}"
            lines.append(f'    {nid}["{_safe_label(item)}"]')
            if prev_nid is None:
                first_nodes[gid] = nid
            prev_nid = nid
        if prev_nid:
            last_nodes[gid] = prev_nid
        lines.append("  end")

    # Style nodes by layer tier
    for i, group in enumerate(layers):
        gid = group_ids[i] if i < len(group_ids) else ""
        style = "fe" if "front" in group.name.lower() else (
            "db" if "data" in group.name.lower() else "be"
        )
        for item in group.items:
            nid = f"{gid}_{_safe_id(item)}"
            lines.append(f"  class {nid} {style};")

    # Cross-tier flow: first FE → first BE → first DB
    if len(group_ids) >= 2:
        fe = first_nodes.get(group_ids[0])
        be = first_nodes.get(group_ids[1])
        if fe and be:
            lines.append(f"  {fe} --> {be}")
    if len(group_ids) >= 3:
        be = last_nodes.get(group_ids[1]) or first_nodes.get(group_ids[1])
        db = first_nodes.get(group_ids[2])
        if be and db:
            lines.append(f"  {be} --> {db}")

    # Auth-specific detail edges when labels match known template
    names = {item.lower() for g in layers for item in g.items}
    if "login" in names:
        login = f"{group_ids[0]}_{_safe_id('Login')}" if group_ids else ""
        auth = f"{group_ids[1]}_{_safe_id('Auth Service')}" if len(group_ids) > 1 else ""
        users = f"{group_ids[2]}_{_safe_id('Users')}" if len(group_ids) > 2 else ""
        sessions = f"{group_ids[2]}_{_safe_id('Sessions')}" if len(group_ids) > 2 else ""
        if login and auth:
            lines.append(f"  {login} --> {auth}")
        if auth and users:
            lines.append(f"  {auth} --> {users}")
        if auth and sessions:
            lines.append(f"  {auth} --> {sessions}")

    return "\n".join(lines)


def _tier_key(layer_name: str) -> str:
    n = (layer_name or "").lower()
    if "front" in n or "client" in n or "ui" in n:
        return "frontend"
    if "gateway" in n or "edge" in n or "bff" in n:
        return "gateway"
    if "data" in n or "store" in n or "persist" in n:
        return "data"
    if "integrat" in n or "vendor" in n:
        return "integration"
    return "service"


def _linear_stack_labels(layers: List[ArchitectureLayerGroup]) -> List[str]:
    """Judge-friendly vertical chain: Frontend → API Gateway → Auth Service → Database."""
    stack: List[str] = []
    for group in layers:
        name = group.name or ""
        items = list(group.items or [])
        low = name.lower()
        if "front" in low:
            stack.append(group.name or "Frontend")
            continue
        if "gateway" in low or any("gateway" in (i or "").lower() for i in items):
            gw = next((i for i in items if "gateway" in i.lower()), items[0] if items else "API Gateway")
            stack.append(gw)
            continue
        if "data" in low:
            stack.append("Database")
            continue
        if "back" in low or "service" in low:
            auth = next((i for i in items if "auth" in i.lower()), None)
            if auth:
                stack.append(auth)
            elif items:
                stack.append(items[0])
            continue
        if items:
            stack.append(items[0])
        else:
            stack.append(name)
    # De-dupe adjacent identical labels
    out: List[str] = []
    for label in stack:
        if out and out[-1].lower() == label.lower():
            continue
        out.append(label)
    return out


def build_architecture_graph(
    layers: List[ArchitectureLayerGroup],
) -> ArchitectureGraph:
    """Interactive node graph + vertical stack for Screen 5."""
    stack_labels = _linear_stack_labels(layers)
    nodes: List[ArchitectureGraphNode] = []
    edges: List[ArchitectureGraphEdge] = []

    cx = 280.0
    y0 = 72.0
    step_y = 108.0
    node_w = 200.0

    # --- Primary wow column: linear stack ---
    stack_ids: List[str] = []
    for i, label in enumerate(stack_labels):
        nid = f"stack_{i}"
        stack_ids.append(nid)
        tier = "frontend"
        if i == 0:
            tier = "frontend"
        elif "gateway" in label.lower():
            tier = "gateway"
        elif "database" in label.lower() or label.lower() == "database":
            tier = "data"
        elif i == len(stack_labels) - 1 and "data" in (layers[-1].name if layers else "").lower():
            tier = "data"
        else:
            tier = "service"
        nodes.append(
            ArchitectureGraphNode(
                id=nid,
                label=label,
                tier=tier,
                layer="Stack",
                kind="stack",
                x=cx - node_w / 2,
                y=y0 + i * step_y,
            )
        )
    for i in range(len(stack_ids) - 1):
        edges.append(
            ArchitectureGraphEdge(
                source=stack_ids[i],
                target=stack_ids[i + 1],
                label="",
                kind="flow",
            )
        )

    # --- Detail column: all components per layer (right side) ---
    col_x = cx + 240.0
    row_h = 64.0
    prev_stack_tail = stack_ids[0] if stack_ids else None
    for gi, group in enumerate(layers):
        tier = _tier_key(group.name)
        tier_y = y0 + gi * step_y
        tier_id = f"tier_{gi}"
        nodes.append(
            ArchitectureGraphNode(
                id=tier_id,
                label=group.name,
                tier=tier,
                layer=group.name,
                kind="tier",
                x=col_x - node_w / 2,
                y=tier_y - 28,
            )
        )
        if prev_stack_tail and gi < len(stack_ids):
            edges.append(
                ArchitectureGraphEdge(
                    source=stack_ids[min(gi, len(stack_ids) - 1)],
                    target=tier_id,
                    label="",
                    kind="flow",
                )
            )
        prev_in_tier: Optional[str] = tier_id
        for ii, item in enumerate(group.items):
            nid = f"c_{gi}_{ii}"
            nodes.append(
                ArchitectureGraphNode(
                    id=nid,
                    label=item,
                    tier=tier,
                    layer=group.name,
                    kind="component",
                    x=col_x - node_w / 2,
                    y=tier_y + ii * row_h,
                )
            )
            edges.append(
                ArchitectureGraphEdge(
                    source=prev_in_tier,
                    target=nid,
                    label="",
                    kind="internal",
                )
            )
            prev_in_tier = nid
        if stack_ids and gi < len(stack_ids):
            edges.append(
                ArchitectureGraphEdge(
                    source=stack_ids[gi],
                    target=tier_id,
                    label="expands",
                    kind="flow",
                )
            )

    return ArchitectureGraph(nodes=nodes, edges=edges, stack=stack_labels)


def _count_mermaid(mermaid: str) -> Tuple[int, int]:
    from .diagram_generator import _count_nodes_edges

    return _count_nodes_edges(mermaid)


_AI_SYSTEM = """You are a solution architect. Given a software requirement, output
JSON ONLY with this shape:
{
  "layers": [
    {"name": "Frontend", "items": ["Login", "Dashboard"]},
    {"name": "Backend", "items": ["Auth Service", "User Service"]},
    {"name": "Database", "items": ["Users", "Sessions"]}
  ]
}
Rules:
- Exactly 3 layers: Frontend, Backend, Database (use Integration instead of
  Database only if there is no persistence).
- 2-5 concrete items per layer, named for THIS requirement.
- No markdown, no commentary.
""".strip()


async def _ai_layers(text: str) -> Optional[List[ArchitectureLayerGroup]]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    try:
        data = await ai.complete_json(
            _AI_SYSTEM,
            f"Requirement:\n---\n{text[:3500]}\n---",
            max_tokens=800,
        )
    except Exception:  # pragma: no cover
        logger.exception("Architecture layer AI failed")
        return None
    if not isinstance(data, dict):
        return None
    raw_layers = data.get("layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        return None
    out: List[ArchitectureLayerGroup] = []
    for row in raw_layers[:5]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        items_raw = row.get("items") or []
        if not name:
            continue
        items = [str(x).strip() for x in items_raw if str(x).strip()][:8]
        if items:
            out.append(ArchitectureLayerGroup(name=name, items=items))
    return out or None


async def generate_architecture(
    text: str,
    *,
    title: str = "",
    use_ai: bool = True,
) -> ArchitectureDiagram:
    """Full architecture: ASCII tree + layered Mermaid + system flowchart."""
    text = (text or "").strip()
    title_label = title or "Architecture"

    method = "heuristic"
    layers = _to_layer_groups(_pick_layers(text))

    if use_ai and text:
        ai_layers = await _ai_layers(text)
        if ai_layers:
            layers = ai_layers
            method = "hybrid"

    tree_text = format_architecture_tree(layers)
    mermaid_layers = build_mermaid_layers(layers)
    graph = build_architecture_graph(layers)

    flow = await generate_diagram(text, title=title_label, use_ai=use_ai)
    layer_nodes, layer_edges = _count_mermaid(mermaid_layers)
    nodes = max(flow.nodes_count, layer_nodes, len(graph.nodes))
    edges = flow.edges_count + layer_edges + len(graph.edges)

    return ArchitectureDiagram(
        title=title_label,
        layers=layers,
        tree_text=tree_text,
        mermaid=flow.mermaid,
        mermaid_layers=mermaid_layers,
        graph=graph,
        nodes_count=nodes,
        edges_count=edges,
        description=(
            f"{len(layers)} layers, {sum(len(g.items) for g in layers)} components, "
            f"flow + layered Mermaid."
        ),
        method=method if flow.method == "heuristic" else flow.method,
        generated_at=flow.generated_at,
    )
