# Helix — Setup & runbook

## One-command startup (Docker)

From the **repository root** (`AI-Thon/`):

```bash
cp .env.example .env
# Edit `.env` and set AZURE_OPENAI_API_KEY (+ AZURE_OPENAI_ENDPOINT and
# AZURE_OPENAI_DEPLOYMENT) for live AI. Leave them blank to run the
# deterministic offline demo path — see docs/GOLDEN_DOMAIN.md.
docker compose up --build
```

Open **http://localhost:5173** — the UI is served by Nginx in the `frontend` container (mapped to host port **5173**). The API is available at **http://localhost:8000** and proxied from the browser as **http://localhost:5173/api/**.

**Demo login (after seed):**

- Email: `demo@demo.com`
- Password: `demo123`

The backend entrypoint runs `helix-backend/scripts/seed.py` on each start; it is **idempotent** (safe to re-run).

### Reset everything (cold start)

```bash
docker compose down -v
docker compose up --build
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_API_KEY` | **Optional** — required only for live LLM generation | Azure OpenAI key. With it: Tier-1 live generation. Without it: Tier-2 clause-grounded mock takes over. See `docs/GOLDEN_DOMAIN.md`. |
| `AZURE_OPENAI_ENDPOINT` | With the key | e.g. `https://your-resource.openai.azure.com` |
| `AZURE_OPENAI_DEPLOYMENT` | With the key | Deployment name (default `o3`) |
| `JWT_SECRET` | Recommended | Secret for signing JWTs (set in `.env` for production demos) |
| `MONGO_URL` | No (defaults in Compose) | Requirement snapshots; stack includes **MongoDB** — Compose defaults to `mongodb://mongo:27017/helix` |
| `POSTGRES_URL` | Same as DB | Accepted as alias for **`DATABASE_URL`** / SQLAlchemy (`helix-backend/app/config.py`) |
| `REDIS_URL` | Optional locally | Compose injects `redis://redis:6379/0` for the backend service |
| `HELIX_USE_CELERY` | No | Set `1` only if you run a Celery worker against Redis |
| `HELIX_DEBUG` | No | Verbose API logging |

Compose injects **`DATABASE_URL`**, **`REDIS_URL`**, and **`MONGO_URL`** for the backend container when using `docker-compose.yml`.

To build a production image from **`helix-frontend/`** (same app as `frontend/`):  
`docker build -f helix-frontend/Dockerfile -t helix-ui helix-frontend`

Optional JIRA REST export (see `helix-backend/app/config.py`): `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`, `JIRA_PROJECT_KEY`, `JIRA_EPIC_LINK_FIELD`.

## Local development (without Docker)

**Backend** (`helix-backend/`):

```bash
cd helix-backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env   # configure DATABASE_URL, REDIS_URL, AZURE_OPENAI_* keys (optional), JWT_SECRET
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (`helix-frontend/` — the only UI tree in this repo):

```bash
cd helix-frontend
npm ci
npm run dev
```

Vite dev server proxies `/api` to **`http://127.0.0.1:8765`** by default (`helix-frontend/vite.config.ts`), matching `helix-backend\run.ps1`. For `uvicorn` on port **8000** instead, set `VITE_API_PROXY_TARGET=http://127.0.0.1:8000` when starting Vite.

**Canonical runbook:** [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

**Manual seed (optional):**

```bash
cd helix-backend   # or run from repo root with PYTHONPATH set to helix-backend
set DATABASE_URL=postgresql://...   # if using Postgres
python scripts/seed.py
```

## Tests & quality

| Scope | Command |
|-------|---------|
| Frontend lint | `cd helix-frontend && npm run lint` |
| Backend | No bundled pytest suite in-tree; use `/docs` interactive API or manual flows |

Health check: `GET http://localhost:8000/api/health`

## Submission checklist (Phase 6)

| Item | Notes |
|------|------|
| **Demo video (~3 min)** | OBS/Loom: upload requirement → AI stream → Kanban → ambiguity → export; show streaming text clearly; end on JIRA export success |
| **Slides (≤7)** | Use `PRESENTATION.md` outline; embed architecture diagram from `ARCHITECTURE.md` |
| **Cold verify** | `docker compose down -v && docker compose up --build` → login demo user → full demo path |
