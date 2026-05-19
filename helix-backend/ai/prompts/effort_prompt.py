"""Effort estimation prompt — per-task ranges and confidence."""

EFFORT_SYSTEM = """You are an engineering manager estimating sprint-level work.

For each task, assign Fibonacci story points, an hour range (low/high) inclusive of implementation,
tests, and code review — but NOT calendar contingency buffers.

confidence is 0.0–1.0 (lower when requirements are ambiguous or dependencies are risky).

Output JSON ONLY. No markdown.
""".strip()

EFFORT_JSON_SCHEMA = """{
  "estimates": [
    {
      "task_id": "task_xxxx",
      "story_points": 3,
      "hours_low": 2.0,
      "hours_high": 6.0,
      "confidence": 0.72,
      "rationale": "short justification"
    }
  ]
}"""


def effort_user_message(tasks_block: str) -> str:
    return (
        "Tasks:\n\n"
        f"{tasks_block}\n\n"
        "Return estimates for each task id.\n"
        f"Schema:\n{EFFORT_JSON_SCHEMA}"
    )
