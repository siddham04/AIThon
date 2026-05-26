# Helix — Why this isn't another GPT wrapper

> **One line:** *Multi-agent orchestration is now table stakes. The
> three things that make Helix different — and that no demo on stage
> next to ours will have — are the **traceable clause graph**, the
> **automated ambiguity workflow**, and the **3-tier provider
> resilience** that keeps every artifact non-empty and cited even
> when the LLM is down.*

**Companion docs:**
[`docs/SCREENSHOT_TOUR.md`](SCREENSHOT_TOUR.md) *(visual proof — see each pillar in a real captured screen)* ·
[`README.md`](../README.md) ·
[`PRESENTATION.md`](../PRESENTATION.md) ·
[`ARCHITECTURE.md`](../ARCHITECTURE.md) ·
[`docs/WORKFLOW.md`](WORKFLOW.md) ·
[`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md) ·
[`docs/JUDGE_MODE.md`](JUDGE_MODE.md)

---

## The three pillars (memorize for Q&A)

### Pillar 1 — Traceable Clause Graph (Provenance you can prove)

> **The slide line:** *"Every story, task, test, and risk carries
> `source_clause_ids` pointing back to the exact sentence that produced
> it. Citations are validated against the project's real clause graph,
> not hallucinated."*

**Why it matters.** A regulated team can ship a ChatGPT-written backlog
exactly once before the auditor asks *"where did this requirement come
from?"* Helix makes that question a one-click answer.

**What's actually different from a GPT wrapper:**

| GPT wrapper | Helix |
|---|---|
| Asks the model for citations, hopes they're real | **Filters** every model-provided id through `filter_clause_ids()` against the real `project.source_clauses` set; logs drops |
| Citations exist only in the chat answer | Citations are a **first-class Pydantic field** (`source_clause_ids: list[str]`) on every artifact in `helix-backend/app/models.py` |
| You take the model's word for it | A **CI-gated contract test** asserts 100% of stories cite a real clause and ≥75% of tasks do — every PR. See [`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md). |
| One-off chat answer | Surfaced as a live **Trace tab** + a CSV export column + a backlog `traceability_matrix` |

**Code you can point at:**

- `helix-backend/app/agents/clause_utils.py` — `filter_clause_ids()`, `resolve_story_id()` — the validators that gate every artifact write.
- `helix-backend/app/models.py` — every `UserStory`, `Task`, `TestCase`, `AmbiguityIssue`, `Risk` model has `source_clause_ids`.
- `helix-backend/app/services/traceability.py` — builds the full `TraceabilityMatrix` from the persisted graph.
- `helix-backend/tests/test_golden_pipeline.py::test_every_artifact_cites_a_clause` — the contract.

**Demo beat:** *"This story `Show delivery-date estimate before payment` was generated from clause `clause_a1b2c3d4` — which is line 7 of the brief. Click trace and you can walk the whole chain from the source sentence to the test case that covers it."*

---

### Pillar 2 — Automated Ambiguity Detection (the agent that says "what do you actually mean?")

> **The slide line:** *"A dedicated AI agent that doesn't write stories
> — it interrogates them. It finds every vague phrase, classifies it,
> drafts the clarifying question, and feeds the answer back into the
> backlog before code is written."*

**Why it matters.** Industry research puts requirements ambiguity at
~30% of mid-sprint rework. Most AI tools amplify ambiguity by writing
confident-sounding stories on top of vague input. Helix does the
opposite — it *surfaces* the ambiguity as a structured artifact you can
resolve.

**What's actually different from a GPT wrapper:**

| GPT wrapper | Helix |
|---|---|
| Treats vague input as the user's problem | A **dedicated agent** (`AmbiguityAgent`) whose only job is to detect, classify, and prompt-clarify |
| One generic "this is ambiguous" warning | **Typed taxonomy** — `undefined_term` · `missing_criteria` · `conflicting` · `unquantified` · `out_of_scope` · `non_functional_gap` |
| No suggested fix | Every issue ships with a `suggested_question` AND a `suggested_resolution` |
| Lost in the chat history | **Heat-map UI** on the workspace, severity-sorted; cited to source clauses |
| No verification | The CI contract asserts ≥2 ambiguities on the golden requirement so this surface can't silently regress |

**Code you can point at:**

- `helix-backend/app/agents/ambiguity.py` — the dedicated agent.
- `helix-backend/app/models.py` — `AmbiguityKind` enum + `AmbiguityIssue` model with severity, excerpt, question, resolution, source clauses.
- `helix-backend/app/services/mock_agents.py::_ambiguity_dict` — deterministic Tier-2 fallback driven by a vague-phrase regex (`tbd | todo | later | maybe | asap | flexible | somehow | unclear | nice to have | figure out | needs discussion`) plus an "unquantified NFR" detector that fires when words like *fast / scalable / secure / reliable / performance* appear without numeric thresholds.
- `helix-backend/tests/test_golden_pipeline.py::test_ambiguities_and_risks_surface` — the contract.

**Demo beat:** *"The brief says refunds should happen 'fast' — three letters. Helix flagged it as `unquantified · high severity`, drafted the clarifying question — 'What numeric SLO applies?' — and suggested 'Define a measurable target with measurement methodology.' That's the conversation a PM should have *before* the sprint starts, not in week three."*

---

### Pillar 3 — 3-Tier Provider Resilience (the demo gods can't kill it)

> **The slide line:** *"Every Helix agent goes through three tiers in
> order — live Azure OpenAI, then a clause-grounded deterministic
> mock, then heuristic guarantors. The Delivery Package is never empty.
> Ever. The full 11-stage pipeline runs in 2 seconds with zero LLM
> keys, and a CI test enforces that contract on every commit."*

**Why it matters.** "Our model went down on stage" is the #1 way an AI
demo dies. "Our model returned an empty array" is the #2. Helix's
3-tier stack means neither of those failure modes ever reaches the
judge. This is also why the live demo is bookable.

**What's actually different from a GPT wrapper:**

| GPT wrapper | Helix |
|---|---|
| One provider, one prayer | **Three tiers**, each engaged automatically when the one above produces empty / unconfigured output |
| Mock data is random Lorem Ipsum | Tier 2 mock is **clause-grounded** — every synthesized story still cites the real source clauses, drives the real ambiguity detector, and feeds the real Decomposer |
| "Add a unit test some day" | A **CI-gated golden-pipeline contract** ([`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md)) runs the full 11-stage pipeline against the canonical e-commerce checkout brief on every PR and asserts 8 non-negotiable invariants in ~2 seconds |
| Pluggable in theory | The provider boundary is **one class** (`AIService`). Adding a second live provider (Anthropic, Bedrock, vLLM-hosted Llama) is a one-class change behind a `pick_provider()` router — see [`PATH_TO_PRODUCTION.md`](PATH_TO_PRODUCTION.md) §2.3 |

**The three tiers, in code:**

```
Tier 1  helix-backend/app/services/ai_service.py        Azure OpenAI o3, JSON mode, tenacity retries
        helix-backend/app/services/llm.py                chat_json_with_fallback dispatcher
                  │
                  │  unconfigured / empty JSON
                  ▼
Tier 2  helix-backend/app/services/mock_agents.py       Clause-grounded deterministic synthesis
                  │
                  │  still 0 stories / 0 tasks
                  ▼
Tier 3  helix-backend/app/agents/scrum_master.py        _heuristic_tasks_from_stories
        helix-backend/app/services/project_bridge.py    ensure_engineering_tasks
                                                         (guarantees ≥1 engineering task per story)
```

**Demo beat:** *"I can pull the network cable right now and the pipeline
still finishes. Watch."* — run `HELIX_USE_AI=false python -m pytest
tests/test_golden_pipeline.py -v` and show 8 passed in 2 seconds.

---

## Bonus differentiators (one-line cards for Q&A)

These don't headline the deck, but they're worth knowing when judges
push:

- **CI-gated bulletproof contract.** [`docs/GOLDEN_DOMAIN.md`](GOLDEN_DOMAIN.md) — 8 invariants, ~2 s, runs on every PR via [`.github/workflows/golden-pipeline.yml`](../.github/workflows/golden-pipeline.yml). Not promise, not slide — green check.
- **Approve-before-export governance gate.** `approved_for_export: bool` on every story and task; `?approved_only=true` filter on `/api/export` — governance is **opt-out, not opt-in**. Source: `helix-backend/app/services/export_filter.py`.
- **Multi-agent transparency.** 11 streamed SSE events with `elapsed_ms` per stage — the user *sees* each agent's contribution. Most AI tools are opaque "spinner → answer". Source: `helix-backend/app/services/demo_orchestrator.py::DEMO_STEPS`.
- **Parallel orchestration.** `_PARALLEL_BATCHES` runs `(quality ‖ review)`, `(architecture ‖ effort_sprint)`, `(apis ‖ tests)` concurrently — 11 stages, ~3 wall-clock cost.
- **Live delivery-readiness gate.** Not a hardcoded "94%" — `delivery_readiness_center.readiness` is a live composite of six sub-scores. Guarded by `test_readiness_is_live_not_hardcoded`. Audit trail in `docs/PHASE5_AI_WORKFLOW_AUDIT.md` H3.
- **Clause-grounded RAG.** In-process FAISS + `all-MiniLM-L6-v2`, per-project namespace. Chat answers carry the same `source_clause_ids` as artifacts — one provenance graph across the whole product.
- **Classical-ML augmentation.** scikit-learn `IsolationForest` for task anomalies, TF-IDF + cosine for duplicate-story detection. Not all intelligence has to come from an LLM.

---

## The 30-second novelty pitch (memorize this for Q&A)

> *"Multi-agent is now table stakes — judges have seen it twice today.*
> *The three things Helix has that the others don't are:*
>
> *One — every artifact carries a* ***source clause id*** *and a CI*
> *test asserts it. Provenance you can prove.*
>
> *Two — a* ***dedicated ambiguity agent*** *with a typed taxonomy that*
> *drafts clarifying questions before the sprint starts.*
>
> *Three — a* ***three-tier provider stack*** *— live LLM, clause-grounded*
> *mock, heuristic guarantors — so the demo never dies and the test*
> *suite proves it in 2 seconds.*
>
> *Together they turn an AI experiment into an SDLC operating layer a*
> *regulated team can actually ship on."*
