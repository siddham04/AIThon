# Helix — Demo Script: *From Document to Delivery*

> **One sentence judges should remember:**
> *"Upload messy requirements → launch the AI team → get a release-ready
> delivery package with full traceability. Under 10 minutes."*

This file is the **tight version** of the demo — designed for a
**60-second live pitch** (or a 60-second video). It's anchored to the
**exact sample requirement** that ships in the app
(`helix-frontend/src/constants/sampleRequirement.js`), so what you say
matches what the judge sees on screen.

For the long version (5-minute click path, mode-by-mode justification,
recovery scripts), see [`docs/GUIDED_TOUR.md`](GUIDED_TOUR.md).

---

## 1. The sample requirement (the *document* in "Document to Delivery")

Helix's **golden domain** is e-commerce checkout. When you click
**Load sample requirement**, the textarea fills with the canonical
**Checkout Revamp Initiative** PRD. Read these passages aloud so the
judge feels the pain *and* sees the rigor:

> **Goal:** Cut cart abandonment by delivering a fast, trustworthy
> checkout flow for returning shoppers and a clear ops surface for
> support agents.
>
> **Functional (sample):**
> - Show a delivery date estimate before payment within **200 ms P95**.
> - Accept saved cards and one digital wallet at launch; **vendor
>   selection is TBD pending procurement review**.
> - Inventory must decrement atomically so two shoppers cannot oversell
>   the last unit.
> - Refunds should happen *"fast"* (legal still drafting the SLA
>   wording).
> - International shoppers see local currency *"where it makes sense"*
>   — exact FX/rounding policy undefined.
>
> **Non-functional (sample):**
> - p95 checkout API latency under **300 ms at 1k concurrent shoppers**.
> - Payment provider uptime assumption **99.9%**.
> - PCI scope must remain **SAQ-A** — never store raw PAN.
> - JWTs ≤ 15 min, refreshed via secure HTTP-only cookie; sessions
>   revocable from the support console.

**Why this requirement?** It's deliberately engineered for the demo:

- **Hard numbers** (200 ms, 99.9%, 1k concurrent, SAQ-A) so the Quality
  + Risk agents have measurable anchors and produce specific output —
  not generic NFR boilerplate.
- **Exactly three ambiguities** — *vendor TBD*, *"fast" refunds*,
  *"where it makes sense"* currency — so the Ambiguity agent has three
  clear, demoable wins without drowning the brief in vague language.
- **Auth + PCI mentions** so the Risk agent reliably emits a security
  risk **and** a compliance risk.
- **Multiple personas** (shopper, support agent) so the Decomposer
  never collapses to one user type.

The bulletproof guarantees on this requirement are codified as a
contract test — see [`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md).

---

## 2. The 60-second live pitch (verbatim)

Stand-up version. Memorize. The bracketed `[ACTION]` cues are what you
click; the *italic* is what you say.

### 0:00 — Problem (10 seconds)

`[Open Landing page]`

> *"This is what a real PRD looks like at 9am on Monday."*

`[Click 'Try as Guest' → 'New project' → 'Load sample requirement']`

`[Scroll the textarea so the judge sees 'TBD', 'fast', 'where it makes sense']`

> *"Checkout revamp. Vendor **TBD**. Refunds happen **'fast'**.
> Currency policy: **'where it makes sense'**. Mixed in with hard
> numbers — 200 ms P95, 1k concurrent, SAQ-A. Engineering teams lose
> 3 to 5 days a sprint translating this into stories, tasks, and
> tests — and another day chasing 'who said this?' when scope changes."*

### 0:10 — Solution (5 seconds)

`[Click 'Ingest' → Mission Control → 'Launch AI team']`

> *"One button. An autonomous AI team takes over."*

### 0:15 — Live proof (35 seconds)

`[Stand back. Narrate the SSE timeline as stages light up]`

> *"Eleven stages, streaming live. **Quality scorer** flagged this PRD
> a D-grade with three gaps."*
>
> *"**Review board** — five reviewers in parallel: BA, Architect, QA,
> Security, PM."*
>
> *"**Ambiguity agent** caught every 'maybe', 'TBD', and 'fast' as a
> blocking question."*
>
> *"**Stories** — five user stories, every one citing the source
> clause it came from."*
>
> *"**Architecture and sprint plan** in parallel. **APIs and tests**
> in parallel. **Jira-ready backlog**. **Release-readiness gate**."*

`[Auto-navigate fires → Delivery Package opens]`

### 0:50 — Outcome (10 seconds)

`[Scroll Delivery Package: Kanban → Mermaid → Tests → Risks → Readiness ring]`

> *"One screen. Every artifact. Live Mermaid architecture, BDD test
> cases, risk register, release-readiness percentage from live
> delivery gates — not a placeholder."*

`[Click any task → Trace tab → click the clause it cites]`

> *"Here are the three things no GPT wrapper does:*
>
> *One — **every artifact cites the clause it came from**, validated
> against the real clause set, not hallucinated. Click any task, see
> the source sentence.*
>
> *Two — that ambiguity heat-map isn't a warning — it's a **typed
> taxonomy** with a clarifying question and suggested resolution per
> issue. PMs resolve scope before the sprint, not in week three.*
>
> *Three — what you just watched ran on **Azure OpenAI**, but pull the
> network cable and the same pipeline runs in **two seconds** through
> a clause-grounded mock plus heuristic guarantors. The full
> 11-stage contract is CI-gated on every PR. The demo gods can't kill
> this."*

### 1:00 — Close (5 seconds)

`[Toggle one story to 'Approved for export' → click Export Jira CSV]`

> *"Upload messy requirements → launch the AI team → release-ready
> Delivery Package with full traceability. Under 10 minutes — and you
> saw it under one. Approved rows only — nothing ships without human
> sign-off."*

`[Stop talking. Wait for the question.]`

---

## 3. The 60-second video script (for the submission MP4)

If you're recording instead of presenting live, use the same beats but
trim the words (no audience eye contact, faster cadence).

| Time | On-screen action | Voiceover (~12 words per beat) |
|------|------------------|--------------------------------|
| 0:00–0:08 | Landing → Try as Guest → New project → Load sample requirement → highlight "TBD", "fast", "where it makes sense" | *"Real e-commerce PRDs look like this. Vendor 'TBD'. Refunds 'fast'. Currency policy 'where it makes sense'. That ambiguity is the problem."* |
| 0:08–0:12 | Click Ingest → Launch AI team | *"One button. Eleven AI agents take over."* |
| 0:12–0:38 | SSE timeline plays (use a 26× speed-up in editing if live LLM, or keep real-time with `HELIX_DEMO_FAST=true`) | *"Quality scorer. Review board, five reviewers in parallel. Ambiguity agent catches every 'maybe'. Stories with clause citations. Architecture and sprint plan in parallel. APIs and tests in parallel. Jira-ready backlog. Release-readiness gate."* |
| 0:38–0:50 | Delivery Package scroll: Executive Summary → Kanban → Mermaid → Tests → Risks → Readiness | *"One screen. Every artifact. Live Mermaid architecture. BDD test cases. Risk register. Release-readiness from live delivery gates — not a placeholder."* |
| 0:50–0:58 | Click any task → Trace tab → click cited clause | *"And the differentiator: every artifact cites its source clause. Audit-ready."* |
| 0:58–1:00 | Toggle Approved → Export Jira CSV → open CSV | *"Approve, export. Nothing ships without human sign-off."* |
| 1:00 (end card) | Static frame: tagline + GitHub URL | *"Helix. From messy document to release-ready delivery. Under ten minutes."* |

**Recording tips for a clean 60-second cut:**

- Use **`HELIX_DEMO_FAST=true`** (the default in `scripts/judge_demo.ps1`)
  — the pipeline finishes in ~30 seconds, no editing needed.
- Use **`HELIX_DEMO_PARALLEL=true`** so the parallel batches actually
  show as "Running (parallel)" badges in the timeline.
- Capture at **1920×1080** with the browser DevTools closed.
- Use the **system cursor highlighter** (Windows: PowerToys MouseHighlighter)
  so judges can follow the clicks at speed.
- Mute system audio; record voiceover separately and align in post.

---

## 4. The problem→solution mapping (for slide notes / Q&A)

When a judge asks *"how does this actually help?"*, point at the
sample requirement and walk this table:

| Pain in the sample PRD | What Helix does | Where it shows up |
|---|---|---|
| *"vendor TBD"*, *"where it makes sense"* | **Ambiguity agent** flags each as a clarifying question with severity | Workspace → Ambiguity heat-map; SSE step 4 |
| *"PCI scope SAQ-A"*, *JWT auth* | **Risk agent** raises a security + a compliance NFR with mitigation | Delivery Package → Risks card |
| *"vendor TBD"* / *FX policy undefined* | **Quality scorer** drops the grade; **Review board** logs them as blockers | Mission Control → quality / review SSE events |
| *"refunds should happen fast"* | **Test architect** generates a BDD scenario *"Given a refund request, when triggered, then completed within N seconds"* with N marked as **clarification needed** | Delivery Package → Tests tab |
| *"200 ms P95"*, *"1k concurrent"* | **Test architect** generates a performance scenario; **Estimator** sizes it | Delivery Package → Tests tab + Sprint board |
| *"who said this?" (audit)* | Every story / task / test carries **`source_clause_ids`** pointing back to the exact sentence | Delivery Package → Trace tab; CSV export includes the column |
| *"governance"* | **`approved_for_export`** flag + **`?approved_only=true`** export filter | Delivery Package → Approve checklist → Export hub |

> **The Q&A reflex.** If a judge says *"what if the AI hallucinates?"*,
> the answer is **always** the same: *"It can't add a citation it
> didn't see. Look — every artifact has `source_clause_ids`. If it
> doesn't cite a clause, it didn't come from your input."*

---

## 5. The one-sentence opening, middle, and close

If you forget everything else, say only these three sentences:

1. **Open:** *"This is what a real e-commerce PRD looks like at 9am on Monday."*
   `[show the Checkout Revamp sample with 'TBD', 'fast', 'where it makes sense' visible]`
2. **Middle:** *"One button. An autonomous AI team takes over."*
   `[click Launch AI team]`
3. **Close:** *"Upload messy requirements → launch the AI team →
   release-ready Delivery Package with full traceability. Under 10
   minutes."*

Everything in between is the **proof** that the close is true. Stop
talking after the close.

---

**Cross-references**

- Long-form 5-min walkthrough: [`docs/GUIDED_TOUR.md`](GUIDED_TOUR.md)
- Offline-safe one-command launcher: [`docs/JUDGE_MODE.md`](JUDGE_MODE.md) ·
  `scripts/judge_demo.ps1` / `scripts/judge_demo.sh`
- Novelty deep-dive (the three differentiators with code refs and contract tests):
  [`docs/NOVELTY.md`](NOVELTY.md)
- Bulletproof contract (the proof for "Functional MVP"):
  [`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md)
- **Screenshot tour** (7 real captures of the populated demo project —
  use as a video-storyboard reference or as the visual fallback if the
  live demo is offline): [`docs/SCREENSHOT_TOUR.md`](SCREENSHOT_TOUR.md)
- Slide deck source: [`PRESENTATION.md`](../PRESENTATION.md)
- Live presenter cue card: [`PRESENTER_CHEATSHEET.md`](../PRESENTER_CHEATSHEET.md)
- Q&A anchors: [`docs/JUDGE_QA.md`](JUDGE_QA.md)
