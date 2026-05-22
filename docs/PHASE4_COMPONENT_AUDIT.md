# Phase 4 — Component Audit

**Project:** Helix (AI-Thon)  
**Date:** 2026-05-22  
**Scope:** `helix-frontend/src`, `helix-backend/app`  
**Active product surfaces (routed):** 8 pages in `App.jsx`

---

## Executive summary

The codebase is a **dual-layer** system: a slim **5-surface product** (Mission Control → Workspace → Delivery Package + Judge Demo + Settings) sitting on top of a **large hackathon-era UI layer** (~35 orphan pages, ~70+ components, 15+ global CSS bundles) that is no longer routed.

| Category | Active | Orphan / redundant | Recommendation |
|----------|--------|------------------|----------------|
| Pages | **8** | **35** | Archive or delete orphan `pages/` |
| Components (heuristic) | ~25 in live tree | **~60+** orphan-only | Delete with orphan pages |
| Hooks | **1** (`useDarkMode`) | **1** (`useKeyboardShortcuts`) | Remove shortcuts hook or wire to AppShell |
| Zustand stores | **2** active (`auth`, `project`) | **1** mostly orphan (`artifact`) | Remove `useArtifactStore` after page purge |
| Frontend API calls | **~20** on golden path | **~94** only from orphan UIs | Keep backend; trim unused *frontend* clients |
| Backend route modules | **32** routers | ~12 UI-only legacy | Keep for demo orchestrator; document as internal |
| Global CSS imports | **4** essential | **11** legacy bundles in `main.jsx` | Lazy-load or delete unused CSS |

**Estimated safe cleanup:** removing orphan frontend code could cut **~40–50%** of `src/pages` + `src/components` and materially shrink bundle/CSS without breaking the autonomous workflow (verified in Phase 3).

---

## 1. Active product inventory (routed)

### Pages (`App.jsx`)

| Route | Page | Purpose |
|-------|------|---------|
| `/` | `Landing.jsx` | Marketing + guest/login |
| `/login`, `/register` | Auth | |
| `/mission-control` | `MissionControl.jsx` | Upload + Launch AI team |
| `/workspace` | `WorkspacePage.jsx` | Chat workspace |
| `/delivery-package` | `DeliveryPackage.jsx` | Single-scroll package + export |
| `/judge-demo` | `WinningDemoScreen.jsx` | Judge autonomous demo |
| `/settings` | `Settings.jsx` | Account / theme / projects |

Legacy URLs redirect via `lib/productFlow.js` (`LEGACY_*_REDIRECTS`) — no extra page components.

### Component tree (live imports only)

```
App
├── ScrollProgress, GlobalRipple
└── AppShell
    ├── Sidebar, TeamFlowBar
    ├── WorkspaceAmbient → AmbientNetField (r3f)
    ├── CommandPalette, OnboardingModal
    └── Outlet
        ├── MissionControl → AutonomousPipelineStrip, MissionAgentExecution
        ├── WorkspacePage → WorkspaceChat → WorkspaceArtifact
        ├── DeliveryPackage → ReadinessScoreRing, MermaidView
        ├── WinningDemoScreen → JudgeDemoPipeline, ReadinessScoreRing
        ├── Settings
        └── Landing → Counter, Tilt, MagneticButton, HeroParticles, LandingIcons
```

### Lib modules (active path)

| Module | Used by |
|--------|---------|
| `productFlow.js` | Sidebar, CommandPalette, redirects |
| `autonomousPipeline.js` | Pipeline strip, Judge demo |
| `winningDemoFlow.js` | Mission Control SSE, Judge demo |
| `missionAgents.js` | Mission execution UI |
| `missionConfig.js` | Mission Control constraints |
| `workspaceActions.js` | Workspace chat intents |
| `deliveryReadiness.js` | Delivery Package fallback score |
| `formatApiError.js` | Login, Register (optional) |

### Hooks (active)

| Hook | Used by |
|------|---------|
| `useDarkMode` | Settings, Landing, WorkspaceAmbient |

### State (Zustand)

| Store | Active usage | Orphan usage |
|-------|--------------|--------------|
| `useAuthStore` | All protected routes | — |
| `useProjectStore` | Mission Control, Settings, Workspace, Delivery, Judge | Many orphan pages |
| `useArtifactStore` | **None on product surfaces** | Dashboard, Analytics, Insights, EngineeringHub, KanbanBoard, SdlcAnalyticsPanel |

**Redundant state:** `useArtifactStore` duplicates data now loaded per-page in `DeliveryPackage` (local `useState`) and is not used on the 5-surface journey. Safe to remove after orphan page deletion.

---

## 2. Orphan pages (35) — not in `App.jsx`

These files remain on disk; builds still bundle many of them only if something imports them (tree-shaking may exclude if truly unreferenced).

| Page | Former role | Overlaps active surface |
|------|-------------|-------------------------|
| `NewProject.jsx` | Ingest wizard | **Mission Control** |
| `DemoFlow.jsx` | Old demo runner | **WinningDemoScreen** |
| `Dashboard.jsx` | Legacy project hub | Mission Control + Delivery Package |
| `DeliveryReadinessScreen.jsx` | Readiness dashboard | Delivery Package (readiness section) |
| `JiraBacklog.jsx` | Backlog UI | Delivery Package (export section) |
| `SprintPlan.jsx` / `SprintPlannerScreen.jsx` | Sprint UI | Delivery Package (sprint section) |
| `PRDGenerator.jsx` | PRD tool | Delivery Package (executive summary) |
| `RequirementStudio.jsx` | Requirement editor | Mission Control upload |
| `Studio.jsx` / `DevStudio.jsx` | Architecture/effort studio | Workspace actions + Delivery Package |
| `ArchitectureVisualizer.jsx` | Diagram viz | Delivery Package (Mermaid) |
| `ReviewBoard.jsx` | Multi-agent review | Demo SSE `review` step (backend only) |
| `RiskCenterScreen.jsx` | Risk heatmap | Delivery Package risks |
| `TraceabilityGraphScreen.jsx` / `Traceability.jsx` | Trace graphs | — |
| `QualityScore.jsx` / `RequirementQualityCenter.jsx` | Quality | Demo `quality` step |
| `Insights.jsx` / `Analytics.jsx` / `AnalyticsRoute.jsx` | Analytics | — |
| `ExecutiveDashboard.jsx` | Exec KPIs | — |
| `EngineeringHub.jsx` / `CommandCenter.jsx` / `ControlTower.jsx` | Hub dashboards | Workspace |
| `ImpactAnalysis.jsx` | Impact graph | — |
| `Assistant.jsx` / `ChatAssistantScreen.jsx` | Chat | **Workspace** |
| `AgentWorkflow.jsx` | Agent pipeline UI | Mission execution panel |
| `MeetingCapture.jsx` | Meeting ingest | Mission Control (meeting mode exists) |
| `DigitalTwin.jsx` | Twin simulation | — |
| `QualityForecast.jsx` | Forecast | — |
| `ProjectManager.jsx` | PM forecast | — |
| `StakeholderPreview.jsx` | Preview | — |
| `RequirementDiff.jsx` | Version diff | — |

**Recommendation:** Move to `src/_archive/pages/` or delete in one PR; update `e2e/smoke.spec.ts` (still targets `/new` + Dashboard).

---

## 3. Unused components (confirmed or orphan-only)

### Confirmed zero importers (safe delete candidates)

| Component | Notes |
|-----------|--------|
| `components/assistant/FloatingAssistant.jsx` | Removed from `AppShell`; never imported elsewhere |
| `components/demo/WinningDemoStoryboard.jsx` | Superseded by `JudgeDemoPipeline` |
| `components/fx/HelpFAB.jsx` | Only referenced itself + removed FAB in shell |
| `components/fx/Reveal.jsx` | No imports found |

### Orphan-only (imported only by orphan pages)

Roughly **60+ files** under:

- `components/controltower/`, `commandcenter/`, `hub/`
- `components/dashboard/` (except shared patterns)
- `components/insights/`, `impact/`, `executive/`
- `components/requirement-studio/`, `workflow/`
- `components/traceability/`, `sprint/`, `architecture/`
- `components/reviewboard/`, `risk/`, `quality/`
- `components/export/ExportHub.jsx` (duplicate export UX)
- `components/chat/CopilotPanel.jsx` (Workspace uses REST assistant, not `/chat` WS)
- `components/artifacts/*` (Kanban, SummaryCard, TestCaseList — Dashboard only)
- `components/diff/*`, `VersionHistory.jsx`
- `components/analytics/TraceGraph3D.jsx`
- `components/fx/DependencyGraphFlow.jsx`, `AiTypingReveal.jsx`

**Keep:** `ReadinessScoreRing`, `MermaidView`, `JudgeDemoPipeline`, `AutonomousPipelineStrip`, `MissionAgentExecution`, `WorkspaceChat`, `WorkspaceArtifact`, layout/onboarding/fx used by Landing or App.

---

## 4. Duplicate / overlapping implementations

| Domain | Duplicate A | Duplicate B | Keep |
|--------|-------------|-------------|------|
| **Ingest + launch** | `NewProject.jsx` | `MissionControl.jsx` | Mission Control |
| **Judge demo** | `DemoFlow.jsx` | `WinningDemoScreen.jsx` | Winning Demo |
| **Pipeline UI** | `AutonomousPipelineStrip` | `JudgeDemoPipeline` | Both (shared `autonomousPipeline.js`) — optional merge later |
| **Readiness UI** | `ReadinessScoreRing` | `ReadinessPanel`, `ReadinessChecklist`, `ExecRingGauge` | Ring on product pages |
| **Export** | Delivery Package buttons | `ExportHub.jsx` | Delivery Package |
| **Assistant** | `WorkspaceChat` + `workspaceActions` | `Assistant.jsx`, `ChatAssistantScreen`, `CopilotPanel`, `FloatingAssistant` | Workspace |
| **Architecture** | `MermaidView` in package | `ArchitectureVisualizer`, `ArchitectureInteractiveGraph`, `DependencyGraphFlow` | MermaidView |
| **Sprint** | Delivery Package section | `SprintPlannerScreen`, `SprintPlannerKanban` | Package section |
| **Backlog** | Delivery Package export | `JiraBacklog.jsx` | Package |

---

## 5. Hooks audit

| Hook | Status | References |
|------|--------|------------|
| `useDarkMode.js` | **Active** | Settings, Landing, ambient |
| `useKeyboardShortcuts.js` | **Orphan-only** | `Dashboard.jsx`, `NewProject.jsx` |

**Recommendation:** Delete hook with orphan pages, or register shortcuts in `AppShell` if still desired (`?` help).

---

## 6. Unused / redundant lib modules

| Lib | Status |
|-----|--------|
| `helixProgressWsUrl.js` | Only via `followTaskProgress.js` → **Dashboard only** |
| `pinnedProjects.js` | **No imports** |
| `followTaskProgress.js` | Dashboard only |
| `followArtifactStream.js` | `AgentWorkflow.jsx` only |
| `workflowAgents.js` | `AgentWorkflowLive.jsx` only |
| `architectureGraph.js`, `traceabilityGraph.js`, `sprintKanban.js`, `qualityRadar.js`, `riskCenter.js`, `dependencyGraph.js`, `aiTypingStream.js` | Orphan feature libs |

---

## 7. API usage — frontend vs backend

### Golden-path APIs (product + Phase 3 workflow)

Used by Mission Control, Delivery Package, Workspace, Judge Demo, or demo orchestrator:

```
POST /api/auth/*
GET  /api/health
POST /api/ingest/text|file|url
GET  /api/projects, /api/projects/{id}
POST /api/demo/{id}/run
GET  /api/artifacts/{id}
GET  /api/testcases/{id}
GET  /api/readiness-center/{id}
GET  /api/studio/diagram|effort|risk/{id}
POST /api/studio/*/run (via workspaceActions)
GET  /api/sprint-plan/{id}/auto
GET  /api/backlog/{id}, /jira-csv, /ado-csv
POST /api/backlog/{id}/jira-push
POST /api/assistant/{id}/ask
```

### Frontend calls with **no active route** (orphan UI only)

| API group | Example paths | Backend still needed? |
|-----------|---------------|------------------------|
| Executive | `/api/executive/dashboard` | Optional (marketing) |
| Control tower | `/api/control-tower/{id}` | Used by demo internals / hub |
| Command center | `/api/command-center/{id}` | Orphan UI |
| Insights | `/api/insights/{id}` | ML service — orphan UI |
| Impact | `/api/impact/...` | Orphan UI |
| Forecast | `/api/forecast/...` | Orphan UI |
| Meeting | `/api/meeting/...` | Mission Control could use — not wired |
| Dev studio | `/api/devstudio/...` | Orphan UI |
| Traceability (standalone) | `/api/traceability/...` | Demo generates data |
| Review board (standalone) | `/api/review-board/...` | **Demo SSE `review` step** |
| Quality (standalone) | `/api/quality/...` | **Demo SSE `quality` step** |
| Chat WebSocket | `/api/chat/{id}` | CopilotPanel only |
| WS progress | `/api/ws/progress/{id}` | Dashboard task progress |
| Export hub | `/api/export/jira|github|markdown|csv` | Overlaps backlog CSV |
| Delivery PRD | `/api/delivery/prd/...` | **404 in Phase 3** — optional |
| Digital twin | `/api/delivery/twin/...` | Orphan UI |
| Delivery PM | `/api/delivery/pm/...` | Orphan UI |
| Requirement versions | `/api/projects/{id}/requirement-versions` | Orphan UI |
| Diff | `/api/diff/compare` | Orphan UI |
| Sprint kanban | `/api/sprint-plan/.../kanban` | Orphan UI |
| Ambiguity (direct) | `/api/ambiguity/analyze/{id}` | Dashboard / studio — demo covers |
| Artifacts generate | `/api/artifacts/generate/{id}` | Dashboard — demo covers |
| Demo steps metadata | `GET /api/demo/steps` | DemoFlow only |

**Recommendation:** Do **not** delete backend routes without tracing `demo_orchestrator.py` and agents. **Do** delete orphan frontend API clients to reduce confusion.

### Backend services with limited/no route exposure

| Service | Notes |
|---------|--------|
| `delivery_cost.py` | Used by `command_center`, `effort_estimator` — internal |
| `executive_dashboard.py` | `/api/executive` only |
| `ml_insights.py` | `/api/insights` only |
| `github_service.py` | `/api/export/github` only |
| `snapshots.py` | Version snapshots — orphan UI |
| `mock_agents.py` | Fallback / tests |
| `nlp_service.py` | Check ingestion path |

All other services in `demo_orchestrator` chain should be **retained**.

---

## 8. Dead code & build weight

### `main.jsx` — global CSS (always loaded)

| Stylesheet | Needed for product? |
|------------|---------------------|
| `index.css`, `helix-design.css`, `helix-native.css`, `workspace.css`, `winning-demo.css` | **Yes** |
| `hackathon-fx.css`, `fx.css`, `tidy.css`, `light-theme.css` | Partial (Landing/tidy) |
| `hub.css`, `executive.css`, `requirement-studio.css`, `agent-workflow.css` | **No** (orphan) |
| `quality-center.css`, `architecture-viz.css`, `sprint-planner.css` | **No** |
| `traceability-graph.css`, `risk-center.css`, `floating-assistant.css`, `delivery-readiness.css` | **No** |

**Recommendation:** Split CSS: `product.css` import chain vs delete 9 orphan stylesheets (~50KB+ gzip savings possible).

### Tests / scripts referencing legacy UI

| Asset | Issue |
|-------|--------|
| `e2e/smoke.spec.ts` | Expects `/new`, Dashboard selectors |
| `playwright.config.ts` webServer | OK |

### Duplicate files (path casing)

Windows may hide duplicate paths like `helix-frontend\src\pages\Login.jsx` vs `Login.jsx` — normalize to single path on commit.

---

## 9. Cleanup plan (prioritized)

### P0 — Safe, high impact (frontend only)

1. **Archive `src/pages/` orphans (35 files)** to `src/_archive/` or delete.
2. **Delete orphan-only components** listed in §3 (batch by folder).
3. **Remove `useArtifactStore`** from `useStore.js` and orphan consumers.
4. **Remove** `FloatingAssistant`, `HelpFAB`, `WinningDemoStoryboard`, `Reveal`.
5. **Trim `main.jsx` CSS** to product + landing bundles only.

### P1 — Consolidate duplicates

6. Delete `DemoFlow.jsx`, `NewProject.jsx`, `Dashboard.jsx` (redirects already in `productFlow.js`).
7. Merge export UX: keep Delivery Package; delete `ExportHub.jsx`.
8. Single assistant path: keep `WorkspaceChat` + `workspaceActions`; delete `Assistant.jsx`, `ChatAssistantScreen`, `CopilotPanel`.

### P2 — API & backend hygiene (careful)

9. Document **internal vs public** APIs in OpenAPI tags (demo vs dashboard).
10. Fix or remove `GET /api/delivery/prd/{id}` if PRD section should render (Phase 3 gap).
11. Keep `demo_orchestrator` services intact; do not remove `review_board`, `quality_scorer`, etc.

### P3 — Nice to have

12. Unify pipeline components (`AutonomousPipelineStrip` + `JudgeDemoPipeline` shared list renderer).
13. Lazy-load `AmbientNetField` / Three.js on Landing only.
14. Add `eslint-plugin-import` rule: no imports from `_archive`.
15. CI: fail if new page added without `App.jsx` route.

---

## 10. What NOT to remove

- `lib/autonomousPipeline.js`, `winningDemoFlow.js`, `missionAgents.js`
- `demo_orchestrator.py` and all agents it imports
- `backlog_export.py`, `test_suite_generator.py`, `diagram_generator.py`
- Legacy **redirects** in `productFlow.js` (bookmark compatibility)
- `CommandPalette`, `OnboardingModal`, `TeamFlowBar`

---

## Appendix — audit artifact

Machine-readable scan: [`docs/phase4-audit-data.json`](phase4-audit-data.json)  
Regenerate: `python scripts/phase4_component_audit.py`
