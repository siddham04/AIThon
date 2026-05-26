# One-click checkout & stock integrity

_Fast checkout with consistent inventory under load._

## Objective
Increase conversion while preventing overselling.

## In scope
- Card/wallet payments
- Inventory reservation
- Latency SLO

## Out of scope
- Tax jurisdictions outside EU
- Offline mode

## Success metrics
- Checkout completion rate
- Oversell incidents = 0

## User Stories
### Pay and confirm order  `story_demo_001`
**As a** Returning shopper, **I want** Complete purchase quickly, **so that** Fewer abandoned carts.

**Acceptance criteria:**
- Given items in cart, when user pays, then order is confirmed
- Receipt shown within 2s of provider callback

### Show delivery date before payment  `story_demo_002`
**As a** Shopper, **I want** See accurate delivery estimate, **so that** Reduce cart abandonment.

**Acceptance criteria:**
- Given cart with address, when viewing checkout, then delivery date displays
- Estimate renders within 200ms P95

## Engineering Tasks
- **[feature]** Integrate payment webhook idempotency `task_demo_001` — 5sp / 6.0h
  - Handle duplicate callbacks without double charge.
- **[feature]** Atomic inventory decrement `task_demo_002` — 8sp / 8.0h
  - Use transaction / compare-and-swap to prevent oversell.
- **[feature]** Delivery estimate API `task_demo_003` — 5sp / 5.0h
  - Compute shipping ETA from warehouse + carrier rules.

## Test Plan
- **[integration]** Successful checkout deducts stock once `test_demo_001`
  - Given SKU A has qty 1
  - When Two parallel checkouts race
  - Then Exactly one succeeds; the other gets sold-out

## Ambiguities
- **[medium/unquantified]** Peak vs sustained load not specified.
  - Excerpt: _1k concurrent users_
  - Ask: Is 1k concurrent checkout sessions or total active users?

## Risks
- **[high/scalability]** Hot SKU contention
  - High concurrency may bottleneck row locks.
  - Mitigation: Partition inventory or queue reservations.


---

_Generated at 2026-05-26 09:05 UTC · model o3 · user demo@demo.com_
