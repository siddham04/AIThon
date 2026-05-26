"""Reproduce the user's quality-scorer issue on the TOMP PRD.
Should NOT score 4% F when the PRD has 6 roles, GWT acceptance criteria, BR-1..BR-6."""
from __future__ import annotations

import asyncio
import os
import sys

os.environ["HELIX_USE_AI"] = "false"
for k in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OAI_KEY",
          "AZURE_OAI_ENDPOINT", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND)

from app.services.quality_scorer import (  # noqa: E402
    _heuristic_score,
    _heuristic_missing,
    _heuristic_completeness,
    _DIMENSION_CUES,
    _enterprise_dimensions,
    score_requirement_text,
)

PRD = """Telecom Order Management Platform (TOMP)
Product Requirements Document
Version 1.0

1. Executive Summary
The Telecom Order Management Platform will provide a centralized solution for
managing customer orders across mobile, broadband, fiber, IPTV, and enterprise
connectivity services. The platform will automate the complete order lifecycle
from order capture through provisioning, activation, billing, fulfillment, and
service assurance. The system should support both B2C and B2B customers.

2. Business Problem
Current order fulfillment suffers from manual order processing, multiple
disconnected systems, delayed activations, high fallout rates, duplicate data
entry, and poor customer visibility. Current average activation time: Mobile 2
days, Fiber 7 days, Enterprise VPN 15 days. Target: reduce activation time by
50%, reduce order fallout by 40%, improve first-time-right fulfillment.

3. Business Objectives
Centralize order management. Automate service provisioning. Improve order
tracking. Reduce manual intervention. Improve customer experience.
Success Metrics: Order completion rate > 98%; Activation SLA compliance > 95%;
Order fallout < 2%; Customer satisfaction increase by 20%.

4. User Roles
Customer can place service orders, track order status, upload documents,
schedule installations. Sales Agent can create orders, modify orders, submit
orders on behalf of customers. Provisioning Engineer can review provisioning
requests, resolve failures, retry activations. Field Technician can receive
installation assignments, update installation status, upload installation
evidence. Order Manager can monitor orders, escalate delays, override workflow
decisions. Operations Administrator can configure workflows, manage products,
manage integrations.

5. Functional Requirements
FR-1 Customer Order Capture: The system shall allow users to create service
orders. The system shall validate mandatory fields before submission.
FR-2 Product Eligibility Validation: The system shall validate network
availability, coverage area, product eligibility, service feasibility. Orders
failing validation shall be rejected.
FR-3 KYC Verification: The system shall integrate with external KYC services.
Failed verification shall prevent order progression.
FR-4 Order Decomposition: Complex orders shall be decomposed into service
orders. Each service order shall be tracked independently.
FR-13 Fallout Management: Order fallout occurs when processing fails. The
system shall classify fallout, route to appropriate teams, track resolution.

6. Non-Functional Requirements
Availability: 99.99%. Performance: 95% of API responses under 2 seconds.
Scalability: Support 10 million subscribers, 1 million monthly orders, 50,000
concurrent users. Security: MFA, RBAC, Encryption at Rest, Encryption in
Transit, Audit Logging. Compliance: GDPR, ISO 27001, PCI-DSS.

7. Business Rules
BR-1 Enterprise services above $50,000 require manager approval.
BR-2 Fiber orders require network feasibility verification.
BR-3 Failed KYC automatically cancels order.
BR-4 Three provisioning failures escalate to operations.
BR-5 Cancelled orders must release reserved inventory.
BR-6 Installation appointments cannot overlap for a technician.

11. Sample User Story
US-001 As a customer, I want to order a fiber broadband connection online, So
that I can activate internet service without visiting a store.
Acceptance Criteria: Given coverage is available, When I submit a valid order
and complete KYC verification, Then the order should be accepted and an
installation appointment should be scheduled automatically.
"""


def main() -> None:
    print(f"PRD length: {len(PRD)} chars, {len(PRD.split())} words")
    print()

    print("==== Per-dimension keyword hits ====")
    txt = PRD.lower()
    for dim, (title, cues) in _DIMENSION_CUES.items():
        hits = [c for c in cues if c in txt]
        marker = "MISSING" if not hits else f"{len(hits)} hits"
        print(f"  {dim.value:<22} {marker:<10}  {title:<35}  cues_hit={hits[:5]}")
    print()

    print("==== Heuristic core ====")
    h = _heuristic_score(PRD)
    print(f"  completeness raw  : {h['breakdown']['completeness']}  (=> {h['breakdown']['completeness']*100:.1f}/100)")
    print(f"  specificity       : {h['breakdown']['specificity']}")
    print(f"  structure         : {h['breakdown']['structure']}")
    print(f"  vocabulary        : {h['breakdown']['vocabulary']}")
    print(f"  testability       : {h['breakdown']['testability']}")
    print(f"  -> quality        : {h['quality']}/100")
    print(f"  -> ambiguity      : {h['ambiguity']}/100")
    print()

    dims = _enterprise_dimensions(h, ambiguity=h["ambiguity"])
    print(f"  enterprise dims   :")
    for k, v in dims.items():
        print(f"     {k:<16} = {v}")
    print()

    missing = _heuristic_missing(PRD)
    print(f"==== _heuristic_missing -> {len(missing)} entries ====")
    for m in missing[:8]:
        print(f"   - {m.dimension.value:<22} {m.title}")
    print()

    print("==== full report (await score_requirement_text) ====")
    r = asyncio.run(score_requirement_text(PRD, use_ai=False))
    print(f"  overall_score   : {r.overall_score}  grade={r.grade}")
    print(f"  clarity         : {r.clarity}")
    print(f"  completeness    : {r.completeness}")
    print(f"  testability     : {r.testability}")
    print(f"  ambiguity       : {r.ambiguity}")
    print(f"  highlights      : {r.highlight_gaps}")


if __name__ == "__main__":
    main()
