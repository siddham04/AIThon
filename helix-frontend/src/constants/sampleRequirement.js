/**
 * Helix golden-domain sample requirement.
 *
 * This is the **canonical e-commerce checkout PRD** used for:
 *   - The Mission Control "Load sample requirement" button
 *   - The onboarding modal "Try a sample" path
 *   - The DEMO_SCRIPT.md verbatim pitch (every italic quote in §2 of
 *     that file appears here)
 *   - The backend golden-pipeline pytest contract
 *     (`helix-backend/tests/test_golden_pipeline.py`)
 *
 * Design rules — change them only on purpose:
 *
 *  1. Domain is **e-commerce checkout** (not the previous catch-all
 *     "Unified Pay & Identity"). One domain = bulletproof demos.
 *  2. Atomic-clause splitter (`split_into_clauses`) should produce
 *     6–10 clauses. Each clause becomes a citation target downstream.
 *  3. At least 4 quantitative SLOs (`< 200 ms`, `99.9%`, `< 10 s`,
 *     `1k concurrent`) so the Risk + Quality agents have measurable
 *     anchors and don't degrade to generic NFR output.
 *  4. Exactly 3 *deliberate* ambiguities — vendor TBD, "fast" refunds,
 *     "where it makes sense" currency policy — so the Ambiguity agent
 *     has clear, demoable wins WITHOUT drowning the brief in vague
 *     language.
 *  5. Auth + PCI mentions present so the Risk agent reliably emits
 *     security + compliance risks.
 *  6. Two or more personas so the Decomposer never collapses to one.
 *
 * If you edit this file, run the contract test:
 *
 *   cd helix-backend
 *   pip install -r requirements-dev.txt
 *   pytest tests/test_golden_pipeline.py -v
 */
export const SAMPLE_REQUIREMENT = `Title: Checkout Revamp Initiative

Goal: Cut cart abandonment by delivering a fast, trustworthy checkout
flow for returning shoppers and a clear ops surface for support agents.

Functional requirements:
- Authenticated shoppers must complete checkout in 3 steps or fewer:
  review cart, choose payment, confirm.
- Show a delivery date estimate before payment within 200 ms P95.
- Accept saved cards and one digital wallet at launch; vendor selection
  is TBD pending procurement review.
- Inventory must decrement atomically when an order is confirmed so two
  shoppers cannot oversell the last unit.
- Support agents need a refund action from the order detail page;
  refunds should happen "fast" (legal still drafting the SLA wording).
- International shoppers see prices in their local currency
  "where it makes sense" — exact FX/rounding policy is undefined.

Non-functional requirements:
- p95 checkout API latency must stay under 300 ms at 1k concurrent
  shoppers.
- Payment provider uptime assumption: 99.9% monthly availability.
- PCI scope must remain SAQ-A: never store or transmit raw PAN data.
- All authentication uses short-lived JWTs (≤ 15 min) refreshed via a
  secure HTTP-only cookie; sessions must be revocable from the support
  console.

Success metrics:
- Checkout completion rate up 8 percentage points within one quarter.
- Zero oversell incidents per 10k orders.
- Support tickets tagged "payment failed randomly" drop by 50%.

Out of scope (this initiative):
- Crypto / BNPL payment methods.
- Tax-jurisdiction logic outside the EU.
- Offline / kiosk checkout mode.
`
