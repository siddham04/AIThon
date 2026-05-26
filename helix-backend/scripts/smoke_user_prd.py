"""End-to-end smoke for the user's hackathon PRD.

Feeds the actual demand-forecasting case study from the user's bug
report through the *same* path Mission Control uses (frontend preamble
prepended + /ingest/text route + run_demo + generate_backlog), then
prints the resulting Jira preview rows.

Lets us eyeball the fix without booting the full backend + frontend.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Force mock-mode so the same heuristic the user hit runs again.
# Clear every LLM-credential variant the shell session might have
# leaked from a previous command so the smoke is hermetic.
for _k in (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OAI_KEY",
    "AZURE_OAI_ENDPOINT",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
):
    os.environ[_k] = ""
os.environ["HELIX_USE_AI"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite:///./helix_smoke_user_prd.db")
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")

# Allow `python scripts/smoke_user_prd.py` from helix-backend root.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app.models import Project
from app.services.ingestion import split_into_clauses
from app.services.demo_orchestrator import run_demo
from app.services.backlog_generator import generate_backlog, to_simple_json


# Frontend preamble the user's Mission Control sends. We include it on
# purpose so the smoke test reproduces the exact byte stream Helix saw.
PREAMBLE = (
    "[Helix team configuration]\n"
    "Team size: 6 engineers\n"
    "Sprint length: 2 weeks\n"
    "Priority mode: delivery-first\n"
    "Tech stack: React · FastAPI · PostgreSQL\n"
    "---\n\n"
)

# The user's actual PRD text from the bug report (lightly cleaned of
# OCR garbage to reflect what they pasted). Layout is intentionally
# messy — that's the realistic input case.
USER_PRD_BODY = (
    "5-10% MAPE Accuracy: Optimizing Demand Forecasting for Cost Efficiency "
    "and Better Decisions for Retail and Professional Services Company "
    "(Chamberlain)\n"
    "\n"
    "Overview\n"
    "A leading retail and professional services company needed a predictive "
    "model to project residential operator demand based on recent momentum. "
    "Their goal was to make data-driven decisions on pricing, promotions, "
    "and demand planning. An accurate forecast would help align business "
    "performance with financial commitments and optimize sales strategies.\n"
    "\n"
    "Our Solution and Approach\n"
    "Business Impact\n"
    "Technology Stack\n"
    "- Data Aggregation: Combined operator units shipped or ordered in RAS "
    "Professional and RAS Retail.\n"
    "High Accuracy - Achieved 5-10% MAPE in forecasts.\n"
    "Forecasting Model Selection: Chose the top model for 1, 3, 6, and "
    "12-month predictions.\n"
    "Cost Reduction - Improved inventory management for greater efficiency.\n"
    "Performance Optimization: Assessed model performance with key metrics.\n"
    "Better Decision-Making - Offered real-time interactive dashboards for "
    "enhanced business insights.\n"
    "Model Evaluation: Compared traditional forecasting models (Regression, "
    "SARIMA, Prophet, Exponential Smoothing, XGBoost) to determine the most "
    "accurate forecasts for various timeframes, including projections for "
    "2025.\n"
    "\n"
    "Key Highlights\n"
    "Demand Forecasting · High Accuracy · Cost Efficiency · Real-Time "
    "Insights · Optimized Decision-Making\n"
    "\n"
    "rsystems.com\n"
    "All rights reserved. Internal\n"
)

FULL_INPUT = PREAMBLE + USER_PRD_BODY


def _hr(title: str) -> None:
    print()
    print("=" * 76)
    print(f" {title}")
    print("=" * 76)


async def main() -> None:
    # 1. Show what the splitter actually keeps now.
    clauses = split_into_clauses(FULL_INPUT)
    _hr(f"After ingestion: {len(clauses)} clauses kept")
    for c in clauses:
        print(f"  [{c.id}] {c.text}")

    # 2. Build a project the way /ingest/text would — i.e. strip the
    #    team-config preamble first so raw_input and the derived name
    #    match production behaviour (the ingestion route does the same).
    from app.api.routes.ingestion import _derive_project_name
    from app.services.ingestion import _strip_team_config_preamble

    text_clean, _ = _strip_team_config_preamble(FULL_INPUT)
    text_clean = text_clean.strip() or FULL_INPUT

    project = Project(
        id="proj_smoke_user_prd",
        name=_derive_project_name(text_clean),
        raw_input=text_clean,
        source_clauses=clauses,
    )
    _hr("Derived project name (was: 'Ingested document')")
    print(f"  {project.name}")

    # 3. Run the pipeline in mock mode (matches the user's session).
    async for _ev in run_demo(project, use_ai=False):
        pass

    _hr(f"Stories ({len(project.stories)})")
    for s in project.stories:
        print(f"  - {s.title}")

    _hr(f"Tasks ({len(project.tasks)})")
    for t in project.tasks:
        print(f"  - {t.title}")

    # 4. Generate the Jira backlog the way the user's preview did.
    backlog = await generate_backlog(project, use_ai=False)
    simple = to_simple_json(backlog)

    _hr("EPIC (was: 'Ingested document')")
    print(f"  Title:       {simple['epic']['title']}")
    print(f"  Description: {simple['epic']['description'][:160]}…")

    _hr("Jira preview (Issue Type | Summary)")
    print(f"  Epic    | {simple['epic']['title']}")
    for s in simple["stories"][:8]:
        print(f"  Story   | {s['title']}")
    for t in simple["tasks"][:8]:
        print(f"  Task    | {t['title']}")
    for st in simple["subtasks"][:8]:
        print(f"  Subtask | {st['title']}")


if __name__ == "__main__":
    asyncio.run(main())
