"""Decomposer Agent — turns the brief into user stories + engineering tasks.

Each story is INVEST-shaped (persona / goal / benefit / acceptance criteria).
Each task is small, owner-actionable, and traces to clauses & a story.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import Project, Severity, Task, TaskType, UserStory
from ..services.ingestion import render_clauses
from .base import Agent


SYSTEM = """You are a Tech Lead breaking work down for a sprint.

Produce:
  1. User stories in INVEST form: title, persona, goal, benefit, and 3-6
     concrete acceptance criteria written as "Given/When/Then" or
     "The system shall ...".
  2. Engineering tasks (1-day or smaller) implementing each story. Tasks
     must be specific (no "build feature X"). Include type, priority,
     skills (e.g. ["react", "fastapi", "postgres"]), and dependencies
     (other task ids you generate, if any).

Every story and task MUST cite the source_clause_ids it derives from.
""".strip()


SCHEMA = """{
  "stories": [
    {
      "title": "string",
      "persona": "string",
      "goal": "string",
      "benefit": "string",
      "acceptance_criteria": ["string", "..."],
      "source_clause_ids": ["clause_xxxx"],
      "tasks": [
        {
          "title": "string",
          "description": "string — implementation detail",
          "type": "feature|bug|chore|spike|infra",
          "priority": "low|medium|high|critical",
          "skills": ["string"],
          "source_clause_ids": ["clause_xxxx"]
        }
      ]
    }
  ]
}"""


class DecomposerAgent(Agent):
    name = "decomposer"
    stage = "Drafting stories & tasks"

    async def run(self, project: Project) -> Dict[str, Any]:
        summary_block = ""
        if project.summary:
            summary_block = (
                "Product brief:\n"
                f"  Title: {project.summary.title}\n"
                f"  Objective: {project.summary.objective}\n"
                f"  In-scope: {', '.join(project.summary.in_scope)}\n"
                f"  Out-of-scope: {', '.join(project.summary.out_of_scope)}\n"
                f"  Personas: {', '.join(project.summary.primary_personas)}\n\n"
            )

        user = (
            f"{summary_block}"
            "Source clauses:\n\n"
            f"{render_clauses(project.source_clauses)}\n\n"
            "Produce stories with their tasks. Be concrete and small."
        )
        data = await self.llm.chat_json_with_fallback(
            self.name,
            project,
            SYSTEM,
            user,
            schema_hint=SCHEMA,
            max_completion_tokens=6000,
        )

        stories: List[UserStory] = []
        tasks: List[Task] = []
        for s in data.get("stories") or []:
            try:
                story = UserStory(
                    title=s.get("title", "Untitled story"),
                    persona=s.get("persona", "User"),
                    goal=s.get("goal", ""),
                    benefit=s.get("benefit", ""),
                    acceptance_criteria=list(s.get("acceptance_criteria") or []),
                    source_clause_ids=list(s.get("source_clause_ids") or []),
                )
            except Exception:
                continue
            stories.append(story)
            for t in s.get("tasks") or []:
                try:
                    tasks.append(
                        Task(
                            title=t.get("title", "Untitled task"),
                            description=t.get("description", ""),
                            type=TaskType(t.get("type", "feature")),
                            priority=Severity(t.get("priority", "medium")),
                            skills=list(t.get("skills") or []),
                            story_id=story.id,
                            source_clause_ids=list(
                                t.get("source_clause_ids")
                                or story.source_clause_ids
                            ),
                        )
                    )
                except Exception:
                    continue
        return {"stories": stories, "tasks": tasks}
