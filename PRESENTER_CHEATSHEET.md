# Helix — presenter cheat sheet (P0 demo)

> **THE line. Memorize it. Open with it. Close with it.**
>
> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

## Who's on stage (15-second opener, before THE line)

> *"Helix is built by three engineers with clean ownership —
> **Siddham Jain** on the AI backend and 11-stage orchestrator,
> **Shubham Gatkal** on the React frontend and the live SSE dashboard,
> **Aditya Khapke** on the demo, QA contracts, and the recovery
> playbook. Every pillar maps to code we can open right now."*

If a judge asks "who did what?" → answer with the 3-pillar table in
[README → Team](README.md#team--who-built-what) or **Slide 8** (Team & Future) of
[PRESENTATION.md](PRESENTATION.md). **Each member owns a concrete,
named file** so the answer never sounds vague.

---

**60-second pitch (verbatim, anchored to the sample requirement):** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — *From Document to Delivery*. **Read this first.**
**Novelty Q&A — the 30-sec differentiator pitch:** [docs/NOVELTY.md](docs/NOVELTY.md). **Memorize this for "what's different about your project?"**
**Demo recovery playbook (if the LLM / app / laptop fails on stage):** [docs/DEMO_RECOVERY.md](docs/DEMO_RECOVERY.md) — **4-tier fallback model with 90-second pre-stage rehearsal checklist.** Run the checklist 5 minutes before stage. If any signal in the playbook fires mid-pitch, switch tiers without explaining the switch.
**Screenshot tour (Tier C — visual fallback):** [docs/SCREENSHOT_TOUR.md](docs/SCREENSHOT_TOUR.md) — 7 real captures of the populated `proj_demo_seed01` (Landing → Mission Control → Judge Demo → Delivery Package → Export Hub → Trace chain → Jira CSV). Open in a second tab during the pitch. Pre-recorded video at [`helix-frontend/docs/judge-screenshots/judge-walkthrough.webm`](helix-frontend/docs/judge-screenshots/judge-walkthrough.webm) (~2 MB, 22 s).
**Committed exports (Tier D — works with zero infra):** [docs/sample-exports/](docs/sample-exports/) — real Jira CSV + ADO CSV + markdown brief + backlog JSON. Open from GitHub if the laptop is dead.
**Guided tour (modes → narrative, 5-min walkthrough):** [docs/GUIDED_TOUR.md](docs/GUIDED_TOUR.md).
**Judge Q&A script:** [docs/JUDGE_QA.md](docs/JUDGE_QA.md) (tasks, security pilot, timing, scope).

## Preflight (2 min before judges)

```powershell
# Terminal A
cd helix-backend
.\run.ps1   # sets HELIX_DEMO_FAST=true (~3–4 min heuristic pipeline)

# Terminal B
cd helix-frontend
npm run dev
```

| Check | URL / command |
|-------|----------------|
| **API health** | `http://127.0.0.1:8765/api/health` → `"status":"ok"` |
| **UI** | `http://localhost:5173` |
| **Backup bookmark** | `http://localhost:5173/project/proj_demo_seed01/ai-workspace` |

Login if needed: `demo@demo.com` / `demo123` (or **Try as Guest** on landing).

---

## 5-minute script (rehearse this)

| Time | Action | Clicks |
|------|--------|--------|
| 0:00–0:20 | Hook: messy req → autonomous AI team → Jira-ready package | 0 |
| 0:20–0:35 | Landing → **Start hackathon demo** (guest + judge) | 1 |
| 0:35–0:40 | **Start Autonomous SDLC Demo** (if not auto-started) | 1 |
| 0:40–4:00 | Narrate pipeline — progress is **SSE only** (no fake timer) | 0 |
| 4:00–4:15 | Finale ring → auto-opens **Delivery Package** | 0 |
| 4:15–4:45 | Scroll **tasks** banner + Jira preview (Task rows); **Approve & Export** | 1 |
| 4:45–5:00 | “Clause → story → task traceability” | 0 |

**If SSE stalls:** open backup bookmark above (pre-baked `proj_demo_seed01`).

### ⚠ Stage discipline — what the script does NOT promise

The UI does **not** ship these surfaces today. Do **not** mention or
gesture at them on stage:

- **No drag-and-drop Kanban board** for stories — they render as a
  vertical list with acceptance criteria + clause IDs. The narrative
  beat is "every card cites its clauses", not "drag a card".
- **No clickable trace graph** — the trace lanes are an animated
  count strip with real values from `/api/traceability/{id}/graph`.
  Say *"3 clauses, 2 stories, 4 tasks, 2 tests, 9 trace links"*; do
  **not** say *"click any node"*.
- **No per-story approve checkbox** — `Approve & Export` is one
  button that bulk-approves every story. That's the demo beat; do
  **not** hunt for a per-row toggle.
- **No five-metric Project Health dashboard** — readiness % is the
  one number we show, and `delivery_readiness_center` is the API.
  If a judge asks "show me project health", **scroll to the
  readiness ring** in the Delivery Package, not a separate dashboard.
- **`Push to Jira REST`** — only click this if `JIRA_BASE_URL` /
  `JIRA_TOKEN` / `JIRA_PROJECT_KEY` are configured on the API host.
  Without env, the button returns a friendly *"Dry run — configure
  JIRA_* env"* toast (fixed in commit ⛓ this session); previously it
  showed a red error toast on stage. **Default rehearsal:** do the
  CSV download path; only click the REST button if you've pre-verified
  the env.

These are the 5 most likely "judge raises an eyebrow" moments. The
codebase has the **API** for command-center, traceability graph, and
per-story approval — only the dedicated UI is deferred. If a judge
asks any of these, the honest answer is *"API is live, UI surface
ships in the next sprint; here's the endpoint"* — open
`/api/command-center/{id}` or `/api/traceability/{id}/graph` in a
browser tab.

---

## Ports & paths

| What | URL / path |
|------|------------|
| **API** | `http://127.0.0.1:8765` |
| **Judge demo** | `/judge-demo` |
| **Delivery package** | `/project/{id}/ai-workspace` |
| **Mission Control** | `/mission-control` (SSE errors → Pipeline warnings panel) |

---

## One-line honest slide (credibility)

> **Readiness %** comes from live delivery-gate scoring after the run (not a hardcoded placeholder). **Tasks** are generated per story via Scrum Master + heuristic fallback so Jira CSV always has engineering rows.

---

## Novelty zinger (use whenever a judge asks "what's different?")

> *"Multi-agent is now table stakes — judges have seen it twice today. The three things Helix has that the others don't are: **one**, every artifact carries a `source_clause_id` and a CI test asserts it; **two**, a dedicated **ambiguity agent** with a typed taxonomy that drafts clarifying questions before the sprint starts; **three**, a **three-tier provider stack** — live Azure → clause-grounded mock → heuristic guarantors — so the demo never dies, and `pytest tests/test_golden_pipeline.py` proves it in 2 seconds."*

Full deep-dive (with code refs): [`docs/NOVELTY.md`](docs/NOVELTY.md).

---

## Scale zinger (use when a judge asks "how does this scale beyond the prototype?")

> *"Three axes, all already planned to **code-level** with concrete
> numbers. **Compute** — Kubernetes HPA + Celery autoscaling on Redis
> queue depth + GPU node pool for embeddings (one A10G,
> batch-32 → ~10× throughput). **AI infrastructure** — single Azure
> provider today behind a one-class `AIService` boundary; adding a
> `pick_provider()` router (Azure ↔ Anthropic ↔ self-hosted
> Llama-3-70B on vLLM) is a one-class change with per-tenant cost
> caps and EU/US region pinning. **Storage** — in-process FAISS today,
> pgvector at pilot (one day's work, same agent API), managed
> Pinecone/Weaviate at production. The cost model is **~$1 per
> pipeline run** at Azure `o3` rates; spend is dominated by tokens,
> not compute — exactly the surface the router is built to optimize.
> Every step is **additive** — `scripts/judge_demo.ps1` keeps working
> unchanged at every stage."*

Pull up **Q&A Appendix A (Scale & Feasibility)** at the bottom of
[`PRESENTATION.md`](PRESENTATION.md) for the table version.
Full code-level deep-dive: [`docs/PATH_TO_PRODUCTION.md`](docs/PATH_TO_PRODUCTION.md).
Q&A long-form: [`docs/JUDGE_QA.md → "How does this scale..."`](docs/JUDGE_QA.md#how-does-this-scale-beyond-a-hackathon-prototype).

---

## Q&A anchors

- **Novelty (the three differentiators):** [`docs/NOVELTY.md`](docs/NOVELTY.md) — each pillar has a code ref and a contract test name. Memorize the 30-sec pitch.
- **Scale beyond prototype:** [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md#how-does-this-scale-beyond-a-hackathon-prototype) for the 90-sec deep dive · [`docs/PATH_TO_PRODUCTION.md`](docs/PATH_TO_PRODUCTION.md) for the week-by-week migration order with code refs · **Q&A Appendix A** at the bottom of [`PRESENTATION.md`](PRESENTATION.md) for the deck-friendly table.
- **Comparison to past hackathon winners** (RiskWise · Apollo · RouteOpt · OpenCodeReview · WorkWizee): full table in **Q&A Appendix B** of [`PRESENTATION.md`](PRESENTATION.md) · verbatim 30-sec answer in [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md#how-does-helix-compare-to-past-hackathon-winners-riskwise--apollo--routeopt--opencodereview--workwizee). **Per-winner one-liners** (memorize):
  - **RiskWise** *(Best Overall, MS Agents Hack)* — *"Same multi-agent shape on a vertical domain; **risk is just 1 of our 10 agents** — we're end-to-end SDLC, not single-task."*
  - **Apollo** *(Best C#, MS Hack)* — *"Apollo's coordinator-with-sub-agents pattern is exactly what `demo_orchestrator.py` does — ours is **role-typed for SDLC stages** (PM / Architect / QA / Risk), not open research."*
  - **RouteOpt** *(1st, NVIDIA NeMo Hack)* — *"Same NL → structured-output bet. They verify routes in Omniverse; **we verify artifacts via a CI-gated golden contract on every PR**."*
  - **OpenCodeReview** *(2nd, NVIDIA NeMo Hack)* — *"They run **at PR time on code**; we run **upstream of code on requirements**. Complementary, not competitor."*
  - **WorkWizee** *(Best Copilot, MS Hack)* — *"They cut **~40% off incident management** by automating one workflow. We cut **~98% off backlog grooming** by automating the requirements-to-tickets workflow."*
- **Comparison to non-winners** (basic Jira plugins / Atlassian Intelligence / *"why not just GPT"* / *"could a single Claude call do this"*): **Q&A Appendix B.3** of [`PRESENTATION.md`](PRESENTATION.md). The shortest defensible line: *"They give you a story-text generator; we give you the whole traceable graph the team actually ships on."*
- **Closer (use after the comparison Q):** *"Apollo, RiskWise, RouteOpt, OpenCodeReview, and WorkWizee each won by tackling one clear workflow with agents. **We match their technical breadth and add the one thing none of them have — clause-grounded provenance on every artifact, validated by a CI test that runs in 2 seconds, every PR.**"*
- **Tasks in CSV:** `_ensure_project_tasks` — at least one task per story on demo path.
- **Readiness ring:** Gate-based % from `build_readiness_center()` (100% when all six gates pass).
- **PRD:** Generated during pipeline; lazy `GET /api/delivery/prd/{id}`.
- **Traceability:** Clause ids on stories/tasks; live ticker during judge run; validated by `filter_clause_ids()`.
- **"What if the LLM is down?"** → Run `HELIX_USE_AI=false pytest tests/test_golden_pipeline.py -v` — 8 passed in ~2 seconds with zero LLM calls. The 3-tier stack guarantees a populated Delivery Package.
- **"What's the cost?"** → ~$0.90–$1.20 per pipeline run at Azure `o3` rates; mock-mode runs cost $0. Full cost model in [`PATH_TO_PRODUCTION.md` §3](docs/PATH_TO_PRODUCTION.md#3-cost-model-back-of-envelope).

## Ctrl+Shift+P

Command palette on any project page.

## P2 features (optional)

| Feature | Where |
|---------|--------|
| Traceability animation | AI Workspace after pipeline |
| Jira CSV preview | `GET /api/backlog/{id}/jira-csv/preview` |
| Live Jira push | AI Workspace · `POST /api/backlog/{id}/jira-push` |
| Voice ingest | Mission Control → **Voice** tab (Chrome/Edge) |
| Rate limits | `HELIX_RATE_LIMIT_PER_MINUTE` (default 120 POST/min) |
| Parallel demo | `HELIX_DEMO_PARALLEL=true` (default on) |

## P1 ops notes

- **JWT rotate:** `POST /api/auth/refresh` with current bearer → new token (`jti` rotated). Change `HELIX_JWT_SECRET` to invalidate all sessions.
- **Generate/analyze routes** require auth (no anonymous LLM burn).
- **Three.js:** off by default; set `VITE_HELIX_HERO_PARTICLES=true` for landing particles only.
