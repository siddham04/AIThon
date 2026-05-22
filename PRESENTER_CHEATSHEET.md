# Helix — presenter cheat sheet (P0 demo)

**Judge Q&A script:** [docs/JUDGE_QA.md](docs/JUDGE_QA.md) (tasks, security pilot, timing, scope).

## Preflight (2 min before judges)

```powershell
# Terminal A
cd helix-backend
.\run.ps1   # sets HELIX_DEMO_FAST=true (~3–4 min heuristic pipeline)

# Terminal B
cd helix-frontend
npm run dev
```

| Check | URL / command |
|-------|----------------|
| **API health** | `http://127.0.0.1:8765/api/health` → `"status":"ok"` |
| **UI** | `http://localhost:5173` |
| **Backup bookmark** | `http://localhost:5173/project/proj_demo_seed01/ai-workspace` |

Login if needed: `demo@demo.com` / `demo123` (or **Try as Guest** on landing).

---

## 5-minute script (rehearse this)

| Time | Action | Clicks |
|------|--------|--------|
| 0:00–0:20 | Hook: messy req → autonomous AI team → Jira-ready package | 0 |
| 0:20–0:35 | Landing → **Start hackathon demo** (guest + judge) | 1 |
| 0:35–0:40 | **Start Autonomous SDLC Demo** (if not auto-started) | 1 |
| 0:40–4:00 | Narrate pipeline — progress is **SSE only** (no fake timer) | 0 |
| 4:00–4:15 | Finale ring → auto-opens **Delivery Package** | 0 |
| 4:15–4:45 | Scroll **tasks** banner + Jira preview (Task rows); **Approve & Export** | 1 |
| 4:45–5:00 | “Clause → story → task traceability” | 0 |

**If SSE stalls:** open backup bookmark above (pre-baked `proj_demo_seed01`).

---

## Ports & paths

| What | URL / path |
|------|------------|
| **API** | `http://127.0.0.1:8765` |
| **Judge demo** | `/judge-demo` |
| **Delivery package** | `/project/{id}/ai-workspace` |
| **Mission Control** | `/mission-control` (SSE errors → Pipeline warnings panel) |

---

## One-line honest slide (credibility)

> **Readiness %** comes from live delivery-gate scoring after the run (not a hardcoded placeholder). **Tasks** are generated per story via Scrum Master + heuristic fallback so Jira CSV always has engineering rows.

---

## Q&A anchors

- **Tasks in CSV:** `_ensure_project_tasks` — at least one task per story on demo path.
- **Readiness ring:** Gate-based % from `build_readiness_center()` (100% when all six gates pass).
- **PRD:** Generated during pipeline; lazy `GET /api/delivery/prd/{id}`.
- **Traceability:** Clause ids on stories/tasks; live ticker during judge run.

## Ctrl+Shift+P

Command palette on any project page.

## P2 features (optional)

| Feature | Where |
|---------|--------|
| Traceability animation | AI Workspace after pipeline |
| Jira CSV preview | `GET /api/backlog/{id}/jira-csv/preview` |
| Live Jira push | AI Workspace · `POST /api/backlog/{id}/jira-push` |
| Voice ingest | Mission Control → **Voice** tab (Chrome/Edge) |
| Rate limits | `HELIX_RATE_LIMIT_PER_MINUTE` (default 120 POST/min) |
| Parallel demo | `HELIX_DEMO_PARALLEL=true` (default on) |

## P1 ops notes

- **JWT rotate:** `POST /api/auth/refresh` with current bearer → new token (`jti` rotated). Change `HELIX_JWT_SECRET` to invalidate all sessions.
- **Generate/analyze routes** require auth (no anonymous LLM burn).
- **Three.js:** off by default; set `VITE_HELIX_HERO_PARTICLES=true` for landing particles only.
