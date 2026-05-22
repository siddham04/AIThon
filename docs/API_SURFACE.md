# Helix API surface — golden path vs internal

**Auth:** `/api/*` (except public health/auth) requires JWT or `X-Helix-Key`.

Do **not** delete backend routers without checking `demo_orchestrator.py` — quality, ambiguity, review, architecture, and test steps run **in-process** during `POST /api/demo/{id}/run` (not always as separate HTTP calls from the UI).

---

## Golden path (active frontend — keep)

| API | Consumer |
|-----|----------|
| `POST /api/auth/login`, `register`, `guest` | Landing, Login, Register |
| `GET /api/health` | Smoke / `demoConfig` |
| `GET/POST /api/projects`, `GET /api/projects/{id}` | Mission Control, Judge Demo, Workspace loader |
| `POST /api/ingest/text`, `file`, `url` | Mission Control |
| `POST /api/demo/{id}/run` | Mission Control SSE, Judge Demo |
| `GET /api/artifacts/{id}` | Mission Control, AI Workspace, Delivery Command |
| `GET /api/testcases/{id}`, `POST .../generate/{id}` | Workspace loader + chat actions |
| `GET /api/readiness-center/{id}` | Mission Control, Workspace loader |
| `GET/POST /api/studio/diagram`, `effort`, `risk/{id}` | Workspace chat (`workspaceActions.js`) |
| `GET/POST /api/sprint-plan/{id}/auto` | Delivery Command, Workspace |
| `GET /api/backlog/{id}/json`, `jira-csv`, `ado-csv`, `POST .../jira-push` | AI Workspace exports |
| `GET /api/export/markdown/{id}`, `json/{id}`, `csv/{id}` | AI Workspace exports |
| `POST /api/assistant/{project_id}/ask` | Copilot + Workspace chat |
| `GET /api/delivery/prd/{id}` | Workspace loader (deferred slice) |
| `GET /api/quality/{id}` | Workspace loader → `DeliveryInsightsPanel` |
| `GET /api/review-board/{id}` | Workspace loader → `DeliveryInsightsPanel` |
| `GET /api/traceability/{id}/graph` | `TraceabilityFlowAnimator` (AI Workspace) |
| `GET /api/delivery/pm/{id}` | Mission Control status strip, Delivery Command |

---

## Demo orchestrator only (backend in-process — keep routes)

These power SSE steps; the old standalone **pages** are gone but services remain:

| Step / domain | Service / agent (not always HTTP from UI) |
|---------------|-------------------------------------------|
| `quality` | `quality_scorer.score_requirement_text` |
| `ambiguity` | `AmbiguityAgent` |
| `review` | Review board agent / persist on project |
| `architecture` | `architecture_generator` / studio |
| `tests` | Test architect / `testcases` routes |

---

## Orphan UI only (no routed frontend — backend retained)

Safe to drop **frontend** `api.get/post` calls; routes stay for scripts, judges, or future surfaces.

| Prefix | Notes |
|--------|--------|
| `/api/executive` | Exec KPI dashboard (removed page) |
| `/api/command-center` | Ops panel |
| `/api/control-tower` | Control tower |
| `/api/insights` | ML widgets |
| `/api/impact` | Impact graph page |
| `/api/forecast` | Quality forecast page |
| `/api/meeting` | Meeting capture page |
| `/api/devstudio` | Extended studio page |
| `/api/delivery/twin` | Digital twin page |
| `/api/diff` | Requirement diff page |
| `/api/risk-center` | Standalone heatmap (studio `/studio/risk` used instead) |
| `/api/chat` | Legacy WebSocket copilot |
| `/api/ws` … progress | Legacy task progress (`followTaskProgress` removed) |
| `/api/ambiguity` | Standalone run (demo runs ambiguity in-process) |

**Not orphan for API** (still called from product UI): `/api/export/*`, `/api/backlog/*`, `/api/delivery/pm`, `/api/delivery/prd`, `/api/quality`, `/api/review-board`, `/api/traceability`.

---

## Public / unauthenticated

| Route | Purpose |
|-------|---------|
| `GET /api/health` | Liveness |
| `POST /api/auth/*` | Login / register |

---

## Operational

- `HELIX_DEMO_FAST=1` — heuristic PRD/PM, no LLM on hot paths.
- `ensure_project_prd()` — PRD persisted before demo SSE `complete`.
- OpenAPI `/docs` when `HELIX_DEBUG` and not production.

See: `docs/PHASE4_COMPONENT_AUDIT.md`, `docs/DEAD_CODE_CLEANUP.md`.
