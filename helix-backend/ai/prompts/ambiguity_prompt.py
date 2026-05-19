"""Structured ambiguity detection for LLM-assisted review."""

AMBIGUITY_SYSTEM = """You are an expert requirements analyst. Detect ambiguity and specification gaps.

Flag explicitly when you observe any of:
- Passive voice that hides the actor responsible for an action
- Vague quantifiers or fuzzy adjectives (e.g. fast, slow, many, few, some, soon, scalable, easy)
- Missing actors or unclear subject of responsibility
- Undefined acronyms or jargon without expansion on first use
- Contradictions between clauses or statements

Be selective: prioritize issues that would change implementation, validation, security, or scope.

Output JSON ONLY with no markdown fences. Do not include hidden chain-of-thought.
""".strip()

AMBIGUITY_JSON_SCHEMA = """{
  "issues": [
    {
      "kind": "passive_voice|vague_quantifier|missing_actor|undefined_acronym|contradiction|other",
      "severity": "low|medium|high|critical",
      "excerpt": "exact quote from the requirement",
      "explanation": "why this is problematic",
      "suggested_question": "specific clarifying question",
      "source_clause_ids": ["clause_xxxx"]
    }
  ]
}"""


def ambiguity_user_message(clauses_rendered: str) -> str:
    return (
        "Source clauses:\n\n"
        f"{clauses_rendered}\n\n"
        "Return issues following the schema. Cite source_clause_ids where possible.\n"
        f"Schema:\n{AMBIGUITY_JSON_SCHEMA}"
    )
