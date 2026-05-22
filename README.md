# Helix — The Intelligent SDLC Copilot

> **From raw thought to shipped feature — with full provenance.**
> Submission for **Code-AI-Thon 2026 · Phase 2 (#BeEXIQO – Be Builder)**
> Track: *AI for SDLC Productivity — Intelligent SDLC Copilot*

Helix turns messy product input — emails, transcripts, briefs, PDFs, voice
notes — into a **traceable graph** of stories, engineering tasks, test
cases, ambiguities, and non-functional risks. A **multi-agent pipeline**
of specialized AI roles collaborates over your input; the workspace lets
your team refine, query, and export everything to Jira, Azure DevOps, or
GitHub Issues in one click.

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
              │
    ┌─────────┴──────────┐
    ▼                    ▼
┌───────────────┐  ┌─────────────────┐
│ Azure OpenAI  │  │ Anthropic Claude │
│ JSON agents:  │  │ preferred for:   │
│ Analyzer,     │  │ Ambiguity, tests, │
│ Decomposer,   │  │ estimator (else  │
│ Risk (+       │  │ Azure JSON        │
│  fallback)    │  │ fallback)        │
└───────────────┘  └─────────────────┘
```

### Tech stack

**Frontend:** React 19 · TypeScript · Vite 8 · Web Speech · **Recharts** and **Chart.js**
(`react-chartjs-2`) on the dashboard for SDLC KPIs (Kanban distribution, artifact mix,
insights-backed quality and burndown).

**Backend:** Python 3.11 · FastAPI · Pydantic v2 · OpenAI SDK (Azure
client) · pypdf · python-docx · **spaCy** / sentence-transformers / FAISS (ingest & RAG paths).

**AI (actual code paths):** **Azure OpenAI** — set `AZURE_OPENAI_*` or hackathon-style
`AZURE_OAI_ENDPOINT` / `AZURE_OAI_KEY` / `PLANNING_MODEL` (see `helix-backend/.env.example`).
The deployment default is **o3** with JSON mode for `Analyzer`, `Decomposer`, and `Risk`, and
as **fallback** for agents that prefer **Anthropic Claude** when `ANTHROPIC_API_KEY` is set
(`Ambiguity`, `TestArchitect`, `Estimator`, and chat). If neither provider is configured,
**demo mode** uses deterministic mock output so the pipeline and UI stay fully usable offline.

**ML / analytics (non-LLM):** **scikit-learn** (`IsolationForest` task anomalies, TF-IDF +
cosine duplicate-story detection) via `GET /api/insights/{project_id}` (`ml_insights.py`),
surfaced in the workspace dashboard and the full **Insights** page. Embeddings for RAG use
**sentence-transformers** (PyTorch). A standalone **TensorFlow** graph is not required for
the delivered demo path — judges can point to sklearn + Azure OpenAI as the primary “AI/ML”
stack in code.

Optional: set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` for Claude; keep Azure variables for
JSON-stage quality. `GET /api/health` reports `azure_openai_configured` and `anthropic_configured`.
Ingest and `/api/ingest/*` responses may include `sensitive_hints` (email-, key-, and
token-shaped patterns) before you run analyze.

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

**Anthropic** (optional; ambiguity / tests / estimator prefer Claude when set):

```
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

Leave keys blank to run **demo mode**: the backend emits deterministic,
clause-grounded artifacts so judges never see an empty pipeline.

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

**Canonical runbook** (voice, ports, smoke test, GitHub): [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

**Public demo URL (hackathon submission):** deploy the single-container image — step-by-step [`docs/DEMO_HOSTING.md`](docs/DEMO_HOSTING.md) (Render Blueprint + `render.yaml`). **Optional UI on Vercel:** [`docs/VERCEL.md`](docs/VERCEL.md) — set **`HELIX_BACKEND_ORIGIN`** on Vercel to your Render URL so `/api` (register/login) proxies correctly.

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

Built with care for **#BeEXIQO**. Be Curious. Be Bold. Be EXIQO.
