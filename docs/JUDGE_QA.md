# Judge Q&A — honest answers (Helix AI-Thon)

Use this when judges ask “can we pilot this?” or challenge numbers on stage.

## “Your backlog only has stories — where are the tasks?”

**Today:** Every pipeline run calls `finalize_demo_project()` so **≥1 engineering task per story** (heuristic fallback if the LLM returns none). Jira CSV includes **Epic → Story → Task → Sub-task** rows.

**Show:** Delivery Package → Export hub → **Jira CSV preview** (look for `Issue Type = Task`). Or showcase: `/project/proj_demo_seed01/ai-workspace`.

## “The demo took forever on stage.”

**Cause:** Full Azure OpenAI path can run **~3–4+ minutes** per project.

**Mitigation (default now):** `HELIX_DEMO_FAST=true` → heuristic agents (~3–4 min, predictable). **Do not** run cold live LLM during the 5-minute slot unless rehearsed.

**Backup:** Pre-baked `proj_demo_seed01` — package loads in seconds. Bookmark on Judge Demo screen.

## “Is this secure enough to pilot?”

| Control | Status |
|---------|--------|
| JWT on all `/api/*` (except auth + health + demo metadata) | **Shipped** — restart API after deploy |
| WebSocket progress | **JWT query token required** |
| Rate limits | **On** (`HELIX_RATE_LIMIT_PER_MINUTE`, default 120) |
| Default JWT secret | **Dev only** — set `JWT_SECRET` before any public URL; use `HELIX_PRODUCTION=1` to fail startup if still default |
| Open LLM proxy routes | **Closed** (global gate + per-route auth) |

**Pilot roadmap (2–4 weeks):** httpOnly cookies, CSP + Mermaid strict (partial), SSO, audit log, pen test on hosted env.

## “First load felt heavy on my laptop.”

- Three.js hero **off by default** (opt-in via env).
- Landing + product routes **lazy-loaded**; Mermaid/Three in separate chunks.
- Venue tip: open **Judge Demo** once on Wi-Fi before presenting (warms chunks).

## “Why so many screens in the repo?”

**Product path is 5 surfaces:** Judge Demo → Mission Control (optional upload) → AI Workspace → Delivery Command → Copilot (+ Settings).

Legacy experiments live under `helix-frontend/src/pages/_archive/` — **not routed**, not in the judge path.

## “PRD 404 / readiness looked fake.”

- **PRD:** Generated during pipeline; persisted **before** SSE `complete`; lazy-created on `GET /delivery/prd/{id}` if missing.
- **Readiness:** **Gate-based score** (`100 × completed_gates / total`), not a fixed 94%.

## “Mobile looked rough.”

Mission Control uses **horizontal scroll strips** (not page overflow). Collapsed sidebar shows **▶ Demo** badge + tooltip for Judge Demo.

---

**Presenter one-liner:** *“Helix is a rehearsed 5-page autonomous SDLC demo with a full backup package, sprint-ready tasks in Jira export, and a clear security path for pilot — not a production GA claim today.”*
