# Helix — canonical runbook (judges & maintainers)

**Use this file first.** Other docs (`GITHUB_PUSH.md`, `GITHUB_DEPLOY.md`, `ARCHITECTURE.md`, `WORKFLOW.md`) are deep dives; this runbook matches the **code that exists in this repo** (`helix-frontend/`, `helix-backend/`).

For the full end-to-end pipeline (11 demo steps + 5-stage analyze) and the eraser.io diagram source, see [`docs/WORKFLOW.md`](WORKFLOW.md) and [`docs/helix-workflow.eraser`](helix-workflow.eraser).

---

## 1. What runs where (do not mix ports)

| Service | URL | Notes |
|--------|-----|--------|
| **API (local script)** | `http://127.0.0.1:8765` | `helix-backend\run.ps1` → `uvicorn` on **8765** |
| **UI (Vite dev)** | `http://localhost:5173` | `cd helix-frontend` → `npm run dev` |
| **API from browser** | Same origin `/api` | Vite proxies to `VITE_API_PROXY_TARGET` (default **8765**) |

There is **no** `frontend/` app folder in this tree — the UI lives only under **`helix-frontend/`**.

---

## 2. Cold start (local, 2 terminals)

**Terminal A — backend**

```powershell
cd helix-backend
.\run.ps1
```

Wait until Uvicorn is listening on **8765**. Health: `GET http://127.0.0.1:8765/api/health`

**Terminal B — frontend**

```powershell
cd helix-frontend
npm ci
npm run dev
```

Open **http://localhost:5173**.

**Demo user** (after seed; `run.ps1` / Docker seed as in `SETUP.md`):

- Email: `demo@demo.com`
- Password: `demo123`

---

## 3. Judge gold path (recommended — no microphone)

Use this in the room **every time** unless you explicitly want the voice beat.

1. **Sign in** (`demo@demo.com` / `demo123`) → **New project**.
2. Stay on **Paste text** (default). Click **Load sample requirement** (fills a realistic PRD-style brief — no mic, no Chrome speech).
3. Click **Ingest** → workspace opens for the new project.
4. **Generate artifacts** → wait for toast / progress → **Kanban** + **summary** + **readiness** update.
5. **Generate tests** and/or **Analyze ambiguity** as time allows.
6. **Export** (CSV / Markdown always work; Jira/GitHub need env — see `SETUP.md`).
7. Optional: **Stakeholder view** or **Analytics** from the sidebar.

**Command palette:** **Ctrl+Shift+P** (jump, generate shortcuts on a project).

This path is what **Playwright** exercises (`helix-frontend/e2e/smoke.spec.ts`): sample load + ingest + dashboard visibility.

---

## 4. Optional: voice → spec (same pipeline after Ingest)

- **Where:** New project → **Paste text** → **Voice** (after or instead of typing / sample).
- **Browser:** **Chrome** or **Edge** (Chromium). **Web Speech API** only — nothing hits Helix until **Ingest**.
- **URL:** Prefer **`http://localhost:5173`** (mic + secure context).
- **Flow:** **Voice** → allow **microphone** → speak → textarea updates → **Stop** → **Ingest**.

Toasts explain mic/network issues. Code: `helix-frontend/src/components/ingestion/VoiceInput.jsx`.

---

## 5. Automated smoke (optional)

With API on **8765** (Playwright can start the Vite dev server — see `helix-frontend/playwright.config.ts`):

```powershell
cd helix-frontend
npm run test:e2e
```

Uses **Load sample requirement** + ingest (no microphone).

---

## 6. Push code to GitHub

See **`docs/GITHUB_PUSH.md`** (HTTPS PAT / Credential Manager / SSH).

---

## 7. Container / CI deploy

See **`docs/GITHUB_DEPLOY.md`** and root **`SETUP.md`** for Docker Compose and secrets.

For a **public HTTPS URL** (hackathon “Demo link”), use **`docs/DEMO_HOSTING.md`** (`Dockerfile.all-in-one` + Render **`render.yaml`**).

---

## 8. Before every live demo (checkbox)

- [ ] Backend up: `/api/health` returns OK.
- [ ] Frontend: `helix-frontend` dev or Compose UI on **5173**.
- [ ] **Gold path ready:** New project → **Load sample requirement** → **Ingest** (no mic rehearsal).
- [ ] If showing **voice:** Chromium + mic allowed for `localhost:5173`.
- [ ] At least one LLM key or accept **demo mode** (mock pipeline) per `README.md`.
- [ ] Optional: `npm run lint` + `npm run build` in `helix-frontend`.
