# Deploy Helix on Vercel (GitHub import)

Vercel hosts the **React (Vite) static build**. The **FastAPI API** still runs on **Render**, Docker, or your machine.

---

## Keep your existing `*.vercel.app` link (no new URL)

**You never need a new Vercel project or domain.** Redeploying updates the app behind the **same** production URL (e.g. `https://ai-thon.vercel.app`).

| Goal | What to do |
|------|------------|
| Fix guest/login on **your current link** | Use the **same** Vercel project → **Deployments** → ⋮ on latest → **Redeploy** (or push to `main` if Git-connected). |
| UI + API under **one** hostname | Leave **`VITE_API_BASE` unset** (default). The app calls `https://<your-app>.vercel.app/api/...`; `middleware.js` proxies to Render. |
| Judges see one demo URL | Submit your **existing** `https://<project>.vercel.app` after Render is live and you redeployed. |

**Do not** create a second Vercel import unless you want a second URL. Change env vars on the **existing** project, then **Redeploy**.

---

## Quick fix — “Could not start a guest session”

1. **Deploy the API** (one-time): [Render](https://render.com) → New → Blueprint → connect this repo → use root `render.yaml` → wait until `https://<name>.onrender.com/api/health` returns JSON.
2. **Vercel → Settings → Environment Variables** (Production + Preview) — only if your Render URL is **not** `https://helix-demo.onrender.com`:
   - **`HELIX_BACKEND_ORIGIN`** = `https://<name>.onrender.com` (no `/api`, no trailing slash)
   - The repo’s `vercel.json` already defaults to `https://helix-demo.onrender.com` (Blueprint service name `helix-demo`).
3. **Redeploy** the Vercel project (required after env changes or pulling this default).
4. Test: open `https://<your-app>.vercel.app/api/health` — you should see JSON, not the React HTML page.

Guest/login use **same-origin** `/api` on your Vercel URL (proxied to Render). Only set **`VITE_API_BASE`** if you intentionally want the browser to call Render directly (Path B).

**Sign in without guest:** `demo@demo.com` / `demo123` (created on API startup).

---

## Why register / login “does not work” on Vercel

The browser loads the UI from `https://<your-app>.vercel.app`. By default the app calls **same-origin** `https://<your-app>.vercel.app/api/...` (see `helix-frontend/src/api/client.js` when `VITE_API_BASE` is unset).

Vercel was **only** serving the SPA — there was **no FastAPI** behind `/api`, so `/api/auth/register` returned **HTML (index.html)** or **404**, and registration failed.

**Fix (in this repo):** Edge **`middleware.js`** proxies every `/api/*` request to your real API host. You must set **`HELIX_BACKEND_ORIGIN`** on Vercel (see below).

---

## Path A — Same-origin `/api` (recommended for Vercel + Render)

1. Deploy the API (e.g. Render `render.yaml` / `Dockerfile.all-in-one`). Copy the service root, e.g. `https://helix-demo.onrender.com` (**no** `/api` suffix, **no** trailing slash).
2. In **Vercel → Project → Settings → Environment Variables** (Production **and** Preview):
   - **`HELIX_BACKEND_ORIGIN`** = `https://helix-demo.onrender.com`
3. **Do not** set `VITE_API_BASE` (or remove it), so the UI keeps using `/api` on the Vercel host.
4. **Redeploy** Vercel after saving env vars (middleware reads them at the edge).

`middleware.js` lives at the **repo root** and is duplicated under **`helix-frontend/middleware.js`** so it still runs if Vercel **Root Directory** is set to **`helix-frontend`**.

### If you see JSON `503` with “HELIX_BACKEND_ORIGIN is not set”

The variable is missing or not redeployed. Add it and trigger a new deployment.

---

## Path B — Cross-origin `VITE_API_BASE` (no proxy)

1. In Vercel env, set **`VITE_API_BASE`** = `https://your-service.onrender.com/api` (must end with `/api`).
2. Redeploy (Vite bakes this at **build** time).
3. On the **API** host, allow your Vercel origin (`HELIX_CORS_ORIGIN_REGEX` or `HELIX_CORS_ORIGINS`). Root `render.yaml` already sets a Vercel-friendly regex for the sample service.

WebSockets use `wss://…/api/ws/…` on the **API host** in this mode, which is better for long-running progress than the edge proxy.

---

## Import checklist (Vercel Dashboard)

| Setting | Value |
|--------|--------|
| **Root Directory** | **Empty** (repo root) *or* `helix-frontend` (middleware exists in both places) |
| **Framework** | Other / Vite (root `vercel.json` pins install/build) |
| **Node** | 20.x or 24.x (≥ 18) |
| **Env (Path A)** | `HELIX_BACKEND_ORIGIN` = `https://…onrender.com` |
| **Env (Path B)** | `VITE_API_BASE` = `https://…onrender.com/api` |

---

## Limits

- **Edge proxy (Path A):** Great for REST (register, login, ingest). **WebSocket / long SSE** through the proxy can be flaky or time out. For a full “Generate artifacts” streaming demo, prefer **Render-only** (`docs/DEMO_HOSTING.md`) or **Path B** with `VITE_API_BASE` pointing at the API.
- **Helix API key:** If `HELIX_API_KEY` is set on the backend, the browser must send that key; the proxy forwards `Authorization` and other headers as sent.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Register returns HTML / JSON parse error | You were hitting the SPA, not the API. Use **Path A** (`HELIX_BACKEND_ORIGIN` + redeploy) or **Path B** (`VITE_API_BASE`). |
| `503` + message about `HELIX_BACKEND_ORIGIN` | Set that env on Vercel and **redeploy**. |
| CORS errors (Path B only) | Fix `HELIX_CORS_ORIGIN_REGEX` / origins on the API. |
| Blank page on refresh | `vercel.json` SPA rewrite should still apply; `/api` is handled by middleware first. |
| Build fails | Run `npm ci && npm run build` in `helix-frontend` locally. |

---

## Why not only Vercel for everything?

Helix needs a **Python API**, **database**, and **long-lived** streaming behaviour. The supported split is **API on Render (or Docker)** + **UI on Vercel** (optional).
