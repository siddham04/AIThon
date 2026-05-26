# Helix — Guided Tour (5 minutes, one continuous story)

> **The line we're proving on screen:**
> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

This doc exists for one reason: **make every Helix surface feel like
one product, not a tab tour.** If you only have 5 minutes with a judge,
follow this script exactly. Every "mode" you switch to is justified by
the same narrative beat — never by features.

**Companion docs:**
[`README.md`](../README.md) · [`PRESENTATION.md`](../PRESENTATION.md) ·
[`docs/JUDGE_MODE.md`](JUDGE_MODE.md) · [`docs/WORKFLOW.md`](WORKFLOW.md) ·
[`PRESENTER_CHEATSHEET.md`](../PRESENTER_CHEATSHEET.md)

---

## 0. Open with the line (10 seconds, before any clicking)

Look the judge in the eye. Say it slowly. Then click.

> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

That's the only sentence they need to remember. Everything that follows
is **proof** of that sentence — never new claims.

---

## 1. The mental model: three surfaces, one story

Helix has **three** product surfaces. That's it. Every other page is a
sub-view of one of these three.

| # | Surface | Narrative beat | Judge's question it answers |
|---|---------|------------------|------------------------------|
| 1 | **Mission Control** | *"Upload"* | *How does messy input get in?* |
| 2 | **Live agent run** (the SSE timeline) | *"Launch the AI team"* | *What are these AI agents actually doing?* |
| 3 | **Delivery Package** (workspace) | *"Release-ready, with full traceability"* | *What did I get, and can I trust it?* |

**Approve & Export** is a button inside Delivery Package — not a fourth
surface. **Chat / Copilot** is a panel inside the workspace — not a
fourth surface. **Trace graph** is a tab inside the workspace — not a
fourth surface.

When in doubt during a demo: **collapse anything that isn't one of
those three.** If a judge asks "what's that?", say *"a sub-view of
[surface]"* and click back.

---

## 2. The 5-minute click path (memorize this exactly)

Pre-flight: `scripts/judge_demo.ps1` (Windows) or
`bash scripts/judge_demo.sh` (mac/Linux/WSL) — see [`docs/JUDGE_MODE.md`](JUDGE_MODE.md).

| Time | Surface | Click | What you say | Why this beat exists |
|------|---------|-------|---------------|----------------------|
| 0:00 | Landing | **Try as Guest** (or **Start hackathon demo**) | *"One click in — no login wall."* | Removes friction; proves the offline guarantee. |
| 0:15 | Mission Control | **New project → Load sample requirement → Ingest** | *"Real-world input: an email, a PDF, a voice note. Helix splits it into atomic clauses for traceability."* | **Beat 1: Upload.** Shows the messy-input → structured-clauses transformation. |
| 0:45 | Mission Control | **Launch AI Team** | *"One button. Same SSE stream every time — no fake timers."* | **Beat 2: Launch the AI team.** Marks the transition from human work to autonomous AI work. |
| 0:45 → 3:30 | Live agent run (SSE timeline) | Just narrate as stages light up | *"Two agents running in parallel: Quality + Review Board… now Stories with clause citations… now Architecture + Sprint Plan in parallel… APIs + Tests in parallel… backlog… readiness gate. 11 stages. Per-stage timings on the right."* | **Beat 2 (proof).** Multi-agent transparency. Judges see the work happen. |
| 3:30 | Auto-navigate to Delivery Package | (No click — `complete` event auto-navigates) | *"And there it is. One screen. Every artifact."* | Removes a click; reinforces "no dashboard tour". |
| 3:30 → 4:15 | Delivery Package | Scroll: Executive summary → Kanban → Architecture (Mermaid) → Tests (G/W/T) → Risks → Readiness | *"Executive summary. Kanban-ready stories. Live Mermaid architecture — not a screenshot. BDD test cases. Risk register. Release-readiness gate — that percentage comes from live delivery-gate scoring, not a placeholder."* | **Beat 3: Release-ready package.** Proves coverage and depth. |
| 4:15 | Delivery Package | Click any task → **Trace** tab | *"Every artifact cites the source clause it came from. Click any task, see the clause chain. This is what makes Helix audit-ready."* | **Beat 3 (proof): full traceability.** The most defensible feature; lean on it. |
| 4:30 | Delivery Package | Toggle a story to **Approved for export** → **Export → Jira CSV (approved only)** | *"And the governance beat — `approved_for_export` is a Pydantic field on every story and task; the export filter is one line. Nothing ships to Jira without human sign-off."* | **The credibility moment.** Regulated teams care about this more than any other feature. |
| 4:45 | Delivery Package | Open the exported CSV in the browser | *"Approved rows only. Same path for Azure DevOps CSV, GitHub Issues JSON, live Jira REST push."* | **Close the loop.** Real artifact, on disk, in their inbox. |
| 5:00 | Land back on Delivery Package | (No click) | Repeat the opening line. *"Upload messy requirements → launch the AI team → release-ready delivery package with full traceability. Under 10 minutes — and you saw it under 5."* | **Bookend.** First and last words match. |

If anything stalls, recover with:
**`http://localhost:5173/project/proj_demo_seed01/ai-workspace`** —
pre-seeded Delivery Package, instant.

---

## 3. Why each surface earns its place (anti-tab-tour mode)

Judges sometimes interpret multiple modes as **scope creep**. Defuse it
preemptively by tying every surface to a beat the judge already heard.

### 3.1 Mission Control = the "Upload" beat

**Not** a "configuration wizard". **Not** a "dashboard".

**The one job:** accept messy input in any shape, normalize it into
**atomic clauses** with stable IDs that every downstream artifact can
cite. Voice / paste / file / URL are four convenience tabs on the same
function.

> **If a judge asks** *"why so many input options?"*: *"Because real
> teams get requirements in all four forms. The clause extraction is
> identical — voice just calls the Web Speech API first."*

### 3.2 Live agent run = the "Launch the AI team" beat

**Not** a "loading screen". **Not** a "progress bar".

**The one job:** make the autonomous work **visible** — so judges
believe it's real LLMs, not a template. Per-stage `elapsed_ms` and
streamed headlines do that. Parallel batches (`quality‖review`,
`architecture‖effort_sprint`, `apis‖tests`) prove orchestration depth.

> **If a judge asks** *"how do I know it's not pre-baked?"*: open
> DevTools → Network → EventStream tab on `/api/demo/{id}/run`. Real
> SSE, per-stage timings.

### 3.3 Delivery Package = the "Release-ready, with full traceability" beat

**Not** a "results page". **Not** a "report".

**The one job:** be the **single screen** a release manager would
approve from. Stories, tests, architecture, sprint plan, risks,
readiness gate, and the approval-gated export — all here. **Trace**
tab proves the citation chain. **Chat** panel (Copilot) is "ask
anything about this package, get answers grounded in the source
clauses".

> **If a judge asks** *"what's the chat for?"*: *"It's the same RAG
> retrieval the agents use, exposed for ad-hoc questions. 'Why did you
> generate this test case?' → it cites the clause."*

---

## 4. Phrases to use (and phrases to never use)

| Use this | Instead of |
|----------|------------|
| "AI team" | "the agents" / "the LLM" |
| "Delivery package" | "the output" / "the results" |
| "Full traceability" / "every artifact cites its clause" | "we use RAG" |
| "Approved before export" / "human gate" | "governance feature" |
| "Live delivery-gate score" | "readiness score" |
| "Under 10 minutes" | "fast" |
| "One upload → one team → one package" | "multi-agent multi-stage system" |
| "Same SSE stream every time" | "real-time" |
| "Three surfaces: Mission Control → Workspace → Delivery Package" | (any list of pages) |

---

## 5. Recovery scripts (when something goes wrong)

| If… | Do this | Say this |
|------|---------|----------|
| Backend is slow to start | Open the **pre-baked** project: `http://localhost:5173/project/proj_demo_seed01/ai-workspace` | *"Let me show you a completed run while the live pipeline warms up."* |
| A stage shows `error` | Continue — orchestrator never aborts | *"And notice — one stage hit a transient error, but the pipeline kept going. Production-grade fault tolerance."* |
| Live LLM rate-limited | Re-run with `HELIX_USE_AI=false` env (or `judge_demo.*` script default) | *"Demo mode runs the deterministic pipeline so the **flow** is provable regardless of provider quota."* |
| Browser hard-refresh needed | Ctrl+Shift+R | *"Refreshing — the SSE stream survives because state lives on the server."* |
| Judge asks for code | Open `helix-backend/app/services/demo_orchestrator.py` and scroll to `_STEP_RUNNERS` | *"Eleven steps, one Python list. Each step is a function under `_step_*`. Add a security-review agent in 30 lines without touching the UI."* |

---

## 6. The one-question-too-many trap

After the 5-minute path, **stop talking**. Let the judge ask a
question. Resist showing more features. Every additional feature
**dilutes** the narrative line they're going to remember.

If they ask "what else?", the right answer is *"that's the product —
what would you want to see next?"* not *"oh and we also have…"*

The mentor was right: the difference between finalist and winner is
**clarity of the story**. You already have enough agents. You already
have enough features. You only have **one** opening line worth
remembering.

> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

Say it. Show it. Stop.
