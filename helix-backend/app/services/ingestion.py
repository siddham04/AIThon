"""Document ingestion + clause segmentation.

Clauses are atomic source spans (sentence-ish) that downstream artifacts cite,
giving every generated task / test / risk a verifiable provenance.

Two pre-processing concerns live here:

  1. The Mission Control UI prepends a ``[Helix team configuration]``
     block (see ``helix-frontend/src/lib/missionConfig.js``) to every
     ingestion payload so the LLM knows team size / sprint length /
     tech-stack preferences. That block is *not* a requirement — if it
     leaks into ``source_clauses`` it becomes garbage stories like
     ``Deliver: Team size: 6 engineers``. We strip it here.

  2. Real-world PRDs (case studies, marketing one-pagers, OCR output)
     contain a lot of non-requirement noise: section headers, copyright
     footers, page numbers, vendor URLs. We filter the most obvious
     offenders before the splitter ever sees them so the downstream
     decomposer only ever gets substantive prose.
"""
from __future__ import annotations

import io
import re
from typing import List, Tuple

from ..models import SourceClause


def extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


def extract_text_from_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if name.endswith(".docx"):
        return extract_text_from_docx(data)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore").strip()
    # Best-effort: try utf-8
    return data.decode("utf-8", errors="ignore").strip()


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+")


# --- Pre-clause filtering ----------------------------------------------- #

# The frontend prepends this block (see helix-frontend/src/lib/missionConfig.js).
# We match leniently — any "[Helix team configuration]" preamble that ends in a
# horizontal rule (``---``) on its own line is stripped wholesale.
_TEAM_CONFIG_BLOCK = re.compile(
    r"^\s*\[Helix team configuration\][\s\S]*?(?:^|\n)-{3,}\s*\n?",
    re.MULTILINE,
)

# Lines that are obviously not requirements. Matched case-insensitively
# against the full stripped line. Keep this conservative — false positives
# here silently drop real requirements.
_NOISE_LINE_PATTERNS = (
    re.compile(r"^all rights reserved\.?$", re.IGNORECASE),
    re.compile(r"^internal$", re.IGNORECASE),
    re.compile(r"^confidential$", re.IGNORECASE),
    re.compile(r"^©.*$", re.IGNORECASE),
    re.compile(r"^copyright\b.*$", re.IGNORECASE),
    re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),  # "1 / 12" footers
    re.compile(r"^[a-z0-9.-]+\.(com|net|org|io|co|ai)/?$", re.IGNORECASE),
    re.compile(r"^[-=_*•·]{3,}$"),  # decorative separators
)

# Section-header heuristic: a short line (<= 6 words) that is title-cased
# or all-caps and contains no sentence verb. Used in addition to the
# explicit allow-list below to skip "Overview", "Key Highlights", etc.
_KNOWN_HEADERS = {
    "overview",
    "summary",
    "introduction",
    "background",
    "our solution",
    "our approach",
    "our solution and approach",
    "solution and approach",
    "the solution",
    "the approach",
    "key highlights",
    "key features",
    "key benefits",
    "key results",
    "technology stack",
    "tech stack",
    "business impact",
    "highlights",
    "appendix",
    "contents",
    "table of contents",
    "references",
    "acknowledgements",
    "abstract",
    "executive summary",
}

# Words that are allowed to be lowercase inside an otherwise title-cased
# section header. "Our Solution and Approach" → header (because "and"
# is in this set so it doesn't disqualify the title-case check).
_HEADER_STOPWORDS = {
    "and", "or", "of", "for", "to", "in", "on", "at", "by",
    "the", "a", "an", "with", "from", "into",
}


def _strip_team_config_preamble(text: str) -> Tuple[str, str]:
    """Remove the Mission Control team-config preamble from ``text``.

    Returns ``(cleaned_text, removed_block)``. ``removed_block`` is the
    raw preamble for callers that want to parse team_size / sprint
    length back out — today nobody does (the planner takes those as
    explicit parameters) but we surface it for forward-compatibility.
    """
    if "[Helix team configuration]" not in text:
        return text, ""
    match = _TEAM_CONFIG_BLOCK.search(text)
    if not match:
        return text, ""
    cleaned = (text[: match.start()] + text[match.end():]).lstrip()
    return cleaned, match.group(0)


def _looks_like_noise(line: str) -> bool:
    """Return True for footer / copyright / page-number style lines."""
    stripped = line.strip()
    if not stripped:
        return True
    for pat in _NOISE_LINE_PATTERNS:
        if pat.match(stripped):
            return True
    return False


def _looks_like_header(line: str) -> bool:
    """Return True for short section-header-style lines we should drop.

    Conservative: only flags lines short enough to obviously be a label
    AND that contain no verb-like token. This deliberately keeps real
    requirements ("Authenticate users with OAuth") even though they
    start with a verb.
    """
    stripped = line.strip().rstrip(":")
    if not stripped:
        return False
    if stripped.lower() in _KNOWN_HEADERS:
        return True
    words = stripped.split()
    if len(words) > 6:
        return False
    # Long-enough lines that are title-case or all-caps and have no
    # action verb look like headers. A loose check is enough.
    if stripped.isupper():
        return True
    # Title-case check that ignores small connector stopwords ("and",
    # "of", "for", ...). Without this, "Our Solution and Approach"
    # slips through because "and" is lowercase — yet that's clearly
    # a section header, not a requirement.
    content_words = [w for w in words if w.lower() not in _HEADER_STOPWORDS]
    if content_words and all(w[:1].isupper() for w in content_words):
        if not stripped.endswith((".", "!", "?")):
            return True
    return False


def split_into_clauses(text: str) -> List[SourceClause]:
    """Split raw text into ordered, indexed clauses.

    Honors bullet points and line breaks; merges very short fragments back
    into the previous clause to avoid noise. Also strips the Mission Control
    team-config preamble and filters obvious page-furniture lines so the
    downstream decomposer never has to invent stories for them.
    """
    text = text.strip()
    if not text:
        return []

    text, _config = _strip_team_config_preamble(text)
    text = text.strip()
    if not text:
        return []

    raw_lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Treat list bullets / numbering as their own line
        line = re.sub(r"^[-*•·]\s+", "", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        if _looks_like_noise(line):
            continue
        if _looks_like_header(line):
            continue
        raw_lines.append(line)

    candidates: List[str] = []
    for line in raw_lines:
        for piece in _SENT_SPLIT.split(line):
            piece = piece.strip()
            if not piece:
                continue
            # Run the noise + header filters AGAIN on each post-split
            # fragment. A line like ``All rights reserved. Internal``
            # passes the line-level filter (neither pattern matches the
            # whole thing) but the sentence splitter produces "Internal"
            # which absolutely is noise. Without this second pass the
            # demo Jira preview gets a "Deliver: Internal" story.
            if _looks_like_noise(piece) or _looks_like_header(piece):
                continue
            candidates.append(piece)

    # Merge tiny fragments
    merged: List[str] = []
    for c in candidates:
        if merged and len(c) < 25 and not merged[-1].endswith((".", "!", "?")):
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)

    clauses_out = [
        SourceClause(index=i, text=t)
        for i, t in enumerate(merged)
    ]
    if not clauses_out:
        # If filtering removed everything (e.g. a PRD that is *only*
        # headers), fall back to the raw text so we never end up with
        # zero clauses — that would break every downstream agent.
        return [SourceClause(index=0, text=text[:4000])]
    return clauses_out


def render_clauses(clauses: List[SourceClause]) -> str:
    """Render clauses for LLM consumption with stable ids."""
    return "\n".join(f"[{c.id}] {c.text}" for c in clauses)
