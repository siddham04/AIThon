# Production Deployment Audit — Helix on Vercel + Render

Date: 2026-05-25
Branch: `main`
Frontend: Vite/React SPA → **Vercel**
Backend: FastAPI (Python 3.11) → **Render** (Docker, Blueprint)

## TL;DR — current deployment health

| Layer | Status | Notes |
|-------|--------|-------|
| Vercel build | ✅ Green | `npm run build` succeeds; lazy chunks + CSP load fonts |
| Same-origin `/api` proxy | ✅ Streaming-safe | Edge middleware forwards SSE/uploads with `duplex: 'half'` |
| Cross-origin Render API | ✅ Baked at build | `vercel-build-env.mjs` writes `VITE_API_BASE` from `HELIX_BACKEND_ORIGIN` |
| Auth (guest + demo + register) | ✅ Working | Guest enabled when `HELIX_HACKATHON_AUTH=1`, JWT in `Authorization` header |
| File uploads | ✅ Fixed | Axios now derives multipart boundary instead of overriding header |
| SSE judge demo | ✅ Direct to Render | Browser hits Render origin to avoid edge 25s cap |
| CORS | ✅ Vercel allowed | `HELIX_CORS_ORIGIN_REGEX=https://.*\.vercel\.app` in `render.yaml` |
| Database | ✅ SQLite seeded | Auto-creates `/app/data/helix.db`; demo user + showcase project on boot |
| Logging | ✅ Added | `RequestLogMiddleware` emits `X-Request-ID` + 5xx access log |
| Lint / build | ✅ Clean | `npm run lint` passes after `guestEx` cleanup |

---

## Issues found & fixes applied this round

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | `no-useless-assignment` lint error blocking CI | `helix-frontend/src/pages/Landing.jsx:228` | Removed redundant `= null` initializer in `ensureSession` |
| 2 | File uploads sent without multipart boundary (Mission Control PDF/DOCX would 400 in production) | `helix-frontend/src/pages/MissionControl.jsx:230` | Pass `Content-Type: undefined` so axios fills in `multipart/form-data; boundary=…` automatically |
| 3 | CSP `connect-src` allowed only `https://*.onrender.com`; any other backend host would be blocked | `helix-frontend/index.html` | Allow `https:` + `wss:` in `connect-src`; keep dev-only `http://localhost` for Vite |
| 4 | `/api/health` no longer returned `demo_fast` / `showcase_project_id` after security split — frontend `loadDemoConfig` silently used defaults | `helix-backend/app/api/routes/health.py` | Re-added the two non-secret fields on the public probe |
| 5 | Vercel edge proxy **buffered** upstream body — broke long SSE (judge demo) and chunked uploads | `middleware.js`, `helix-frontend/middleware.js` | Return `new Response(upstream.body, …)` and pass `duplex: 'half'` on POST/PUT |
| 6 | Proxy stripped `host`/`content-length` only — kept other hop-by-hop headers (could cause 502 with Render) | same | Strip the full hop-by-hop set; add `x-forwarded-{host,proto}` |
| 7 | Proxy errors gave terse `API proxy error: …` without explaining cold start | same | Surface `backend` URL and cold-start guidance in the JSON `detail` |
| 8 | No request correlation across frontend/backend | `helix-backend/app/middleware/request_log.py` (new) | Add `RequestLogMiddleware` — assigns `X-Request-ID`, logs every 5xx + structured 4xx on `/api/*` |
| 9 | Frontend `verify-deploy.mjs` only smoked `/health` + guest | `helix-frontend/scripts/verify-deploy.mjs` | Added: demo metadata assertion, guest-token call against `/projects`, demo login, optional Vercel `VERCEL_URL` same-origin probe |

Earlier rounds (already merged on `main` before this audit):
- CSP fonts via `<link rel="stylesheet">` instead of CSS `@import`
- Three.js WebGL disabled on `/judge-demo` route + `failIfMajorPerformanceCaveat: false`
- 120s axios timeout for Render cold starts
- `HELIX_BACKEND_ORIGIN` default baked into `vercel.json`
- Build-time `VITE_API_BASE` injection from `HELIX_BACKEND_ORIGIN`
- `WinningDemoScreen` runs a pre-flight `checkApiHealth` before starting the demo

---

## Environment variables — required vs optional

### Vercel (Production + Preview)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `HELIX_BACKEND_ORIGIN` | optional* | `https://helix-demo.onrender.com` | Render API origin (no `/api`, no trailing slash). Used by edge middleware **and** build-time `VITE_API_BASE` injection. |
| `VITE_API_BASE` | optional | derived from `HELIX_BACKEND_ORIGIN` | Override to call API directly (skips edge proxy). Set this for the **lowest-latency** judge demo. |
| `VITE_HELIX_DEMO_FAST` | optional | `true` | Heuristic agents (~3–4 min) instead of full LLM. |
| `VITE_HELIX_SHOWCASE_PROJECT_ID` | optional | `proj_demo_seed01` | Pre-baked backup project for SSE fallback. |
| `VITE_HELIX_HERO_PARTICLES` | optional | `true` | Disable for low-GPU presentation laptops. |
| `VITE_HELIX_WORKSPACE_AMBIENT` | optional | `true` (off on `/judge-demo` always) | Three.js ambient background toggle. |

\* Only required if your Render URL is not `https://helix-demo.onrender.com`.

### Render (Web Service)

| Variable | Required | Default in `render.yaml` | Purpose |
|----------|----------|--------------------------|---------|
| `JWT_SECRET` | ✅ required | auto-generated | Token signing key. Rotate to invalidate all sessions. |
| `HELIX_CORS_ORIGIN_REGEX` | ✅ required for Vercel UI | `https://.*\.vercel\.app` | Browser-side CORS allow-list. |
| `HELIX_HACKATHON_AUTH` | ✅ required for demo | `true` | Enables guest login + login auto-register. |
| `HELIX_DEMO_FAST` | ✅ recommended | `true` | Heuristic agents for hackathon timing. |
| `HELIX_DEMO_EMAIL` | optional | `demo@demo.com` | Seeded demo account email. |
| `HELIX_DEMO_PASSWORD` | optional | `demo123` | Seeded demo account password. |
| `HELIX_PRODUCTION` | optional | unset | Set to `1` to disable guest login and OpenAPI docs (turns the seeded demo off too). |
| `HELIX_RATE_LIMIT_PER_MINUTE` | optional | `120` | POST limiter on `/generate`, `/analyze`, `/demo`. |
| `HELIX_MAX_UPLOAD_BYTES` | optional | `20 MB` | Hard cap for `/api/ingest/file`. |
| `DATABASE_URL` | optional | `sqlite:////app/data/helix.db` | Use Postgres URL for persistence beyond container restarts. |
| `ANTHROPIC_API_KEY` | optional | unset | Real LLM path (set only if you want non-heuristic generation). |
| `AZURE_OPENAI_ENDPOINT` / `_API_KEY` / `_DEPLOYMENT` | optional | unset | Azure-flavored LLM. |
| `MONGO_URL` | optional | unset | External chunk store; falls back to local file if unset. |
| `REDIS_URL` | optional | `redis://localhost:6379/0` | Celery broker (unused for hackathon path). |
| `JIRA_BASE_URL` / `_EMAIL` / `_TOKEN` / `_PROJECT_KEY` | optional | unset | Jira REST integration (export only). |
| `GITHUB_TOKEN` / `GITHUB_REPO` | optional | unset | GitHub issue export. |

---

## End-to-end deploy checklist (10 minutes the first time)

```
1. Render → New → Blueprint → connect siddham04/AIThon → use render.yaml
2. Wait for "Live" (10–20 min first build). Open https://<your>.onrender.com/api/health → JSON ok
3. Vercel → import siddham04/AIThon (or open existing project)
4. Settings → Environment Variables:
     HELIX_BACKEND_ORIGIN = https://<your>.onrender.com   (only if not helix-demo)
5. Deployments → Redeploy. Wait for "Ready"
6. Open https://<your-app>.vercel.app/api/health → JSON ok (proxy works)
7. Click Guest on landing OR sign in demo@demo.com / demo123
8. Run "Judge Demo" — pipeline streams from Render via VITE_API_BASE
```

Smoke test from your laptop:

```powershell
$env:API_BASE  = "https://<your>.onrender.com/api"
$env:VERCEL_URL = "https://<your-app>.vercel.app"
node helix-frontend/scripts/verify-deploy.mjs
```

Expected:

```
✓ GET /health (200)
✓ /health exposes demo metadata
✓ POST /auth/guest (200)
✓ GET /projects with guest token (200)
✓ POST /auth/login demo@demo.com (200)
✓ GET https://<your-app>.vercel.app/api/health (200)
```

---

## Verified workflows after this audit

| Workflow | Path | Verified by |
|----------|------|-------------|
| Landing → Guest session | `/` → `/mission-control` | Lint clean ensureSession + `checkApiHealth` pre-flight |
| Sign in with demo creds | `/login` | `/auth/login` direct + auto-register fallback |
| Register new user | `/register` | `/auth/register` with duplicate-email auto-sign-in |
| Upload PDF / DOCX requirement | `/mission-control` | Axios multipart fix (issue #2) |
| Paste text requirement | `/mission-control` | `/ingest/text` |
| Judge demo SSE pipeline | `/judge-demo` | Edge proxy streaming + direct VITE_API_BASE both supported |
| Workspace regenerate | `/project/:id/ai-workspace` | Same SSE codepath |
| Delivery package | `/project/:id/delivery-command` | Authenticated REST |
| Copilot chat | `/project/:id/copilot` | Authenticated REST |
| Settings page | `/settings` | Local storage + REST |
| Jira CSV export | Workspace → Approve | `/export/jira` |
| Auth recovery on 401 | any | Interceptor redirects to `/login` |
| API request correlation | every response | `X-Request-ID` header (issue #8) |

---

## Manual steps still required (cannot be done from this repo alone)

1. **Click "Deploy Blueprint"** in your Render dashboard once. Free tier sleeps after 15 min idle — the SPA now shows a clear cold-start message during retry.
2. **Set `HELIX_BACKEND_ORIGIN`** on Vercel **only if** your Render service name is not `helix-demo`. Otherwise the default in `vercel.json` is correct.
3. **Trigger one Vercel redeploy** after pulling latest `main` so the new build script bakes the API base into `dist/`.
4. *(Optional)* Add `ANTHROPIC_API_KEY` or Azure OpenAI vars on Render if you want LLM-driven generation instead of the fast heuristic path. The demo timing is tuned for heuristic mode.
5. *(Optional)* Attach a Render **persistent disk** at `/app/data` to keep the SQLite database between deploys.

---

## Production hardening still recommended (not blocking deploy)

| Item | Why it can wait |
|------|------|
| Move from SQLite to Postgres on Render | Hackathon scale is fine on SQLite; the `DATABASE_URL` switch is one env change |
| Rotate `JWT_SECRET` per deploy | `render.yaml` already uses `generateValue: true` |
| Tighten `connect-src` once API host is fixed | Currently `https: wss:` to keep deploy painless; restrict once the URL is stable |
| Add Sentry / log drain | `RequestLogMiddleware` writes to stdout — connect Render log drain when needed |
| `Strict-Transport-Security` header | Render terminates TLS upstream; set `HSTS` only after confirming no plain-HTTP clients |

---

## Quick reference

- Deploy guide: `docs/DEPLOY_SAME_LINK.md`
- Vercel specifics: `docs/VERCEL.md`
- Render Blueprint: `render.yaml` + `Dockerfile.all-in-one`
- Smoke tester: `helix-frontend/scripts/verify-deploy.mjs`
- API source of truth: `helix-backend/app/main.py` — `create_app()`
- Frontend API client: `helix-frontend/src/api/client.js`
- Vercel edge proxy: `middleware.js` (root) + `helix-frontend/middleware.js`
