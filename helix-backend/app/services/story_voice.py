"""Normalize AI-generated story persona / goal / benefit text.

The user-story template across the codebase is::

    f"As a {persona}, I want {goal}, so that {benefit}."

For that template to render as grammatical English the agent JSON has
to follow strict conventions:

* ``persona``  → noun phrase, no trailing period   (e.g. "Customer")
* ``goal``     → bare verb phrase, lowercase initial
                  (e.g. "place a service order")
* ``benefit``  → independent clause starting with a subject + auxiliary
                  (e.g. "they can activate service without visiting a store")

In practice LLMs frequently violate those conventions and produce
"I want **Place** a service order" or "so that **to** comply with X".
These helpers fix both at the data layer so every downstream view
(Jira CSV, GitHub Markdown, exec summary, in-app preview) reads cleanly
without each consumer having to do its own grammar repair.

Pure, no side effects, no deps — safe to import from any agent.
"""
from __future__ import annotations


# Prefixes that signal "what follows is a bare verb phrase" (e.g.
# "to comply with X"). When stripped, the residue needs a subject so
# the user-story template renders as a complete clause.
_VERB_INTRODUCER_PREFIXES: tuple[str, ...] = (
    "in order to ",
    "to ",
)

# Prefix the template itself adds; if the AI also adds it, just dedupe.
# The text after this prefix is already a clause and must NOT have
# "the team can" prepended.
_TEMPLATE_PREFIX = "so that "

# Words that already signal "this clause has a subject + auxiliary".
# If the benefit starts with one of these we leave it alone.
_BENEFIT_STARTERS: frozenset[str] = frozenset(
    {
        "we", "i", "users", "user", "customers", "customer", "the", "they",
        "it", "every", "all", "no", "any", "an", "a", "this", "these",
        "our", "their", "his", "her", "its", "operators", "operator",
        "admins", "admin", "agents", "agent", "engineers", "engineer",
        "stakeholders", "stakeholder", "ops",
    }
)


def normalize_persona(persona: str) -> str:
    """Strip noise; default to ``"User"`` when empty."""
    p = (persona or "").strip().rstrip(".")
    return p or "User"


def normalize_goal(goal: str) -> str:
    """Lowercase the leading verb of a goal phrase.

    "Place a service order"   → "place a service order"
    "API rate limiting works" → "API rate limiting works"   (preserves acronym)
    "to view my orders"       → "to view my orders"         (already lowercase)
    ""                        → ""
    """
    g = (goal or "").strip().rstrip(".")
    if not g:
        return ""
    parts = g.split(None, 1)
    head = parts[0]
    # Only downcase Word-Case openings (e.g. "Place"); preserve acronyms
    # like "API" / "REST" / "JWT" (head.isupper()) and lowercase heads.
    if (
        len(head) >= 2
        and head[0].isupper()
        and head[1].islower()
    ):
        g = head.lower() + ((" " + parts[1]) if len(parts) > 1 else "")
    return g


def normalize_benefit(benefit: str) -> str:
    """Make a benefit phrase render cleanly under ``"so that {benefit}"``.

    Two failure modes the AI exhibits in practice:

    1. ``"to comply with regulations"`` — strip ``to``/``in order to`` and
       prepend ``"the team can"`` so the template reads as a clause.
    2. ``"so that revenue grows"`` — dedupe the redundant ``so that``
       prefix that the template will add itself; do NOT prepend a subject
       because the residue is already a complete clause.

    Anything that already begins with a subject pronoun (``I``, ``we``,
    ``users``, ``the system``, etc.) is left untouched. We do not try to
    detect "bare verb phrase without a prefix" (e.g. ``"Comply with X"``)
    because the heuristic would mis-fire on noun-led clauses like
    ``"Revenue grows"`` — better to leave a slightly odd phrasing
    alone than to introduce a confident grammatical error.
    """
    b = (benefit or "").strip().rstrip(".")
    if not b:
        return ""

    lowered = b.lower()

    # Case A — verb-introducer prefix → strip and rebuild as a clause.
    needs_subject = False
    for bad in _VERB_INTRODUCER_PREFIXES:
        if lowered.startswith(bad):
            b = b[len(bad):].lstrip()
            needs_subject = True
            break
    else:
        # Case B — the AI already wrote "so that …"; dedupe but leave
        # the residue alone, it's already a clause.
        if lowered.startswith(_TEMPLATE_PREFIX):
            b = b[len(_TEMPLATE_PREFIX):].lstrip()

    if not b:
        return ""

    if not needs_subject:
        return b

    first = b.split(None, 1)[0].lower().rstrip(",;:")
    if first in _BENEFIT_STARTERS:
        return b

    # The verb-introducer guarantees what follows is a bare verb phrase.
    # Downcase any stray capital so the joined output reads naturally:
    # "so that the team can deliver value".
    if b[0].isupper() and (len(b) < 2 or not b[1].isupper()):
        b = b[0].lower() + b[1:]
    return f"the team can {b}"


def normalize_voice(
    persona: str, goal: str, benefit: str
) -> tuple[str, str, str]:
    """Convenience wrapper — apply all three normalisers at once."""
    return normalize_persona(persona), normalize_goal(goal), normalize_benefit(benefit)
