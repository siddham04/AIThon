# Helix — Deploy to Render + Vercel (the manual quickstart)

> **You'll do this once.** ~15 minutes end-to-end if you follow the
> order below. Render hosts the FastAPI backend; Vercel hosts the
> React SPA; both read the GitHub repo directly. The single demo URL
> you'll submit is the Vercel one — Vercel's edge `middleware.js`
> proxies `/api/*` to Render so you get same-origin auth + SSE.

**Companion docs:** [`docs/DEMO_HOSTING.md`](DEMO_HOSTING.md) *(the
3-option overview)* · [`docs/VERCEL.md`](VERCEL.md) *(deep dive on
Vercel paths A vs B)* · [`docs/RENDER_SPLIT_DEPLOY.md`](RENDER_SPLIT_DEPLOY.md)
*(Render API-only blueprint)* · [`docs/DEPLOY_SAME_LINK.md`](DEPLOY_SAME_LINK.md)
*(keep an existing `*.vercel.app` URL)* · [`docs/GITHUB_DEPLOY.md`](GITHUB_DEPLOY.md)
*(secrets / GitHub Actions side)* · [`docs/JUDGE_MODE.md`](JUDGE_MODE.md)
*(post-deploy smoke + recovery)*.

---

## What's already in the repo (you don't need to author any of this)

| File | What it does |
|---|---|
| `render.yaml` | Render Blueprint — one Web service, Docker runtime, Free plan, `/api/health` healthcheck, JWT auto-generated, CORS pre-allowed for `*.vercel.app`, mock mode by default |
| `Dockerfile.all-in-one` | Multi-stage build: builds React with Vite → copies `dist` to `/app/static` → runs uvicorn that serves both `/api/*` and the SPA |
| `deploy/all-in-one/entrypoint.sh` | Seeds the demo user + showcase project, then `exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"` (Render injects `PORT` at runtime) |
| `vercel.json` *(repo root)* | Build cmd `npm run build --prefix helix-frontend`, output `helix-frontend/dist`, SPA rewrites, default `HELIX_BACKEND_ORIGIN=https://helix-demo.onrender.com` |
| `helix-frontend/vercel.json` | Same config but for when Vercel's Root Directory is set to `helix-frontend/` |
| `middleware.js` *(repo root + `helix-frontend/middleware.js`)* | Edge proxy — forwards `/api/*` from your Vercel hostname to `HELIX_BACKEND_ORIGIN` |
| `helix-backend/Dockerfile` | API-only image (for `docs/RENDER_SPLIT_DEPLOY.md` route) |
| `helix-frontend/Dockerfile` | UI-only image (rarely used; we deploy the UI on Vercel) |

---

## Step 1 — Push to GitHub (you may have already done this)

```powershell
git status                         # confirm you have changes to push
git push origin main               # both Render and Vercel watch this branch
```

> If you haven't connected the repo yet: the repo URL pattern is
> `https://github.com/<your-user>/AIThon`. Vercel and Render both
> auto-detect on branch push.

---

## Render Free-tier guarantee — no memory or build OOM

The default build is **slim-install safe** for Render Free (512 MB RAM,
~25 min build budget). Both `Dockerfile.all-in-one` and
`helix-backend/Dockerfile` default to `REQUIREMENTS_FILE=requirements-render.txt`
— which drops the four heavy ML wheels that historically OOM Render
Free builds:

| Dropped from slim install | Wheel size | Where it's used | Behaviour when missing |
|---|---|---|---|
| `sentence-transformers` (+ PyTorch) | ~200 MB | `rag_service` semantic search | Returns empty list — agents fall back to clause-id grounding from `project.source_clauses` |
| `spacy` (+ `en_core_web_sm`) | ~100 MB | `nlp_service.detect_ambiguities` (passive voice, vague tokens) | Heuristic regex path takes over |
| `scikit-learn` (+ `scipy`) | ~110 MB | `ml_insights` anomaly + similarity | Heuristic scoring takes over |
| `faiss-cpu` | ~50 MB | RAG index | Returns empty list (paired with sentence-transformers gate) |

**Total saving: ~460 MB during build, ~250 MB at runtime.**

Every one of these deps is **lazily imported inside a try/except** —
the application boots cleanly even when none are installed, and the
golden + adversarial test suite (28/28 green) covers the exact code
paths Render hits. The slim build is the **same code Render Free has
been running successfully**; this just makes the install configuration
explicit and reproducible.

**Need the full ML stack?** Two options:

1. **Render Starter or larger** (1 GB+ RAM) — in the dashboard, set
   build arg `REQUIREMENTS_FILE=requirements.txt`. Save → Manual
   Deploy → Clear cache & deploy.
2. **Locally for development** — `pip install -r requirements.txt`
   continues to install everything for local dev / CI / tests.

---

## Step 2 — Deploy backend to Render (~10 min cold first deploy)

1. Open https://dashboard.render.com/ → **New** → **Blueprint**.
2. **Connect** the GitHub repo, pick branch **`main`**.
3. Render reads root `render.yaml` and offers to create the service
   **`helix-demo`** with the **`Dockerfile.all-in-one`** runtime. Approve.
4. **Region:** `oregon` (default — change if you want closer latency).
5. **Plan:** `free` (default — sleeps after 15 min idle, ~30–60s cold start).
6. Click **Apply**. First build = ~10 min (Python + spaCy + frontend build).
7. When the build is green, copy the service URL — e.g.
   `https://helix-demo.onrender.com`.

### Smoke checks (run these before you go to Step 3)

```powershell
# 1. Health endpoint returns JSON
curl https://helix-demo.onrender.com/api/health
# Expect: {"status":"ok","version":"...","demo_fast":true,...}

# 2. Seeded showcase project exists
curl https://helix-demo.onrender.com/api/projects/proj_demo_seed01
# Expect: HTTP 401 (auth-protected) — that's correct, just not 404 / 500

# 3. Demo login works
curl -X POST https://helix-demo.onrender.com/api/auth/login `
     -H "Content-Type: application/json" `
     -d '{"email":"demo@demo.com","password":"demo123"}'
# Expect: {"token":"eyJ...","user":{...}}
```

If any check fails, click into the Render service → **Logs** tab and
look for the seed step (`Seeding demo user…` / `Showcase project ready`).

### Optional — turn on the live LLM tier

The default deploy runs **Tier 2 mock + Tier 3 heuristics** — that's
the offline-safe path the demo is built around (see
[`docs/NOVELTY.md`](NOVELTY.md) pillar 3). To enable Tier 1 (live Azure
OpenAI), add these in the Render dashboard → service → **Environment**
(do **not** put real keys in `render.yaml`):

```text
AZURE_OPENAI_ENDPOINT       = https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY        = <your key>
AZURE_OPENAI_DEPLOYMENT     = o3
AZURE_OPENAI_API_VERSION    = 2024-12-01-preview
HELIX_USE_AI                = true        # flip from default false
```

Save → **Manual Deploy** → **Clear build cache & deploy** so the new
env takes effect. *(You don't have to do this for the demo — mock mode
is already CI-validated by the golden-pipeline contract.)*

---

## Step 3 — Deploy frontend to Vercel (~3 min)

1. Open https://vercel.com/new and **Import** the same GitHub repo.
2. **Root Directory:** leave **empty** (root) — `vercel.json` at the
   repo root handles the build. *(Or set it to `helix-frontend/` —
   `helix-frontend/vercel.json` works either way.)*
3. **Framework:** `Other` / `Vite` (auto-detected; pinned by `vercel.json`).
4. **Environment Variables** — Production **AND** Preview:

   | Key | Value |
   |---|---|
   | `HELIX_BACKEND_ORIGIN` | Your Render URL from Step 2 — **no `/api` suffix, no trailing slash** (e.g. `https://helix-demo.onrender.com`) |
   | `VITE_HELIX_DEMO_FAST` | `true` *(skips slow LLM defaults in the UI)* |

   > **Don't set `VITE_API_BASE`.** Leaving it unset is what makes
   > Vercel's edge `middleware.js` proxy `/api/*` calls to Render —
   > one demo URL, same-origin auth + SSE.

5. Click **Deploy**. First build ≈ 2 min (Vite + bundling Three.js,
   GSAP, Mermaid).
6. When green, copy the production URL — e.g.
   `https://ai-thon.vercel.app`.

### Smoke checks (the demo readiness gate)

```powershell
# Replace <vercel> with your Vercel URL and <render> with your Render URL.
$vercel = "https://<vercel>.vercel.app"

# 1. SPA loads
curl -I $vercel
# Expect: HTTP/2 200 with text/html

# 2. /api proxy works — should return JSON, not HTML
curl $vercel/api/health
# Expect: {"status":"ok",...}  (proxied by middleware.js → Render)

# 3. Demo login through the proxy
curl -X POST $vercel/api/auth/login `
     -H "Content-Type: application/json" `
     -d '{"email":"demo@demo.com","password":"demo123"}'
# Expect: {"token":"eyJ...","user":{...}}

# 4. Open the seeded showcase in a browser
start $vercel/project/proj_demo_seed01/ai-workspace
# Expect: populated Delivery Package within ~3 s (NOT the empty state)
```

If `/api/health` returns the React HTML instead of JSON, the edge
proxy didn't pick up `HELIX_BACKEND_ORIGIN` — go back to Vercel
**Settings → Environment Variables**, confirm the env, then
**Deployments → … → Redeploy** (env changes need a fresh deploy).

---

## Step 4 — Pre-stage rehearsal (from [`docs/DEMO_RECOVERY.md`](DEMO_RECOVERY.md))

Run **5 minutes before stage** to confirm all four demo recovery tiers
are green:

```powershell
$vercel = "https://<vercel>.vercel.app"
$render = "https://<render>.onrender.com"

# Tier A — live LLM (only if you turned on Azure in Step 2.optional)
curl "$render/api/health" | findstr ok

# Tier B — mock pipeline via backup bookmark
start "$vercel/project/proj_demo_seed01/ai-workspace"

# Tier C — static screenshot tour (works without anything running)
start "https://github.com/<your-user>/AIThon/blob/main/docs/SCREENSHOT_TOUR.md"

# Tier D — committed sample exports
start "https://github.com/<your-user>/AIThon/tree/main/docs/sample-exports"
```

All four should respond in under 3 s.

---

## Step 4.5 — Production Hardening *(optional, ONLY before public launch — not for the hackathon judging URL)*

The default deploy is configured for **judges**, not paying customers.
Several security gates are intentionally relaxed so judges can register
on the fly, use guest mode, and log in as `demo@demo.com`. If you
keep the same Vercel + Render URL **after** the hackathon and open it
to the public, flip these in the **Render dashboard → Environment**
(do *not* commit them to `render.yaml` — they're per-deploy):

| Env var | Production value | Why |
|---|---|---|
| `HELIX_PRODUCTION` | `1` | Master switch — disables hackathon-auth paths in `app/config.py:259-263`, blocks the default JWT secret, disables `/docs` |
| `HELIX_HACKATHON_AUTH` | `false` | Closes the guest-login path and the auto-register-on-login fallback |
| `HELIX_DEMO_EMAIL` *(remove)* | *(remove from Render env)* | Removes the seeded `demo@demo.com` account on next deploy |
| `HELIX_DEMO_PASSWORD` *(remove)* | *(remove from Render env)* | Same — never leave a known password on a public deploy |
| `HELIX_CORS_ORIGINS` | `https://<your-vercel>.vercel.app` | Replaces the permissive `*.vercel.app` regex |
| `HELIX_CORS_ORIGIN_REGEX` *(remove)* | *(remove from Render env)* | Disable the wildcard — explicit allowlist only |
| `JWT_SECRET` | *(Render auto-generates via `generateValue: true` in `render.yaml`)* | Verify in dashboard → should be a 64-char random string, never the repo default |
| `HELIX_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Shorten from the 7-day default |
| Re-add **registration gating** in code | open `app/api/routes/auth.py:19-36` | Currently registration is always-open; add a `Depends(allow_hackathon_auth)` gate before public launch |

After saving env vars → **Render dashboard → Manual Deploy → Clear
build cache & deploy** so the new env actually takes effect (a normal
redeploy reuses the cached worker).

**Additional pre-public-launch items** (full list with file:line in
[`docs/AUDIT_REPORT.md` §1.2](AUDIT_REPORT.md#12-security-subagent-evidenced)):

- Fix SSRF on URL ingest (`app/services/ingestion_service.py:53-61` — disable redirects or revalidate each hop)
- Switch `/api/export/csv` to `QUOTE_ALL` (the safer `/api/backlog/{id}/jira-csv` path is already correct)
- Add `request.is_disconnected()` checks to SSE routes
- Wrap LLM calls in `asyncio.wait_for(..., 120.0)` to bound hang time
- Tighten password policy from `min_length=1` to a real complexity gate
- Add structured metrics + Prometheus / OpenTelemetry exporter

**For the hackathon judging URL specifically: do none of the above.**
The judges need `demo@demo.com` to work, guest mode to work, and the
showcase project to be seeded. Production hardening happens *after*
you decide to keep the link live for actual users.

---

## Step 5 — What to submit

| Submission field | What to paste |
|---|---|
| **Demo URL** | The Vercel URL — `https://<vercel>.vercel.app` |
| **GitHub URL** | `https://github.com/<your-user>/AIThon` |
| **API health URL** *(if asked)* | `https://<vercel>.vercel.app/api/health` (proxy through Vercel) **or** `https://<render>.onrender.com/api/health` (direct to Render) |
| **Demo credentials** *(if asked)* | `demo@demo.com` / `demo123` *(seeded on backend startup)* |
| **Backup demo path** *(if the form has it)* | `https://<vercel>.vercel.app/project/proj_demo_seed01/ai-workspace` *(opens the populated showcase directly — no SSE needed)* |

---

## Cost — what you'll spend

| Service | Plan | Monthly cost | Notes |
|---|---|---|---|
| **Render Web Service** | Free | **$0** | Sleeps after 15 min idle; ~30–60 s cold start. Fine for judging; upgrade to Starter ($7) if you want always-on. |
| **Vercel Hobby** | Free | **$0** | 100 GB bandwidth, unlimited deploys; no cold start for static SPA. |
| **Azure OpenAI** *(only if you enabled Tier 1)* | Pay-per-call | **~$0.90–$1.20 per pipeline run** | Mock mode = $0. See [`docs/PATH_TO_PRODUCTION.md` §3](PATH_TO_PRODUCTION.md#3-cost-model-back-of-envelope). |
| **TOTAL for the hackathon demo** | | **$0** | Mock-mode default. Live LLM only if you actively turn it on. |

---

## Common pitfalls (and the one-line fix)

| Symptom | Fix |
|---|---|
| Vercel `/api/health` returns HTML | `HELIX_BACKEND_ORIGIN` env not set or not redeployed → Vercel → Settings → Env Vars → add it → Deployments → Redeploy |
| Render service builds but `/api/health` returns 502 | Open Render logs — likely OOM on Free tier from sentence-transformers. `render.yaml` already sets `HELIX_DISABLE_EMBEDDINGS=1` to fix this; confirm it's applied |
| Login returns *"Could not start a guest session"* | The browser is hitting Vercel's SPA instead of the Render API. Same fix as row 1 — confirm `HELIX_BACKEND_ORIGIN` and redeploy Vercel |
| First Vercel build fails on Three.js / Mermaid chunk size | Build succeeds despite the warning — chunks are lazy-loaded. If it actually errors, run `npm ci && npm run build` in `helix-frontend/` locally to reproduce |
| Render cold start kills the live SSE during demo | Open the Vercel URL once before stage (warm the Render worker); or stay on the **backup bookmark** path (Tier B in `DEMO_RECOVERY.md`) which doesn't depend on SSE |
| Showcase project missing on first visit | The seeder runs on container start. Refresh after 30 s, or check Render logs for `Showcase backup ready: proj_demo_seed01` |

---

## When things change — what to redo

| Change | Render | Vercel |
|---|---|---|
| Backend code (`helix-backend/**`) | Auto-redeploy on push to `main` | No action |
| Frontend code (`helix-frontend/**`) | No action | Auto-redeploy on push to `main` |
| Docker base image / system deps | Auto-redeploy (rebuilds layer) | No action |
| `render.yaml` env vars | **Manual: Render → service → Manual Deploy → Clear cache & deploy** | No action |
| `vercel.json` or `middleware.js` | No action | Auto-redeploy on push |
| Add Azure OpenAI keys after first deploy | Add in Render dashboard → save → manual redeploy | No action |
| Change `HELIX_BACKEND_ORIGIN` | No action | Save in Vercel env → Deployments → Redeploy |

---

## What's verified working as of this commit

| Check | How | Status |
|---|---|---|
| Backend golden-pipeline contract | `pytest tests/test_golden_pipeline.py` | **8/8 passed in ~2 s** |
| Frontend lint | `npm run lint` in `helix-frontend/` | Clean |
| Frontend production build | `npm run build` in `helix-frontend/` | `dist/` written in 2.06 s |
| Pitch deck regeneration | `python scripts/build_pitch_deck.py` | `docs/Helix-AI-Thon-Pitch.pptx` written (9 slides) |
| Judge-snapshot Playwright capture | `npx playwright test e2e/judge-snapshot.spec.ts` | 7 screenshots + 2 MB WebM + 5 sample exports written in ~22 s |
| `render.yaml` healthcheck path | `GET /api/health` returns `{"status":"ok"}` | Verified locally |
| Vercel edge proxy | `middleware.js` reads `HELIX_BACKEND_ORIGIN` and rewrites `/api/*` | Verified config |
| Demo recovery 4-tier model | All four tiers documented + reproducible | `docs/DEMO_RECOVERY.md` |

Everything above runs in CI on every PR via
[`.github/workflows/golden-pipeline.yml`](../.github/workflows/golden-pipeline.yml).
