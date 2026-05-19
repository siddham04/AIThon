"""Chain-of-thought artifact generation: decompose requirements into SDLC artifacts."""

ARTIFACT_SYSTEM = """You are a principal product engineer and tech lead. Your job is to read raw
requirements and produce a rigorous, traceable breakdown.

Work in clear chain-of-thought internally (think step by step), but DO NOT include your reasoning
in the output. Only output valid JSON matching the schema exactly — no markdown fences, no prose.

Rules:
- Ground every user story and task in the supplied text; avoid inventing major scope not implied.
- Acceptance criteria must be testable (Given/When/Then style phrasing is fine as bullet strings).
- Tasks must roll up to stories where possible; include priority as low|medium|high|critical.
- hours_low and hours_high are engineer-hours per task (realistic range).
- risks: concrete delivery/tech/product risks tied to the brief.
- ambiguities: questions or gaps that still need PM/engineering answers (not generic platitudes).
""".strip()

ARTIFACT_JSON_SCHEMA = """{
  "summary": "string — executive summary of the initiative",
  "user_stories": ["string — As a … I want … so that …"],
  "acceptance_criteria": ["string — testable criteria, can map to stories implicitly by order if needed"],
  "tasks": [
    {
      "title": "string",
      "desc": "string — implementation notes",
      "priority": "low|medium|high|critical",
      "hours_low": 1.0,
      "hours_high": 4.0
    }
  ],
  "risks": ["string"],
  "ambiguities": ["string"]
}"""


def artifact_user_message(requirements_text: str) -> str:
    return (
        "Requirements text:\n---\n"
        f"{requirements_text.strip()}\n---\n\n"
        "Produce the JSON object with keys: summary, user_stories, acceptance_criteria, "
        "tasks (array of objects with title, desc, priority, hours_low, hours_high), risks, ambiguities.\n"
        f"Schema:\n{ARTIFACT_JSON_SCHEMA}"
    )
