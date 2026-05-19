# Deploy Helix on Vercel (GitHub import)

Vercel is **excellent for the React (Vite) frontend**. It does **not** run the full Helix stack (FastAPI, long SSE streams, WebSockets, SQLite/Postgres, background jobs) in the same way as Docker or Render. For a **working demo with zero extra servers**, use **Render only** with `render.yaml` + `Dockerfile.all-in-one` (see [`DEMO_HOSTING.md`](DEMO_HOSTING.md)).

This guide covers the common **split** setup:

| Layer | Where | URL example |
|-------|--------|--------------|
| **API + optional same-origin UI** | Render (`Dockerfile.all-in-one` or Compose) | `https://helix-demo.onrender.com` |
| **UI only on Vercel** (optional) | Vercel imports this GitHub repo | `https://your-app.vercel.app` |

---

## What you get after connecting GitHub to Vercel

With the files in this repo, Vercel will:

1. Run `npm ci` in `helix-frontend/`
2. Run `npm run build` (Vite) there
3. Publish `helix-frontend/dist` as a static site
4. Apply SPA rewrites so `/project/...` and `/login` load `index.html`

You still need a **running API**. Point the UI at it with **`VITE_API_BASE`** (build-time variable).

---

## One-time Vercel project settings (Dashboard)

1. **Import** the GitHub repository (`siddham04/AIThon` or your fork).
2. **Root Directory**  
   - **Recommended (simplest):** leave **empty** (repo root). The root **`vercel.json`** already sets `installCommand`, `buildCommand`, and `outputDirectory`.  
   - **Alternative:** set Root Directory to **`helix-frontend`**. Then Vercel uses **`helix-frontend/vercel.json`** instead; you can delete or ignore the root `vercel.json` to avoid duplication.
3. **Framework Preset** — *Other* or *Vite* is fine; root `vercel.json` pins commands explicitly.
4. **Node.js Version** — **24.x** (matches your build settings) or **20.x** / **22.x**; Helix requires **>= 18**.
5. **Build & Development Settings** — leave defaults unless you override; root `vercel.json` supplies:
   - `installCommand`: `npm ci --prefix helix-frontend`
   - `buildCommand`: `npm run build --prefix helix-frontend`
   - `outputDirectory`: `helix-frontend/dist`
6. **Fluid Compute / Build machine** — your choices are fine; they only affect build/runtime performance on Vercel’s side.

---

## Required environment variable (Vercel)

Add under **Settings → Environment Variables** (for **Production** and **Preview**):

| Name | Example value | Notes |
|------|----------------|--------|
| **`VITE_API_BASE`** | `https://helix-demo.onrender.com/api` | **No trailing slash** issues: use exactly `.../api` so REST hits `/api/...` and WebSocket becomes `wss://.../api/ws/...` (see `src/lib/helixProgressWsUrl.js`). |

Redeploy after changing `VITE_API_BASE` (Vite bakes it in at build time).

---

## CORS on the API (Render / Docker)

When the UI is on `https://*.vercel.app` and the API on another host, the browser sends **cross-origin** requests. The API must allow your Vercel origin.

- **`HELIX_CORS_ORIGIN_REGEX`** — set on the **API** host, e.g.  
  `https://.*\.vercel\.app`  
  The Render blueprint in **`render.yaml`** already adds this for the `helix-demo` service.
- **`HELIX_CORS_ORIGINS`** — keep including `http://localhost:5173` for local dev.

If you use a **custom domain** on Vercel, add that full origin to **`HELIX_CORS_ORIGINS`** on the API (comma-separated) or extend the regex.

---

## Recommended flows

### A — Single URL (simplest for judges)

1. Deploy **only** on Render with **`render.yaml`**.  
2. Use the Render URL as **Demo Link**; **do not require Vercel**.

### B — Vercel “marketing” URL + Render API

1. Deploy API on Render; copy base like `https://helix-demo.onrender.com`.  
2. Connect the same repo to Vercel; set **`VITE_API_BASE`** = `https://helix-demo.onrender.com/api`.  
3. Use the **Vercel** URL as **Demo Link** if you want `*.vercel.app` branding.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Blank page / 404 on refresh | Ensure `vercel.json` **rewrites** are present (included in repo). |
| Network error calling API | Check **`VITE_API_BASE`**, HTTPS, and CORS regex on API. |
| WebSocket / progress stuck | `VITE_API_BASE` must be full `https://host/api` so `wss://host/api/ws/...` is used. |
| Build fails on Vercel | Use Node **20+**; run `npm ci && npm run build` locally in `helix-frontend` and fix errors. |

---

## Why not “only Vercel” for everything?

Helix needs a **long-lived Python process**, **database**, and **WebSocket/SSE** behavior that does not map cleanly to Vercel Serverless defaults without a large rewrite. The supported path is **API on Render (or Docker)** + **optional UI on Vercel**.
