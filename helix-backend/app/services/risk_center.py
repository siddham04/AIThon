"""AI Risk Center — Screen 8 severity-band heat map.

Builds HIGH / MEDIUM / LOW rows with clickable risk items (title, risk label,
probability %) for demo and live project data.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional

from ..models import (
    Risk,
    RiskCenterBand,
    RiskCenterHeatmap,
    RiskCenterItem,
    RiskPrediction,
)

if TYPE_CHECKING:
    from ..models import Project


_BAND_ORDER = ("high", "medium", "low")
_BAND_LABELS = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}

_SEVERITY_TO_BAND = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_PROB_BY_SEVERITY = {
    "critical": 88,
    "high": 72,
    "medium": 45,
    "low": 18,
}

_CATEGORY_RISK_LABEL = {
    "security": "Security review needed",
    "compliance": "Compliance risk",
    "performance": "Performance risk",
    "scalability": "Scalability risk",
    "dependency": "External dependency",
    "data": "Data migration risk",
    "ux": "UX-breaking change",
}


def _band_for_severity(sev: str) -> str:
    return _SEVERITY_TO_BAND.get((sev or "medium").lower(), "medium")


def _probability(sev: str, *, override: Optional[int] = None) -> int:
    if override is not None:
        return max(0, min(100, override))
    return _PROB_BY_SEVERITY.get((sev or "medium").lower(), 40)


def _risk_label_from_risk(r: Risk) -> str:
    cat = r.category.value if hasattr(r.category, "value") else str(r.category)
    if cat in _CATEGORY_RISK_LABEL:
        return _CATEGORY_RISK_LABEL[cat]
    desc = (r.description or "").strip()
    if desc:
        return desc.split(".")[0][:80]
    return "Delivery risk"


def _item_from_pipeline_risk(r: Risk) -> RiskCenterItem:
    sev = r.severity.value if hasattr(r.severity, "value") else str(r.severity)
    band = _band_for_severity(sev)
    return RiskCenterItem(
        id=r.id,
        title=r.title,
        risk=_risk_label_from_risk(r),
        probability=_probability(sev),
        severity=band,
        category=r.category.value if hasattr(r.category, "value") else str(r.category),
        mitigation=r.mitigation or "",
        source="pipeline",
    )


def _items_from_prediction(pred: RiskPrediction) -> List[RiskCenterItem]:
    items: List[RiskCenterItem] = []
    level = pred.risk_level.value if hasattr(pred.risk_level, "value") else str(pred.risk_level)
    band = _band_for_severity(level)
    score = pred.score or _probability(level)

    for i, alert in enumerate(pred.alerts or []):
        sev = (alert.severity or "medium").lower()
        items.append(
            RiskCenterItem(
                id=f"pred_alert_{i}",
                title=_title_from_alert(alert.message, pred),
                risk=alert.message,
                probability=max(score - i * 4, 35),
                severity=_band_for_severity(sev),
                category=(pred.categories[0] if pred.categories else "dependency"),
                mitigation=(pred.mitigations[i] if i < len(pred.mitigations) else ""),
                source="prediction",
            )
        )

    if not items and pred.reasons:
        for i, reason in enumerate(pred.reasons[:4]):
            items.append(
                RiskCenterItem(
                    id=f"pred_reason_{i}",
                    title=_title_from_reason(reason),
                    risk=reason,
                    probability=max(score - i * 6, 30),
                    severity=band,
                    category=(pred.categories[0] if pred.categories else ""),
                    mitigation=(
                        pred.mitigations[i] if i < len(pred.mitigations) else ""
                    ),
                    source="prediction",
                )
            )
    return items


def _title_from_alert(message: str, pred: RiskPrediction) -> str:
    msg = (message or "").lower()
    if "payment" in msg or "payment" in " ".join(pred.categories or []):
        return "Payment Gateway"
    if "external" in msg or "integration" in msg:
        return "Third-Party API"
    if "compliance" in msg:
        return "Compliance Controls"
    if "security" in msg or "auth" in msg:
        return "Auth Service"
    if "migration" in msg or "data" in msg:
        return "Database Migration"
    return message[:48] if message else "Requirement Risk"


def _title_from_reason(reason: str) -> str:
    r = (reason or "").lower()
    if "payment" in r:
        return "Payment Gateway"
    if "external" in r or "api" in r:
        return "Payment Gateway"
    if "auth" in r or "login" in r:
        return "Auth Service"
    if "migration" in r or "schema" in r:
        return "Database Migration"
    if "compliance" in r or "gdpr" in r or "pci" in r:
        return "PCI Compliance"
    words = reason.split()[:4]
    return " ".join(words).title()[:40] if words else "Risk Item"


def _items_from_defect_modules(modules: List[str]) -> List[RiskCenterItem]:
    items: List[RiskCenterItem] = []
    for i, mod in enumerate(modules[:6]):
        sev = "high" if i < 2 else "medium"
        items.append(
            RiskCenterItem(
                id=f"module_{i}",
                title=mod,
                risk="Defect-prone module",
                probability=68 - i * 8,
                severity=_band_for_severity(sev),
                category="performance",
                mitigation="Add characterization tests + monitor error budget",
                source="module",
            )
        )
    return items


def _pack_bands(items: List[RiskCenterItem]) -> List[RiskCenterBand]:
    by_band: dict[str, List[RiskCenterItem]] = {b: [] for b in _BAND_ORDER}
    for item in items:
        band = item.severity if item.severity in by_band else "medium"
        by_band[band].append(item)

    bands: List[RiskCenterBand] = []
    for level in _BAND_ORDER:
        row = by_band[level]
        if not row and level != "low":
            continue
        bands.append(
            RiskCenterBand(
                level=level,
                label=_BAND_LABELS[level],
                items=row,
            )
        )
    # Always show LOW row for the visual (even if empty in live data)
    if not any(b.level == "low" for b in bands):
        bands.append(RiskCenterBand(level="low", label="LOW", items=by_band["low"]))
    return bands


def build_demo_risk_center() -> RiskCenterHeatmap:
    """Curated demo — Payment Gateway @ 72% external dependency."""
    items = [
        RiskCenterItem(
            id="demo_payment",
            title="Payment Gateway",
            risk="External dependency",
            probability=72,
            severity="high",
            category="dependency",
            mitigation="Circuit-break the integration + idempotent webhook handler",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_auth",
            title="Auth Service",
            risk="Security review needed",
            probability=68,
            severity="high",
            category="security",
            mitigation="Threat-model login flow before merge",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_pci",
            title="PCI Compliance",
            risk="Compliance risk",
            probability=65,
            severity="high",
            category="compliance",
            mitigation="Loop in legal / DPO; document data retention",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_db",
            title="Database Migration",
            risk="Data migration risk",
            probability=58,
            severity="high",
            category="data",
            mitigation="Reversible migration + snapshot rollback drill",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_sms",
            title="SMS Provider",
            risk="External dependency",
            probability=45,
            severity="medium",
            category="dependency",
            mitigation="Retry with exponential backoff + DLQ",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_cache",
            title="Session Store",
            risk="Performance risk",
            probability=38,
            severity="medium",
            category="performance",
            mitigation="Load test hot path; capture p99 baseline",
            source="demo",
        ),
        RiskCenterItem(
            id="demo_ui",
            title="UI Theme",
            risk="UX-breaking change",
            probability=18,
            severity="low",
            category="ux",
            mitigation="A/B rollout with in-app migration banner",
            source="demo",
        ),
    ]
    bands = _pack_bands(items)
    return RiskCenterHeatmap(
        bands=bands,
        total_items=len(items),
        headline="7 risks across delivery — Payment Gateway is the top external dependency",
    )


def build_risk_center(project: "Project") -> RiskCenterHeatmap:
    """Aggregate pipeline risks, requirement prediction, and defect modules."""
    items: List[RiskCenterItem] = []
    seen_titles: set[str] = set()

    for r in project.risks or []:
        item = _item_from_pipeline_risk(r)
        key = item.title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        items.append(item)

    if project.requirement_risk:
        for item in _items_from_prediction(project.requirement_risk):
            key = item.title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            items.append(item)

    if project.defect_prediction and project.defect_prediction.high_risk_modules:
        for item in _items_from_defect_modules(
            project.defect_prediction.high_risk_modules
        ):
            key = item.title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            items.append(item)

    # Payment gateway boost when requirement text mentions it
    text = (project.raw_input or "").lower()
    if re.search(r"\bpayment\s+gateway\b", text) and not any(
        "payment" in i.title.lower() for i in items
    ):
        items.insert(
            0,
            RiskCenterItem(
                id="req_payment_gateway",
                title="Payment Gateway",
                risk="External dependency",
                probability=72,
                severity="high",
                category="dependency",
                mitigation="Circuit-break + reconciliation tests on staging",
                source="prediction",
            ),
        )

    if not items:
        return build_demo_risk_center()

    bands = _pack_bands(items)
    high_n = sum(1 for i in items if i.severity == "high")
    return RiskCenterHeatmap(
        bands=bands,
        total_items=len(items),
        headline=f"{len(items)} risks — {high_n} high severity across the delivery surface",
    )
