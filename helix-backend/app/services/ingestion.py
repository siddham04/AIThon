"""Document ingestion + clause segmentation.

Clauses are atomic source spans (sentence-ish) that downstream artifacts cite,
giving every generated task / test / risk a verifiable provenance.
"""
from __future__ import annotations

import io
import re
from typing import List

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


def split_into_clauses(text: str) -> List[SourceClause]:
    """Split raw text into ordered, indexed clauses.

    Honors bullet points and line breaks; merges very short fragments back
    into the previous clause to avoid noise.
    """
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
        raw_lines.append(line)

    candidates: List[str] = []
    for line in raw_lines:
        for piece in _SENT_SPLIT.split(line):
            piece = piece.strip()
            if piece:
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
        return [SourceClause(index=0, text=text[:4000])]
    return clauses_out


def render_clauses(clauses: List[SourceClause]) -> str:
    """Render clauses for LLM consumption with stable ids."""
    return "\n".join(f"[{c.id}] {c.text}" for c in clauses)
