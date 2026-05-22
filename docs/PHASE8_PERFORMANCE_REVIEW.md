# Phase 8 — Performance Review

**Date:** 2026-05-22  
**Scope:** `helix-frontend` (Vite 8 build) + `helix-backend` API latency (Phase 3 reference)  
**Build command:** `npm run build` in `helix-frontend/`

## Executive summary

| Area | Status | Headline |
|------|--------|----------|
| Bundle size | **Poor** | ~4.8 MB total assets; main chunk **820 KB** (270 KB gzip); Three.js ambient **880 KB** |
| Dependencies | **Heavy** | Mermaid, Three/R3F, Framer Motion on product path; 13 global CSS bundles |
| React / re-renders | **Fair** | Some memoization; pipeline tick + route animations add churn |
| API latency | **Slow (expected)** | Full demo pipeline ~**220 s** (`use_ai=false`); Delivery Package fan-out OK |
| Memory / leaks | **Fair** | Most listeners cleaned up; SSE abort on navigate is a gap |
| Slow components | **Identified** | `WorkspaceAmbient`, Mermaid graph, `Landing` GSAP, large CSS |

**Verdict:** UX is smooth for demos on a desktop, but **first load and authenticated shell** pay for WebGL + animation libraries that are not required for the golden path. Biggest wins: route code-splitting, drop/defer Three.js ambient, lazy Mermaid, trim CSS.

---

## 1. Bundle size

### Production build (2026-05-22)

| Asset | Raw | Gzip | Notes |
|-------|-----|------|-------|
| `index-*.js` (main) | **820 KB** | **270 KB** | React, router, all **eager** product pages |
| `AmbientNetField-*.js` | **880 KB** | **234 KB** | Three + R3F (`WorkspaceAmbient`) |
| `index-*.css` | **291 KB** | **50 KB** | 13 imported stylesheets + `index.css` |
| Mermaid ecosystem | ~2.0+ MB (split) | ~500+ KB | cytoscape 434 KB, core chunks 594 KB, katex 259 KB, etc. |
| `HeroParticles-*.js` | 2.4 KB | 1.1 KB | Lazy; pulls separate Three path on Landing |
| **Total `dist/assets`** | **~4.8 MB** | — | 70+ JS chunks |

Vite warns: chunks **> 500 KB** (`index`, `AmbientNetField`, `cytoscape`, `chunk-NNHCCRGN`).

### Root causes

1. **No route-level `React.lazy`** — `App.jsx` statically imports Landing, Mission Control, Delivery Package, Judge Demo, etc. → one large main chunk.
2. **`WorkspaceAmbient` lazy-loaded but always mounted** in `AppShell` for every authenticated route except `/workspace` → **880 KB** Three.js chunk still fetched on Mission Control / Delivery Package.
3. **`DeliveryPackage` imports `MermaidView`** statically → entire Mermaid diagram stack loads when opening delivery package (even if architecture section is below fold).
4. **`main.jsx` imports 13 CSS files** for legacy/orphan screens (`hub.css`, `traceability-graph.css`, …) → **291 KB** CSS on every page.

### Recommendations (bundle)

| Priority | Action | Est. impact |
|----------|--------|-------------|
| **P0** | `React.lazy()` + `Suspense` per route in `App.jsx` | Main chunk −40–60% initial |
| **P0** | Default-off `WorkspaceAmbient` (toggle or `prefers-reduced-motion`); or CSS gradient fallback | −880 KB JS on most routes |
| **P1** | `const MermaidView = lazy(() => import('...'))` in Delivery Package only when diagram exists | Defer ~2 MB Mermaid until needed |
| **P1** | Remove orphan CSS imports from `main.jsx`; keep `helix-design.css` + `workspace.css` + `tidy.css` | CSS −150–200 KB |
| **P2** | `vite build --analyze` / `rollup-plugin-visualizer` in CI | Prevent regressions |
| **P2** | Drop unused deps from `package.json` after Phase 4 purge (`d3`, `recharts`, `@xyflow` if no imports) | Smaller `node_modules` + future-proof |

---

## 2. Large dependencies

| Package | ~Size impact | On golden path? | Notes |
|---------|--------------|-----------------|-------|
| `three` + `@react-three/fiber` + `drei` | **~1 MB+** | Yes (AppShell ambient) | `useFrame` runs every frame |
| `mermaid` | **~2 MB** (chunked) | Delivery Package | cytoscape + katex bundled |
| `framer-motion` | **~100–150 KB** | Landing, AppShell, Mission, Judge Demo | Route transitions + agent UI |
| `gsap` + `@gsap/react` | **~50–80 KB** | Landing, Sidebar | Loaded in `gsapInit` + Landing |
| `react-markdown` | Moderate | Delivery Package, Workspace | Re-parses on parent render |
| `d3`, `recharts`, `chart.js`, `@xyflow` | Large | **Orphan pages only** | Not in `App.jsx` — safe to remove if pages deleted |
| `react-syntax-highlighter` | Large | Orphan Dev Studio | Not on product routes |
| `react-beautiful-dnd` | Moderate | Orphan kanban | Incompatible note with React 19 |

---

## 3. Re-renders & React performance

### What’s done well

- **Mission Control:** `useReducer` for execution state (avoids deep `setState` merges); `useCallback` / `useMemo` for pipeline handlers and derived flags.
- **Zustand selectors:** `useProjectStore((s) => s.setProjects)` — narrow subscriptions.
- **Delivery Package:** `Promise.all` for 10 API calls — single loading wave, one re-render batch at end.
- **Reduced motion:** `useReducedMotion` in AppShell, Sidebar, several legacy pages.

### Hot spots

| Component / pattern | Issue | Severity |
|---------------------|-------|----------|
| `AppShell` `AnimatePresence` + `key={location.pathname}` | Full outlet remount on every nav → state loss + layout thrash | Medium |
| `MissionControl` `setInterval(420ms)` while `pipelineRunning` | Dispatches `tick` ~2.4/s → re-renders entire execution UI | Medium |
| `MissionAgentExecution` `motion.div` + `layout` per agent | Layout animations measure DOM each update | Medium |
| `DeliveryPackage` | No `React.memo` on sections; `ReactMarkdown` for exec summary re-renders when any state changes | Low–Med |
| `GlobalRipple` | Document-level `pointerdown` — cheap; OK | Low |
| `WorkspaceChat` | Streaming tokens → frequent `setState` (expected) | Low |

### Recommendations (React)

| Priority | Action |
|----------|--------|
| **P1** | Pause or remove `tick` interval when no agent is `running`; drive UI only from SSE events |
| **P1** | Replace AppShell route `AnimatePresence` with CSS transition or `key` only on major steps |
| **P2** | `memo(PackageSection)` + `useMemo` for markdown body in Delivery Package |
| **P2** | Split Mission Control form vs execution panel to isolate re-renders |

---

## 4. API latency

### Measured (Phase 3, `use_ai=false`)

| Flow | Duration | Notes |
|------|----------|-------|
| `POST /api/demo/{id}/run` (SSE, 11 steps) | **~220 s** | Sequential agent pipeline |
| Delivery Package load | 10 parallel GETs | Dominated by slowest endpoint |
| Health / auth | &lt; 2 s | Fast |

### Backend structure

- **Demo orchestrator** runs agents **sequentially** (`demo_orchestrator.py`) — quality → review → ambiguity → … → readiness. Latency is dominated by LLM/mock work, not HTTP overhead.
- **Ad-hoc** `/api/studio/*/analyze` etc. repeat full inference per call.
- **SQLite** default — fine for demo; connection pool matters at scale.

### Recommendations (API)

| Priority | Action |
|----------|--------|
| **P1** | Expose step timings in SSE (partially exists) + UI progress — set expectations |
| **P1** | Cache artifacts on project row; Delivery Package GETs should be mostly DB reads |
| **P2** | Parallelize independent steps (e.g. risk + quality) where safe |
| **P2** | `use_ai=true` budget: show per-step timeout + partial package |
| **P3** | Redis/Celery for long jobs; poll/WebSocket already exists for artifacts |

---

## 5. Memory leaks & runtime cost

| Location | Behavior | Risk |
|----------|----------|------|
| `GlobalRipple` | Removes listener on unmount | OK |
| `MermaidView` | `cancelled` flag on unmount | OK |
| `MissionControl` `runPipeline` | `AbortController` on Stop; **no abort on unmount** | **Med** — SSE continues if user navigates away |
| `WorkspaceAmbient` | `useFrame` + WebGL context while mounted | **GPU/battery** — not a leak, but continuous cost |
| `WinningDemoScreen` | `autoPlayCleanupRef` cleared on unmount | OK |
| `Landing` scroll listener | Cleaned in `useEffect` return | OK |

### Recommendations

```javascript
// MissionControl.jsx — add on unmount:
useEffect(() => () => abortRef.current?.abort(), [])
```

| Priority | Action |
|----------|--------|
| **P1** | Abort demo SSE on route leave / unmount |
| **P1** | Unmount `WorkspaceAmbient` when tab hidden (`document.visibilityState`) |
| **P2** | Dispose Mermaid render id / clear `innerHTML` on unmount (already partially done) |

---

## 6. Slow components (ranked)

1. **`WorkspaceAmbient` / `AmbientNetField`** — 880 KB JS + continuous WebGL frame loop on Mission Control, Delivery Package, Settings.
2. **`MermaidView` + diagram stack** — Large parse/render on first architecture view; `securityLevel: 'loose'` adds work.
3. **`Landing`** — GSAP scroll + lazy HeroParticles; acceptable for marketing route only if code-split.
4. **`DeliveryPackage` initial load** — 10 APIs + large markdown + optional Mermaid.
5. **`CommandPalette`** — Always mounted in AppShell; index search over commands each keystroke (minor).

---

## 7. Target metrics (suggested)

| Metric | Current (est.) | Target |
|--------|----------------|--------|
| Main entry JS (gzip) | ~270 KB | &lt; 120 KB |
| Auth shell extra JS | +234 KB (Three) | 0 KB default |
| CSS (gzip) | ~50 KB | &lt; 25 KB |
| LCP (Mission Control, fast 4G) | Poor | &lt; 2.5 s |
| Demo pipeline (mock) | ~220 s | &lt; 90 s with parallel steps |
| Delivery Package TTI | 2–5 s (network) | &lt; 1.5 s cached |

---

## 8. Optimization roadmap

### Quick wins (&lt; 1 day)

- Lazy-load routes in `App.jsx`.
- Gate `WorkspaceAmbient` behind `localStorage helix_fx` or env `VITE_DISABLE_AMBIENT=1`.
- Lazy `MermaidView` in Delivery Package.
- Strip unused CSS imports from `main.jsx`.
- Abort SSE on Mission Control unmount.

### Medium (1–3 days)

- Split Delivery Package fetch: critical (project, artifacts, tests) vs deferred (diagram, sprint, risk).
- Reduce Mission Control interval / event-only updates.
- Backend: persist PRD/readiness during pipeline so Delivery Package avoids 404/re-fetch.

### Longer term

- Remove orphan pages/deps (Phase 4).
- Replace Framer route transitions with CSS on product shell.
- Job queue + progress WS authenticated and tied to user.
- Bundle budget in CI (fail if main &gt; 150 KB gzip).

---

## 9. Verification

```bash
cd helix-frontend
npm run build                    # chunk table in stdout
npm run preview -- --port 4173   # Lighthouse on /mission-control

# Optional: install visualizer
# npx vite-bundle-visualizer
```

---

## 10. Code references

| Topic | File |
|-------|------|
| Eager routes | `helix-frontend/src/App.jsx` |
| CSS bloat | `helix-frontend/src/main.jsx` |
| Three ambient | `helix-frontend/src/components/layout/AppShell.jsx` |
| Pipeline tick | `helix-frontend/src/pages/MissionControl.jsx` |
| Mermaid | `helix-frontend/src/components/studio/MermaidView.jsx` |
| Parallel API load | `helix-frontend/src/pages/DeliveryPackage.jsx` |
| Demo latency | `helix-backend/app/services/demo_orchestrator.py` |
| Phase 3 timing | `docs/phase3-workflow-results.json` |
