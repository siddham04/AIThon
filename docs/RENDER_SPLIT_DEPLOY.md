# Render API + Vercel UI (fix “Dockerfile.all-in-one: no such file”)

## Why that error happens

Render log:

```text
open Dockerfile.all-in-one: no such file or directory
```

You set **Root Directory** = `helix-backend` but **Dockerfile Path** = `Dockerfile.all-in-one`.

That file lives at the **repo root**, not inside `helix-backend/`. Docker looks for:

`helix-backend/Dockerfile.all-in-one` → missing.

---

## Correct settings (API only on Render)

In **Render → your Web Service → Settings**:

| Field | Value |
|--------|--------|
| **Root Directory** | `helix-backend` |
| **Dockerfile Path** | `Dockerfile` |
| **Health Check Path** | `/api/health` |

**Not** `Dockerfile.all-in-one` for this layout.

Save → **Manual Deploy**.

---

## Or use the API Blueprint

1. Render → **New** → **Blueprint**
2. Repo: `siddham04/AIThon`, branch `main`
3. Select **`render-api.yaml`** (not `render.yaml`)
4. Apply

Service name defaults to `helix-api`.

---

## Vercel (unchanged)

| Key | Value |
|-----|--------|
| `HELIX_BACKEND_ORIGIN` | `https://<your-render-service>.onrender.com` |

Redeploy Vercel. Test `https://<app>.vercel.app/api/health`.

---

## All-in-one on Render (UI + API one URL)

Only if you have enough build RAM (Starter+):

| Field | Value |
|--------|--------|
| **Root Directory** | *(empty)* |
| **Dockerfile Path** | `Dockerfile.all-in-one` |

---

## Verify

- Render: `https://<service>.onrender.com/api/health` → JSON
- Vercel: `https://<app>.vercel.app/` → UI
- Vercel: `https://<app>.vercel.app/api/health` → JSON
