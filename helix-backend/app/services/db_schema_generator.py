"""Database Schema Suggestions.

Given a requirement, propose tables, fields, relationships, plus
ready-to-run SQL DDL and a Mermaid ER diagram.

Hybrid: an entity-recognizer + standard-fields heuristic produces a
schema even with the LLM disabled; the LLM can override / extend.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import (
    DatabaseSchema,
    SchemaField,
    SchemaRelationship,
    SchemaTable,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.db_schema")


# ---------- Heuristic ---------------------------------------------------- #


# Domain entity recognizers — each provides typical fields.
_ENTITY_RECIPES: List[tuple[re.Pattern[str], str, str, List[Dict[str, Any]]]] = [
    (
        re.compile(r"\b(user|users|account|accounts|customer|customers)\b", re.I),
        "users", "User",
        [
            {"name": "email", "type": "string", "unique": True, "nullable": False, "indexed": True, "description": "Login identifier"},
            {"name": "password_hash", "type": "string", "nullable": False, "description": "Argon2 / bcrypt hash"},
            {"name": "full_name", "type": "string", "nullable": True},
            {"name": "phone", "type": "string", "nullable": True, "indexed": True},
            {"name": "is_active", "type": "boolean", "nullable": False, "default": "true"},
        ],
    ),
    (
        re.compile(r"\b(ticket|tickets|support\s+ticket)\b", re.I),
        "tickets", "Ticket",
        [
            {"name": "subject", "type": "string", "nullable": False, "description": "Short summary"},
            {"name": "body", "type": "text", "nullable": False, "description": "Full description"},
            {"name": "status", "type": "enum", "nullable": False, "default": "'open'", "description": "open | in_progress | waiting | resolved | closed"},
            {"name": "priority", "type": "enum", "nullable": False, "default": "'medium'", "description": "low | medium | high | critical"},
            {"name": "user_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id", "description": "Reporter"},
            {"name": "assignee_id", "type": "uuid", "nullable": True, "indexed": True, "foreign_key": "users.id", "description": "Owner"},
        ],
    ),
    (
        re.compile(r"\b(comment|comments|reply|replies)\b", re.I),
        "comments", "Comment",
        [
            {"name": "body", "type": "text", "nullable": False},
            {"name": "ticket_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "tickets.id"},
            {"name": "author_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id"},
        ],
    ),
    (
        re.compile(r"\b(status|statuses)\b", re.I),
        "statuses", "Status",
        [
            {"name": "name", "type": "string", "unique": True, "nullable": False, "description": "open / in_progress / closed / ..."},
            {"name": "color", "type": "string", "nullable": True, "description": "Hex color"},
            {"name": "sort_order", "type": "integer", "nullable": False, "default": "0"},
        ],
    ),
    (
        re.compile(r"\b(order|orders)\b", re.I),
        "orders", "Order",
        [
            {"name": "customer_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id"},
            {"name": "total_amount", "type": "decimal", "nullable": False, "description": "In minor units"},
            {"name": "currency", "type": "string", "nullable": False, "default": "'INR'"},
            {"name": "status", "type": "enum", "nullable": False, "default": "'created'"},
        ],
    ),
    (
        re.compile(r"\b(product|products|catalog|items)\b", re.I),
        "products", "Product",
        [
            {"name": "name", "type": "string", "nullable": False, "indexed": True},
            {"name": "sku", "type": "string", "unique": True, "nullable": False},
            {"name": "price", "type": "decimal", "nullable": False},
            {"name": "stock", "type": "integer", "nullable": False, "default": "0"},
        ],
    ),
    (
        re.compile(r"\b(payment|payments|invoice|invoices)\b", re.I),
        "payments", "Payment",
        [
            {"name": "amount", "type": "decimal", "nullable": False},
            {"name": "currency", "type": "string", "nullable": False, "default": "'INR'"},
            {"name": "status", "type": "enum", "nullable": False, "default": "'created'"},
            {"name": "user_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id"},
            {"name": "external_id", "type": "string", "nullable": True, "indexed": True, "description": "Gateway reference"},
        ],
    ),
    (
        re.compile(r"\b(otp|two[- ]?factor|2fa|mfa)\b", re.I),
        "otp_codes", "OTPCode",
        [
            {"name": "user_id", "type": "uuid", "nullable": True, "indexed": True, "foreign_key": "users.id"},
            {"name": "code_hash", "type": "string", "nullable": False, "description": "Hashed OTP"},
            {"name": "channel", "type": "enum", "nullable": False, "default": "'sms'", "description": "sms | email | voice"},
            {"name": "expires_at", "type": "datetime", "nullable": False, "indexed": True},
            {"name": "used_at", "type": "datetime", "nullable": True},
        ],
    ),
    (
        re.compile(r"\b(session|sessions|token|tokens)\b", re.I),
        "sessions", "Session",
        [
            {"name": "user_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id"},
            {"name": "refresh_token_hash", "type": "string", "nullable": False, "indexed": True},
            {"name": "expires_at", "type": "datetime", "nullable": False},
            {"name": "ip_address", "type": "string", "nullable": True},
            {"name": "user_agent", "type": "string", "nullable": True},
        ],
    ),
    (
        re.compile(r"\b(notification|notifications)\b", re.I),
        "notifications", "Notification",
        [
            {"name": "user_id", "type": "uuid", "nullable": False, "indexed": True, "foreign_key": "users.id"},
            {"name": "channel", "type": "enum", "nullable": False, "default": "'email'", "description": "email | sms | push"},
            {"name": "subject", "type": "string", "nullable": True},
            {"name": "body", "type": "text", "nullable": False},
            {"name": "status", "type": "enum", "nullable": False, "default": "'queued'"},
            {"name": "sent_at", "type": "datetime", "nullable": True},
        ],
    ),
    (
        re.compile(r"\b(audit|log|history|activity)\b", re.I),
        "audit_logs", "AuditLog",
        [
            {"name": "actor_id", "type": "uuid", "nullable": True, "indexed": True, "foreign_key": "users.id"},
            {"name": "action", "type": "string", "nullable": False, "indexed": True},
            {"name": "subject_type", "type": "string", "nullable": True},
            {"name": "subject_id", "type": "uuid", "nullable": True, "indexed": True},
            {"name": "metadata", "type": "json", "nullable": True},
        ],
    ),
]


def _standard_fields() -> List[SchemaField]:
    return [
        SchemaField(
            name="id", type="uuid", nullable=False, primary_key=True,
            description="Primary key", default="gen_random_uuid()",
        ),
        SchemaField(
            name="created_at", type="datetime", nullable=False,
            description="Row creation timestamp", default="now()",
        ),
        SchemaField(
            name="updated_at", type="datetime", nullable=False,
            description="Last update timestamp", default="now()",
        ),
    ]


def _heuristic_schema(text: str, *, title: str = "") -> DatabaseSchema:
    text = (text or "").strip()
    if not text:
        return DatabaseSchema(title=title or "Schema", method="heuristic")

    seen: set[str] = set()
    tables: List[SchemaTable] = []
    for pat, table_name, label, recipe in _ENTITY_RECIPES:
        if table_name in seen:
            continue
        if pat.search(text):
            seen.add(table_name)
            fields: List[SchemaField] = []
            fields.extend(_standard_fields())
            for r in recipe:
                fields.append(
                    SchemaField(
                        name=r["name"],
                        type=r["type"],
                        nullable=r.get("nullable", True),
                        primary_key=False,
                        foreign_key=r.get("foreign_key"),
                        indexed=r.get("indexed", False),
                        unique=r.get("unique", False),
                        default=r.get("default"),
                        description=r.get("description", ""),
                    )
                )
            tables.append(
                SchemaTable(
                    name=table_name,
                    label=label,
                    description=f"{label} entity inferred from the requirement.",
                    fields=fields,
                )
            )

    # Always include `users` if any FK references it.
    needs_users = any(
        any(f.foreign_key == "users.id" for f in t.fields)
        for t in tables
    )
    if needs_users and "users" not in seen:
        seen.add("users")
        users = next(
            (e for e in _ENTITY_RECIPES if e[1] == "users"), None
        )
        if users:
            recipe = users[3]
            tables.insert(
                0,
                SchemaTable(
                    name="users",
                    label="User",
                    description="Implicit user table required by foreign keys.",
                    fields=_standard_fields()
                    + [
                        SchemaField(
                            name=r["name"], type=r["type"],
                            nullable=r.get("nullable", True),
                            indexed=r.get("indexed", False),
                            unique=r.get("unique", False),
                            default=r.get("default"),
                            description=r.get("description", ""),
                        )
                        for r in recipe
                    ],
                ),
            )

    # Fallback: infer one generic entity from a Capitalized noun in the text.
    if not tables:
        m = re.search(r"\b([A-Z][a-z]{3,})\b", text)
        guess = m.group(1) if m else "Record"
        table_name = (guess.lower() + "s").replace(" ", "_")
        tables.append(
            SchemaTable(
                name=table_name,
                label=guess,
                description=f"Generic entity for the requirement (guessed from '{guess}').",
                fields=_standard_fields()
                + [
                    SchemaField(name="title", type="string", nullable=False, description="Short label"),
                    SchemaField(name="metadata", type="json", nullable=True, description="Open-ended metadata"),
                ],
            )
        )

    relationships = _extract_relationships(tables)
    sql = _build_sql(tables)
    er = _build_mermaid_er(tables, relationships)

    return DatabaseSchema(
        title=title or "Suggested schema",
        summary=(
            f"{len(tables)} tables · "
            f"{sum(len(t.fields) for t in tables)} fields · "
            f"{len(relationships)} relationships"
        ),
        tables=tables,
        relationships=relationships,
        sql_ddl=sql,
        mermaid_er=er,
        method="heuristic",
    )


def _extract_relationships(tables: List[SchemaTable]) -> List[SchemaRelationship]:
    out: List[SchemaRelationship] = []
    by_name = {t.name for t in tables}
    for t in tables:
        for f in t.fields:
            if not f.foreign_key:
                continue
            target = f.foreign_key.split(".", 1)[0]
            if target not in by_name:
                continue
            out.append(
                SchemaRelationship(
                    from_table=t.name,
                    to_table=target,
                    cardinality="many_to_one",
                    via_field=f.name,
                    description=f"{t.name}.{f.name} → {f.foreign_key}",
                )
            )
    return out


# ---------- Renderers --------------------------------------------------- #


_SQL_TYPE_MAP = {
    "uuid": "UUID",
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "boolean": "BOOLEAN",
    "datetime": "TIMESTAMPTZ",
    "decimal": "NUMERIC(12,2)",
    "json": "JSONB",
    "enum": "VARCHAR(40)",  # surface as string with check, simpler for portability
}


def _build_sql(tables: List[SchemaTable]) -> str:
    lines: List[str] = []
    for t in tables:
        lines.append(f"-- {t.label} ({t.description})")
        lines.append(f"CREATE TABLE IF NOT EXISTS {t.name} (")
        col_defs: List[str] = []
        for f in t.fields:
            sql_type = _SQL_TYPE_MAP.get(f.type, "VARCHAR(255)")
            parts = [f"  {f.name}", sql_type]
            if f.primary_key:
                parts.append("PRIMARY KEY")
            if not f.nullable and not f.primary_key:
                parts.append("NOT NULL")
            if f.unique and not f.primary_key:
                parts.append("UNIQUE")
            if f.default:
                parts.append(f"DEFAULT {f.default}")
            if f.foreign_key:
                parts.append(f"REFERENCES {f.foreign_key}")
            col_defs.append(" ".join(parts))
        lines.append(",\n".join(col_defs))
        lines.append(");")
        for f in t.fields:
            if f.indexed and not f.primary_key:
                lines.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{t.name}_{f.name} ON {t.name}({f.name});"
                )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _build_mermaid_er(
    tables: List[SchemaTable],
    relationships: List[SchemaRelationship],
) -> str:
    lines = ["erDiagram"]
    for t in tables:
        lines.append(f"  {t.name.upper()} {{")
        for f in t.fields:
            note = ""
            if f.primary_key:
                note = "PK"
            elif f.foreign_key:
                note = "FK"
            elif f.unique:
                note = "UK"
            label = f"    {f.type} {f.name}"
            if note:
                label += f" {note}"
            lines.append(label)
        lines.append("  }")
    for r in relationships:
        # ER cardinality uses crow's foot syntax.
        # many-to-one → "many to one" → "}|--||"
        lhs = "}|"
        rhs = "||"
        if r.cardinality == "one_to_one":
            lhs, rhs = "||", "||"
        elif r.cardinality == "one_to_many":
            lhs, rhs = "||", "|{"
        elif r.cardinality == "many_to_many":
            lhs, rhs = "}|", "|{"
        lines.append(
            f"  {r.from_table.upper()} {lhs}--{rhs} {r.to_table.upper()} : \"{r.via_field}\""
        )
    return "\n".join(lines)


# ---------- AI augmentation -------------------------------------------- #


_AI_SYSTEM = """You are a Database Architect. For the given
requirement, propose tables, columns, and relationships an engineer
can run on PostgreSQL. Use snake_case for tables / columns. Always
include id (uuid PK), created_at, updated_at. Honor real-world
relationships (FKs).""".strip()


_AI_SCHEMA = """{
  "title": "string",
  "summary": "string",
  "tables": [
    {
      "name": "tickets",
      "label": "Ticket",
      "description": "string",
      "fields": [
        {"name": "subject", "type": "string", "nullable": false, "primary_key": false, "foreign_key": null, "indexed": false, "unique": false, "default": null, "description": "string"}
      ],
      "relationships": ["string — human readable hint"]
    }
  ],
  "relationships": [
    {"from_table": "tickets", "to_table": "users", "cardinality": "many_to_one", "via_field": "user_id", "description": "string"}
  ]
}"""


_VALID_TYPES = {
    "uuid", "string", "text", "integer", "bigint", "boolean",
    "datetime", "decimal", "json", "enum",
}
_VALID_CARDINALITIES = {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}


def _coerce_field(raw: Any) -> Optional[SchemaField]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    ftype = str(raw.get("type") or "string").strip().lower()
    if ftype not in _VALID_TYPES:
        ftype = "string"
    return SchemaField(
        name=name[:64],
        type=ftype,
        nullable=bool(raw.get("nullable", True)),
        primary_key=bool(raw.get("primary_key", False)),
        foreign_key=(str(raw.get("foreign_key")).strip() if raw.get("foreign_key") else None),
        indexed=bool(raw.get("indexed", False)),
        unique=bool(raw.get("unique", False)),
        default=(str(raw.get("default")).strip() if raw.get("default") else None),
        description=str(raw.get("description") or "").strip(),
    )


async def _ai_schema(text: str, baseline: DatabaseSchema, *, title: str) -> Optional[DatabaseSchema]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    base_blob = "\n".join(f"  - {t.name} ({t.label})" for t in baseline.tables) or "  (none)"
    user = (
        f"Requirement:\n---\n{text[:4000]}\n---\n\n"
        f"Heuristic baseline tables (override or extend):\n{base_blob}\n\n"
        f"Return ONLY JSON in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=4500)
    except Exception:  # pragma: no cover
        logger.exception("DB Schema AI failed")
        return None

    tables: List[SchemaTable] = []
    seen: set[str] = set()
    for raw in data.get("tables") or []:
        try:
            name = str(raw.get("name") or "").strip().lower().replace(" ", "_")
            if not name or name in seen:
                continue
            seen.add(name)
            fields = [
                f for f in (_coerce_field(x) for x in (raw.get("fields") or []))
                if f is not None
            ]
            # Always guarantee an id PK
            if not any(f.primary_key for f in fields):
                fields.insert(
                    0,
                    SchemaField(
                        name="id", type="uuid", nullable=False,
                        primary_key=True, default="gen_random_uuid()",
                        description="Primary key",
                    ),
                )
            tables.append(
                SchemaTable(
                    name=name[:64],
                    label=str(raw.get("label") or name.title()).strip()[:64],
                    description=str(raw.get("description") or "").strip(),
                    fields=fields,
                    relationships=[
                        str(s).strip()
                        for s in (raw.get("relationships") or [])
                        if str(s).strip()
                    ],
                )
            )
        except Exception:
            continue

    if not tables:
        return None

    relationships: List[SchemaRelationship] = []
    for raw in data.get("relationships") or []:
        try:
            ft = str(raw.get("from_table") or "").strip().lower()
            tt = str(raw.get("to_table") or "").strip().lower()
            if not ft or not tt:
                continue
            card = str(raw.get("cardinality") or "many_to_one").strip().lower()
            if card not in _VALID_CARDINALITIES:
                card = "many_to_one"
            relationships.append(
                SchemaRelationship(
                    from_table=ft,
                    to_table=tt,
                    cardinality=card,
                    via_field=str(raw.get("via_field") or "").strip(),
                    description=str(raw.get("description") or "").strip(),
                )
            )
        except Exception:
            continue

    if not relationships:
        relationships = _extract_relationships(tables)

    sql = _build_sql(tables)
    er = _build_mermaid_er(tables, relationships)

    return DatabaseSchema(
        title=str(data.get("title") or title or "Suggested schema").strip(),
        summary=str(data.get("summary") or "").strip()
        or (
            f"{len(tables)} tables · "
            f"{sum(len(t.fields) for t in tables)} fields · "
            f"{len(relationships)} relationships"
        ),
        tables=tables,
        relationships=relationships,
        sql_ddl=sql,
        mermaid_er=er,
        method="hybrid",
    )


# ---------- Public API ------------------------------------------------- #


async def generate_schema(
    text: str,
    *,
    title: str = "",
    use_ai: bool = True,
) -> DatabaseSchema:
    baseline = _heuristic_schema(text, title=title)
    if use_ai:
        ai_out = await _ai_schema(text, baseline, title=title)
        if ai_out is not None:
            return ai_out
    return baseline


def to_simple_json(schema: DatabaseSchema) -> List[str]:
    """Render the canonical user-facing shape — list of table labels:
    `["Ticket", "User", "Comments", "Status"]`."""
    return [t.label or t.name for t in schema.tables]
