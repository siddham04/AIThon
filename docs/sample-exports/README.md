# Committed deliverables — Helix demo project

> **Async judges & static reviewers**: these are the *byte-identical*
> outputs of the Helix pipeline running against the canonical
> e-commerce checkout requirement (`proj_demo_seed01`). No mock-ups,
> no crafted samples — every file in this folder was written by the
> live FastAPI export endpoints. Open them in Excel, VS Code, or
> GitHub directly.

| File | Source endpoint | Size | What it is |
|------|----------------|------|------------|
| [`checkout-revamp.jira.csv`](checkout-revamp.jira.csv) | `GET /api/backlog/{id}/jira-csv` | ~4 KB | **Full Jira-importable CSV** — 18 rows: 1 Epic + 2 Stories + 3 Tasks + 12 Sub-tasks, with parent links, priority, story points, hour estimates, labels |
| [`checkout-revamp.azure-devops.csv`](checkout-revamp.azure-devops.csv) | `GET /api/backlog/{id}/ado-csv` | ~3.6 KB | Same backlog with Azure DevOps column shape (Work Item Type, Iteration Path, Tags, etc.) |
| [`checkout-revamp.tasks.csv`](checkout-revamp.tasks.csv) | `GET /api/export/csv/{id}` | ~600 B | Flat task list — engineering view: `task_id, title, type, priority, story_id, estimate_points, estimate_hours, confidence, skills, description, approved_for_export` |
| [`checkout-revamp.brief.md`](checkout-revamp.brief.md) | `GET /api/export/markdown/{id}` | ~2 KB | Executive markdown brief — objective, scope, stories with AC, engineering tasks, test plan, ambiguities, risks, **audit footer** (`Generated at … · model … · user …`) |
| [`checkout-revamp.backlog.json`](checkout-revamp.backlog.json) | `GET /api/export/json/{id}` | ~16 KB | Full Pydantic-validated `Project` graph — source clauses, summary, stories, tasks, tests, ambiguities, risks, **`source_clause_ids` on every artefact** for provenance |

## How to regenerate

Run the Playwright capture spec — it pulls each export from the live
API and overwrites this folder atomically.

```powershell
# helix-backend on :8765, helix-frontend on :5173 must be up
cd helix-frontend
$env:E2E_SKIP_WEB_SERVER='1'
$env:E2E_BASE_URL='http://localhost:5173'
$env:E2E_BACKEND_URL='http://127.0.0.1:8765'
npx playwright test e2e/judge-snapshot.spec.ts --project=chromium
```

Source: [`helix-frontend/e2e/judge-snapshot.spec.ts`](../../helix-frontend/e2e/judge-snapshot.spec.ts).

## Why these files exist in the repo

They are **Tier D** of the demo recovery playbook in
[`../DEMO_RECOVERY.md`](../DEMO_RECOVERY.md) — the fallback for when
the demo laptop is dead, the network is gone, or you're explaining
Helix over a phone call. Even with zero infrastructure running, the
deliverables are on GitHub and a judge can verify the system produces
real, structured, importable output.

The [`SCREENSHOT_TOUR.md`](../SCREENSHOT_TOUR.md) explains how these
artefacts appear *inside* the running product (Frame 4 — Delivery
Package, Frame 7 — Jira CSV preview).
