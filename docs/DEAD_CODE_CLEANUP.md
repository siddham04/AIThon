# Dead code & state cleanup — status (May 2026)

## Done (P0)

| Item | Status |
|------|--------|
| `useArtifactStore` | **Removed** from `store/useStore.js`; zero references in `helix-frontend/src` |
| `useKeyboardShortcuts` | **Removed** (`hooks/useKeyboardShortcuts.js`) |
| Orphan pages | **9 active** at `pages/` root; legacy pages removed (see `pages/_archive/README.md`) |
| Orphan component trees | **Removed** (~65 files): hub, dashboard, insights, workflow, etc. |
| Libs: `pinnedProjects`, `helixProgressWsUrl`, `followTaskProgress`, `workflowAgents`, `followArtifactStream`, graph/radar libs | **Deleted** |
| `main.jsx` CSS | **2 global imports**: `index.css`, `helix-native.css` only |
| Route CSS | `helix-design` → Landing/Login/Register; `product-five` → AppShell; `winning-demo`, `workspace` per page/component |

## Active state pattern

**AI Workspace / Delivery** use **local state** + `loadWorkspaceData()` (not Zustand artifacts):

- Critical: `artifacts`, `readiness-center`
- Deferred: `testcases`, `quality`, `review-board`, `studio/*`, `sprint-plan`, `delivery/prd`

## CSS note

Legacy screen bundles (`hub.css`, `executive.css`, `quality-center.css`, …) are **no longer imported** anywhere. Styles for product surfaces live in `product-five.css`, `helix-design.css`, and the large `index.css` baseline. Unused files under `src/styles/` can be deleted without affecting the build.

## APIs

See **`docs/API_SURFACE.md`** for golden path vs internal. Backend routes for executive/insights/etc. are intentionally kept; demo orchestrator uses in-process agents for quality/ambiguity/review.

## Duplicate surfaces — resolved mapping

| Keep (routed) | Removed / merged into |
|---------------|------------------------|
| `MissionControl.jsx` | `NewProject`, `RequirementStudio` (ingest + launch) |
| `WinningDemoScreen.jsx` | `DemoFlow` |
| `AiWorkspace.jsx` | `DeliveryPackage`*, `DeliveryReadinessScreen`, `JiraBacklog`, `SprintPlan*`, `PRDGenerator` |
| `DeliveryCommandCenter.jsx` | Sprint planner / traceability graph pages (plan + dependency graph) |
| `WorkspaceChat` (+ `CopilotChat.jsx` route) | `Assistant`, `ChatAssistantScreen`, `CopilotPanel`, `FloatingAssistant` |
| Export buttons on `AiWorkspace` | `ExportHub` component |
| `ReadinessScoreRing` | `ReadinessPanel`, `ReadinessChecklist`, `ExecRingGauge` |

\*Legacy URL `/delivery-package` redirects to `/ai-workspace` via `productFlow.js`.

All removed **pages** are off the router (files deleted or recoverable from git). Removed **components** have zero imports from the 9 active pages.

## Build

`npm run build` passes after cleanup.
