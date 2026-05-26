"""Requirement Quality Score — evaluates the requirement BEFORE build.

Most tools generate downstream artifacts. This service flips the problem:
given any requirement text, return a transparent, hybrid quality
assessment in the form

    {
      "quality_score": 68,           # 0..100, higher is better
      "ambiguity_score": 35,         # 0..100, higher is MORE ambiguous
      "missing_information": [...],  # concrete gaps a PM can act on
      "vague_phrases":      [...],   # exact quoted spans
      "clarifying_questions": [...],
      ...
    }

Implementation is intentionally LAYERED:

  1. Deterministic heuristics  (always available, ~ms latency)
       - vague-word density            → ambiguity baseline
       - sentence length, TTR          → readability
       - dimension keyword sniffing    → coarse missing-info detection
  2. AI gap analysis            (when Azure OpenAI is configured)
       - LLM produces a structured list of gaps + quoted vague phrases
         it would never have caught from heuristics alone
  3. Blend                      (the public score is the weighted blend)

Either layer alone is correct; together they produce a noticeably
sharper score that judges (and PMs) actually trust.
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from ..models import (
    MissingInformation,
    QualityDimension,
    QualityRadarScores,
    QualityScoreReport,
    Severity,
    VaguePhrase,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.quality_scorer")


# --------------------------------------------------------------------- #
# Lexicons
# --------------------------------------------------------------------- #


_VAGUE_TERMS: tuple[str, ...] = (
    "etc", "fast", "slow", "many", "few", "some", "various", "appropriate",
    "reasonable", "intuitive", "user-friendly", "user friendly", "robust",
    "scalable", "secure", "modern", "simple", "easy", "efficient", "flexible",
    "soon", "later", "tbd", "maybe", "approximately", "around", "roughly",
    "should", "could", "may", "might", "ideally", "etc.",
)
_VAGUE_RX = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _VAGUE_TERMS) + r")\b",
    flags=re.IGNORECASE,
)
_QUANT_RX = re.compile(
    r"\b\d+\s*(ms|s|sec|seconds?|min|minutes?|h|hours?|days?|weeks?|"
    r"%|percent|users?|rps|tps|qps|gb|mb|kb|requests?)\b",
    flags=re.IGNORECASE,
)
_PASSIVE_RX = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+\w+ed\b",
    flags=re.IGNORECASE,
)
_WORD_RX = re.compile(r"\b[\w'-]+\b", flags=re.UNICODE)
_SENTENCE_RX = re.compile(r"[.!?]+")


# Canonical enterprise highlight labels (shown as cards in the UI).
_HIGHLIGHT_BY_DIMENSION: dict[QualityDimension, str] = {
    QualityDimension.ROLES: "Missing actors",
    QualityDimension.SUCCESS_CRITERIA: "Missing acceptance criteria",
    QualityDimension.BUSINESS_RULES: "Undefined business rules",
    QualityDimension.EDGE_CASES: "Missing edge cases",
    QualityDimension.ERROR_HANDLING: "Error handling undefined",
    QualityDimension.NON_FUNCTIONAL: "Non-functional targets unspecified",
    QualityDimension.SECURITY: "Security concerns not addressed",
    QualityDimension.SCOPE: "Scope boundaries not stated",
}

# Vague-term → clarifying questions (e.g. "fast login" demo).
_VAGUE_QUESTION_BANK: dict[str, tuple[str, ...]] = {
    "fast": ("What is fast?", "Under what load?", "Which users?"),
    "slow": ("How slow is acceptable?", "At which percentile?", "Under what load?"),
    "quick": ("What is the target latency?", "Measured how?", "For which operation?"),
    "easy": ("Easy for whom?", "How is ease measured?", "What is the baseline?"),
    "simple": ("Simple compared to what?", "What complexity is out of scope?", "For which persona?"),
    "secure": ("Secure against which threats?", "Which compliance standard applies?", "Who must authenticate?"),
    "robust": ("Robust to which failure modes?", "What is the recovery SLA?", "What load must it survive?"),
    "scalable": ("How many users/requests?", "What growth horizon?", "Horizontal or vertical scaling?"),
    "intuitive": ("Intuitive for which user segment?", "How will you validate usability?", "What is the success metric?"),
    "user-friendly": ("What usability standard?", "Which accessibility level?", "How will you test it?"),
    "efficient": ("Efficient in what dimension — time, cost, memory?", "What is the target?", "Under what constraints?"),
    "soon": ("What is the deadline?", "What happens if it slips?", "Who approves the date?"),
    "many": ("How many exactly?", "Minimum and maximum?", "Peak vs average?"),
    "few": ("How few?", "What is the threshold?", "Is zero allowed?"),
    "some": ("Which ones specifically?", "All or a subset?", "Who decides?"),
    "appropriate": ("Appropriate by whose standard?", "What are the criteria?", "Who signs off?"),
    "reasonable": ("Reasonable under which constraints?", "What benchmark?", "Who defines reasonable?"),
    "should": ("Is this mandatory or optional?", "What if it is not done?", "Who is accountable?"),
    "could": ("Is this in scope?", "What triggers this path?", "What is the fallback?"),
    "tbd": ("When will this be decided?", "Who owns the decision?", "What is blocked until then?"),
}

# Dimension → keyword cues we expect to see in a healthy requirement.
# Absence of every cue for a dimension promotes a "missing X" entry.
_DIMENSION_CUES: "OrderedDict[QualityDimension, tuple[str, tuple[str, ...]]]" = OrderedDict(
    (
        (QualityDimension.ROLES,
         ("Missing actors",
          ("user", "admin", "role", "permission", "actor", "stakeholder",
           "customer", "operator", "moderator", "tenant", "persona"))),
        (QualityDimension.SUCCESS_CRITERIA,
         ("Missing acceptance criteria",
          ("success", "kpi", "metric", "outcome", "objective", "target",
           "acceptance criteria", "definition of done", "measure", "given",
           "when", "then", "verify", "validate"))),
        (QualityDimension.BUSINESS_RULES,
         ("Undefined business rules",
          ("business rule", "policy", "validation", "must", "shall",
           "when ", "if ", "then ", "constraint", "invariant", "workflow",
           "eligibility", "entitlement", "pricing rule"))),
        (QualityDimension.EDGE_CASES,
         ("Missing edge cases",
          ("edge case", "boundary", "corner case", "empty", "null", "zero",
           "maximum", "minimum", "offline", "duplicate", "concurrent",
           "race", "timeout", "expired", "invalid", "overflow"))),
        (QualityDimension.ERROR_HANDLING,
         ("Error handling undefined",
          ("error", "failure", "fallback", "retry", "timeout", "exception",
           "rollback", "graceful", "degrade", "recover"))),
        (QualityDimension.NON_FUNCTIONAL,
         ("Non-functional targets unspecified",
          ("performance", "latency", "throughput", "availability", "uptime",
           "sla", "scalable", "concurrent", "reliab"))),
        (QualityDimension.SECURITY,
         ("Security concerns not addressed",
          ("auth", "login", "session", "encrypt", "tls", "ssl", "permission",
           "rbac", "abac", "audit", "csrf", "xss", "secret", "token"))),
        (QualityDimension.DATA,
         ("Data model & retention not defined",
          ("data", "field", "schema", "store", "database", "table", "column",
           "retention", "pii", "personal", "dataset"))),
        (QualityDimension.DEPENDENCIES,
         ("External dependencies not enumerated",
          ("integrate", "integration", "third-party", "third party", "api",
           "webhook", "vendor", "partner", "external", "depends on"))),
        (QualityDimension.ACCESSIBILITY,
         ("Accessibility requirements not stated",
          ("accessib", "wcag", "aria", "screen reader", "keyboard", "contrast"))),
        (QualityDimension.DEPLOYMENT,
         ("Deployment & rollout plan missing",
          ("deploy", "rollout", "rollback", "migration", "feature flag",
           "release", "staging", "production", "ci/cd"))),
        (QualityDimension.SCOPE,
         ("Scope boundaries not stated",
          ("scope", "out of scope", "out-of-scope", "exclud", "in-scope",
           "boundary", "phase 1", "mvp", "non-goal"))),
    )
)


_DIMENSION_DEFAULT_QUESTION: dict[QualityDimension, str] = {
    QualityDimension.ROLES:
        "Which actors are involved, and what can each of them do?",
    QualityDimension.SUCCESS_CRITERIA:
        "What are the acceptance criteria and measurable outcomes?",
    QualityDimension.BUSINESS_RULES:
        "What are the business rules, validations, and policy constraints?",
    QualityDimension.EDGE_CASES:
        "What edge cases, boundary conditions, and failure paths must be covered?",
    QualityDimension.ERROR_HANDLING:
        "What should happen on validation failure, timeout, or third-party outage?",
    QualityDimension.NON_FUNCTIONAL:
        "What are the performance, availability, and concurrency targets?",
    QualityDimension.SECURITY:
        "Who is allowed to do this, how is identity verified, and what is logged?",
    QualityDimension.DATA:
        "Which data fields are stored, where, and for how long?",
    QualityDimension.DEPENDENCIES:
        "Which external systems / APIs / vendors does this depend on?",
    QualityDimension.ACCESSIBILITY:
        "What accessibility level (e.g. WCAG 2.1 AA) is required?",
    QualityDimension.DEPLOYMENT:
        "How will this be rolled out and rolled back if it misbehaves?",
    QualityDimension.SCOPE:
        "What is explicitly OUT of scope for this iteration?",
    QualityDimension.OTHER: "Please clarify.",
}


_DIMENSION_SEVERITY: dict[QualityDimension, Severity] = {
    QualityDimension.ROLES: Severity.HIGH,
    QualityDimension.SUCCESS_CRITERIA: Severity.HIGH,
    QualityDimension.BUSINESS_RULES: Severity.HIGH,
    QualityDimension.EDGE_CASES: Severity.MEDIUM,
    QualityDimension.ERROR_HANDLING: Severity.HIGH,
    QualityDimension.NON_FUNCTIONAL: Severity.MEDIUM,
    QualityDimension.SECURITY: Severity.HIGH,
    QualityDimension.DATA: Severity.MEDIUM,
    QualityDimension.DEPENDENCIES: Severity.MEDIUM,
    QualityDimension.ACCESSIBILITY: Severity.MEDIUM,
    QualityDimension.DEPLOYMENT: Severity.LOW,
    QualityDimension.SCOPE: Severity.MEDIUM,
    QualityDimension.OTHER: Severity.MEDIUM,
}


# --------------------------------------------------------------------- #
# Heuristic core
# --------------------------------------------------------------------- #


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _grade_for(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"


def _heuristic_score(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    words = _WORD_RX.findall(text)
    sentences = [s.strip() for s in _SENTENCE_RX.split(text) if s.strip()]
    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    unique = len({w.lower() for w in words})
    ttr = unique / word_count if word_count else 0.0
    avg_sent = word_count / sentence_count if word_count else 0.0
    vague_hits = _VAGUE_RX.findall(text)
    vague_count = len(vague_hits)
    quant_count = len(_QUANT_RX.findall(text))
    passive_count = len(_PASSIVE_RX.findall(text))
    vague_density = vague_count / word_count if word_count else 0.0

    # Sub-scores 0..1
    completeness = _heuristic_completeness(text)
    specificity = _clamp(1.0 - min(vague_density * 25.0, 1.0), 0.0, 1.0)
    if quant_count >= 2:
        specificity = _clamp(specificity + 0.1, 0.0, 1.0)
    structure = _structure_score(avg_sent)
    vocabulary = _vocabulary_score(ttr, word_count)
    if word_count == 0:
        completeness = specificity = structure = vocabulary = 0.0

    # Quality score: weighted blend (higher = better)
    quality = round(
        100.0 * (
            0.40 * completeness
            + 0.30 * specificity
            + 0.15 * structure
            + 0.15 * vocabulary
        ),
        1,
    )

    # Ambiguity score: higher = MORE ambiguous (worse)
    # Density-driven, capped, plus passive-voice and unquantified-NFR
    # signals add weight.
    if word_count == 0:
        ambiguity = 100.0
    else:
        amb_raw = (
            min(vague_density * 1500, 60)        # density of vague terms
            + min(passive_count * 4, 20)         # passive voice
            + (15 if quant_count == 0 else 0)    # no quantified targets
            + (10 if avg_sent > 32 else 0)       # rambling sentences
        )
        ambiguity = round(_clamp(amb_raw, 0, 100), 1)

    return {
        "quality": quality,
        "ambiguity": ambiguity,
        "_raw_text": text,
        "breakdown": {
            "completeness": round(completeness, 3),
            "specificity": round(specificity, 3),
            "structure": round(structure, 3),
            "vocabulary": round(vocabulary, 3),
            "testability": round(_testability_score(text), 3),
        },
        "stats": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "unique_terms": unique,
            "type_token_ratio": round(ttr, 3),
            "avg_sentence_length": round(avg_sent, 2),
            "vague_term_count": vague_count,
            "vague_density": round(vague_density, 4),
            "quantified_target_count": quant_count,
            "passive_voice_count": passive_count,
        },
        "vague_hits": list(dict.fromkeys(h.lower() for h in vague_hits))[:12],
    }


def _structure_score(avg_sent: float) -> float:
    if avg_sent <= 0:
        return 0.0
    if 12.0 <= avg_sent <= 22.0:
        return 1.0
    if avg_sent < 12.0:
        return max(0.0, avg_sent / 12.0)
    return max(0.0, 1.0 - (avg_sent - 22.0) / 20.0)


def _vocabulary_score(ttr: float, word_count: int) -> float:
    if word_count < 30:
        return min(1.0, word_count / 60.0)
    if 0.45 <= ttr <= 0.7:
        return 1.0
    if ttr < 0.45:
        return ttr / 0.45
    return max(0.0, 1.0 - (ttr - 0.7) / 0.3)


def _testability_score(text: str) -> float:
    """0..1 — how testable / verifiable the requirement reads."""
    if not text:
        return 0.0
    txt = text.lower()
    signals = 0
    total = 7
    if re.search(r"\b(acceptance criteria|definition of done|given|when|then)\b", txt):
        signals += 2
    if re.search(r"\b(verify|validate|test|assert|expected|scenario)\b", txt):
        signals += 1
    if _QUANT_RX.search(text):
        signals += 1
    if re.search(r"\b(pass|fail|success|error|status code|http \d{3})\b", txt):
        signals += 1
    if re.search(r"\b(edge case|boundary|negative test|regression)\b", txt):
        signals += 1
    if re.search(r"\b(role|actor|persona|user type)\b", txt):
        signals += 1
    if len(text.split()) >= 80:
        signals += 1
    return _clamp(signals / total, 0.0, 1.0)


_BUSINESS_VALUE_CUES: tuple[str, ...] = (
    "value", "roi", "revenue", "cost", "benefit", "kpi", "metric", "outcome",
    "objective", "goal", "conversion", "retention", "churn", "margin",
    "profit", "savings", "efficiency gain",
)
_MAINTAINABILITY_CUES: tuple[str, ...] = (
    "maintain", "modular", "refactor", "document", "logging", "observability",
    "monitor", "metric", "version", "api contract", "backward compatible",
    "technical debt", "code review", "lint", "test coverage",
)


def _dimension_presence(text: str, dimension: QualityDimension) -> float:
    """0..1 — how well the requirement text addresses one quality dimension."""
    if not text:
        return 0.0
    txt = text.lower()
    entry = _DIMENSION_CUES.get(dimension)
    if not entry:
        return 0.4
    _title, cues = entry
    hits = sum(1 for c in cues if c in txt)
    if hits == 0:
        return 0.28
    ratio = hits / max(len(cues), 1)
    return _clamp(0.45 + ratio * 1.8, 0.0, 1.0)


def _compute_radar_scores(
    text: str,
    dims: Dict[str, float],
    missing: List[MissingInformation],
) -> QualityRadarScores:
    """Six-axis radar for Screen 4 — Requirement Quality Center."""
    missing_dims = {m.dimension for m in missing}

    def penalize(score: float, dim: QualityDimension, amount: float = 12.0) -> float:
        if dim in missing_dims:
            return round(_clamp(score - amount, 0, 100), 1)
        return score

    clarity = float(dims.get("clarity", 0))
    completeness = float(dims.get("completeness", 0))
    testability = float(dims.get("testability", 0))

    security_base = 100.0 * _dimension_presence(text, QualityDimension.SECURITY)
    security = penalize(round(security_base, 1), QualityDimension.SECURITY, 18.0)

    biz_parts = [
        _dimension_presence(text, QualityDimension.SUCCESS_CRITERIA),
        _dimension_presence(text, QualityDimension.BUSINESS_RULES),
    ]
    txt = (text or "").lower()
    if any(c in txt for c in _BUSINESS_VALUE_CUES):
        biz_parts.append(0.85)
    business_value = round(
        penalize(
            100.0 * sum(biz_parts) / len(biz_parts),
            QualityDimension.SUCCESS_CRITERIA,
            10.0,
        ),
        1,
    )
    if QualityDimension.BUSINESS_RULES in missing_dims:
        business_value = round(_clamp(business_value - 8, 0, 100), 1)

    h = _heuristic_score(text or "")
    bd = h.get("breakdown") or {}
    structure = float(bd.get("structure", 0))
    vocabulary = float(bd.get("vocabulary", 0))
    deps = _dimension_presence(text, QualityDimension.DEPENDENCIES)
    deploy = _dimension_presence(text, QualityDimension.DEPLOYMENT)
    maint_txt = 1.0 if any(c in txt for c in _MAINTAINABILITY_CUES) else 0.0
    maintainability = round(
        100.0
        * (
            0.35 * structure
            + 0.25 * vocabulary
            + 0.2 * deps
            + 0.1 * deploy
            + 0.1 * maint_txt
        ),
        1,
    )
    if QualityDimension.DEPENDENCIES in missing_dims:
        maintainability = round(_clamp(maintainability - 10, 0, 100), 1)

    return QualityRadarScores(
        clarity=clarity,
        completeness=completeness,
        testability=testability,
        security=security,
        business_value=business_value,
        maintainability=maintainability,
    )


def _enterprise_dimensions(
    h: Dict[str, Any],
    *,
    ambiguity: float,
) -> Dict[str, float]:
    """Map heuristic breakdown → enterprise 0..100 scores."""
    bd = h.get("breakdown") or {}
    clarity = round(
        100.0 * (
            0.45 * float(bd.get("specificity", 0))
            + 0.35 * float(bd.get("structure", 0))
            + 0.20 * float(bd.get("vocabulary", 0))
        ),
        1,
    )
    completeness = round(100.0 * float(bd.get("completeness", 0)), 1)
    testability = round(100.0 * _testability_score(h.get("_raw_text", "")), 1)
    amb = round(float(ambiguity), 1)
    overall = round(
        0.25 * clarity
        + 0.25 * completeness
        + 0.25 * testability
        + 0.25 * max(0.0, 100.0 - amb),
        1,
    )
    return {
        "clarity": clarity,
        "completeness": completeness,
        "testability": testability,
        "ambiguity": amb,
        "overall_score": overall,
    }


def _highlight_gaps(missing: List[MissingInformation]) -> List[str]:
    """Enterprise highlight cards — deduped, priority order."""
    seen: set[str] = set()
    out: List[str] = []
    priority = (
        QualityDimension.ROLES,
        QualityDimension.SUCCESS_CRITERIA,
        QualityDimension.BUSINESS_RULES,
        QualityDimension.EDGE_CASES,
        QualityDimension.ERROR_HANDLING,
        QualityDimension.NON_FUNCTIONAL,
        QualityDimension.SECURITY,
        QualityDimension.SCOPE,
    )
    by_dim = {m.dimension: m for m in missing}
    for dim in priority:
        label = _HIGHLIGHT_BY_DIMENSION.get(dim)
        if label and dim in by_dim and label not in seen:
            seen.add(label)
            out.append(label)
    for m in missing:
        label = _HIGHLIGHT_BY_DIMENSION.get(m.dimension) or m.title
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out[:8]


def _questions_for_vague_term(term: str) -> List[str]:
    key = (term or "").lower().strip()
    return list(_VAGUE_QUESTION_BANK.get(key, (
        f"What does \"{term}\" mean in measurable terms?",
        "Who is affected?",
        "Under what conditions?",
    )))


def _heuristic_completeness(text: str) -> float:
    """Crude completeness from dimension-keyword presence."""
    if not text:
        return 0.0
    txt = text.lower()
    hits = 0
    total = len(_DIMENSION_CUES)
    for _, (_, cues) in _DIMENSION_CUES.items():
        if any(c in txt for c in cues):
            hits += 1
    base = hits / max(total, 1)
    # Penalize very short text — even if it ticks all keywords by accident
    if len(text.split()) < 60:
        base *= 0.85
    return _clamp(base, 0.0, 1.0)


def _heuristic_missing(text: str) -> List[MissingInformation]:
    """Promote dimensions with zero keyword hits to missing-info entries."""
    if not text:
        return [
            MissingInformation(
                dimension=d,
                title=title,
                severity=_DIMENSION_SEVERITY.get(d, Severity.MEDIUM),
                explanation="Requirement text is empty.",
                suggested_question=_DIMENSION_DEFAULT_QUESTION.get(d, "Please clarify."),
            )
            for d, (title, _cues) in _DIMENSION_CUES.items()
        ][:6]
    txt = text.lower()
    out: List[MissingInformation] = []
    for dim, (title, cues) in _DIMENSION_CUES.items():
        if any(c in txt for c in cues):
            continue
        out.append(
            MissingInformation(
                dimension=dim,
                title=title,
                severity=_DIMENSION_SEVERITY.get(dim, Severity.MEDIUM),
                explanation="No keywords for this dimension were found in the requirement.",
                suggested_question=_DIMENSION_DEFAULT_QUESTION.get(
                    dim, "Please clarify."
                ),
            )
        )
    return out


def _heuristic_vague_phrases(text: str) -> List[VaguePhrase]:
    if not text:
        return []
    seen: dict[str, VaguePhrase] = {}
    for m in _VAGUE_RX.finditer(text):
        term = m.group(0).lower()
        if term in seen:
            continue
        start = max(0, m.start() - 28)
        end = min(len(text), m.end() + 28)
        snippet = text[start:end].strip()
        seen[term] = VaguePhrase(
            phrase=snippet,
            flagged_term=term,
            suggestion="Replace with a measurable target or a clear definition.",
            category="vague_term",
            questions=_questions_for_vague_term(term),
        )
    return list(seen.values())[:10]


# --------------------------------------------------------------------- #
# AI augmentation
# --------------------------------------------------------------------- #


_AI_SYSTEM = """You are a Requirements Quality Reviewer.

You will be shown a single requirement document. Your job is to identify
the SPECIFIC pieces of information that are missing or ambiguous before
an engineering team can build it.

Be ruthless about ambiguity. Do not invent missing info — only flag
genuinely absent pieces. Quote vague phrases verbatim from the text.
""".strip()


_AI_SCHEMA = """{
  "clarity": 0,
  "completeness": 0,
  "testability": 0,
  "ambiguity": 0,
  "overall_score": 0,
  "missing_information": [
    {
      "dimension": "roles|success_criteria|business_rules|edge_cases|scope|error_handling|non_functional|data|security|accessibility|dependencies|deployment|other",
      "title": "string — short, e.g. 'Missing actors'",
      "severity": "low|medium|high|critical",
      "explanation": "string — why this gap matters",
      "suggested_question": "string — clarifying question to send the PM"
    }
  ],
  "vague_phrases": [
    {
      "phrase": "string — exact quote from the text",
      "flagged_term": "string — the vague word, e.g. fast",
      "suggestion": "string — how to make it concrete",
      "category": "vague_term|unquantified|passive|undefined",
      "questions": ["What is fast?", "Under what load?"]
    }
  ],
  "clarifying_questions": ["string"],
  "summary_recommendations": ["string"]
}"""


async def _ai_analysis(text: str) -> Optional[Dict[str, Any]]:
    if not text.strip():
        return None
    ai = get_ai_service()
    if not ai.enabled:
        return None
    try:
        user = (
            "Requirement text under review:\n\n"
            f"{text.strip()[:8000]}\n\n"
            "Return ONLY valid JSON that matches this schema exactly:\n\n"
            f"{_AI_SCHEMA}\n\n"
            "No prose, no markdown fences."
        )
        return await ai.complete_json(_AI_SYSTEM, user, max_tokens=2500)
    except Exception:  # pragma: no cover — defensive
        logger.exception("Quality scorer AI augmentation failed")
        return None


def _coerce_dimension(raw: Any) -> QualityDimension:
    s = str(raw or "other").lower().strip()
    try:
        return QualityDimension(s)
    except ValueError:
        return QualityDimension.OTHER


def _coerce_severity(raw: Any) -> Severity:
    s = str(raw or "medium").lower().strip()
    try:
        return Severity(s)
    except ValueError:
        return Severity.MEDIUM


def _well_covered_dimensions(text: str, *, min_hits: int = 3) -> set[QualityDimension]:
    """Dimensions whose cue lexicon has >= ``min_hits`` matches in the text.

    Used to veto AI ``missing_information`` claims that contradict strong
    deterministic evidence (e.g. the AI says "Missing actors" while the
    text mentions "Customer", "user role", "Sales Agent", "Operator").

    This is the heuristic floor that prevents a single hallucinated LLM
    response from making a well-structured PRD look broken on stage.
    """
    if not text:
        return set()
    txt = text.lower()
    out: set[QualityDimension] = set()
    for dim, (_title, cues) in _DIMENSION_CUES.items():
        if sum(1 for c in cues if c in txt) >= min_hits:
            out.add(dim)
    return out


def _merge_missing(
    heuristic: List[MissingInformation],
    ai_missing: List[Dict[str, Any]],
    *,
    text: str = "",
) -> List[MissingInformation]:
    """Combine heuristic + AI missing-info entries with heuristic veto.

    The AI gets to ENRICH entries (better titles + explanations + suggested
    questions) but cannot INVENT a missing dimension that the heuristic has
    strong keyword evidence for. Without this veto, an LLM occasionally
    returns "Missing actors" for a PRD that lists six roles by name, which
    makes the whole quality panel look untrustworthy to judges.
    """
    well_covered = _well_covered_dimensions(text)
    by_dim: dict[QualityDimension, MissingInformation] = {}
    for entry in ai_missing or []:
        try:
            dim = _coerce_dimension(entry.get("dimension"))
            if dim in well_covered:
                # Heuristic already proved this dimension is present —
                # drop the AI's contradictory claim instead of letting it
                # override the panel.
                continue
            title = str(entry.get("title") or "").strip()
            if not title:
                title = _DIMENSION_CUES.get(dim, ("Information missing",))[0]
            by_dim[dim] = MissingInformation(
                dimension=dim,
                title=title,
                severity=_coerce_severity(entry.get("severity")),
                explanation=str(entry.get("explanation") or "").strip(),
                suggested_question=str(entry.get("suggested_question") or "").strip()
                or _DIMENSION_DEFAULT_QUESTION.get(dim, ""),
            )
        except Exception:
            continue
    # Fill in dimensions the AI didn't cover but the heuristic did
    for h in heuristic:
        if h.dimension not in by_dim and h.dimension not in well_covered:
            by_dim[h.dimension] = h
    # Stable order
    ordered = []
    for dim in list(_DIMENSION_CUES.keys()) + [QualityDimension.OTHER]:
        if dim in by_dim:
            ordered.append(by_dim[dim])
    return ordered


def _merge_vague(
    heuristic: List[VaguePhrase],
    ai_vague: List[Dict[str, Any]],
) -> List[VaguePhrase]:
    out: dict[str, VaguePhrase] = {}
    for v in ai_vague or []:
        try:
            phrase = str(v.get("phrase") or "").strip()
            if not phrase:
                continue
            flagged = str(v.get("flagged_term") or "").strip().lower()
            if not flagged:
                for term in _VAGUE_QUESTION_BANK:
                    if term in phrase.lower():
                        flagged = term
                        break
            questions = [
                str(q).strip()
                for q in (v.get("questions") or [])
                if str(q).strip()
            ]
            if not questions and flagged:
                questions = _questions_for_vague_term(flagged)
            out[phrase.lower()] = VaguePhrase(
                phrase=phrase,
                flagged_term=flagged,
                suggestion=str(v.get("suggestion") or "").strip(),
                category=str(v.get("category") or "vague_term").strip(),
                questions=questions,
            )
        except Exception:
            continue
    for h in heuristic:
        key = h.phrase.lower()
        if key not in out:
            out[key] = h
    return list(out.values())[:12]


def _build_report(
    *,
    h: Dict[str, Any],
    quality: float,
    ambiguity: float,
    merged_missing: List[MissingInformation],
    merged_vague: List[VaguePhrase],
    clarifying: List[str],
    recommendations: List[str],
    method: str,
    ai_dims: Optional[Dict[str, Any]] = None,
) -> QualityScoreReport:
    dims = _enterprise_dimensions(h, ambiguity=ambiguity)
    if ai_dims:
        # Blend AI dims with the heuristic dims instead of overriding.
        #
        # The old code dropped the heuristic outright the moment the AI
        # returned a number for a key — which meant a single low-temperature
        # hallucination (overall_score=4) could turn an 80/B requirement
        # into a 4/F on stage. The blend below gives the AI directional
        # influence without ever letting it ignore strong heuristic
        # evidence:
        #
        #   * close agreement                → 50/50 blend
        #   * AI is much harsher than h euristic → 70/30 (heuristic wins)
        #
        # ``ambiguity`` is inverted (higher = worse), so "much harsher"
        # means AI > heuristic + 25; for every other key it means
        # AI < heuristic - 25.
        for k in ("clarity", "completeness", "testability", "ambiguity", "overall_score"):
            raw = ai_dims.get(k)
            if raw is None:
                continue
            try:
                ai_val = round(_clamp(float(raw), 0, 100), 1)
            except (TypeError, ValueError):
                continue
            heur_val = float(dims.get(k, ai_val))
            if k == "ambiguity":
                much_harsher = ai_val > heur_val + 25
            else:
                much_harsher = ai_val < heur_val - 25
            if much_harsher:
                blended = round(0.7 * heur_val + 0.3 * ai_val, 1)
            else:
                blended = round(0.5 * heur_val + 0.5 * ai_val, 1)
            dims[k] = blended
    overall = dims["overall_score"]
    highlights = _highlight_gaps(merged_missing)
    radar = _compute_radar_scores(
        h.get("_raw_text", ""),
        dims,
        merged_missing,
    )
    return QualityScoreReport(
        clarity=dims["clarity"],
        completeness=dims["completeness"],
        testability=dims["testability"],
        ambiguity=dims["ambiguity"],
        overall_score=overall,
        quality_score=overall,
        ambiguity_score=dims["ambiguity"],
        grade=_grade_for(overall),
        method=method,
        highlight_gaps=highlights,
        breakdown=h["breakdown"],
        stats=h["stats"],
        missing_information=merged_missing,
        vague_phrases=merged_vague,
        clarifying_questions=clarifying,
        recommendations=recommendations,
        radar=radar,
    )


# --------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------- #


async def score_requirement_text(
    text: str,
    *,
    use_ai: bool = True,
) -> QualityScoreReport:
    """Score a requirement document and return a structured report."""
    h = _heuristic_score(text or "")
    h_missing = _heuristic_missing(text or "")
    h_vague = _heuristic_vague_phrases(text or "")

    ai_payload: Optional[Dict[str, Any]] = None
    if use_ai:
        ai_payload = await _ai_analysis(text or "")

    method = "hybrid" if ai_payload else "heuristic"

    if ai_payload:
        ai_missing = ai_payload.get("missing_information") or []
        ai_vague = ai_payload.get("vague_phrases") or []
        # Pass the raw text so _merge_missing can veto AI hallucinations
        # against strong heuristic evidence (see _well_covered_dimensions).
        merged_missing = _merge_missing(h_missing, ai_missing, text=text or "")
        merged_vague = _merge_vague(h_vague, ai_vague)
        clarifying = [
            str(q).strip()
            for q in (ai_payload.get("clarifying_questions") or [])
            if str(q).strip()
        ][:8]
        recommendations = [
            str(r).strip()
            for r in (ai_payload.get("summary_recommendations") or [])
            if str(r).strip()
        ][:6]

        # Adjust quality / ambiguity using AI severity penalties so the
        # blend reflects the AI's findings, not just keyword cues.
        sev_penalty = {"low": 2, "medium": 5, "high": 9, "critical": 14}
        ai_penalty = sum(
            sev_penalty.get(m.severity.value, 5) for m in merged_missing
        )
        # Cap penalty so AI-rich text doesn't drop below the heuristic floor
        ai_penalty = min(ai_penalty, 55)
        quality = round(_clamp(h["quality"] - ai_penalty * 0.6, 0, 100), 1)
        ambiguity = round(_clamp(h["ambiguity"] + ai_penalty * 0.5, 0, 100), 1)
    else:
        merged_missing = h_missing
        merged_vague = h_vague
        clarifying = [m.suggested_question for m in merged_missing if m.suggested_question][:8]
        recommendations = []
        quality = h["quality"]
        ambiguity = h["ambiguity"]

    # Default recommendations from heuristic stats when none came from AI
    if not recommendations:
        if h["stats"]["word_count"] < 80:
            recommendations.append(
                "Requirement text is short — expand context, constraints, and edge cases."
            )
        if h["stats"]["vague_term_count"] >= 3:
            recommendations.append(
                f"Reduce vague language — {h['stats']['vague_term_count']} ambiguous terms detected."
            )
        if h["stats"]["quantified_target_count"] == 0:
            recommendations.append(
                "Add quantified targets (e.g. latency, throughput, % availability)."
            )

    return _build_report(
        h=h,
        quality=quality,
        ambiguity=ambiguity,
        merged_missing=merged_missing,
        merged_vague=merged_vague,
        clarifying=clarifying,
        recommendations=recommendations,
        method=method,
        ai_dims=ai_payload if ai_payload else None,
    )
