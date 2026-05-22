"""Requirement Version Diff.

Heuristic: split each version into normalised sentences, then walk a
SequenceMatcher to label each opcode as added / removed / changed.

Optional LLM pass groups the diffs into a "what really changed" summary
(e.g. "MFA replaced Email Login").
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from ..models import DiffEntry, RequirementDiffReport
from .ai_service import get_ai_service

logger = logging.getLogger("helix.requirement_diff")


_BULLET_RE = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s+", re.M)


def _normalise(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip().rstrip(".").lower()


def _atomise(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    # Strip bullets, then split on bullets / newlines / sentence ends.
    text = _BULLET_RE.sub("", text)
    chunks = re.split(r"(?:\n+|(?<=[.!?])\s+)", text)
    return [c.strip().rstrip(".") for c in chunks if c.strip()]


def _heuristic_diff(version_a: str, version_b: str, title_a: str, title_b: str) -> RequirementDiffReport:
    a_atoms = _atomise(version_a)
    b_atoms = _atomise(version_b)
    a_norm = [_normalise(x) for x in a_atoms]
    b_norm = [_normalise(x) for x in b_atoms]

    sm = SequenceMatcher(a=a_norm, b=b_norm, autojunk=False)
    added: List[DiffEntry] = []
    removed: List[DiffEntry] = []
    changed: List[DiffEntry] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            for j in range(j1, j2):
                added.append(DiffEntry(kind="added", text=b_atoms[j]))
        elif tag == "delete":
            for i in range(i1, i2):
                removed.append(DiffEntry(kind="removed", text=a_atoms[i]))
        elif tag == "replace":
            # Pair them up; surplus on either side becomes pure add/remove.
            pair_count = min(i2 - i1, j2 - j1)
            for k in range(pair_count):
                changed.append(
                    DiffEntry(
                        kind="changed",
                        before=a_atoms[i1 + k],
                        after=b_atoms[j1 + k],
                        text=f"{a_atoms[i1 + k]} → {b_atoms[j1 + k]}",
                    )
                )
            for i in range(i1 + pair_count, i2):
                removed.append(DiffEntry(kind="removed", text=a_atoms[i]))
            for j in range(j1 + pair_count, j2):
                added.append(DiffEntry(kind="added", text=b_atoms[j]))

    summary = (
        f"{len(added)} added, {len(removed)} removed, {len(changed)} changed."
    )

    return RequirementDiffReport(
        title_a=title_a or "Version A",
        title_b=title_b or "Version B",
        summary=summary,
        added=added,
        removed=removed,
        changed=changed,
        method="heuristic",
    )


# ---------- AI summary pass ------------------------------------------- #


_AI_SYSTEM = (
    "You are a senior product analyst comparing two requirement "
    "versions. Given the structured diff, write ONE paragraph that "
    "tells the human what materially changed and why it matters. "
    "Output ONLY valid JSON."
)

_AI_SCHEMA = '{"summary": "string"}'


async def _ai_summarise(report: RequirementDiffReport) -> Optional[RequirementDiffReport]:
    ai = get_ai_service()
    if not ai.enabled:
        return None

    def _bullets(entries: List[DiffEntry]) -> str:
        return "\n".join(f"  - {e.text}" for e in entries[:30]) or "  (none)"

    user = (
        f"Added:\n{_bullets(report.added)}\n\n"
        f"Removed:\n{_bullets(report.removed)}\n\n"
        f"Changed:\n{_bullets(report.changed)}\n\n"
        f"Schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=900)
    except Exception:
        logger.exception("Diff AI failed")
        return None
    new_summary = str(data.get("summary") or "").strip()
    if not new_summary:
        return None
    return report.model_copy(update={"summary": new_summary, "method": "hybrid"})


async def compute_requirement_diff(
    version_a: str,
    version_b: str,
    *,
    title_a: str = "Version A",
    title_b: str = "Version B",
    use_ai: bool = True,
) -> RequirementDiffReport:
    base = _heuristic_diff(version_a, version_b, title_a, title_b)
    if not use_ai:
        return base
    refined = await _ai_summarise(base)
    return refined or base


__all__ = ["compute_requirement_diff"]
