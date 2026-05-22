# Phase 10 — Demo Readiness Review

**Simulated scenario:** 5-minute hackathon pitch to judges (laptop + projector, API on `localhost:8765` or hosted).  
**Product paths:** Judge Demo (`/judge-demo`) vs Mission Control golden path.  
**Evidence:** Phases 1–9, `WinningDemoScreen.jsx`, `MissionControl.jsx`, Phase 3 timing (~220 s pipeline, `use_ai=false`).

---

## Simulated 5-minute run (recommended script)

### Path A — **Judge Demo** (fewest clicks, best for kiosk)

| Time | Action | Clicks | What judges see |
|------|--------|--------|-----------------|
| 0:00–0:20 | Hook: “Messy req → autonomous AI team → Jira-ready package” | 0 | Slide or verbal only |
| 0:20–0:35 | Landing → **Try as Guest** | 1 | Instant auth |
| 0:35–0:40 | Sidebar → **Judge Demo** (▶ icon) | 1 | “No dashboard tour” copy |
| 0:40–0:45 | **Start Autonomous SDLC Demo** | 1 | Pipeline + % bar |
| 0:45–4:00 | *Narrate while backend runs* | 0 | Beats light up (PM → Arch → Stories → Tests → Package) |
| 4:00–4:20 | Finale: **94% PROJECT READY** ring | 0 | Wow moment |
| 4:20–4:45 | **Open delivery package** → scroll 1 story + Mermaid | 1 | Tangible output |
| 4:45–5:00 | **Download Jira CSV** + one-line traceability | 1 | “Ships to your board” |

**Clicks before value appears:** 3  
**Clicks to export:** +2 (package + CSV)  
**Risk:** Backend SSE ~3–4 min (mock) or longer with live LLM — **tight for 5:00** unless pre-run.

### Path B — **Mission Control** (stronger “AI visible” story)

| Time | Action | Clicks |
|------|--------|--------|
| 0:00–0:25 | Guest + Mission Control | 2 |
| 0:25–0:35 | **Load demo PRD** | 1 |
| 0:35–0:40 | **Launch AI team** | 1 |
| 0:40–3:50 | Narrate **Live stream** terminal + agent bars | 0 |
| 3:50–4:10 | Auto-nav to Delivery Package (or sidebar) | 0–1 |
| 4:10–5:00 | Stories + diagram + Jira CSV | 1–2 |

**Clicks:** 4–5  
**AI visibility:** **Higher** — `MissionAgentExecution` log + PM/ARCH/QA/SCRUM tags.

### Path C — **Backup if network fails** (30 s)

Open pre-baked ` /project/{proj_id}/delivery-package` → scroll → download CSV. Say pipeline ran pre-show. **Clicks:** 1–2.

---

## Evaluation (judge lens)

### Does the story make sense?

| Verdict | **Yes — 8/10** |
|---------|----------------|
| Narrative | Upload → AI team runs SDLC → package → export is coherent and matches hackathon brief. |
| Friction | Sidebar labels collapsed to icons; “Judge Demo” vs “Mission Control” may confuse without rehearsal. |
| Gap | **0 tasks** in validated run undermines “Scrum Master planned the sprint” line — stories-only backlog. |

### Is the value obvious?

| Verdict | **Mostly — 7.5/10** |
|---------|---------------------|
| Clear | “You don’t write stories/tests by hand” on Mission Control; Judge Demo tagline is strong. |
| Weak | Time-saved % is in deck, not on-screen during run; value appears only after long wait or finale ring. |
| Fix | Overlay “~4h → ~12 min” on finale or first beat completion. |

### Are there too many clicks?

| Path | Pre-wait clicks | Verdict |
|------|-----------------|--------|
| Judge Demo | **3** | **Good** for hackathon |
| Mission Control | **4** (+ optional config) | **Acceptable** |
| Wrong path | Landing → Login form → New project → … | **Avoid** — use Guest + Judge Demo |

Optional config (team size, tech stack) on Mission Control adds cognitive load — **skip in 5 min demo**.

### Is the AI visible?

| Surface | Visibility | Score |
|---------|------------|-------|
| Mission Control | SSE headlines in terminal, agent bars, block progress | **9/10** |
| Judge Demo | Pipeline steps + % + actor labels; less “model working” detail | **7/10** |
| Workspace | Chat stream (not in 5 min path) | N/A |
| Backend | No “Powered by o3” badge during run | Missed opportunity |

**Issue:** Judge Demo runs **`runPipelineAutoPlay`** (~26 s of timed UI beats) **in parallel** with backend SSE (~220 s). UI beats can finish on timers before real steps complete — judges may think AI finished when it has not.

### Is the wow factor strong enough?

| Verdict | **Good, not great — 7.5/10** |
|---------|-------------------------------|
| Hits | 94% readiness ring; multi-agent pipeline; live progress; Mermaid architecture; Jira CSV in one click. |
| Misses | No single “holy shit” moment under 60 s; no voice→spec in golden path; no live Jira push; tasks empty. |
| Ceiling | With pre-baked package + 90 s narrated Judge Demo start → **8.5/10** possible. |

---

## Demo readiness score

| Dimension | /10 | Notes |
|-----------|-----|-------|
| Story clarity | 8 | Tight positioning; fix task gap in script |
| Value obviousness | 7.5 | Add on-screen ROI hook |
| Click economy | 8.5 | Judge path is lean |
| AI visibility | 7.5 | Prefer MC terminal or sync judge UI to SSE |
| Wow factor | 7.5 | Finale ring helps; needs faster or pre-baked beat |
| **5-min feasibility** | **6.5** | Live full pipeline often **>5 min** — rehearse or pre-run |

**Overall demo readiness: 7.5 / 10** — Ready with **rehearsed Judge Demo + pre-baked project backup**; not ready for cold “full live pipeline” in exactly 5:00 without risk.

---

## Top 10 improvements (demo-blocking → polish)

1. **Pre-bake one showcase project** — pipeline complete, Delivery Package full; open via bookmark if SSE stalls.
2. **Remove or gate `runPipelineAutoPlay`** on Judge Demo — drive UI **only** from SSE events (no desync).
3. **Fix Scrum / decomposer** so **tasks > 0** — Jira CSV and “sprint-ready” story hold up in Q&A.
4. **Default Judge Demo to `use_ai: false`** for predictable ~3:40 timing (or env `HELIX_DEMO_FAST=true`).
5. **Auto-open Delivery Package** on judge finale (same as Mission Control `setTimeout` navigate) — save 1 click.
6. **One-click “Run hackathon demo”** on Landing → Guest + `/judge-demo` + start (zero sidebar hunt).
7. **Persist PRD during pipeline** — fix `GET /delivery/prd/{id}` 404 so Executive Summary isn’t a fallback.
8. **On-screen time-saved ticker** during pipeline (“Clause 7 → Story 3…”).
9. **Disable `WorkspaceAmbient` Three.js** for demo builds — faster shell load on venue Wi-Fi.
10. **Presenter runbook card** in repo root: ports, guest path, backup `proj_id`, opening line.

---

## Top 10 bugs (demo-impacting)

1. **Judge UI timer vs SSE desync** — `runPipelineAutoPlay` (~26 s) vs backend ~220 s (`WinningDemoScreen.jsx`).
2. **Hardcoded 94% readiness** — `_step_readiness` sets `center.readiness = 94` (`demo_orchestrator.py`) — credibility if questioned.
3. **0 tasks after pipeline** — Phase 3 validated run; empty Jira task rows.
4. **`GET /api/delivery/prd/{id}` → 404** — PRD section empty unless artifacts fallback.
5. **Mission Control: no SSE abort on unmount** — navigating away leaves stream running.
6. **SSE `error` steps not surfaced in UI** — pipeline can fail silently in Mission Control.
7. **Guest + auto-register auth** — fine for demo; accidental double-login toast edge cases.
8. **Mission Control mobile** — config/input row overflows 390px (Phase 2).
9. **Delivery Package loading** — 10 parallel GETs; slowest blocks entire page spinner.
10. **Playwright smoke** still targets legacy `/new` routes (Phase 1) — team may think E2E is green when product path untested.

---

## Top 10 UX issues (during demo)

1. **Collapsed sidebar** — icons only; judges may not find “Judge Demo” without label.
2. **3–4 minute dead air** on live pipeline — need narration script or progressive headlines.
3. **Delivery Package empty state** before first run — confusing if judge opens nav early.
4. **Input mode tiles** (4 choices) on Mission Control — decision paralysis; hide for demo mode.
5. **Team constraints panel** — looks like required setup; should be collapsed by default.
6. **Two competing entry points** — Mission Control vs Judge Demo without “start here” in app.
7. **Finale requires extra click** to Delivery Package — anticlimax after ring.
8. **No in-app “what’s happening now”** subtitle on Judge Demo tied to SSE `headline` field.
9. **Export only CSV on product page** — judges expecting “push to Jira” may not see REST push button.
10. **Heavy initial load** (~500 KB+ JS) — slow first paint on conference Wi-Fi.

---

## Top 10 wow-factor opportunities

1. **Single CTA on Landing:** “Start 90-second autonomous demo” → judge flow end-to-end.
2. **Surface SSE headlines in Judge UI** — e.g. “10 ambiguities · 6 risks” as large captions under active beat.
3. **Clause → story fly-in** — animate traceability link when stories beat completes (1 clause highlights).
4. **Live agent avatars** — PM / Architect / QA / Scrum light up with short “thinking” copy from `missionAgents`.
5. **Instant replay mode** — play pre-recorded SSE JSON for 60 s when offline (deterministic wow).
6. **Jira CSV preview modal** — show first 5 rows before download (“ready for import”).
7. **Before/after split screen** — left: messy requirement; right: package sections pop in as beats complete.
8. **Voice ingest 10 s** — Web Speech on Mission Control for “messy meeting” beat (already in codebase elsewhere).
9. **Real `jira-push` success toast** with issue keys when env configured — stronger than CSV.
10. **Post-demo “Send package to email / Slack”** — even mock — memorable closer.

---

## Presenter cheat sheet (printable)

```
OPEN:  "Helix is an autonomous SDLC team — not a requirements dashboard."

PATH:  Landing → Try as Guest → Judge Demo (▶) → Start Autonomous SDLC Demo

SAY:   While bar moves — "PM scored quality, architect drew APIs, QA wrote 20 tests,
       scrum planned the sprint — you didn't touch Jira."

WOW:   94% ring → Open delivery package → one story + diagram → Download Jira CSV

BACKUP: /project/proj_XXXXX/delivery-package  (pre-run phase3_workflow_test.py)

AVOID: Mission Control config tiles, Workspace, Settings, legacy URLs, live use_ai=true on slow Wi-Fi
```

---

## Verdict

| Question | Answer |
|----------|--------|
| Ready to demo? | **Yes**, with rehearsal and backup project |
| Best 5-min path? | **Judge Demo** (clicks) + **Mission Control terminal** (narration) hybrid: start on Judge, if asked “show AI working” jump to pre-run MC project log |
| Biggest risk? | **Time** and **UI/SSE desync** on Judge Demo |
| Biggest untapped wow? | **Traceability animation** + **headline-driven storytelling** during wait |

---

## Related docs

- Phase 3 workflow: `docs/PHASE3_WORKFLOW_EXECUTION.md`
- Phase 9 judge scores: `docs/PHASE9_HACKATHON_JUDGE_REVIEW.md`
- Pitch outline: `PRESENTATION.md`
- RUNBOOK: `docs/RUNBOOK.md` (if present)
