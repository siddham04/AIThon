# Make your existing Vercel link work (one checklist)

Your **`https://<project>.vercel.app` URL never changes** when you redeploy. Follow this once.

## 1. Render API (required)

1. [Render](https://dashboard.render.com/) → **New** → **Blueprint** → repo **AIThon** → branch **main**
2. Wait until deploy is **Live** (first build ~15–20 min)
3. Open `https://helix-demo.onrender.com/api/health` → JSON with `"status":"ok"`

If your service name is **not** `helix-demo`, copy **your** URL (no `/api`).

## 2. Same Vercel project (do not create a new one)

1. [Vercel](https://vercel.com/) → open the project that owns your hackathon link
2. **Settings → Environment Variables** (Production + Preview):
   - `HELIX_BACKEND_ORIGIN` = `https://helix-demo.onrender.com` (or your Render URL)
   - Only if your Render URL differs from the repo default
3. **Deployments** → latest → **Redeploy** (wait for build to finish)

Repo `vercel.json` already sets defaults; redeploy pulls latest `main`.

## 3. Verify on your link

Replace `<app>` with your hostname:

| Test | Expected |
|------|----------|
| `https://<app>.vercel.app/api/health` | JSON (proxied) |
| Landing → **Guest** or `demo@demo.com` / `demo123` | Enters app |
| **Judge Demo** | Pipeline runs (first API call may take 60s if Render slept) |

## 4. Local dev

```powershell
cd helix-backend; .\run.ps1
cd helix-frontend; npm run dev
```

Open `http://localhost:5173/judge-demo`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 503 HELIX_BACKEND_ORIGIN | Redeploy Vercel; set env to live Render URL |
| Network Error / timeout | Wake Render: open Render `/api/health`, wait 60s, retry |
| Demo stalls | Use **Open backup package** on judge-demo page |
| CORS in console | Redeploy Render from this repo (`HELIX_CORS_ORIGIN_REGEX` in `render.yaml`) |

**Single URL only (no Vercel):** use Render URL from step 1 as your demo link — UI + API together.
