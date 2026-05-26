# Public demo link (for hackathon “Demo URL”)

I (the repo) **cannot** create a live `https://…` address without **your** cloud account. Use one of the options below; when the deploy finishes, paste the **HTTPS service URL** into the submission field **Demo Link**.

---

## Option A — Render (recommended, free tier)

1. Push this repository to GitHub (already at `https://github.com/siddham04/AIThon` if unchanged).
2. Open [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**.
3. Connect the **AIThon** repo and select branch **`main`**.
4. Render reads root **`render.yaml`** and builds **`Dockerfile.all-in-one`**.
5. Wait for the first deploy (10–20+ minutes: Python + spaCy + frontend build).
6. Open the service URL, e.g. **`https://helix-demo.onrender.com`** (exact name from Render).
7. **Demo login** (seeded on startup): `demo@demo.com` / `demo123` (see `README.md` / `docs/RUNBOOK.md`).

**Cold start:** Free services sleep after idle; the first open after sleep can take ~30–60s.

**Data:** Default image uses **SQLite** under `/app/data` (ephemeral on free tier — fine for judges, not for production).

**Optional AI keys:** In the Render service → **Environment**, add `AZURE_OPENAI_API_KEY` (plus `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`) from `.env.example` if you want Tier-1 live LLM calls instead of the deterministic clause-grounded mock. The mock path is fully usable for judges — see `docs/GOLDEN_DOMAIN.md`.

---

## Option B — Docker on your own VM

On any Linux VM with Docker:

```bash
git clone https://github.com/siddham04/AIThon.git
cd AI-Thon
docker build -f Dockerfile.all-in-one -t helix-demo .
docker run -p 8080:8000 -e PORT=8000 -e JWT_SECRET="$(openssl rand -base64 32)" helix-demo
```

Open `http://<server-ip>:8080`. Put **`http://…`** in the demo field only if the portal allows non-HTTPS; otherwise use HTTPS + a domain.

---

## What was added for single-URL demos

- **`Dockerfile.all-in-one`** — builds the React app, copies it to `/app/static`, runs **uvicorn** on **`PORT`** (Render sets this).
- **`HELIX_SERVE_SPA` / `HELIX_STATIC_DIR`** — FastAPI serves the SPA and keeps **`/api/*`** as today (`helix-backend/app/main.py`).
- **`deploy/all-in-one/entrypoint.sh`** — runs `scripts/seed.py` then uvicorn.

Local dev is unchanged: still use `helix-backend` + `helix-frontend` on **8765** / **5173** per `docs/RUNBOOK.md`.

---

## Submission field

| Field        | What to enter |
|-------------|----------------|
| **Demo Link** | Your Render URL **`https://<service>.onrender.com`** (or other HTTPS host) after deploy. |

If the form **requires** a URL before you have deployed, deploy first, or temporarily use the GitHub repo URL and explain in **Instructions to Run** that the public demo is pending (less ideal for judges).

---

## Option C — Vercel (frontend) + Render (API)

Use this if you want a **`*.vercel.app`** URL for the UI while the API stays on Render.

**Your Vercel URL does not change when you redeploy** — use the same Vercel project, set env (or rely on repo defaults), and **Redeploy** so `/api` on that hostname works. See **`docs/VERCEL.md`** → *Keep your existing link*.

1. Complete **Option A** so you have `https://<service>.onrender.com` (API + optional same-origin UI).
2. Import the **same** GitHub repo into [Vercel](https://vercel.com/) and follow **`docs/VERCEL.md`**.
3. On Vercel, set **`HELIX_BACKEND_ORIGIN`** = `https://<service>.onrender.com` (no `/api` suffix) and **redeploy**. Leave **`VITE_API_BASE` unset** so the UI uses same-origin `/api` (proxied by `middleware.js`).
4. *(Alternative)* Set **`VITE_API_BASE`** = `https://<service>.onrender.com/api` instead of using the proxy; then ensure the Render API allows your Vercel origin (**`HELIX_CORS_ORIGIN_REGEX`** is already set in root `render.yaml` for `*.vercel.app`).

**Demo Link:** you can submit either the **Render** URL (full app in one) or the **Vercel** URL (UI on Vercel, API on Render).
