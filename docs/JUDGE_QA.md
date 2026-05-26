# Judge Q&A — honest answers (Helix AI-Thon)

Use this when judges ask “can we pilot this?” or challenge numbers on stage.

## “Your backlog only has stories — where are the tasks?”

**Today:** Every pipeline run calls `finalize_demo_project()` so **≥1 engineering task per story** (heuristic fallback if the LLM returns none). Jira CSV includes **Epic → Story → Task → Sub-task** rows.

**Show:** Delivery Package → Export hub → **Jira CSV preview** (look for `Issue Type = Task`). Or showcase: `/project/proj_demo_seed01/ai-workspace`.

## “The demo took forever on stage.”

**Cause:** Full Azure OpenAI path can run **~3–4+ minutes** per project.

**Mitigation (default now):** `HELIX_DEMO_FAST=true` → heuristic agents (~3–4 min, predictable). **Do not** run cold live LLM during the 5-minute slot unless rehearsed.

**Backup:** Pre-baked `proj_demo_seed01` — package loads in seconds. Bookmark on Judge Demo screen.

## “Is this secure enough to pilot?”

| Control | Status |
|---------|--------|
| JWT on all `/api/*` (except auth + health + demo metadata) | **Shipped** — restart API after deploy |
| WebSocket progress | **JWT query token required** |
| Rate limits | **On** (`HELIX_RATE_LIMIT_PER_MINUTE`, default 120) |
| Default JWT secret | **Dev only** — set `JWT_SECRET` before any public URL; use `HELIX_PRODUCTION=1` to fail startup if still default |
| Open LLM proxy routes | **Closed** (global gate + per-route auth) |

**Pilot roadmap (2–4 weeks):** httpOnly cookies, CSP + Mermaid strict (partial), SSO, audit log, pen test on hosted env.

## “First load felt heavy on my laptop.”

- Three.js hero **off by default** (opt-in via env).
- Landing + product routes **lazy-loaded**; Mermaid/Three in separate chunks.
- Venue tip: open **Judge Demo** once on Wi-Fi before presenting (warms chunks).

## “Why so many screens in the repo?”

**Product path is 5 surfaces:** Judge Demo → Mission Control (optional upload) → AI Workspace → Delivery Command → Copilot (+ Settings).

Legacy experiments live under `helix-frontend/src/pages/_archive/` — **not routed**, not in the judge path.

## “PRD 404 / readiness looked fake.”

- **PRD:** Generated during pipeline; persisted **before** SSE `complete`; lazy-created on `GET /delivery/prd/{id}` if missing.
- **Readiness:** **Gate-based score** (`100 × completed_gates / total`), not a fixed 94%.

## “Mobile looked rough.”

Mission Control uses **horizontal scroll strips** (not page overflow). Collapsed sidebar shows **▶ Demo** badge + tooltip for Judge Demo.

## “How does this scale beyond a hackathon prototype?”

**30-second answer (memorize this):**

> *“Three scale axes, all already planned to **code-level** in
> [`docs/PATH_TO_PRODUCTION.md`](PATH_TO_PRODUCTION.md). **Compute** —
> FastAPI today, **Kubernetes HPA + Celery autoscaling on Redis-queue
> depth** at pilot, GPU node pool for embeddings (~10× throughput on
> one A10G via batch-32). **AI infrastructure** — single Azure
> provider today behind a one-class `AIService` boundary, **policy
> router** at pilot (Azure ↔ Anthropic ↔ self-hosted Llama-3-70B on
> vLLM, with per-tenant cost caps + region pinning). **Storage** —
> in-process FAISS today, **pgvector at pilot, managed
> Pinecone / Weaviate / Qdrant with per-tenant namespaces at
> production.** Every step is **additive** — the demo path
> (`scripts/judge_demo.ps1`) keeps working unchanged at every
> stage. That's the point of the demo-mode/live-mode split.”*

**90-second deep-dive (have these ready):**

| Axis | Today | Pilot (1–2 teams) | Production (org-wide) |
|---|---|---|---|
| **Compute** | `uvicorn --reload`, single process | Gunicorn + 4× Uvicorn workers behind ALB; Celery worker pool on separate ASG, scaled by Redis queue depth; Redis Sentinel for HA | Kubernetes (HPA on CPU + custom metric `helix_pipeline_active_runs`); separate Deployments for API / Celery / embedding worker; dead-letter queue for failed steps |
| **GPU / Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` on CPU (~100 ms/clause) | Dedicated Celery worker pool with **one A10G**; batch 32 clauses/call → **~10× throughput** | Azure `text-embedding-3-large` or Bedrock Titan-Embed; cached per `(model_id, clause_hash)` in Redis with 30-day TTL; self-hosted MiniLM stays as offline fallback |
| **LLM routing** | Azure OpenAI `o3` (single live provider) + 3-tier resilience (Azure → clause-grounded mock → heuristic guarantors) | **`pick_provider(agent, cost_budget, latency_budget, region)`** policy router — adds Anthropic Claude / Bedrock behind the same `AIService` boundary (one-class change); per-project budget caps + EU/US pinning | **Add self-hosted Llama-3-70B-Instruct on vLLM** (one A100 / 4× L40S) for cost-sensitive agents (Quality Scorer, Review Board); keep Claude / o3 for ambiguity / tests; multi-region failover |
| **Vector store** | In-process FAISS (`IndexFlatIP`); per-project | **`CREATE EXTENSION vector;` → `pgvector` HNSW index** (1 day's work — zero change to agent code, `rag_service.search()` keeps the same signature) | Pinecone / Weaviate / Qdrant managed cluster; **per-tenant namespace** for hard isolation; async re-embed on model upgrades |
| **Multi-tenancy** | Single Postgres, `owner_id` column | `tenant_id` column on every owned table + Postgres RLS policy (`CREATE POLICY tenant_isolation USING (tenant_id = current_setting('app.tenant_id')::uuid)`); JWT carries `tenant_id` + `roles[]` | Per-tenant schema or dedicated cluster for top tier; **SSO + SCIM 2.0** (Okta / Azure AD / Google); RBAC roles: `viewer` / `editor` / `admin` / `exporter` / `auditor` |
| **Job runtime** | FastAPI `BackgroundTasks`; Celery+Redis wired for long pipeline runs | Celery worker pool, dead-letter queue per pipeline step | Per-step retry budget configurable via `_STEP_RUNNERS` metadata; graceful drain on rolling deploy |
| **Observability** | Loguru → stdout; `GET /api/health` checks providers + DB | **OpenTelemetry from day 1** (auto-instrument FastAPI, SQLAlchemy, Redis, httpx); span per agent step using existing `step_id` | Explicit SLOs: `/api/health` 99.9% / 28d · pipeline P95 < 60 s mock, < 8 min live · pipeline success > 99% / 28d · citation coverage > 0.9/run · cost < $0.50 mock / $5 live |
| **Security & compliance** | JWT, rate limits, sensitive scan, approve-to-export gate (already shipped — see `helix-backend/app/services/{sensitive_scan,export_filter}.py`) | CSP / HSTS, per-tenant KMS-wrapped secrets, output guardrails on chat, differential prompt logging | **SOC 2 Type II** controls, per-tenant data residency enforced by router + RAG namespace, pen test per major release, **BYOK** (customer KMS wraps row-level encryption keys) |

**Cost model judges can argue with:** ~**$0.90–$1.20 per pipeline
run** at Azure `o3` rates ([`docs/PATH_TO_PRODUCTION.md`](PATH_TO_PRODUCTION.md#3-cost-model-back-of-envelope)).
At 100 runs/day per team, infrastructure spend is **dominated by LLM
tokens**, not compute — which is exactly the cost surface the policy
router is built to optimize. Mock-mode runs cost **$0**.

**Migration order — no big-bang rewrites:**
Week 1 OTel · Week 2 pgvector · Week 3 SSO + tenant RLS · Week 4
policy router + first pilot · Week 5–6 Kubernetes + SLO dashboards ·
Week 7+ SOC 2 / BYOK / region pinning. Source: [`PATH_TO_PRODUCTION.md` §4](PATH_TO_PRODUCTION.md#4-migration-order-no-big-bang-rewrites).

**Why this isn't theoretical:** The provider boundary is **one class
today** (`helix-backend/app/services/ai_service.py`), the RAG layer
already has a signature-compatible swap target (`rag_service.search`
doesn't change), Celery + Redis are already wired for the long
pipeline path, and `HELIX_PRODUCTION=1` already gates guest mode +
default-JWT fail-fast. The roadmap is *additive*, not a rewrite.

## “How does Helix compare to past hackathon winners (RiskWise / Apollo / RouteOpt / OpenCodeReview / WorkWizee)?”

**30-second answer (memorize this):**

> *“All five of those winners proved the same shape: **NL input →
> multi-agent pipeline → structured output → measurable
> productivity win.** RiskWise did it for supply chains, Apollo for
> research, RouteOpt for fleet routing, OpenCodeReview for code
> review, WorkWizee for incident workflows. **Helix does it for the
> SDLC** — and adds the one thing none of them have: **clause-grounded
> provenance** on every artifact (story · task · sub-task · test ·
> risk · ambiguity), validated by a **CI-gated golden-pipeline
> contract** (8 invariants, 2 s, every PR). We're not claiming
> dual-LLM — we're Azure-only today, with the provider boundary
> already a one-class swap (see [`docs/NOVELTY.md`](NOVELTY.md) pillar
> 3 + [`docs/PATH_TO_PRODUCTION.md`](PATH_TO_PRODUCTION.md) §2.3).”*

**The lens that lands well in Q&A:**

| From this winner | What Helix absorbed | The proof in code |
|---|---|---|
| **RiskWise** *(Best Overall, MS Agents Hack)* | Role-typed agents on a high-value vertical wins | 10 single-responsibility agents in `helix-backend/app/agents/` (risk is just one of them) |
| **Apollo** *(Best C#, MS Hack)* | Coordinator-with-sub-agents pattern outperforms one big call | `demo_orchestrator.py` is the coordinator; Phase-2 parallel orchestrator runs `quality+review` and `architecture+effort_sprint` in parallel batches |
| **RouteOpt** *(1st, NVIDIA NeMo Hack)* | NL → structured-output wins when paired with simulation / verification | Same shape — Helix verifies via the CI-gated [golden contract](GOLDEN_DOMAIN.md) (8 invariants, 2.07 s) instead of Omniverse |
| **OpenCodeReview** *(2nd, NVIDIA NeMo Hack)* | Interchangeable LLMs (provider-agnostic) is ship-readiness | `AIService` is **one class**; the `pick_provider()` router is a one-class change ([`PATH_TO_PRODUCTION.md` §2.3](PATH_TO_PRODUCTION.md)); resilience today uses the same boundary for Tier-2 mock + Tier-3 heuristics |
| **WorkWizee** *(Best Copilot, MS Hack)* | Productivity wins are measured against a concrete workflow (~40% off incident management) | Helix targets *requirements → tickets* — **~98% reduction** in upfront SDLC structuring (~4 hr manual → ~4 min mock), reported per-run by `ProductivityMetrics` |

**The conclusion line (use as your closer):**

> *“Apollo, RiskWise, RouteOpt, OpenCodeReview, and WorkWizee each won
> by tackling one clear workflow with agents. Helix matches their
> technical breadth — multi-agent orchestration, parallel batches,
> streaming UI, structured exports, CI-gated contract — and adds the
> one thing none of them have: clause-grounded provenance on every
> artifact. The domain is different; the bet is the same; the
> difference is **we can prove ours, every PR.**”*

**Cross-references for the appendix:** Full 5-winner comparison table
+ "what Helix learned from each" + non-winner comparisons (vs Jira
plugins, Atlassian Intelligence, "why not just GPT") live in
[`PRESENTATION.md` → Q&A Appendix B](../PRESENTATION.md). Verbatim
one-liner per winner in [`PRESENTER_CHEATSHEET.md`](../PRESENTER_CHEATSHEET.md).

---

**Presenter one-liner:** *“Helix is a rehearsed 5-page autonomous SDLC demo with a full backup package, sprint-ready tasks in Jira export, and a clear security path for pilot — not a production GA claim today.”*
