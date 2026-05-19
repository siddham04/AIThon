"""Test Architect Agent — generates Given/When/Then test cases.

Goes beyond happy paths: explicitly enumerates edge cases (boundary,
auth, concurrency, failure modes) per story.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai.prompts.testcase_prompt import TESTCASE_SYSTEM, testcase_user_message

from ..models import Project, TestCase, TestType
from ..services.ai_service import get_ai_service
from .base import Agent


SYSTEM = """You are a Senior QA Architect designing a test plan.

For each user story, produce a comprehensive set of test cases covering:
  - Happy path
  - Boundary / edge cases
  - Negative / error cases
  - At least one of: security, performance, or accessibility (when applicable)

Format each test in Given / When / Then. Include a short list of
edge_cases (failure modes worth probing). Cite the story id and source
clause ids.
""".strip()


SCHEMA = """{
  "tests": [
    {
      "title": "string",
      "type": "unit|integration|e2e|performance|security|accessibility",
      "given": "string",
      "when": "string",
      "then": "string",
      "edge_cases": ["string"],
      "story_id": "story_xxxx",
      "source_clause_ids": ["clause_xxxx"]
    }
  ]
}"""


class TestArchitectAgent(Agent):
    name = "tests"
    stage = "Designing test cases"

    async def run(self, project: Project) -> Dict[str, Any]:
        if not project.stories:
            return {"test_cases": []}

        story_block = "\n".join(
            f"- id={s.id} | {s.title}\n  persona: {s.persona}\n  goal: {s.goal}\n"
            f"  AC:\n    - " + "\n    - ".join(s.acceptance_criteria)
            for s in project.stories
        )
        ai = get_ai_service()
        if ai.enabled:
            data = await ai.complete_json(
                TESTCASE_SYSTEM,
                testcase_user_message(story_block),
                max_tokens=8192,
            )
        else:
            user = (
                "Stories to test:\n\n"
                f"{story_block}\n\n"
                "Generate the test plan. Use the story id (id=story_xxxx) verbatim."
            )
            data = await self.llm.chat_json_with_fallback(
                self.name,
                project,
                SYSTEM,
                user,
                schema_hint=SCHEMA,
                max_completion_tokens=5000,
            )

        story_ids = {s.id for s in project.stories}
        cases: List[TestCase] = []
        for t in data.get("tests") or []:
            try:
                sid = t.get("story_id")
                if sid not in story_ids:
                    sid = None
                cases.append(
                    TestCase(
                        title=t.get("title", "Untitled test"),
                        type=TestType(t.get("type", "unit")),
                        given=t.get("given", ""),
                        when=t.get("when", ""),
                        then=t.get("then", ""),
                        edge_cases=list(t.get("edge_cases") or []),
                        story_id=sid,
                        source_clause_ids=list(t.get("source_clause_ids") or []),
                    )
                )
            except Exception:
                continue
        return {"test_cases": cases}
