"""End-to-end smoke that mirrors the EXACT flow the AI Workspace UI follows.

1. Authenticate as guest.
2. Ingest a TOMP-shaped PRD → get back a real project id.
3. Launch the persisted demo pipeline (the one the UI uses).
4. Fetch every workspace slice (artifacts, tests, quality, review,
   sprintPlan, prd, architectureDiagram, apiContracts).
5. Print judge-relevant counts so we can prove that:
     * tasks ≥ 5x stories (was 1:1)
     * architecture has layers + nodes (was "not visible")
     * api contracts has REST endpoints (was "not visible")
     * sprint plan has tasks (was "pending")

Run only against a backend started in mock mode — never against
prod (the script wipes nothing but does spawn synthetic users).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api"

PRD = """Telecom Order Management Platform (TOMP) PRD v1.

Executive Summary. The Telecom Order Management Platform will provide a
centralized solution for managing customer orders across mobile, broadband,
fiber, IPTV, and enterprise connectivity. The platform will automate the
order lifecycle from capture through provisioning, activation, billing,
fulfillment, and assurance. Both B2C and B2B customers must be supported.

User Roles. Customer can place service orders, track status, upload
documents. Sales Agent can create and modify orders. Provisioning Engineer
reviews provisioning and resolves failures. Field Technician receives
installation assignments. Operations Administrator manages workflows.

Functional Requirements. FR-1 customers shall create service orders. FR-2
system shall validate network availability and product eligibility. FR-3
system shall integrate with external KYC services and reject failures.
FR-4 complex orders shall decompose into service orders. FR-5 system shall
provision through OSS systems with remediation. FR-6 customers select
installation slots, technicians receive assignments. FR-7 customers track
order progress in real time. FR-8 customers modify orders before activation.
FR-9 orders may be cancelled with reversal. FR-10 send SMS/email/push
notifications. FR-11 activated services create billing accounts. FR-12 SLA
monitoring with alerts. FR-13 fallout classified and routed to teams.
FR-14 audit log retention 7 years.

Business Rules. BR-1 enterprise services above $50,000 require manager
approval. BR-2 fiber requires feasibility verification. BR-3 failed KYC
cancels the order. BR-4 three provisioning failures escalate. BR-5
cancelled orders release reserved inventory. BR-6 installation appointments
cannot overlap.

Non-Functional Requirements. Availability 99.99%. 95% API responses under
2 seconds. Support 10 million subscribers, 1 million monthly orders,
50,000 concurrent users. Security MFA, RBAC, encryption at rest and in
transit, audit logging. Compliance GDPR, ISO 27001, PCI-DSS.

Acceptance Criteria. Given coverage is available, When the customer
submits a valid order and completes KYC verification, Then the order
shall be accepted and an installation appointment shall be scheduled.
"""


def _request(method: str, path: str, *, body=None, token=None, stream=False):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if stream:
        headers["Accept"] = "text/event-stream"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    return urllib.request.urlopen(req, timeout=60)


def _post(path, body, token=None):
    with _request("POST", path, body=body, token=token) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path, token=None):
    with _request("GET", path, token=token) as r:
        return json.loads(r.read().decode("utf-8"))


def _stream(path, body, token):
    seen_complete = False
    with _request("POST", path, body=body, token=token, stream=True) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if not payload:
                continue
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("status") == "complete":
                seen_complete = True
                break
    return seen_complete


def main() -> None:
    t0 = time.monotonic()
    print("Step 1/5 — guest login")
    token = _post("/auth/guest", {})["access_token"]

    print("Step 2/5 — ingest TOMP PRD")
    ing = _post("/ingest/text", {"text": PRD}, token=token)
    project_id = ing.get("project_id") or ing.get("id") or ing.get("project", {}).get("id")
    if not project_id:
        print(f"  ! could not derive project id from {ing.keys()}", file=sys.stderr)
        sys.exit(1)
    print(f"  project_id = {project_id}")

    print("Step 3/5 — launch persisted pipeline (this is what the UI does)")
    ok = _stream(f"/demo/{project_id}/run", {"use_ai": False}, token=token)
    print(f"  stream complete: {ok}")

    print("Step 4/5 — fetch workspace slices (mirrors loadWorkspaceData.js)")
    project = _get(f"/projects/{project_id}", token=token)
    artifacts = _get(f"/artifacts/{project_id}", token=token)
    tests = _get(f"/testcases/{project_id}", token=token)
    sprint_plan = _get(f"/sprint-plan/{project_id}/auto", token=token)
    arch = _get(f"/studio/diagram/{project_id}", token=token)
    apis = _get(f"/devstudio/contract/{project_id}", token=token)
    summary = _get(f"/executive/{project_id}/delivery-summary", token=token)

    print("Step 5/5 — summary")
    print(f"  elapsed: {(time.monotonic() - t0):.2f}s")
    print()

    # Pull counts from whichever shape the endpoint returned.
    stories = artifacts.get("stories") if isinstance(artifacts, dict) else []
    tasks = artifacts.get("tasks") if isinstance(artifacts, dict) else []
    test_list = tests if isinstance(tests, list) else (tests.get("test_cases") or [])
    contract_list = (apis or {}).get("contracts") or []
    layer_list = (arch or {}).get("layers") or []
    plan_tasks = (sprint_plan or {}).get("tasks") or []

    print("==== ARTIFACT COUNTS ====")
    print(f"  stories          : {len(stories)}")
    print(f"  tasks            : {len(tasks)}    (target >= 5x stories)")
    print(f"  tests            : {len(test_list)}")
    print(f"  api_contracts    : {len(contract_list)}")
    print(f"  architecture     : {len(layer_list)} layers, "
          f"{(arch or {}).get('nodes_count', 0)} nodes")
    print(f"  sprint_plan      : {len(plan_tasks)} tasks, "
          f"{(sprint_plan or {}).get('total_story_points', 0)} pts")
    print()

    print("==== HEALTH CHECKS ====")
    checks = [
        ("tasks >= 5x stories", len(tasks) >= 5 * max(len(stories), 1)),
        ("architecture has >= 3 layers", len(layer_list) >= 3),
        ("api contracts has >= 4 endpoints", len(contract_list) >= 4),
        ("sprint plan has tasks", len(plan_tasks) > 0),
        ("tests >= 10", len(test_list) >= 10),
    ]
    for label, passed in checks:
        marker = "PASS" if passed else "FAIL"
        print(f"  {marker:<4}  {label}")

    print()
    print("==== ARCHITECTURE LAYERS ====")
    for layer in layer_list[:6]:
        items = layer.get("items") or []
        print(f"  {layer.get('name', '?'):<18} : {', '.join(items[:6])}")

    print()
    print("==== API CONTRACTS (first 10) ====")
    for c in contract_list[:10]:
        method = c.get("method", "?")
        endpoint = c.get("endpoint", "?")
        print(f"  {method:<6} {endpoint}")

    print()
    print("==== SAMPLE LANE-FANOUT TASKS (first 12) ====")
    for t in (tasks or [])[:12]:
        skills = (t.get("skills") or [])
        title = (t.get("title") or "")[:80]
        print(f"  - {title} [{', '.join(skills[:3])}]")

    print()
    print("==== EXECUTIVE DELIVERY SUMMARY (Approve & Export hero) ====")
    if summary:
        print(f"  Project           : {summary.get('project_name')}")
        print(f"  Requirements      : {summary.get('requirements_count')}")
        print(f"  Epics             : {summary.get('epics_count')}")
        print(f"  Stories           : {summary.get('stories_count')}")
        print(f"  Tasks             : {summary.get('tasks_count')}")
        print(f"  APIs              : {summary.get('apis_count')}")
        print(f"  Test Cases        : {summary.get('test_cases_count')}")
        print(f"  Risks             : {summary.get('risks_count')}")
        print(f"  Ambiguities       : {summary.get('ambiguities_count')}")
        print(f"  Arch Components   : {summary.get('architecture_components_count')}")
        print(f"  Readiness Score   : {summary.get('readiness_score')}/100")
        print(f"  Quality Score     : {summary.get('quality_score')}/100")
        print(f"  Confidence Score  : {summary.get('confidence_score')}/100")
        print(f"  Sprints           : {summary.get('sprint_count')}")
        print(f"  Delivery (weeks)  : {summary.get('estimated_delivery_weeks')}")
        print(f"  Total Story Pts   : {summary.get('estimated_total_points')}")
        print(f"  Total Hours       : {summary.get('estimated_total_hours')}")
        print(f"  Projected Cost    : ${summary.get('projected_cost_usd'):,.0f} "
              f"(@${summary.get('blended_hourly_rate_usd'):.0f}/hr)")
        print(f"  Hours Saved       : {summary.get('hours_saved_vs_manual'):,}")
        print(f"  Cost Saved        : ${summary.get('cost_saved_usd'):,.0f}")
        print(f"  Weeks Saved       : {summary.get('weeks_saved_vs_manual')}")
        print(f"  >>> VERDICT       : {summary.get('verdict_label', '?').upper()} <<<")
        for r in (summary.get("verdict_reasons") or [])[:4]:
            print(f"      + {r}")
        for b in (summary.get("blocking_items") or [])[:4]:
            print(f"      ! {b}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTPError {exc.code} at {exc.url}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
