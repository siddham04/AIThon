"""BDD / Gherkin-oriented test generation prompt."""

TESTCASE_SYSTEM = """You are a staff QA engineer. For EACH user story provided, design Behaviour-Driven
Development style scenarios using Given / When / Then.

For every story you MUST output exactly four scenarios:
1) positive path — primary happy flow
2) negative path — invalid input, unauthorized, business rule violation, or failure handling
3) edge case — boundary values, empty states, concurrency/idempotency where relevant
4) security — authn/authz, injection, data exposure, abuse cases (mark type as security)

Use concise, concrete steps. Cite the story id verbatim.

Output JSON ONLY (no markdown). No chain-of-thought in the output.
""".strip()

TESTCASE_JSON_SCHEMA = """{
  "tests": [
    {
      "story_id": "story_xxxx",
      "category": "positive|negative|edge|security",
      "title": "string",
      "type": "unit|integration|e2e|performance|security|accessibility",
      "given": "string",
      "when": "string",
      "then": "string",
      "edge_cases": ["optional extra probes"],
      "source_clause_ids": ["clause_xxxx"]
    }
  ]
}"""


def testcase_user_message(stories_block: str) -> str:
    return (
        "User stories (with ids):\n\n"
        f"{stories_block}\n\n"
        "Generate tests per story as specified. Include story_id on every test.\n"
        f"Schema:\n{TESTCASE_JSON_SCHEMA}"
    )
