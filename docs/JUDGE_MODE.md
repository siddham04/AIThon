# Helix — Judge Mode (offline-safe green path)

> **The one line you'll see proven on screen:**
> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

> **The one-page guarantee.** Read this if you're a judge, evaluator, or
> presenter and you need a **reliable, repeatable demo in ≤5 minutes**
> on a fresh machine — with **no LLM keys, no network, no surprises**.

**Companion docs:**
[`README.md`](../README.md) · [`PRESENTATION.md`](../PRESENTATION.md) ·
[`docs/RUNBOOK.md`](RUNBOOK.md) · [`docs/WORKFLOW.md`](WORKFLOW.md) ·
[`docs/JUDGE_QA.md`](JUDGE_QA.md) ·
[`docs/PATH_TO_PRODUCTION.md`](PATH_TO_PRODUCTION.md) ·
[`docs/DEMO_RECOVERY.md`](DEMO_RECOVERY.md) **— 4-tier fallback playbook with rehearsal checklist** ·
[`docs/SCREENSHOT_TOUR.md`](SCREENSHOT_TOUR.md)
*(static fallback if the live demo is offline — real Playwright captures
of the populated `proj_demo_seed01` project + a 22-second
[`judge-walkthrough.webm`](../helix-frontend/docs/judge-screenshots/judge-walkthrough.webm))* ·
[`docs/sample-exports/`](sample-exports/) *(committed Jira CSV / ADO
CSV / markdown brief / backlog JSON — Tier-D deliverables)*

---

## 1. The promise

Run **`scripts/judge_demo.ps1`** (Windows) or
**`scripts/judge_demo.sh`** (macOS / Linux / WSL) from the repo root.

It will:

1. Boot the backend on **`http://127.0.0.1:8765`** in **demo mode**
   (`HELIX_DEMO_FAST=true`, no LLM keys required — deterministic mock
   pipeline).
2. Boot the frontend on **`http://localhost:5173`**.
3. Open the **seeded demo project** in your browser at
   **`/project/proj_demo_seed01/ai-workspace`** so the Delivery Package
   is rendered **before you even click anything**.
4. Print a green ✓ for every gate it verifies (backend health, seeded
   user, seeded project, SSE reachability, demo pipeline returns 11
   stages with `done` status).

**Failure mode:** if any gate fails, the script exits non-zero with a
single-line cause and the next command you should run. There is no
"silent success" path.

---

## 2. One-command demo

### Windows (PowerShell)

```powershell
git clone https://github.com/<you>/AI-Thon.git
cd AI-Thon
.\scripts\judge_demo.ps1
```

### macOS / Linux / WSL

```bash
git clone https://github.com/<you>/AI-Thon.git
cd AI-Thon
bash scripts/judge_demo.sh
```

### Docker (single container, no Node / Python install needed)

```bash
cd AI-Thon
docker build -t helix-demo -f Dockerfile.all-in-one .
docker run --rm -p 8765:8765 -p 5173:5173 helix-demo
# Then open http://localhost:5173/project/proj_demo_seed01/ai-workspace
```

The Dockerfile already sets `HELIX_DEMO_FAST=1` so it works offline.

---

## 3. What "green path" guarantees (the offline contract)

These behaviors are wired in code and **do not need any LLM key**:

| Guarantee | Code reference |
|---|---|
| Seeded user `demo@demo.com` / `demo123` exists | `helix-backend/scripts/seed.py` (run automatically on backend start) |
| Seeded project `proj_demo_seed01` exists with full pipeline state | `helix-backend/scripts/seed.py` |
| 11-step demo pipeline always completes (never aborts) | `helix-backend/app/services/demo_orchestrator.py` — per-step `try/except` yields `error` events but continues |
| **Tasks always exist** when stories exist | `helix-backend/app/services/project_bridge.py` `ensure_engineering_tasks` (heuristic fallback from stories) — invoked by `_step_jira`, `finalize_demo_project`, and the backlog generator |
| **PRD endpoint never 404s** after a run | `helix-backend/app/api/routes/delivery.py` `get_prd` lazily generates if missing |
| **Readiness % is live**, not a placeholder | `_step_readiness` reads `center.readiness` directly; UI line: *"Readiness X% from live delivery gates after this run — not a placeholder."* (`helix-frontend/src/pages/WinningDemoScreen.jsx`) |
| Demo mode emits deterministic mock JSON for every agent | `helix-backend/app/agents/mock_agents.py` |
| SSE stream never stalls more than ~30s in `HELIX_DEMO_FAST=true` | `helix-backend/run.ps1`, `Dockerfile`, `Dockerfile.all-in-one` set this by default |
| Exports work without external auth | CSV / Markdown / Jira CSV / ADO JSON / GitHub Issues JSON all render from the in-memory `Project` graph |

If you want to flex the **Tier-1 live LLM** path, set
`HELIX_USE_AI=true` and provide `AZURE_OPENAI_API_KEY` (plus
`AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`) in
`helix-backend/.env` — the same script works. Without keys, the Tier-2
clause-grounded mock + Tier-3 heuristic chain kicks in automatically —
see [`docs/NOVELTY.md`](NOVELTY.md) pillar 3.

---

## 4. The 4-minute click path (memorize this)

> All times assume `HELIX_DEMO_FAST=true` (default in `judge_demo.*`).

| Time | Click | What judges see |
|------|-------|------------------|
| 0:00 | Land on `/project/proj_demo_seed01/ai-workspace` | Pre-baked Delivery Package — proves Helix without any wait |
| 0:30 | Click **Mission Control** → **New project** → **Load sample requirement** → **Ingest** | New project created, source clauses extracted |
| 1:00 | Click **Launch AI Team** | SSE timeline starts — 11 stages stream in |
| 1:00–3:30 | Narrate as stages light up | `quality` + `review` parallel → `stories` → `architecture` + `effort_sprint` parallel → `apis` + `tests` parallel → `jira` → `readiness` |
| 3:30 | Finale ring + auto-nav to **Delivery Package** | "PROJECT READY — X% delivery readiness" (live, not constant) |
| 3:30–4:30 | Scroll Delivery Package: Kanban → Mermaid → Tests → Risks → Readiness | One screen, every artifact |
| 4:30 | Toggle a story to **Approved for export**, click **Export → Jira CSV (approved only)** | Approval gate proves governance — CSV opens with only approved rows |
| 4:45 | Open **Trace** tab, click any task | Citation chain back to source clause (`source_clause_ids`) |

If anything stalls, **fall back to the seeded project**:
`http://localhost:5173/project/proj_demo_seed01/ai-workspace`.

---

## 5. Pre-flight checklist (15 seconds before judges arrive)

- [ ] **Backend healthy:** `curl http://127.0.0.1:8765/api/health` → `{"status":"ok"}`
- [ ] **UI loads:** `http://localhost:5173` renders the landing page
- [ ] **Seeded project loads:** `http://localhost:5173/project/proj_demo_seed01/ai-workspace`
- [ ] **Login works:** `demo@demo.com` / `demo123` (or "Try as Guest")
- [ ] **(Optional) Voice rehearsal:** Chrome / Edge, mic allowed for `localhost:5173`
- [ ] **Backup tab open:** the seeded project URL, so one click recovers

The `judge_demo` script automates the first four lines.

---

## 6. Troubleshooting (only what's actually happened)

| Symptom | Cause | Fix |
|---|---|---|
| Backend won't start | Port 8765 in use | `netstat -ano \| findstr 8765` then kill PID |
| Postgres not reachable | Local Docker compose not running | Script falls back to SQLite (`helix.db`) automatically; this is fine for the demo |
| Mission Control "stuck at ingest" | Browser cached old build | Hard-refresh (Ctrl+Shift+R) or restart `npm run dev` |
| Export button greyed out | No items marked `approved_for_export` | Toggle one, retry (this is the governance feature, not a bug) |
| Live LLM very slow (>30s/stage) | Azure rate limit | Re-run with `HELIX_USE_AI=false` to confirm demo path works; show live path with mocked timer if needed |
| Voice button doesn't appear | Not Chrome/Edge, or non-secure context | Switch browser; use **Paste text** instead |

Anything else: read `docs/RUNBOOK.md` §8 and `docs/JUDGE_QA.md`.

---

## 7. What judges should look at if they doubt the demo

| Doubt | Code path to point at |
|---|---|
| *"Are these real LLM agents or just templates?"* | `helix-backend/app/agents/*.py` — 10 agent files, each with its own SYSTEM prompt + SCHEMA. Toggle `HELIX_USE_AI=true` (with `AZURE_OPENAI_API_KEY` set) to hit Azure OpenAI live. |
| *"Is the traceability real?"* | `helix-backend/app/agents/clause_utils.py` (`filter_clause_ids`, `resolve_story_id`) and the `source_clause_ids` field on every artifact model in `models.py` |
| *"Is the readiness score real?"* | `_step_readiness` in `demo_orchestrator.py` reads `center.readiness` from `build_readiness_center` — no hardcoded constant. UI label says so explicitly. |
| *"Does the approval gate actually filter export?"* | `helix-backend/app/services/export_filter.py` + `?approved_only=true` query param on `/api/export/*` |
| *"Is SSE real or replayed?"* | Open DevTools → Network → `EventStream` tab on `/api/demo/{id}/run` — server-sent events with per-stage `elapsed_ms` |
| *"What changes between demo mode and live?"* | `helix-backend/app/services/llm.py` `chat_json_with_fallback` — demo path returns `mock_agents.synthetic_json`; live path hits Azure with retry |
