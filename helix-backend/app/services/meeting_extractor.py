"""Meeting-to-Requirement Agent.

Take an unstructured meeting transcript or notes (Zoom/Teams/raw)
and emit:

* Requirements
* Stories
* Tasks
* Risks
* Action Items
* Decisions

Strategy:
    LLM-first when configured. A heuristic fallback uses speaker patterns,
    action verbs, and risk keywords so the feature still works offline.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from ..models import (
    ActionItem,
    ExtractedRequirement,
    ExtractedRisk,
    ExtractedStory,
    ExtractedTask,
    MeetingExtraction,
    Severity,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.meeting_extractor")


# ---------- Heuristic patterns ----------------------------------------- #


# "Aliya:", "[10:32] Aliya:", "Aliya (Host):", "ALIYA:" — very forgiving.
_SPEAKER_RE = re.compile(
    r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,2})\s*(?:\([^)]+\))?\s*:\s*(.+)$"
)
_ACTION_VERBS = re.compile(
    r"^\s*(?:we\s+)?(?:will|need to|should|must|have to|going to|plan to|let'?s|action(?: item)?:?)\s+",
    re.I,
)
_OWNER_ASSIGN = re.compile(r"\b@([A-Z][\w'.-]+)|\bowner:\s*([A-Z][\w'.-]+)", re.I)
_DECISION_RE = re.compile(r"^\s*(?:decision|decided|agreed|conclud\w+)\s*[:\-]\s*(.+)$", re.I)
_RISK_RE = re.compile(
    r"\b(risk|concern|blocked?|blocker|worry|might fail|could break|might break|delay)\b",
    re.I,
)
_REQ_RE = re.compile(
    r"\b(must|should|shall|need to|requires?|requirement|user (?:should|must|wants? to))\b",
    re.I,
)


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _heuristic_extract(text: str, source_type: str) -> MeetingExtraction:
    text = (text or "").strip()
    if not text:
        return MeetingExtraction(source_type=source_type)

    attendees: set[str] = set()
    decisions: List[str] = []
    actions: List[ActionItem] = []
    requirements: List[ExtractedRequirement] = []
    risks: List[ExtractedRisk] = []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        m = _SPEAKER_RE.match(ln)
        speaker, body = (None, ln)
        if m:
            speaker, body = m.group(1), m.group(2)
            if speaker:
                attendees.add(speaker.strip())

        for sentence in _split_sentences(body):
            d = _DECISION_RE.match(sentence)
            if d:
                decisions.append(d.group(1).strip())
                continue
            if _ACTION_VERBS.search(sentence):
                owner = ""
                om = _OWNER_ASSIGN.search(sentence)
                if om:
                    owner = (om.group(1) or om.group(2) or "").strip()
                if not owner and speaker:
                    owner = speaker
                actions.append(
                    ActionItem(
                        description=re.sub(_ACTION_VERBS, "", sentence).strip().rstrip(".") or sentence,
                        owner=owner,
                    )
                )
            if _REQ_RE.search(sentence) and not _ACTION_VERBS.search(sentence):
                requirements.append(
                    ExtractedRequirement(
                        text=sentence.strip().rstrip("."),
                        persona=(speaker or ""),
                        confidence=0.6,
                    )
                )
            if _RISK_RE.search(sentence):
                sev = Severity.HIGH if re.search(r"\b(blocked?|blocker|delay)\b", sentence, re.I) else Severity.MEDIUM
                risks.append(
                    ExtractedRisk(
                        description=sentence.strip().rstrip("."),
                        severity=sev,
                    )
                )

    # Stories from requirements — naive but useful.
    stories: List[ExtractedStory] = []
    for req in requirements[:8]:
        title = req.text
        if len(title) > 100:
            title = title[:97] + "…"
        stories.append(
            ExtractedStory(
                title=title,
                persona=req.persona or "Stakeholder",
                goal=req.text,
                benefit="",
            )
        )

    # Tasks from action items
    tasks = [
        ExtractedTask(title=a.description[:120], owner=a.owner)
        for a in actions[:12]
    ]

    summary_bits: List[str] = []
    if attendees:
        summary_bits.append(f"{len(attendees)} attendee" + ("" if len(attendees) == 1 else "s"))
    if decisions:
        summary_bits.append(f"{len(decisions)} decision" + ("" if len(decisions) == 1 else "s"))
    summary_bits.append(f"{len(requirements)} requirement candidate" + ("" if len(requirements) == 1 else "s"))
    summary_bits.append(f"{len(actions)} action item" + ("" if len(actions) == 1 else "s"))
    summary = ", ".join(summary_bits) + "."

    return MeetingExtraction(
        source_type=source_type,
        title="Meeting capture",
        summary=summary,
        attendees=sorted(attendees),
        decisions=decisions,
        requirements=requirements,
        stories=stories,
        tasks=tasks,
        risks=risks,
        action_items=actions,
        method="heuristic",
    )


# ---------- AI extraction ---------------------------------------------- #


_AI_SYSTEM = """You are a meticulous Product Operations analyst. From
a raw meeting transcript or notes, extract structured artifacts. Be
faithful — do not invent attendees or decisions. If something is
ambiguous, prefer to omit it. Output ONLY valid JSON.""".strip()


_AI_SCHEMA = """{
  "title": "string",
  "summary": "string — 2-3 sentences",
  "attendees": ["string"],
  "decisions": ["string"],
  "requirements": [
    {"text": "string", "persona": "string", "confidence": 0.0}
  ],
  "stories": [
    {"title": "string", "persona": "string", "goal": "string", "benefit": "string"}
  ],
  "tasks": [
    {"title": "string", "owner": "string", "estimate_hours": 0}
  ],
  "risks": [
    {"description": "string", "severity": "low|medium|high|critical"}
  ],
  "action_items": [
    {"description": "string", "owner": "string", "due": "string"}
  ]
}"""


async def _ai_extract(text: str, source_type: str) -> Optional[MeetingExtraction]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    snippet = (text or "")[:8000]
    user = (
        f"Source type: {source_type}\n\n"
        f"Transcript / notes:\n---\n{snippet}\n---\n\n"
        f"Extract artifacts in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=4500)
    except Exception:
        logger.exception("Meeting AI extraction failed")
        return None

    def _str_list(key: str) -> List[str]:
        return [str(s).strip() for s in (data.get(key) or []) if str(s).strip()]

    requirements = []
    for r in (data.get("requirements") or []):
        if not isinstance(r, dict):
            continue
        t = str(r.get("text") or "").strip()
        if not t:
            continue
        try:
            conf = float(r.get("confidence") or 0.7)
        except (TypeError, ValueError):
            conf = 0.7
        requirements.append(
            ExtractedRequirement(
                text=t,
                persona=str(r.get("persona") or "").strip(),
                confidence=max(0.0, min(1.0, conf)),
            )
        )

    stories = []
    for s in (data.get("stories") or []):
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "").strip()
        if not title:
            continue
        stories.append(
            ExtractedStory(
                title=title,
                persona=str(s.get("persona") or "").strip(),
                goal=str(s.get("goal") or "").strip(),
                benefit=str(s.get("benefit") or "").strip(),
            )
        )

    tasks = []
    for t in (data.get("tasks") or []):
        if not isinstance(t, dict):
            continue
        title = str(t.get("title") or "").strip()
        if not title:
            continue
        try:
            est = float(t.get("estimate_hours")) if t.get("estimate_hours") not in (None, "") else None
        except (TypeError, ValueError):
            est = None
        tasks.append(
            ExtractedTask(
                title=title,
                owner=str(t.get("owner") or "").strip(),
                estimate_hours=est,
            )
        )

    risks = []
    for r in (data.get("risks") or []):
        if not isinstance(r, dict):
            continue
        desc = str(r.get("description") or "").strip()
        if not desc:
            continue
        sev_raw = str(r.get("severity") or "medium").strip().lower()
        try:
            sev = Severity(sev_raw)
        except ValueError:
            sev = Severity.MEDIUM
        risks.append(ExtractedRisk(description=desc, severity=sev))

    actions = []
    for a in (data.get("action_items") or []):
        if not isinstance(a, dict):
            continue
        desc = str(a.get("description") or "").strip()
        if not desc:
            continue
        actions.append(
            ActionItem(
                description=desc,
                owner=str(a.get("owner") or "").strip(),
                due=str(a.get("due") or "").strip() or None,
            )
        )

    return MeetingExtraction(
        source_type=source_type,
        title=str(data.get("title") or "Meeting capture").strip(),
        summary=str(data.get("summary") or "").strip(),
        attendees=_str_list("attendees"),
        decisions=_str_list("decisions"),
        requirements=requirements,
        stories=stories,
        tasks=tasks,
        risks=risks,
        action_items=actions,
        method="hybrid",
    )


async def extract_meeting(
    text: str,
    *,
    source_type: str = "transcript",
    use_ai: bool = True,
) -> MeetingExtraction:
    if not (text or "").strip():
        return MeetingExtraction(source_type=source_type)

    if use_ai:
        ai_out = await _ai_extract(text, source_type)
        if ai_out:
            return ai_out
    return _heuristic_extract(text, source_type)
