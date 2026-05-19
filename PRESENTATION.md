# Presentation outline (≤ 7 slides)

Use this content in Google Slides, PowerPoint, or Pitch. Paste the **mermaid** diagram from `ARCHITECTURE.md` as an image export if needed.

---

### Slide 1 — Problem

Manual SDLC breakdown from a messy requirement costs hours: stories, tasks, tests, and ambiguity review are duplicated across tools with weak traceability back to the original text.

---

### Slide 2 — Demo screenshot A

**Requirement ingestion** — New project: paste, file, URL, or **Voice** (Chrome; Web Speech API). Then **Ingest** → workspace. Exact ports and checklist: **`docs/RUNBOOK.md`**.

*(Insert screenshot: ingestion / new project.)*

---

### Slide 3 — Demo screenshot B

**AI streaming** — The analyze pipeline streams over SSE (`/api/artifacts/stream/...`): each stage (intent, ambiguity, backlog, tests, estimates, risks) completes with structured JSON merged into the workspace. When `ANTHROPIC_API_KEY` is set, Claude powers ambiguity / test / estimate agents; otherwise Azure OpenAI JSON (or demo mock) keeps the timeline full.

*(Insert screenshot: streaming panel / multi-agent timeline with stage labels.)*

---

### Slide 4 — Demo screenshot C

**Kanban & ambiguity** — Tasks grouped by status; ambiguity cards highlight unclear scope with suggested questions.

*(Insert screenshot: Kanban + ambiguity view.)*

---

### Slide 5 — Architecture

Reuse the **system diagram** from `ARCHITECTURE.md` (React → Nginx → FastAPI → Postgres / Redis / RAG).

---

### Slide 6 — Impact

**Time saved (example):** average **4 hours** of manual breakdown vs **12 minutes** with Helix assisted generation → ~**95%** reduction in upfront SDLC structuring time for comparable artifact depth.

**Methodology (defensible):** manual minutes use the same heuristics as code (`helix-backend/app/agents/orchestrator.py`: minutes per clause, story, task, test, ambiguity, risk); Helix wall-clock baseline ~4 minutes; dollar estimate uses a fixed engineer-minute rate (`ENGINEER_MIN_COST_USD`). **Citation quality:** `citation_item_rate` = fraction of stories+tasks+tests with ≥1 `source_clause_id` after analyze (also returned on `GET /api/artifacts/{project_id}`).

Also cite **traceability**: every task/test linked to source clauses → fewer defects from misunderstood scope.

**Optional live beat:** mark a story “approved for export,” then export with `approved_only=true` to show governance without new ML.

---

### Slide 7 — Roadmap

- Team-managed prompt packs per domain (fintech, healthcare).
- Persistent vector store + cross-project retrieval governance.
- Deeper JIRA/Azure DevOps two-way sync and test-case execution hooks.
- (Shipped for demo) Human-approved export gate + ingest sensitive-pattern hints + per-stage pipeline timings in SSE.

---

**Speaker notes:** Close the demo video on the **JIRA export success** screen to mirror the live pitch.
