# Helix — The Intelligent SDLC Copilot

> **Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes.**
>
> Submission for **Code-AI-Thon 2026 · Phase 2 (#BeEXIQO – Be Builder)**
> Track: *AI for SDLC Productivity — Intelligent SDLC Copilot*

Helix turns messy product input — emails, transcripts, briefs, PDFs, voice
notes — into a **traceable graph** of stories, engineering tasks, test
cases, ambiguities, and non-functional risks. A **multi-agent pipeline**
of specialized AI roles collaborates over your input; the workspace lets
your team refine, query, and export everything to Jira, Azure DevOps, or
GitHub Issues in one click.

---

## Three things no GPT wrapper does (the novelty answer)

> *Multi-agent is now table stakes. These three are what separate Helix
> — and every one is provable in code in 60 seconds.* Deep dive in
> [`docs/NOVELTY.md`](docs/NOVELTY.md).

1. **Traceable Clause Graph.** Every story, task, test, and risk
   carries a `source_clause_ids` field **validated against the real
   clause set** (`helix-backend/app/agents/clause_utils.py`). Citations
   you can prove, not citations you have to trust. CI-gated by
   `test_every_artifact_cites_a_clause` — 100% of stories, ≥75% of
   tasks, every PR.
2. **Automated Ambiguity Workflow.** A dedicated agent
   (`helix-backend/app/agents/ambiguity.py`) whose only job is to find
   vague language, classify it via a **typed taxonomy**
   (`undefined_term · missing_criteria · conflicting · unquantified
   · out_of_scope · non_functional_gap`), and draft a clarifying
   question + suggested resolution **before** sprint planning.
3. **3-Tier Provider Resilience.** Azure OpenAI (`o3`, JSON mode) →
   clause-grounded deterministic mock (`mock_agents.py`) → heuristic
   guarantors (`_heuristic_tasks_from_stories`,
   `ensure_engineering_tasks`). Pipeline is **never empty, ever.** Full
   11-stage run with zero LLM keys in **~2 seconds** — proven by the
   golden-pipeline contract on every PR.

---

## Team — who built what

> *Three engineers, three pillars. Every member owns code judges can
> open during Q&A.*

| Member | Pillar | What they own (concrete) |
|---|---|---|
| **Siddham Jain** | **Tech Lead — AI Backend & Orchestration** | 11-stage `helix-backend/app/services/demo_orchestrator.py`; the 10 specialized agents in `helix-backend/app/agents/` (Analyzer, Ambiguity, Decomposer, Test Architect, Estimator, Risk, Scrum Master, Quality Scorer, Review Board, PM); 3-tier provider resilience (`ai_service.py` · `mock_agents.py` · heuristic guarantors); FAISS RAG (`services/rag.py`); FastAPI + SSE streaming; the CI-gated golden-pipeline contract (`tests/test_golden_pipeline.py`) |
| **Shubham Gatkal** | **Frontend & Design Engineering** | React 19 + Vite SPA (`helix-frontend/`); the GSAP / Three.js animation surface — `HeroHelix`, `HeroParticles`, `AmbientNetField`, `WorkspaceAmbientCanvas`; Mission Control live SSE timeline; Delivery Package single-scroll layout; Jira CSV preview + Traceability Flow Animator components; the design system (`helix-design.css` · `helix-native.css`) |
| **Aditya Khapke** | **Product, QA & Demo Engineering** | The end-to-end demo narrative ([`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md), [`PRESENTATION.md`](PRESENTATION.md)); the canonical *"Checkout Revamp"* sample requirement; [`docs/SCREENSHOT_TOUR.md`](docs/SCREENSHOT_TOUR.md) + [`docs/DEMO_RECOVERY.md`](docs/DEMO_RECOVERY.md) (the 4-tier fallback playbook); the Playwright e2e suite (`judge-snapshot`, `phase2-ui`, `phase3-workflow`); `scripts/judge_demo.ps1` / `.sh`; the [`docs/GOLDEN_DOMAIN.md`](docs/GOLDEN_DOMAIN.md) contract definition |

The split is **non-overlapping by surface, fully integrated by
contract**: the golden-pipeline test runs the backend's orchestrator
on the frontend's sample requirement and asserts the artefacts both
disciplines depend on — provenance and structural completeness — in
~2 seconds on every PR.

---

## Why this is different

Most "requirement summarizers" stop at bullet points. Helix is a true
**SDLC operating layer**:

| Capability | What it does | Why it matters |
| --- | --- | --- |
| **Multi-agent pipeline** | Analyzer → Ambiguity → Decomposer → Test Architect → Estimator → Risk | Each stage uses a focused, role-specialized prompt — far higher quality than one monolithic call |
| **Ambiguity heat-map** | Severity-scored, with a clarifying question per issue | Surfaces the rework-causing gaps *before* sprint planning |
| **Traceability graph** | Every story / task / test / risk cites its source clause | Audit-ready for regulated environments; eliminates "where did this come from?" debates |
| **Risk agent** | Surfaces non-functional risks (security, compliance, perf, scale, data, UX) | Catches the issues that cause incidents 3 sprints later |
| **Estimator with confidence** | Story points + hours + 0–1 confidence | Engineering leaders see *uncertainty*, not false precision |
| **Voice → Spec** | Web Speech API dictation | PMs in meetings can capture intent on the fly |
| **Conversational refinement** | Chat with full project context, citing artifact ids | Stakeholders can interrogate the brief without leaving the workspace |
| **Export everywhere** | Markdown · CSV · Jira CSV · ADO JSON · GitHub Issues JSON | Drops into the team's existing pipeline — no migration |
| **Human-in-the-loop export** | `approved_for_export` on stories/tasks; `?approved_only=true` on export | Governance: only reviewed rows reach Jira/GitHub/CSV |
| **Citation quality bar** | `citation_item_rate` on metrics + artifact bundle API | Quantifies clause-grounding for trust narratives |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         React + TypeScript UI                    │
│  Ingest · Pipeline stream · Workspace tabs · Trace graph · Chat  │
└─────────────┬────────────────────────────────────────────────────┘
              │  REST + Server-Sent Events
┌─────────────▼────────────────────────────────────────────────────┐
│                     FastAPI · Pydantic v2                        │
│   Routes:  /ingest   /analyze (SSE)   /chat   /export   /health  │
└─────────────┬────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────┐
│                     Multi-Agent Orchestrator                     │
│                                                                  │
│   ┌────────────┐  ┌─────────────┐                                │
│   │ Analyzer   │  │ Ambiguity   │   ← parallel                   │
│   └─────┬──────┘  └─────┬───────┘                                │
│         └──────┬────────┘                                        │
│         ┌──────▼─────────┐                                       │
│         │  Decomposer    │   stories + tasks                     │
│         └──────┬─────────┘                                       │
│   ┌────────────┼────────────┐                                    │
│   ▼            ▼            ▼                                    │
│ Tests      Estimator      Risk    ← parallel                     │
│                                                                  │
│   Each agent emits a Pydantic-validated patch merged into the    │
│   shared Project artifact. SSE events include per-stage timing.  │
└─────────────┬────────────────────────────────────────────────────┘
              │  3-tier resilience (see docs/NOVELTY.md, pillar 3)
    ┌─────────┴────────────┬────────────────────────┐
    ▼                      ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐
│ Tier 1           │  │ Tier 2           │  │ Tier 3                │
│ Azure OpenAI o3  │  │ Clause-grounded  │  │ Heuristic guarantors  │
│ JSON mode, all   │  │ deterministic    │  │ _ensure_project_tasks │
│ agents, retries  │  │ mock (offline    │  │ never-empty backlog   │
│                  │  │  + CI fallback)  │  │                       │
└──────────────────┘  └──────────────────┘  └───────────────────────┘
```

### Tech stack

**Frontend:** React 19 · TypeScript · Vite 8 · Web Speech · **Recharts** and **Chart.js**
(`react-chartjs-2`) on the dashboard for SDLC KPIs (Kanban distribution, artifact mix,
insights-backed quality and burndown).

**Backend:** Python 3.11 · FastAPI · Pydantic v2 · OpenAI SDK (Azure
client) · pypdf · python-docx · **spaCy** / sentence-transformers / FAISS (ingest & RAG paths).

**AI (actual code paths):** **Azure OpenAI** is the single live provider
— set `AZURE_OPENAI_*` (or the hackathon-style aliases
`AZURE_OAI_ENDPOINT` / `AZURE_OAI_KEY` / `PLANNING_MODEL`) in
`helix-backend/.env`. The deployment default is **`o3` with JSON mode**;
every agent goes through `LLMService.chat_json_with_fallback` or
`AIService.complete_json`. When no key is configured (or the model
returns empty JSON for an agent), the orchestrator falls through to the
**Tier-2 clause-grounded mock** (`helix-backend/app/services/mock_agents.py`)
and finally to **Tier-3 heuristic guarantors** so the pipeline is never
empty. See [`docs/NOVELTY.md`](docs/NOVELTY.md) pillar 3 for the full
3-tier story and [`docs/GOLDEN_DOMAIN.md`](docs/GOLDEN_DOMAIN.md) for
the CI-gated contract that proves it.

**ML / analytics (non-LLM):** **scikit-learn** (`IsolationForest` task
anomalies, TF-IDF + cosine duplicate-story detection) via
`GET /api/insights/{project_id}` (`ml_insights.py`), surfaced in the
workspace dashboard and the full **Insights** page. Embeddings for RAG
use **sentence-transformers** (PyTorch) `all-MiniLM-L6-v2` indexed per
project in FAISS. Judges can point to **sklearn + Azure OpenAI** as the
primary "AI/ML" stack in code.

`GET /api/health` reports `azure_openai_configured`. Ingest and
`/api/ingest/*` responses may include `sensitive_hints` (email-, key-,
and token-shaped patterns) before you run analyze. Adding a second live
LLM provider (Anthropic, Bedrock, vLLM-hosted Llama) is a one-class
change behind `AIService` — see [`docs/PATH_TO_PRODUCTION.md`](docs/PATH_TO_PRODUCTION.md) §2.3.

---

## Quick start

### 1. Backend
```powershell
cd helix-backend
.\run.ps1
```
This bootstraps a virtualenv, installs deps, copies `.env.example` →
`.env`, and starts the API on `http://127.0.0.1:8765`.

Edit `helix-backend\.env` with at least one provider:

**Azure OpenAI** (JSON stages + fallback). You can use either naming style:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=o3
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

Or the hackathon-style aliases (supported by the same backend):

```
AZURE_OAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OAI_KEY=<your-key>
PLANNING_MODEL=o3
```

Leave keys blank to run the **deterministic offline path** — the
orchestrator routes through the Tier-2 clause-grounded mock + Tier-3
heuristic guarantors so judges never see an empty pipeline. The full
11-stage run completes in ~2 seconds without an LLM key — proven by
the golden-pipeline contract test on every PR (see
[`docs/GOLDEN_DOMAIN.md`](docs/GOLDEN_DOMAIN.md)).

### Smoke demo (judges / CI)

With backend on **8765**:
```powershell
cd AI-Thon
python scripts/smoke_demo.py
```
Or: `.\scripts\smoke_demo.ps1`

Starts nothing automatically — run `helix-backend\run.ps1` in another terminal first.

### 2. Frontend (this repo)

```powershell
cd helix-frontend
npm ci
npm run dev
```

Opens at **`http://localhost:5173`**. Vite proxies **`/api`** to the API (`helix-frontend/vite.config.ts`; default **`http://127.0.0.1:8765`** to match `helix-backend\run.ps1`).

**Single UI tree:** `helix-frontend/` only in this checkout.

**Judge Mode** (one-command, offline-safe green path — read this first if you're evaluating): [`docs/JUDGE_MODE.md`](docs/JUDGE_MODE.md). Run **`.\scripts\judge_demo.ps1`** (Windows) or **`bash scripts/judge_demo.sh`** (macOS / Linux / WSL) from the repo root — boots backend + frontend in demo mode, polls health, opens the pre-baked Delivery Package in your browser.

**Demo Script — *From Document to Delivery*** (the **60-second pitch** anchored to the exact sample requirement, plus a parallel video-recording script): [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md). Memorize the three-sentence opener/middle/close before any live demo.

**Screenshot Tour — *for judges who don't run the app*** (a 7-frame walkthrough of the *populated* product — Landing → Mission Control → Judge Demo → Delivery Package full scroll → Export Hub → Traceability chain → Jira CSV preview. Real Playwright captures of the seeded `proj_demo_seed01` project, not mock-ups. Use as a deck companion or as the unembarrassable fallback when the live demo is offline): [`docs/SCREENSHOT_TOUR.md`](docs/SCREENSHOT_TOUR.md). Re-capture with `npx playwright test e2e/judge-snapshot.spec.ts` from `helix-frontend/`.

**Demo Recovery Playbook — *if the LLM / app / laptop fails on stage*** (a 4-tier fallback model — **A** live LLM → **B** clause-grounded mock pipeline (~2 s) → **C** static screenshots + the recorded **`judge-walkthrough.webm`** → **D** byte-identical committed exports in [`docs/sample-exports/`](docs/sample-exports/). Includes a 90-second pre-stage rehearsal checklist and per-tier failure-signal → recovery-action mappings): [`docs/DEMO_RECOVERY.md`](docs/DEMO_RECOVERY.md). **Read this before stage.**

**Committed sample exports — *the deliverables, on disk*** (5 real artefacts pulled from the live API for the canonical checkout demo — Jira CSV with full Epic→Story→Task→Sub-task hierarchy, ADO CSV, tasks CSV, executive markdown brief with audit footer, full backlog JSON. Open them in Excel / VS Code / GitHub without running anything): [`docs/sample-exports/`](docs/sample-exports/).

**Golden Domain & Bulletproof Contract** (the *Functional MVP* proof — e-commerce checkout is the canonical domain, the 11-step pipeline is CI-gated against 8 non-negotiable invariants, and the contract lives in version control): [`docs/GOLDEN_DOMAIN.md`](docs/GOLDEN_DOMAIN.md). Run locally with `cd helix-backend; pip install -r requirements-dev.txt; pytest tests/test_golden_pipeline.py -v`.

**Guided Tour** (5-minute scripted walkthrough — the *exact* click path and narration that ties **Mission Control → Workspace → Delivery Package** into one continuous story): [`docs/GUIDED_TOUR.md`](docs/GUIDED_TOUR.md). Open this with [`PRESENTER_CHEATSHEET.md`](PRESENTER_CHEATSHEET.md) before any live demo.

**Canonical runbook** (voice, ports, smoke test, GitHub): [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

**End-to-end workflow** (11-step demo pipeline + 5-stage analyze pipeline, with diagrams): [`docs/WORKFLOW.md`](docs/WORKFLOW.md). Diagram source for eraser.io: [`docs/helix-workflow.eraser`](docs/helix-workflow.eraser) — paste into <https://app.eraser.io> ("New file → Diagram-as-Code") to render the cloud-architecture and sequence diagrams.

**Path to production** (vector DB swap, GPU embeddings, multi-tenant, RBAC, SLOs): [`docs/PATH_TO_PRODUCTION.md`](docs/PATH_TO_PRODUCTION.md).

**Public demo URL (hackathon submission):** the manual 15-minute quickstart is **[`docs/DEPLOY_RENDER_VERCEL.md`](docs/DEPLOY_RENDER_VERCEL.md)** — one Render Blueprint + one Vercel import, with copy-paste env vars and post-deploy smoke checks. Deeper dives: [`docs/DEMO_HOSTING.md`](docs/DEMO_HOSTING.md) *(option overview)* and [`docs/VERCEL.md`](docs/VERCEL.md) *(edge-proxy paths)*.

**Fix your existing Vercel link (no new URL):** [`docs/DEPLOY_SAME_LINK.md`](docs/DEPLOY_SAME_LINK.md)

**Prebuilt PDFs for the portal:** [`docs/pdf/Helix-Implementation-Report.pdf`](docs/pdf/Helix-Implementation-Report.pdf) (implementation report; identical copy [`Helix-Implementation-Report-PORTAL.pdf`](docs/pdf/Helix-Implementation-Report-PORTAL.pdf) for re-upload). [`docs/pdf/Helix-Executive-Summary.pdf`](docs/pdf/Helix-Executive-Summary.pdf) (optional custom attachment). Regenerate: `python scripts/build_submission_pdfs.py` (after `pip install -r scripts/requirements-docs-pdf.txt`).

**Submission ZIP under 50 MB:** [`docs/SUBMISSION_ZIP.md`](docs/SUBMISSION_ZIP.md) and `scripts/make_submission_zip.ps1` (excludes `node_modules`, virtualenvs, `.git`, `dist`).

---

## How to demo (5-minute script — matches current UI)

1. **Sign in** → **New project** → **Paste text** → **Load sample requirement** → **Ingest** (no mic; same pipeline as paste). Optional: **Voice** (Chrome/Edge; see runbook) or **Upload file** / **URL import**.
2. **Ingest** → opens **Workspace** for the project.
3. **Generate artifacts** → wait for completion → review **summary**, **Kanban**, **readiness**.
4. **Generate tests** / **Analyze ambiguity** as needed; use **Copilot** for Q&A.
5. **Export** (CSV, Markdown, Jira/GitHub when configured) and **Stakeholder view** / **Analytics** from the sidebar.

Command palette: **Ctrl+Shift+P** (jump menu; generation shortcuts when on a project).

---

## Project layout

```
AI-Thon/
├── helix-backend/          FastAPI API + Dockerfile + seed (`scripts/seed.py`)
├── helix-frontend/         React + Vite UI (local dev + Docker build context)
├── docker-compose.yml      Postgres · Redis · Mongo · backend · frontend image build
├── docs/                   RUNBOOK, VERCEL, SUBMISSION_ZIP, demo hosting, GitHub notes
└── ...
```

---

## Strategic outcomes (mapped to the brief)

| Hackathon outcome | How Helix delivers |
| --- | --- |
| **Increased AI adoption** | One product surface for PMs, devs, QA, and tech leads |
| **Measurable productivity gains** | Live MetricsBar shows hours / cost saved + speedup vs. manual |
| **Pipeline of scalable AI solutions** | Pluggable agent architecture — add new roles (security review, compliance check) without touching UI |
| **Innovation culture** | Voice-to-spec, multi-agent transparency, traceability — none of which exist in current tools |
| **Leadership visibility** | Confidence-scored estimates and risk surfacing give engineering leaders early signal |

---

## Theme alignment & rubric self-score

**Theme:** *AI for SDLC Productivity — Intelligent SDLC Copilot* (Code-AI-Thon 2026 · Phase 2 · #BeEXIQO).

| Rubric criterion | Self-score | Evidence in repo |
|---|---|---|
| Innovation / Novelty | **4.5 / 5** | **Three differentiators no GPT wrapper has** — traceable clause graph, automated ambiguity workflow, 3-tier provider resilience. Each one provable in code in 60 seconds. See [`docs/NOVELTY.md`](docs/NOVELTY.md) + `PRESENTATION.md` Slide 7 (Technical Highlights). |
| Technical Difficulty | **5.0 / 5** | 11-step SSE pipeline, 3-tier provider resilience (Azure → clause-grounded mock → heuristic guarantors), in-process RAG over FAISS, Phase-2 parallel orchestrator, graph persistence, CI-gated golden-pipeline contract — `helix-backend/app/services/demo_orchestrator.py`, `helix-backend/app/agents/orchestrator.py`, [`.github/workflows/golden-pipeline.yml`](.github/workflows/golden-pipeline.yml) |
| Implementation (MVP) | **4.5 / 5** | All 11 stages wired with heuristic fallbacks; demo mode guarantees offline green path — [`docs/JUDGE_MODE.md`](docs/JUDGE_MODE.md), `scripts/judge_demo.ps1`. **CI-gated bulletproof contract on the e-commerce golden domain** — [`docs/GOLDEN_DOMAIN.md`](docs/GOLDEN_DOMAIN.md), [`.github/workflows/golden-pipeline.yml`](.github/workflows/golden-pipeline.yml). |
| Impact / Market Fit | **4.5 / 5** | Quantified ROI in `PRESENTATION.md` Slide 6 (`citation_item_rate`, hours/cost saved, ~$1/run cost model); regulated-team-ready governance via `?approved_only=true` |
| Presentation / Story | **4.5 / 5** | 60-sec elevator + 8-slide arc + scripted demo + judge cheat sheet — `PRESENTATION.md`, `PRESENTER_CHEATSHEET.md`, `docs/JUDGE_MODE.md` |
| Feasibility / Scalability | **4.5 / 5** | Dockerized today (`docker-compose.yml`, `Dockerfile.all-in-one`); production roadmap with concrete swaps — [`docs/PATH_TO_PRODUCTION.md`](docs/PATH_TO_PRODUCTION.md) |
| Theme Alignment | **5.0 / 5** | Direct mapping in the *Strategic outcomes* table above; pluggable agent architecture extends to security / compliance roles without UI changes |

> **Credibility note for evaluators.** The three credibility-affecting
> issues called out in earlier audits — *hardcoded readiness 94%*,
> *0 tasks after Scrum*, and *PRD endpoint 404* — have been **fixed in
> code**. Resolution tables with file references live in
> [`docs/PHASE3_WORKFLOW_EXECUTION.md`](docs/PHASE3_WORKFLOW_EXECUTION.md)
> and [`docs/PHASE5_AI_WORKFLOW_AUDIT.md`](docs/PHASE5_AI_WORKFLOW_AUDIT.md).

---

Built with care for **#BeEXIQO**. Be Curious. Be Bold. Be EXIQO.
