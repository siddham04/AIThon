"""ML-powered SDLC insights.

This module is the "scikit-learn brain" of Helix. It takes a fully-loaded
:class:`~app.models.Project` and produces:

* **Requirement quality score** — fully explainable heuristic (length,
  vocabulary diversity, ambiguity density, structural completeness).
* **Anomaly detection on tasks** — scikit-learn :class:`IsolationForest`
  applied to a numeric feature matrix (effort, hours, confidence,
  description length, dependency count, ambiguity proximity). Top-N
  anomalous tasks are returned with a human-readable reason.
* **Duplicate / near-duplicate detection on stories** — scikit-learn
  :class:`TfidfVectorizer` + cosine similarity over story
  ``title + goal + acceptance_criteria``. Pairs above a configurable
  threshold are returned.
* **Risk heatmap** — pivots ``Risk.category × Risk.severity`` to a 2D
  count grid so the UI can paint a heatmap.
* **Burndown / forecast** — simple, fully transparent projection of
  remaining effort against an assumed weekly velocity.

The scikit-learn import is lazy and falls back gracefully if the wheel
is not installed, so the API never fails to boot. The endpoint surfaces
``ml_enabled`` so the UI can degrade nicely.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any, Iterable

from ..models import (
    AmbiguityIssue,
    Project,
    Risk,
    Severity,
    Task,
    UserStory,
)

log = logging.getLogger("helix.ml_insights")

# Ambiguity / vagueness lexicon used by both the quality score and the
# anomaly reasoner. Kept inline so this module has zero NLP-data
# downloads.
_AMBIGUITY_TERMS: tuple[str, ...] = (
    "etc",
    "fast",
    "slow",
    "many",
    "few",
    "some",
    "various",
    "appropriate",
    "reasonable",
    "intuitive",
    "user-friendly",
    "user friendly",
    "robust",
    "scalable",
    "secure",
    "modern",
    "simple",
    "easy",
    "efficient",
    "flexible",
    "soon",
    "later",
    "tbd",
    "maybe",
    "approximately",
    "around",
    "roughly",
    "should",
    "could",
    "may",
    "might",
    "ideally",
    "etc.",
)

_AMBIGUITY_RX = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _AMBIGUITY_TERMS) + r")\b",
    flags=re.IGNORECASE,
)

_WORD_RX = re.compile(r"\b[\w'-]+\b", flags=re.UNICODE)
_SENTENCE_RX = re.compile(r"[.!?]+")


# --------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------- #


def build_insights(
    project: Project,
    *,
    velocity_points_per_week: float = 20.0,
    duplicate_threshold: float = 0.72,
    anomaly_top_k: int = 8,
) -> dict[str, Any]:
    """Compute the full insights bundle for one project."""
    ml_available = _try_import_sklearn() is not None

    quality = _requirement_quality(project)
    anomalies = _task_anomalies(
        project.tasks,
        project.ambiguities,
        top_k=anomaly_top_k,
        ml_available=ml_available,
    )
    duplicates = _story_duplicates(
        project.stories,
        threshold=duplicate_threshold,
        ml_available=ml_available,
    )
    risk_heatmap = _risk_heatmap(project.risks)
    burndown = _burndown(project.tasks, velocity_points_per_week)

    return {
        "project_id": project.id,
        "ml_enabled": ml_available,
        "models": _models_used(ml_available),
        "quality": quality,
        "anomalies": anomalies,
        "duplicates": duplicates,
        "risk_heatmap": risk_heatmap,
        "burndown": burndown,
    }


def _models_used(ml_available: bool) -> list[dict[str, str]]:
    if not ml_available:
        return [
            {
                "name": "Heuristic fallback",
                "purpose": "Quality, anomalies, similarity",
                "library": "pure python",
            }
        ]
    return [
        {
            "name": "IsolationForest",
            "purpose": "Task anomaly detection",
            "library": "scikit-learn",
        },
        {
            "name": "TfidfVectorizer + cosine_similarity",
            "purpose": "Near-duplicate story detection",
            "library": "scikit-learn",
        },
        {
            "name": "Lexicon-based quality score",
            "purpose": "Requirement readiness scoring",
            "library": "pure python",
        },
    ]


# --------------------------------------------------------------------- #
# Quality score
# --------------------------------------------------------------------- #


def _requirement_quality(project: Project) -> dict[str, Any]:
    text = (project.raw_input or "").strip()
    if not text and project.source_clauses:
        text = "\n".join(c.text for c in project.source_clauses)

    words = _WORD_RX.findall(text)
    sentences = [s.strip() for s in _SENTENCE_RX.split(text) if s.strip()]
    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    unique_terms = len({w.lower() for w in words})
    ttr = unique_terms / word_count if word_count else 0.0
    avg_sentence = word_count / sentence_count if word_count else 0.0
    amb_hits = len(_AMBIGUITY_RX.findall(text))
    amb_density = amb_hits / word_count if word_count else 0.0

    has_acceptance = any(
        len(s.acceptance_criteria or []) > 0 for s in project.stories
    )
    has_personas = bool(
        (project.summary and project.summary.primary_personas)
        or any((s.persona or "").strip() for s in project.stories)
    )
    has_success_metrics = bool(
        project.summary and project.summary.success_metrics
    )

    # 5 sub-scores (0–1) for an explainable breakdown.
    completeness = _clamp(
        0.35 * float(bool(text))
        + 0.30 * float(has_acceptance)
        + 0.20 * float(has_personas)
        + 0.15 * float(has_success_metrics),
        0.0,
        1.0,
    )
    specificity = _clamp(1.0 - min(amb_density * 25.0, 1.0), 0.0, 1.0)
    structure = _clamp(_sentence_length_score(avg_sentence), 0.0, 1.0)
    vocabulary = _clamp(_ttr_score(ttr, word_count), 0.0, 1.0)
    coverage = _clamp(_coverage_score(project), 0.0, 1.0)

    overall = round(
        100.0
        * (
            0.30 * completeness
            + 0.25 * specificity
            + 0.15 * structure
            + 0.10 * vocabulary
            + 0.20 * coverage
        ),
        1,
    )

    recommendations: list[str] = []
    if not has_acceptance:
        recommendations.append(
            "Add explicit acceptance criteria — none of the current stories declare any."
        )
    if amb_density > 0.02 and word_count > 40:
        recommendations.append(
            f"Reduce vague language — {amb_hits} ambiguity-prone terms detected "
            f"(density {amb_density:.1%})."
        )
    if avg_sentence > 32:
        recommendations.append(
            f"Sentences average {avg_sentence:.0f} words — split long sentences for clarity."
        )
    if not has_personas:
        recommendations.append(
            "Name the primary persona(s) — every story should answer 'who is this for?'."
        )
    if not has_success_metrics:
        recommendations.append(
            "Declare success metrics in the summary so QA and PMs can verify outcomes."
        )
    if word_count < 80:
        recommendations.append(
            "Requirement text is short — expand context, constraints, and edge cases."
        )

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "breakdown": {
            "completeness": round(completeness, 3),
            "specificity": round(specificity, 3),
            "structure": round(structure, 3),
            "vocabulary": round(vocabulary, 3),
            "coverage": round(coverage, 3),
        },
        "stats": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "unique_terms": unique_terms,
            "type_token_ratio": round(ttr, 3),
            "avg_sentence_length": round(avg_sentence, 2),
            "ambiguity_hits": amb_hits,
            "ambiguity_density": round(amb_density, 4),
            "has_acceptance_criteria": has_acceptance,
            "has_personas": has_personas,
            "has_success_metrics": has_success_metrics,
            "story_count": len(project.stories),
            "task_count": len(project.tasks),
            "test_count": len(project.test_cases),
            "risk_count": len(project.risks),
        },
        "recommendations": recommendations,
    }


def _sentence_length_score(avg: float) -> float:
    if avg <= 0:
        return 0.0
    # Ideal English business writing ~12–22 words per sentence.
    if 12.0 <= avg <= 22.0:
        return 1.0
    if avg < 12.0:
        return max(0.0, avg / 12.0)
    return max(0.0, 1.0 - (avg - 22.0) / 20.0)


def _ttr_score(ttr: float, word_count: int) -> float:
    if word_count < 30:
        # Short text — TTR is noisy, give partial credit based on length only.
        return min(1.0, word_count / 60.0)
    # Ideal TTR for business prose ~0.45–0.7.
    if 0.45 <= ttr <= 0.7:
        return 1.0
    if ttr < 0.45:
        return ttr / 0.45
    return max(0.0, 1.0 - (ttr - 0.7) / 0.3)


def _coverage_score(project: Project) -> float:
    """How well downstream artifacts cite the requirement."""
    items = list(project.stories) + list(project.tasks) + list(project.test_cases)
    if not items:
        return 0.0
    cited = sum(1 for x in items if getattr(x, "source_clause_ids", None))
    return cited / len(items)


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"


# --------------------------------------------------------------------- #
# Anomaly detection
# --------------------------------------------------------------------- #


def _task_feature_row(task: Task, ambiguity_pressure: float) -> list[float]:
    desc = (task.description or "") + " " + (task.title or "")
    return [
        float(task.estimate_points or 0),
        float(task.estimate_hours or 0.0),
        float(task.confidence if task.confidence is not None else 0.5),
        float(len(desc)),
        float(len(task.dependencies or [])),
        float(len(task.skills or [])),
        float(len(task.source_clause_ids or [])),
        float(ambiguity_pressure),
    ]


def _task_anomalies(
    tasks: list[Task],
    ambiguities: list[AmbiguityIssue],
    *,
    top_k: int,
    ml_available: bool,
) -> dict[str, Any]:
    if not tasks:
        return {
            "method": "isolation_forest" if ml_available else "heuristic",
            "items": [],
            "summary": "No tasks to analyze.",
        }

    pressure = _ambiguity_pressure_by_story(ambiguities, tasks)

    rows = [
        _task_feature_row(t, pressure.get(t.story_id or "", 0.0)) for t in tasks
    ]

    if not ml_available or len(tasks) < 4:
        return _heuristic_task_anomalies(tasks, rows, pressure, top_k)

    sk = _try_import_sklearn()
    np = sk["np"]
    IsolationForest = sk["IsolationForest"]

    X = np.array(rows, dtype=float)
    contamination = max(0.05, min(0.3, top_k / max(len(tasks), 1)))
    model = IsolationForest(
        n_estimators=120,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X)
    raw_scores = model.score_samples(X)  # higher = more normal
    preds = model.predict(X)  # -1 anomaly, 1 normal
    feature_means = X.mean(axis=0)
    feature_stds = X.std(axis=0)

    items: list[dict[str, Any]] = []
    for task, row, score, pred in zip(tasks, rows, raw_scores, preds):
        reasons = _anomaly_reasons(task, row, feature_means, feature_stds)
        items.append(
            {
                "task_id": task.id,
                "title": task.title,
                "type": getattr(task.type, "value", str(task.type)),
                "priority": getattr(task.priority, "value", str(task.priority)),
                "story_id": task.story_id,
                "estimate_points": task.estimate_points,
                "estimate_hours": task.estimate_hours,
                "confidence": task.confidence,
                "anomaly_score": round(float(-score), 4),  # invert so higher = weirder
                "is_anomaly": bool(pred == -1),
                "reasons": reasons,
            }
        )

    items.sort(key=lambda r: r["anomaly_score"], reverse=True)
    return {
        "method": "isolation_forest",
        "contamination": round(float(contamination), 3),
        "n_samples": len(tasks),
        "items": items[:top_k],
        "summary": (
            f"IsolationForest flagged "
            f"{sum(1 for i in items if i['is_anomaly'])} of {len(items)} tasks "
            "as outliers; top results shown."
        ),
    }


def _heuristic_task_anomalies(
    tasks: list[Task],
    rows: list[list[float]],
    pressure: dict[str, float],
    top_k: int,
) -> dict[str, Any]:
    """Fallback when scikit-learn or enough data is unavailable."""
    if not rows:
        return {"method": "heuristic", "items": [], "summary": "No tasks to analyze."}
    cols = list(zip(*rows))
    means = [sum(c) / len(c) for c in cols]
    stds = [_std(c, m) for c, m in zip(cols, means)]
    items: list[dict[str, Any]] = []
    for task, row in zip(tasks, rows):
        z = 0.0
        for v, m, s in zip(row, means, stds):
            if s > 1e-9:
                z = max(z, abs(v - m) / s)
        reasons = _anomaly_reasons(task, row, means, stds)
        items.append(
            {
                "task_id": task.id,
                "title": task.title,
                "type": getattr(task.type, "value", str(task.type)),
                "priority": getattr(task.priority, "value", str(task.priority)),
                "story_id": task.story_id,
                "estimate_points": task.estimate_points,
                "estimate_hours": task.estimate_hours,
                "confidence": task.confidence,
                "anomaly_score": round(z, 4),
                "is_anomaly": z >= 2.0,
                "reasons": reasons,
            }
        )
    items.sort(key=lambda r: r["anomaly_score"], reverse=True)
    flagged = sum(1 for i in items if i["is_anomaly"])
    return {
        "method": "heuristic",
        "n_samples": len(tasks),
        "items": items[:top_k],
        "summary": f"Z-score fallback flagged {flagged} of {len(items)} tasks.",
    }


def _anomaly_reasons(
    task: Task,
    row: list[float],
    means: Iterable[float],
    stds: Iterable[float],
) -> list[str]:
    feature_labels = (
        "estimate (points)",
        "estimate (hours)",
        "confidence",
        "description length",
        "dependency count",
        "skill count",
        "citation count",
        "ambiguity pressure",
    )
    reasons: list[str] = []
    for label, v, m, s in zip(feature_labels, row, means, stds):
        if s < 1e-9:
            continue
        z = (v - m) / s
        if abs(z) >= 1.8:
            direction = "high" if z > 0 else "low"
            reasons.append(
                f"{label} unusually {direction} ({_fmt_num(v)} vs typical {_fmt_num(m)})"
            )
    if task.confidence is not None and task.estimate_points and task.confidence < 0.4:
        reasons.append(
            "Low model confidence on a sized task — review the breakdown before sprint planning."
        )
    if (task.estimate_points or 0) >= 13 and not (task.dependencies or []):
        reasons.append(
            "Large estimate but zero declared dependencies — may be missing handoffs."
        )
    if not task.source_clause_ids:
        reasons.append(
            "Task has no citation back to a source clause — traceability gap."
        )
    return reasons[:4]


def _ambiguity_pressure_by_story(
    ambiguities: list[AmbiguityIssue],
    tasks: list[Task],
) -> dict[str, float]:
    """Per-task ambiguity pressure: count of unresolved high/critical
    ambiguities touching the same clauses."""
    if not ambiguities:
        return {}
    sev_w = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15}
    clause_weight: Counter[str] = Counter()
    for a in ambiguities:
        if a.resolved:
            continue
        sev = getattr(a.severity, "value", str(a.severity)).lower()
        w = sev_w.get(sev, 0.4)
        for cid in a.source_clause_ids or []:
            clause_weight[cid] += w
    if not clause_weight:
        return {}
    by_story: dict[str, float] = {}
    for t in tasks:
        if not t.story_id:
            continue
        pressure = sum(clause_weight.get(c, 0.0) for c in (t.source_clause_ids or []))
        if pressure:
            by_story[t.story_id] = max(by_story.get(t.story_id, 0.0), pressure)
    return by_story


# --------------------------------------------------------------------- #
# Duplicate detection (TF-IDF + cosine)
# --------------------------------------------------------------------- #


def _story_corpus(story: UserStory) -> str:
    parts = [story.title or "", story.goal or "", story.benefit or ""]
    parts.extend(story.acceptance_criteria or [])
    return "  ".join(p for p in parts if p).strip()


def _story_duplicates(
    stories: list[UserStory],
    *,
    threshold: float,
    ml_available: bool,
) -> dict[str, Any]:
    if len(stories) < 2:
        return {
            "method": "tfidf_cosine" if ml_available else "jaccard",
            "threshold": threshold,
            "pairs": [],
            "summary": "Need at least two stories to compare.",
        }

    corpora = [_story_corpus(s) for s in stories]
    if all(not c for c in corpora):
        return {
            "method": "tfidf_cosine" if ml_available else "jaccard",
            "threshold": threshold,
            "pairs": [],
            "summary": "Stories have no text to compare.",
        }

    if ml_available:
        return _tfidf_duplicates(stories, corpora, threshold)
    return _jaccard_duplicates(stories, corpora, threshold)


def _tfidf_duplicates(
    stories: list[UserStory],
    corpora: list[str],
    threshold: float,
) -> dict[str, Any]:
    sk = _try_import_sklearn()
    TfidfVectorizer = sk["TfidfVectorizer"]
    cosine_similarity = sk["cosine_similarity"]
    try:
        vec = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        matrix = vec.fit_transform(corpora)
    except ValueError:
        return _jaccard_duplicates(stories, corpora, threshold)

    sim = cosine_similarity(matrix)
    pairs: list[dict[str, Any]] = []
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            s = float(sim[i, j])
            if s >= threshold:
                pairs.append(
                    {
                        "story_a": _story_brief(stories[i]),
                        "story_b": _story_brief(stories[j]),
                        "similarity": round(s, 3),
                        "overlap_terms": _shared_terms(corpora[i], corpora[j], limit=6),
                    }
                )
    pairs.sort(key=lambda r: r["similarity"], reverse=True)
    return {
        "method": "tfidf_cosine",
        "threshold": threshold,
        "pairs": pairs[:10],
        "summary": f"{len(pairs)} duplicate-leaning pair(s) at ≥{int(threshold * 100)}% similarity.",
    }


def _jaccard_duplicates(
    stories: list[UserStory],
    corpora: list[str],
    threshold: float,
) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    token_sets = [
        {w.lower() for w in _WORD_RX.findall(text) if len(w) > 2}
        for text in corpora
    ]
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            a, b = token_sets[i], token_sets[j]
            if not a or not b:
                continue
            sim = len(a & b) / len(a | b)
            if sim >= threshold:
                pairs.append(
                    {
                        "story_a": _story_brief(stories[i]),
                        "story_b": _story_brief(stories[j]),
                        "similarity": round(sim, 3),
                        "overlap_terms": sorted(list(a & b))[:6],
                    }
                )
    pairs.sort(key=lambda r: r["similarity"], reverse=True)
    return {
        "method": "jaccard",
        "threshold": threshold,
        "pairs": pairs[:10],
        "summary": f"{len(pairs)} duplicate-leaning pair(s) (Jaccard fallback).",
    }


def _story_brief(s: UserStory) -> dict[str, Any]:
    return {
        "id": s.id,
        "title": s.title,
        "persona": s.persona,
        "goal": s.goal,
    }


def _shared_terms(a: str, b: str, *, limit: int = 6) -> list[str]:
    sa = {w.lower() for w in _WORD_RX.findall(a) if len(w) > 3}
    sb = {w.lower() for w in _WORD_RX.findall(b) if len(w) > 3}
    return sorted(sa & sb)[:limit]


# --------------------------------------------------------------------- #
# Risk heatmap
# --------------------------------------------------------------------- #


def _risk_heatmap(risks: list[Risk]) -> dict[str, Any]:
    severities = [s.value for s in Severity]
    categories = sorted({r.category.value for r in risks}) if risks else []
    grid: list[dict[str, Any]] = []
    counts: Counter[tuple[str, str]] = Counter()
    risk_index: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in risks:
        key = (r.category.value, r.severity.value)
        counts[key] += 1
        risk_index.setdefault(key, []).append(
            {"id": r.id, "title": r.title, "mitigation": r.mitigation}
        )
    for cat in categories:
        for sev in severities:
            key = (cat, sev)
            grid.append(
                {
                    "category": cat,
                    "severity": sev,
                    "count": counts.get(key, 0),
                    "risks": risk_index.get(key, []),
                }
            )
    return {
        "categories": categories,
        "severities": severities,
        "grid": grid,
        "total": len(risks),
        "highest_severity": _highest_severity(risks),
    }


def _highest_severity(risks: list[Risk]) -> str | None:
    if not risks:
        return None
    order = ["critical", "high", "medium", "low"]
    have = {r.severity.value for r in risks}
    for level in order:
        if level in have:
            return level
    return None


# --------------------------------------------------------------------- #
# Burndown forecast
# --------------------------------------------------------------------- #


def _burndown(tasks: list[Task], velocity: float) -> dict[str, Any]:
    if not tasks:
        return {
            "total_points": 0,
            "completed_points": 0,
            "remaining_points": 0,
            "velocity_points_per_week": velocity,
            "weeks_to_done": 0.0,
            "series": [],
            "assumed_complete_when_approved": True,
        }
    total = sum(int(t.estimate_points or 0) for t in tasks)
    # Treat approved-for-export as "done" for the forecast; gives the UI a
    # live, click-driven burndown that responds to the export gate.
    completed = sum(
        int(t.estimate_points or 0) for t in tasks if getattr(t, "approved_for_export", False)
    )
    remaining = max(total - completed, 0)
    v = max(velocity, 1.0)
    weeks_to_done = round(remaining / v, 2)

    series: list[dict[str, Any]] = []
    weeks = int(math.ceil(weeks_to_done)) if weeks_to_done > 0 else 1
    weeks = max(weeks, 4)
    remaining_curve = total - completed
    for w in range(weeks + 1):
        ideal = max(total - v * w, 0)
        projected = max(remaining_curve - v * w, 0)
        series.append(
            {
                "week": w,
                "ideal_remaining": round(ideal, 2),
                "projected_remaining": round(projected, 2),
            }
        )

    return {
        "total_points": total,
        "completed_points": completed,
        "remaining_points": remaining,
        "velocity_points_per_week": velocity,
        "weeks_to_done": weeks_to_done,
        "series": series,
        "assumed_complete_when_approved": True,
    }


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


_SKLEARN_CACHE: dict[str, Any] | None = None
_SKLEARN_TRIED: bool = False


def _try_import_sklearn() -> dict[str, Any] | None:
    """Lazy import scikit-learn so the API boots even without the wheel."""
    global _SKLEARN_CACHE, _SKLEARN_TRIED
    if _SKLEARN_TRIED:
        return _SKLEARN_CACHE
    _SKLEARN_TRIED = True
    try:
        import numpy as np  # type: ignore
        from sklearn.ensemble import IsolationForest  # type: ignore
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        _SKLEARN_CACHE = {
            "np": np,
            "IsolationForest": IsolationForest,
            "TfidfVectorizer": TfidfVectorizer,
            "cosine_similarity": cosine_similarity,
        }
    except Exception as exc:  # pragma: no cover - fallback path
        log.info("scikit-learn unavailable, falling back to heuristics: %s", exc)
        _SKLEARN_CACHE = None
    return _SKLEARN_CACHE


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _std(values: Iterable[float], mean: float) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))


def _fmt_num(v: float) -> str:
    if v == 0:
        return "0"
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"
