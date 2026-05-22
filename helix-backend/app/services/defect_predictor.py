"""Defect Prediction.

Predicts which modules are MOST defect-prone for a given requirement.

Heuristic: each module category has an inherent base risk (auth and
payments are historically the riskiest), and that base is amplified by
complexity drivers in the requirement text. The LLM (when enabled)
augments the explanation but does NOT change the ranking — the ranking
is deterministic so the same input always returns the same modules.

Output:

    {
      "high_risk_modules": ["Authentication", "Payments"]
    }
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import DefectModule, DefectPrediction
from .ai_service import get_ai_service

logger = logging.getLogger("helix.defect_predictor")


# ---------- Module taxonomy + base risk -------------------------------- #


_MODULES: List[tuple[str, re.Pattern[str], int, List[str]]] = [
    (
        "Authentication", re.compile(
            r"\b(login|auth(?:enticate)?|otp|2fa|mfa|sso|oauth|password|token|jwt|session|sign[- ]?in)\b",
            re.I,
        ),
        70,
        ["Auth flows are the historical #1 source of customer-facing defects."],
    ),
    (
        "Payments", re.compile(
            r"\b(payment|billing|invoice|subscription|stripe|razorpay|paypal|charge|refund|checkout)\b",
            re.I,
        ),
        72,
        ["Payment defects are 'all bug, no rollback' — every miss is a money or PCI event."],
    ),
    (
        "Authorization / RBAC", re.compile(
            r"\b(rbac|role|permission|access\s+control|authoriz\w+)\b", re.I,
        ),
        62,
        ["Permission bugs cause silent over-exposure that QA rarely catches."],
    ),
    (
        "Notification / Messaging", re.compile(
            r"\b(notification|email|sms|push\s+notif|smtp|twilio|sendgrid)\b", re.I,
        ),
        45,
        ["External SMS/SMTP providers fail in flaky ways and are rarely re-tested in CI."],
    ),
    (
        "Search & Indexing", re.compile(
            r"\b(search|elastic\s*search|lucene|solr|opensearch|index(ing)?|reindex)\b", re.I,
        ),
        50,
        ["Indexing pipelines fail silently — defects manifest as 'no results' not as errors."],
    ),
    (
        "Reporting / Analytics", re.compile(
            r"\b(report|dashboard|analytics|kpi|metric|aggregat\w+)\b", re.I,
        ),
        40,
        ["Aggregation off-by-one bugs are subtle and only show up at month-end."],
    ),
    (
        "File / Upload", re.compile(
            r"\b(upload|attach(ment)?|s3|object\s+store|cdn)\b", re.I,
        ),
        45,
        ["File handling defects span size limits, MIME validation, and storage IAM."],
    ),
    (
        "Migration / Backfill", re.compile(
            r"\b(migrat(e|ion)|backfill|re[- ]?architect|schema\s+change|alter\s+table)\b", re.I,
        ),
        72,
        ["Data migrations are typically one-way; rehearsals on production-shaped data are rarely complete."],
    ),
    (
        "External Integrations", re.compile(
            r"\b(third[- ]?party|external\s+api|webhook|sdk|integration)\b", re.I,
        ),
        58,
        ["Third-party APIs change without notice and degrade silently."],
    ),
    (
        "Real-time / WebSocket", re.compile(
            r"\b(real[- ]?time|websocket|streaming|sse|long[- ]?polling)\b", re.I,
        ),
        55,
        ["Reconnect, ordering, and back-pressure are perennial defect generators."],
    ),
    (
        "Background Jobs / Queue", re.compile(
            r"\b(queue|worker|background\s+job|cron|kafka|rabbitmq|sqs)\b", re.I,
        ),
        50,
        ["Idempotency mistakes here look fine in dev but bite under production load."],
    ),
    (
        "ML / Inference", re.compile(
            r"\b(machine\s+learning|llm|inference|embedding|hallucinat\w+|model\s+drift)\b", re.I,
        ),
        58,
        ["Model drift + non-determinism complicate regression testing."],
    ),
    (
        "Caching", re.compile(
            r"\b(cache|redis|memcache|invalidat\w+)\b", re.I,
        ),
        45,
        ["Cache invalidation is one of the famous 'two hard problems'."],
    ),
    (
        "Database / ORM", re.compile(
            r"\b(database|orm|sql|postgres|mysql|mongo)\b", re.I,
        ),
        50,
        ["N+1 queries and lock contention emerge under load."],
    ),
    (
        "Frontend State", re.compile(
            r"\b(react|frontend|ui|component|state\s+management|store)\b", re.I,
        ),
        40,
        ["Local-state vs server-state mismatches are subtle and hard to reproduce."],
    ),
]


# Complexity drivers — text patterns that boost risk across all modules.
_GLOBAL_DRIVERS: List[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(no\s+rollback|irreversible|destructive)\b", re.I), 8, "No rollback path"),
    (re.compile(r"\b(real[- ]?time|low[- ]?latency|p99|throughput)\b", re.I), 6, "Latency-sensitive"),
    (re.compile(r"\b(gdpr|hipaa|pci|sox|compliance)\b", re.I), 7, "Compliance scope"),
    (re.compile(r"\b(legacy|untested|no\s+coverage)\b", re.I), 8, "Touches legacy code"),
    (re.compile(r"\b(scal\w+|10x|100x|peak\s+load)\b", re.I), 6, "Scalability sensitivity"),
    (re.compile(r"\b(deadline|by\s+(eod|next\s+week|tomorrow))\b", re.I), 4, "Tight deadline"),
]


def _level_from_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _heuristic_predict(text: str) -> DefectPrediction:
    text = (text or "").strip()
    if not text:
        return DefectPrediction(summary="No requirement text provided.")

    global_bumps: List[tuple[str, int]] = []
    global_total = 0
    for pat, weight, label in _GLOBAL_DRIVERS:
        if pat.search(text):
            global_bumps.append((label, weight))
            global_total += weight

    modules: List[DefectModule] = []
    for name, pat, base, default_drivers in _MODULES:
        if not pat.search(text):
            continue
        score = base + global_total
        # Length amplifier — short specs mean hidden complexity for these modules
        length = len(text)
        if length < 80:
            score += 6
        score = min(score, 100)
        drivers = list(default_drivers)
        drivers.extend(label for label, _ in global_bumps)
        modules.append(
            DefectModule(
                name=name,
                risk_score=score,
                risk_level=_level_from_score(score),
                drivers=drivers[:6],
                notes=f"Base {base} + {global_total} from global drivers.",
            )
        )

    # If nothing matched, still give a defensible answer.
    if not modules:
        modules = [
            DefectModule(
                name="General Application Logic",
                risk_score=35 + global_total,
                risk_level=_level_from_score(35 + global_total),
                drivers=[label for label, _ in global_bumps] or [
                    "Requirement is too thin to localize risk to a module."
                ],
                notes="Fallback — no domain modules detected.",
            )
        ]

    # Sort by risk descending; high-risk = top 3 + everything ≥ high.
    modules.sort(key=lambda m: m.risk_score, reverse=True)
    high_risk = [
        m.name for m in modules
        if m.risk_level in ("high", "critical")
    ]
    if not high_risk and modules:
        high_risk = [modules[0].name]

    avg = int(round(sum(m.risk_score for m in modules) / max(1, len(modules))))
    summary = (
        f"{len(high_risk)} high-risk module"
        f"{'' if len(high_risk) == 1 else 's'} detected "
        f"(overall avg {avg}/100)."
    )

    return DefectPrediction(
        high_risk_modules=high_risk,
        modules=modules,
        overall_risk=avg,
        summary=summary,
        method="heuristic",
    )


# ---------- AI augmentation -------------------------------------------- #


_AI_SYSTEM = """You are a Senior Quality Engineer predicting defect
risk by module from a requirement. Be calibrated. Output ONLY valid
JSON. Do not invent modules; refine the heuristic baseline by
RE-WORDING drivers to be requirement-specific.""".strip()


_AI_SCHEMA = """{
  "high_risk_modules": ["string"],
  "modules": [
    {
      "name": "string",
      "risk_score": 0,
      "drivers": ["string — specific to THIS requirement"],
      "notes": "string"
    }
  ],
  "summary": "string"
}"""


async def _ai_augment(text: str, baseline: DefectPrediction) -> Optional[DefectPrediction]:
    ai = get_ai_service()
    if not ai.enabled or not baseline.modules:
        return None
    base_blob = "\n".join(
        f"  - {m.name} ({m.risk_score}/{m.risk_level})"
        for m in baseline.modules
    )
    user = (
        f"Requirement:\n---\n{text[:4000]}\n---\n\n"
        f"Heuristic baseline (override or refine):\n{base_blob}\n\n"
        f"Return ONLY JSON in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=1800)
    except Exception:
        logger.exception("Defect AI failed")
        return None

    by_name = {m.name: m for m in baseline.modules}
    refined: List[DefectModule] = []
    for raw in data.get("modules") or []:
        try:
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            score_raw = raw.get("risk_score")
            try:
                score = int(score_raw) if score_raw is not None else by_name.get(name, baseline.modules[0]).risk_score
            except (TypeError, ValueError):
                score = by_name.get(name, baseline.modules[0]).risk_score
            score = max(0, min(100, score))
            drivers = [
                str(d).strip()
                for d in (raw.get("drivers") or [])
                if str(d).strip()
            ][:6]
            if not drivers and name in by_name:
                drivers = list(by_name[name].drivers)
            refined.append(
                DefectModule(
                    name=name,
                    risk_score=score,
                    risk_level=_level_from_score(score),
                    drivers=drivers,
                    notes=str(raw.get("notes") or "").strip(),
                )
            )
        except Exception:
            continue

    if not refined:
        return None

    refined.sort(key=lambda m: m.risk_score, reverse=True)
    high_risk = [
        str(s).strip()
        for s in (data.get("high_risk_modules") or [])
        if str(s).strip()
    ] or [m.name for m in refined if m.risk_level in ("high", "critical")] or [refined[0].name]

    avg = int(round(sum(m.risk_score for m in refined) / max(1, len(refined))))
    return DefectPrediction(
        high_risk_modules=high_risk,
        modules=refined,
        overall_risk=avg,
        summary=str(data.get("summary") or "").strip()
        or baseline.summary,
        method="hybrid",
    )


async def predict_defects(text: str, *, use_ai: bool = True) -> DefectPrediction:
    baseline = _heuristic_predict(text)
    if not use_ai:
        return baseline
    refined = await _ai_augment(text, baseline)
    return refined or baseline


def to_simple_json(pred: DefectPrediction) -> Dict[str, Any]:
    """Render the canonical user-facing shape:
    `{ "high_risk_modules": ["Authentication", "Payments"] }`."""
    return {"high_risk_modules": list(pred.high_risk_modules)}
