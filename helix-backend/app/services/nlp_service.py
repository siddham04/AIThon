"""Lightweight ambiguity cues using spaCy (en_core_web_sm)."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("helix.nlp")

_VAGUE_WORDS = frozenset(
    {
        "fast",
        "slow",
        "quick",
        "soon",
        "many",
        "few",
        "some",
        "several",
        "often",
        "usually",
        "scalable",
        "easy",
        "simple",
        "robust",
        "user-friendly",
        "intuitive",
        "better",
        "large",
        "small",
    }
)

_PASSIVE_AUX = re.compile(
    r"\b(am|is|are|was|were|been|being)\s+\w+ed\b|\b(is|are|was|were)\s+\w+en\b",
    re.I,
)


def _load_nlp():
    try:
        import spacy

        return spacy.load("en_core_web_sm")
    except Exception as exc:  # pragma: no cover
        logger.warning("spaCy model unavailable (%s); NLP ambiguity detection degraded.", exc)
        return None


_nlp = None
_nlp_tried = False


def _get_nlp():
    global _nlp, _nlp_tried
    if _nlp_tried:
        return _nlp
    _nlp_tried = True
    _nlp = _load_nlp()
    return _nlp


def detect_ambiguities(text: str) -> List[Dict[str, Any]]:
    """Return heuristic ambiguity highlights: passive voice, vague tokens, missing subjects."""
    text = (text or "").strip()
    out: List[Dict[str, Any]] = []
    if not text:
        return out

    for m in _PASSIVE_AUX.finditer(text):
        span = m.group(0)
        out.append(
            {
                "kind": "passive_voice",
                "span": span[:200],
                "detail": "Passive construction may hide the responsible actor.",
                "start_char": m.start(),
            }
        )

    tokens = re.findall(r"[A-Za-z]+", text.lower())
    for i, w in enumerate(tokens):
        if w in _VAGUE_WORDS:
            out.append(
                {
                    "kind": "vague_quantifier",
                    "span": w,
                    "detail": "Vague or unquantified wording; define measurable criteria.",
                    "start_char": None,
                }
            )

    nlp = _get_nlp()
    if nlp is None:
        return out[:100]

    doc = nlp(text[:490000])
    for sent in doc.sents:
        root = sent.root
        subjs = [c for c in root.children if c.dep_ in ("nsubj", "nsubjpass")]
        if root.pos_ == "VERB" and not subjs:
            frag = sent.text.strip().replace("\n", " ")
            if len(frag) > 240:
                frag = frag[:237] + "..."
            out.append(
                {
                    "kind": "missing_subject",
                    "span": frag,
                    "detail": "Sentence appears to lack an explicit subject for the main verb.",
                    "start_char": sent.start_char,
                }
            )

    return out[:150]
