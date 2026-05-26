# Helix — Golden Domain & Bulletproof Pipeline Contract

> **The premise.** Hackathon judges score on the **MVP that works**, not
> the MVP that promises. Helix picks **one strong domain — e-commerce
> checkout — and guarantees every pipeline step produces non-empty,
> well-formed, traceable artifacts on it**. Every guarantee is enforced
> by a CI-gated pytest, so it cannot silently regress.

**Companion docs:**
[`README.md`](../README.md) ·
[`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) ·
[`docs/JUDGE_MODE.md`](JUDGE_MODE.md) ·
[`docs/WORKFLOW.md`](WORKFLOW.md) ·
[`docs/PHASE3_WORKFLOW_EXECUTION.md`](PHASE3_WORKFLOW_EXECUTION.md)

---

## 1. The golden domain

**E-commerce checkout** — specifically the *"Checkout Revamp
Initiative"* PRD shipped as the in-app sample
(`helix-frontend/src/constants/sampleRequirement.js`). One domain.
One canonical brief. One contract.

We chose checkout because it exercises every Helix agent for **real
work**, not generic boilerplate:

| Helix agent | What checkout makes it actually do |
|---|---|
| **Ingest** | Splits a mixed FR + NFR + scope PRD into 6–10 atomic clauses |
| **Quality Scorer** | Drops the grade because of `vendor TBD`, *"fast"*, *"where it makes sense"* |
| **Review Board** | All 5 reviewers (BA · Architect · QA · Security · PM) have something material to flag |
| **Ambiguity Agent** | Exactly 3 deliberate ambiguities to surface |
| **Risk Agent** | PCI-SAQ-A + JWT auth + 99.9% provider SLA = real security, compliance, dependency risks |
| **Decomposer + PM + Scrum** | Multi-persona (shopper, support agent, ops) keeps the backlog from collapsing to one user |
| **Architect** | Real components: cart, checkout, inventory, payment, refund, auth |
| **Estimator + Sprint Planner** | Hard SLOs (200 ms, 1k concurrent) drive realistic story-point sizing |
| **Test Architect** | Concrete BDD scenarios with numeric thresholds |

If a new agent ever wants in, it has to prove itself on **this exact
brief** first.

---

## 2. The bulletproof contract

These invariants are codified in
[`helix-backend/tests/test_golden_pipeline.py`](../helix-backend/tests/test_golden_pipeline.py)
and gated by [`.github/workflows/golden-pipeline.yml`](../.github/workflows/golden-pipeline.yml)
on every push and PR.

| Invariant | Threshold | Why it matters |
|---|---|---|
| Every declared pipeline step emits ≥ 1 event | 11 steps, plus `boot` | Proves the orchestrator never silently skips a stage |
| `readiness` step always completes with `status=done` | 100% of runs | The closing frame of every live demo |
| **Zero `error` events on the golden run** | 0 / 11 | One red lane on stage = lost credibility |
| Atomic clauses extracted | ≥ 5 | Anything less and traceability looks thin |
| User stories generated | ≥ 4 | Backlog has visible bulk |
| Engineering tasks generated | ≥ 4 | Closes the Phase-3 *"0 tasks after Scrum"* regression for good |
| Test cases generated | ≥ 4 | QA tab can't be empty on stage |
| Stories citing a real clause id | **100%** | Provenance contract |
| Tasks citing a real clause id | **≥ 75%** | Heuristic tasks inherit parent clauses; tolerates safe fallback |
| Test cases with valid `story_id` (when set) | **100%** | No orphan tests pointing at fake stories |
| Ambiguities surfaced | ≥ 2 | The brief contains 3 deliberate ones; missing them = regression |
| Risks surfaced | ≥ 2 | Auth + PCI must produce risks |
| Risk categories include `security` or `compliance` | ≥ 1 | The PCI/JWT signals must not be lost |
| Readiness % is in `[0, 100]` and matches `delivery_readiness_center.readiness` | exact equality | Guards the *hardcoded 94* regression flagged in [`docs/PHASE5_AI_WORKFLOW_AUDIT.md`](PHASE5_AI_WORKFLOW_AUDIT.md) (H3) |
| `jira_backlog.epic` is populated and has ≥ 1 story | always | Jira CSV export can't be empty |
| `traceability_matrix` is populated | always | Trace tab can't be empty |

**Loosening any of these thresholds requires editing this table AND the
test together**, in the same commit. There is no "skip the test"
escape hatch in CI for this domain.

---

## 3. How the contract is enforced

```
helix-frontend/src/constants/sampleRequirement.js   ← user-facing sample
                              │
                              │  (must be kept in lock-step)
                              ▼
helix-backend/tests/test_golden_pipeline.py         ← GOLDEN_REQUIREMENT constant
                              │
                              ▼
            run_demo(project, use_ai=False)         ← full 11-step pipeline
                              │
                              ▼
       assertions on stories / tasks / tests /
       ambiguities / risks / readiness / export
                              │
                              ▼
.github/workflows/golden-pipeline.yml               ← gates every push + PR
```

The test runs **in mock mode** (`HELIX_USE_AI=false`, no LLM keys
configured) so CI is free, fast, and immune to provider outages. The
mock agents in `helix-backend/app/services/mock_agents.py` are
clause-driven, so giving them the focused checkout brief produces a
realistic, deterministic e-commerce package every run.

---

## 4. Running the contract locally

```powershell
cd helix-backend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/test_golden_pipeline.py -v
```

Expected output (abridged):

```
tests/test_golden_pipeline.py::test_pipeline_runs_all_steps              PASSED
tests/test_golden_pipeline.py::test_no_step_emits_error                  PASSED
tests/test_golden_pipeline.py::test_stories_tasks_tests_non_empty        PASSED
tests/test_golden_pipeline.py::test_every_artifact_cites_a_clause        PASSED
tests/test_golden_pipeline.py::test_tests_reference_real_stories         PASSED
tests/test_golden_pipeline.py::test_ambiguities_and_risks_surface        PASSED
tests/test_golden_pipeline.py::test_readiness_is_live_not_hardcoded      PASSED
tests/test_golden_pipeline.py::test_export_artifacts_populated           PASSED
================================== 8 passed in ~Xs ==================================
```

If anything fails on `main`, **do not ship**. Open the failing
assertion, find the regression in the agents or orchestrator, fix it,
and re-run.

---

## 5. Editing the golden requirement

If you genuinely need to change the brief (rare):

1. Edit **`helix-frontend/src/constants/sampleRequirement.js`** — the
   user-facing source of truth.
2. Mirror the change into the `GOLDEN_REQUIREMENT` constant in
   **`helix-backend/tests/test_golden_pipeline.py`**.
3. Update the verbatim quotes in
   **[`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md)** §1 so the live pitch
   still matches what the judge sees.
4. Re-run `pytest tests/test_golden_pipeline.py -v` and fix any
   regressions in the agents or in the thresholds.
5. If you adjust a threshold in this doc, change it in the test in the
   same commit.

The design rules at the top of `sampleRequirement.js` exist to keep
the brief in the demo's *sweet spot*: focused enough that judges can
follow, ambiguous enough to showcase the Ambiguity agent, quantified
enough to give the Risk + Quality agents anchors.

---

## 6. Why this matters for judging

The rubric weakness reviewers keep hitting is **"Functional MVP — does
the core flow actually work end-to-end?"** This contract is the
single, mechanical answer to that question:

> *"Yes. We run the full 11-step pipeline on our golden e-commerce
> requirement in CI on every commit, and we assert eight non-negotiable
> properties about the output. If any of them ever regress, the build
> goes red and the demo can't ship. The contract is in version control
> at `docs/GOLDEN_DOMAIN.md`."*

That is a **demonstrable functional MVP** — not a promise, not a
slide. It's a green check on the README.
