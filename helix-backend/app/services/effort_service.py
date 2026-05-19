"""Aggregate per-task estimates into project-level rollups."""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Mapping


def calculate_project_estimate(tasks: List[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate `{story_points, hours_low, hours_high, confidence}` entries."""
    points = 0
    hours_low = 0.0
    hours_high = 0.0
    confidences: List[float] = []

    for t in tasks:
        sp = t.get("story_points")
        if sp is None:
            sp = t.get("estimate_points")
        try:
            points += int(sp or 0)
        except (TypeError, ValueError):
            pass
        try:
            lo = float(t.get("hours_low", 0) or 0)
            hi = float(t.get("hours_high", 0) or 0)
        except (TypeError, ValueError):
            lo, hi = 0.0, 0.0
        hours_low += lo
        hours_high += hi
        try:
            c = float(t.get("confidence", 0) or 0)
            if c > 0:
                confidences.append(min(1.0, max(0.0, c)))
        except (TypeError, ValueError):
            pass

    confidence = round(mean(confidences), 3) if confidences else None
    return {
        "total_points": points,
        "hours_low": round(hours_low, 2),
        "hours_high": round(hours_high, 2),
        "confidence": confidence,
    }
