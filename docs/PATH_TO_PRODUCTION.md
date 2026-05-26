# Helix — Path to Production

> **The one-page production roadmap.** Helix is a hackathon-grade demo
> today: Docker Compose, in-process FAISS, single-tenant, demo-mode
> fallbacks. This document is the **concrete, code-level** plan to take
> the same architecture from "judges can click through it" to "a
> regulated engineering team can ship on it" — without rewriting the
> agent layer.

**Companion docs:**
[`README.md`](../README.md) · [`ARCHITECTURE.md`](../ARCHITECTURE.md) ·
[`docs/WORKFLOW.md`](WORKFLOW.md) ·
[`docs/PHASE7_SECURITY_REVIEW.md`](PHASE7_SECURITY_REVIEW.md) ·
[`docs/PHASE8_PERFORMANCE_REVIEW.md`](PHASE8_PERFORMANCE_REVIEW.md)

---

## 1. Maturity stages

| Stage | Today | Pilot (1–2 teams) | Production (org-wide) |
|---|---|---|---|
| **Auth** | JWT + guest mode | JWT + SSO (OIDC) | SSO + SCIM provisioning + service accounts |
| **Tenancy** | Single-tenant (per-user projects) | Per-team row-level isolation | Per-tenant DB schema + per-tenant RAG namespace |
| **Vector store** | In-process FAISS | Postgres `pgvector` (already alongside Postgres) | Pinecone / Weaviate / Qdrant managed cluster |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` on CPU | Same model on GPU (A10G) for batch | Provider embeddings (Azure `text-embedding-3-large`) + cached |
| **LLM** | Azure OpenAI `o3` (single provider) + clause-grounded mock + heuristic guarantors — see [`GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md) | Add second provider (Anthropic Claude or Bedrock) behind the existing `AIService` pluggable boundary; per-project budget caps | Multi-region failover (Azure ↔ Anthropic ↔ self-hosted Llama on vLLM) with policy router |
| **Compute** | `uvicorn --reload` | Gunicorn + Uvicorn workers behind ALB | Kubernetes (HPA on CPU + RPS) + Celery autoscaling |
| **Data** | SQLite fallback / single Postgres | Postgres HA (primary + standby) | Postgres HA + read replicas + nightly logical backups |
| **Job runtime** | FastAPI `BackgroundTasks` or Celery+Redis | Celery + Redis Sentinel | Celery + Redis Cluster + dead-letter queues |
| **Observability** | Loguru → stdout | OpenTelemetry → Datadog / Honeycomb | OTEL + SLO dashboards + alerting (PagerDuty) |
| **Secrets** | `.env` files | Vault / Doppler / AWS SM | KMS-backed secret rotation + short-lived tokens |
| **Network** | localhost / `docker compose` | Single VPC, ALB, WAF | Multi-AZ VPC, private subnets, mTLS service-to-service |

---

## 2. Concrete upgrade paths

### 2.1 Vector store: FAISS → pgvector → managed

**Today.** `helix-backend/app/services/rag_service.py` builds per-project FAISS indexes in process. Restart loses the index; multi-pod deploys can't share.

**Pilot — pgvector (1 day's work).**

- Add Postgres `CREATE EXTENSION vector;` migration.
- Replace `IndexFlatIP` with `pgvector` column on a new `clause_embeddings(project_id, clause_id, embedding vector(384))` table.
- `cosine_distance` query via SQLAlchemy; rerank top-k in Python (same logic).
- Add HNSW index: `CREATE INDEX ON clause_embeddings USING hnsw (embedding vector_cosine_ops);`.
- Zero change to agent code — `rag_service.search(project_id, query)` keeps the same signature.

**Production — managed (Pinecone / Weaviate / Qdrant).**

- One-namespace-per-tenant for hard isolation.
- Async ingest via Celery (already wired): on new clauses, enqueue `embed_and_upsert(project_id, clause_ids)`.
- Replace direct embedding generation with batched calls to a GPU pool (see §2.2).
- Add periodic re-embedding on model upgrades (`embedding_version` column).

### 2.2 Embeddings: CPU → GPU pool → provider

**Today.** `sentence-transformers/all-MiniLM-L6-v2` loaded in-process; CPU is fine for demo (<100ms/clause).

**Pilot.** Move embedding into a dedicated Celery worker pool with one A10G GPU; batch 32 clauses per call → ~10× throughput. Bound concurrent batches by GPU memory.

**Production.** Switch to Azure `text-embedding-3-large` (or AWS Bedrock Titan-Embed) for higher-quality retrieval. Cache embeddings per `(model_id, clause_hash)` in Redis with 30-day TTL. Reserve self-hosted MiniLM as offline-safety fallback (the same code path Helix already uses for demo mode).

### 2.3 LLM routing: single provider + 3-tier resilience → multi-provider policy router

**Today.** Single live provider — **Azure OpenAI** (`o3`, JSON mode) — wired through `helix-backend/app/services/llm.py` (`chat_json_with_fallback`) and `helix-backend/app/services/ai_service.py` (`AIService` — streaming, retries, artifact JSON). The **resilience comes from the 3-tier fallback chain**: Azure → clause-grounded mock (`mock_agents.synthetic_json`) → heuristic guarantors (`_heuristic_tasks_from_stories`, `_ensure_project_tasks`). Every artifact still carries `source_clause_ids` regardless of which tier produced it. This is the contract that the CI-gated golden-pipeline test enforces on every push.

**Pilot — add a second live provider.** The pluggable boundary is already in place — `AIService` is the only class that talks to a provider, so adding Anthropic Claude (or Bedrock) is a one-class change behind a `pick_provider()` policy router in front of `chat_json_with_fallback`:

```python
# pseudo-code, drop-in for existing call sites
provider = pick_provider(
    agent_name,
    cost_budget_remaining_usd,
    latency_budget_ms,
    region,
)
```

Rules:

- Per-project monthly budget cap (Postgres column).
- Latency budget per agent — falls back from the preferred provider to the alternate when P95 > target; final fallback stays the deterministic mock.
- Regional pinning (EU project → EU endpoint only) for data residency.

**Production.** Add a third option: **self-hosted Llama-3-70B-Instruct** on vLLM (one A100 / 4× L40S node) for cost-sensitive agents (Quality Scorer, Review Board) where JSON quality is sufficient. Keep Claude / o3 for ambiguity / tests where reasoning matters. Same `pick_provider()` chooses between all three — and the Tier 2/3 mock + heuristic chain stays underneath as the unembarrassable last resort.

### 2.4 Multi-tenancy & RBAC

**Today.** Single Postgres database, `owner_id` column on `ProjectRecord`. Guest mode permitted. JWT issued with `HELIX_ALLOW_INSECURE_JWT=1` in dev.

**Pilot.**

1. Disable guest in `HELIX_PRODUCTION=1` mode (already supported — see `helix-backend/run.ps1`).
2. Add `tenant_id` column to every owned table; introduce row-level security: `CREATE POLICY tenant_isolation ON projects USING (tenant_id = current_setting('app.tenant_id')::uuid);`
3. JWT carries `tenant_id` and `roles[]`; FastAPI dependency `get_current_user` sets the session var per request.
4. Roles: `viewer` (read), `editor` (PATCH approval), `admin` (project create/delete), `exporter` (export endpoints), `auditor` (read-only across tenant).

**Production.**

- SCIM 2.0 for IdP-driven user lifecycle (Okta / Azure AD / Google).
- Per-tenant Postgres schema **or** dedicated cluster for the top tier — Helix already separates `pipeline_json` from normalized rows, so per-tenant schema is cheap.
- Per-tenant RAG namespace (see §2.1).
- Audit log table: every `PATCH /api/artifacts/*`, every export, every chat message. Append-only, separate retention.

### 2.5 Job runtime: BackgroundTasks → Celery → Kubernetes

**Today.** FastAPI `BackgroundTasks` for short jobs; Celery+Redis already wired for `/api/demo/{id}/run` long pipeline. Single Uvicorn process.

**Pilot.**

- Gunicorn + 4× Uvicorn workers behind ALB.
- Celery worker pool on a separate ASG, scaled by Redis queue depth.
- Redis Sentinel for HA.
- HPA based on CPU + custom metric `helix_pipeline_active_runs`.

**Production.**

- Kubernetes with separate Deployments for API, Celery worker, embedding worker (GPU node selector).
- Dead-letter queue for failed pipeline steps; per-step retry budget configurable via `_STEP_RUNNERS` metadata (Helix already returns `error` events without aborting — promote those to retry candidates).
- Graceful drain on rolling deploy (Celery `--soft-time-limit`).

### 2.6 Observability & SLOs

**Today.** Structured logs (Loguru) to stdout; `GET /api/health` checks providers and DB.

**Pilot — OpenTelemetry from day 1.**

- Auto-instrument FastAPI, SQLAlchemy, Redis, httpx.
- Span per agent step (use existing `step_id` from `demo_orchestrator`).
- Export to Datadog / Honeycomb / Tempo.

**Production — explicit SLOs (target / threshold / window):**

| SLO | Target | Window | Action on miss |
|---|---|---|---|
| `/api/health` availability | 99.9% | 28d | Page on-call |
| `/api/ingest/*` P95 latency | < 2s | 7d | Investigate; scale up |
| `/api/demo/{id}/run` E2E P95 (with `HELIX_DEMO_FAST=true`) | < 60s | 7d | Investigate orchestrator/worker contention |
| `/api/demo/{id}/run` E2E P95 (live LLM) | < 8 min | 7d | Investigate LLM provider; consider router fallback |
| Pipeline success rate | > 99% | 28d | DLQ inspection + provider failover |
| Citation coverage (`citation_item_rate`) | > 0.9 | per run | Flag in UI; block export if < 0.5 |
| Cost per pipeline run | < $0.50 (mock) / $5 (live) | 7d | Review router policy |

### 2.7 Security & compliance hardening

**Already in code:**

- `helix-backend/app/services/sensitive_scan.py` — ingest-time PII / secret-shape hints surfaced before analyze.
- `helix-backend/app/services/export_filter.py` — `approved_for_export` flag + `?approved_only=true` filter for governed export.
- Rate limiting (`HELIX_RATE_LIMIT_PER_MINUTE`).
- JWT rotation (`POST /api/auth/refresh`).
- Generate/analyze routes require auth.

**Pilot adds:**

- CSP / HSTS headers (Nginx).
- Per-tenant secret encryption at rest (KMS).
- Output guardrails on chat: redact `sensitive_hints` matches from streamed responses.
- Differential prompt logging — log prompts, **never** log LLM-returned PII without redaction.

**Production adds:**

- SOC 2 Type II controls: change management, access reviews, incident response runbook.
- Data residency: per-tenant region pinning enforced in router (§2.3) **and** RAG namespace (§2.1).
- Penetration test before each major release; dependency scanning (Snyk / Dependabot) gated in CI.
- BYOK option for top-tier customers (their KMS key wraps row-level encryption keys).

---

## 3. Cost model (back-of-envelope)

Per pipeline run (one requirement → 11-step demo, live LLM path):

| Stage | Model | ~Tokens in / out | Cost @ Azure o3 |
|---|---|---|---|
| Quality | o3 JSON | 4k / 1k | ~$0.05 |
| Review (×5) | o3 JSON | 5 × (3k / 0.5k) | ~$0.15 |
| Ambiguity + Risk | o3 JSON | 5k / 1k | ~$0.05–0.10 |
| Stories (Analyst → PM → Scrum) | o3 JSON × 3 | 15k / 4k | ~$0.30 |
| Architecture | o3 JSON | 4k / 1k | ~$0.05 |
| Effort + Sprint | o3 JSON | 4k / 1k | ~$0.05 |
| APIs | o3 JSON | 3k / 1k | ~$0.04 |
| Tests | o3 JSON | 5k / 2k | ~$0.10 |
| Jira backlog | o3 JSON | 3k / 1k | ~$0.04 |
| Readiness + Defects + PRD | o3 JSON | 5k / 2k | ~$0.08 |
| **Total** | | | **~$0.90–$1.20 / run** |

Compare to ~$300 in engineer-time for the manual baseline (4 hr × $75/hr loaded engineer rate). Even at 100 runs/day per team, infrastructure spend is **dominated by LLM tokens**, not compute — which is exactly the cost surface the policy router (§2.3) is built to optimize.

Mock-mode runs (`HELIX_DEMO_FAST=true`, no provider calls) cost **$0** in tokens and serve as the green-path baseline.

---

## 4. Migration order (no big-bang rewrites)

1. **Week 1.** OpenTelemetry instrumentation (zero behavior change, immediate visibility).
2. **Week 2.** pgvector migration (§2.1 pilot) + retire in-process FAISS for prod path. Keep FAISS as the offline-mode fallback.
3. **Week 3.** Disable guest, add SSO (`HELIX_PRODUCTION=1` already gates this) + tenant_id column + RLS policy.
4. **Week 4.** Policy router (§2.3) with cost caps; ship the first live pilot.
5. **Week 5–6.** Kubernetes deploy, dead-letter queue, SLO dashboards, output guardrails.
6. **Week 7+.** SOC 2 prep, BYOK, region pinning, scale-out.

Every step is **additive** — the demo path (`scripts/judge_demo.ps1`) keeps working unchanged at every stage. That is the entire point of the demo-mode/live-mode split in the existing codebase.
