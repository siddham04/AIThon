# Helix — canonical runbook (judges & maintainers)

**Use this file first.** Other docs (`GITHUB_PUSH.md`, `GITHUB_DEPLOY.md`, `ARCHITECTURE.md`) are deep dives; this runbook matches the **code that exists in this repo** (`helix-frontend/`, `helix-backend/`).

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

## 3. Five-minute demo path (actual UI labels)

1. **Sign in** → **New project** (sidebar or landing).
2. **Paste text** tab: paste a PRD *or* click **Load sample requirement** *or* use **Voice** (see §4).
3. Click **Ingest** → lands on **Workspace** (`/project/:id`).
4. Toolbar: **Generate artifacts** → wait for progress strip / toast → Kanban + summary populate.
5. **Generate tests** / **Analyze ambiguity** as needed.
6. **Export** panel: CSV / Markdown / etc. (Jira/GitHub need env — see `SETUP.md`).
7. Optional: **Stakeholder view** / **Analytics** from sidebar.

Keyboard: **Ctrl+Shift+P** command palette (see in-app shortcuts on New project / dashboard).

---

## 4. Voice → spec (30 seconds)

- **Where:** New project → **Paste text** → **Voice** button under Requirements.
- **Browser:** **Chrome** or **Edge** (Chromium). Uses **Web Speech API** only — **no** Helix API until **Ingest**.
- **URL:** Prefer **`http://localhost:5173`** (secure context for mic). Plain `http` on random LAN hostnames may block speech.
- **Flow:** **Voice** → allow **microphone** → speak → text appears in textarea → **Stop** → **Ingest**.

If it fails, the UI shows a **toast** with the usual cause (mic blocked, network to speech service, etc.). Implementation: `helix-frontend/src/components/ingestion/VoiceInput.jsx`.

---

## 5. Automated smoke (optional)

From repo root, with API on **8765** and UI dev server on **5173** (Playwright can start UI — see `helix-frontend/playwright.config.ts`):

```powershell
cd helix-frontend
npm run test:e2e
```

Uses `demo@demo.com` / `demo123` and the sample ingest path (no microphone).

---

## 6. Push code to GitHub

See **`docs/GITHUB_PUSH.md`** (HTTPS PAT / Credential Manager / SSH). This environment cannot store your token.

---

## 7. Container / CI deploy

See **`docs/GITHUB_DEPLOY.md`** and root **`SETUP.md`** for Docker Compose and secrets.

---

## 8. Before every live demo (checkbox)

- [ ] Backend up: `/api/health` returns OK.
- [ ] Frontend: `helix-frontend` dev or Compose UI on **5173**.
- [ ] Browser: Chromium for voice; mic permission not “blocked”.
- [ ] At least one LLM key or accept **demo mode** (mock pipeline) per `README.md`.
- [ ] Optional: `npm run lint` + `npm run build` in `helix-frontend`.
