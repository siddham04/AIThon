"""QA Agent — comprehensive test planning.

Fourth agent in the Multi-Agent SDLC Pipeline. Generates:

    - Test cases (Given/When/Then)
    - Edge cases
    - Negative scenarios
    - Security / performance / accessibility where applicable
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai.prompts.testcase_prompt import TESTCASE_SYSTEM, testcase_user_message

from ..models import Project, TestCase, TestType
from ..services.ai_service import get_ai_service
from .base import Agent
from .clause_utils import filter_clause_ids, resolve_story_id


SYSTEM = """You are a Senior QA Architect — the QA Agent in a multi-agent SDLC pipeline.

For each user story produce test cases in three buckets:
  1. Functional (happy path)
  2. Edge cases (boundaries, concurrency, timeouts)
  3. Negative scenarios (invalid input, auth failures, outages)

Also include security, performance, or accessibility tests when the story
implies them. Format each test as Given / When / Then. Set `type` to
unit|integration|e2e|performance|security|accessibility. List specific
edge_cases on each test. Cite story_id and source_clause_ids verbatim.
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
    stage = "QA Agent"

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

        cases: List[TestCase] = []
        for t in data.get("tests") or []:
            try:
                title = t.get("title", "Untitled test")
                sid = resolve_story_id(
                    project,
                    t.get("story_id"),
                    agent="test_architect",
                    title=str(title),
                )
                cases.append(
                    TestCase(
                        title=title,
                        type=TestType(t.get("type", "unit")),
                        given=t.get("given", ""),
                        when=t.get("when", ""),
                        then=t.get("then", ""),
                        edge_cases=list(t.get("edge_cases") or []),
                        story_id=sid,
                        source_clause_ids=filter_clause_ids(
                            project,
                            t.get("source_clause_ids"),
                            agent="test_architect",
                            context=str(title)[:40],
                        ),
                    )
                )
            except Exception:
                continue
        return {"test_cases": cases}
