"""Pre-LLM scan: warn or block secret-like content in requirements."""
from __future__ import annotations

import re
from typing import List

from fastapi import HTTPException, status

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_SK_OPENAI = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_JWTISH = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def scan_sensitive_hints(text: str, *, max_hints: int = 5) -> List[str]:
    """Return short, human-readable hints (empty if nothing suspicious)."""
    if not (text or "").strip():
        return []
    hints: List[str] = []
    if _EMAIL.search(text):
        hints.append("Email-like pattern detected — consider redacting before sharing.")
    if _AWS_KEY.search(text):
        hints.append("Possible AWS access key id (AKIA…) — remove before external LLM.")
    if _SK_OPENAI.search(text):
        hints.append("Possible API secret (sk-…) — rotate if this was a real key.")
    if _JWTISH.search(text):
        hints.append("JWT-shaped token detected — do not send real tokens to third parties.")
    return hints[:max_hints]


def _blocking_reasons(text: str) -> List[str]:
    reasons: List[str] = []
    if _AWS_KEY.search(text):
        reasons.append("AWS access key pattern (AKIA…)")
    if _SK_OPENAI.search(text):
        reasons.append("API secret pattern (sk-…)")
    if _JWTISH.search(text):
        reasons.append("JWT-shaped token")
    return reasons


def enforce_no_secrets_in_prompt(text: str) -> None:
    """Raise 400 when content must not be sent to an external LLM."""
    reasons = _blocking_reasons(text or "")
    if not reasons:
        return
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail={
            "message": "Remove secrets from the requirement before AI processing.",
            "blocked": reasons,
            "hints": scan_sensitive_hints(text),
        },
    )
