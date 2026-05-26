"""End-to-end SSE smoke: hit the running backend, ingest a tiny PRD, launch
the demo pipeline, and print every SSE event with timing so we can prove
the orchestrator streams progress (no UI required)."""
from __future__ import annotations

import json
import sys
import time
import urllib.request


BASE = "http://127.0.0.1:8000/api"

PRD = """Telecom Order Management Platform (TOMP) PRD v1.

User Roles. Customer can place service orders, track order status, upload
documents, and schedule installation. Sales Agent can create orders, modify
orders, and submit on behalf of customers. Provisioning Engineer can review
provisioning requests and resolve failures. Field Technician can receive
installation assignments and update status. Operations Administrator manages
products, workflows, and integrations.

Functional Requirements. FR-1 customers shall create service orders.
FR-2 system shall validate network availability, coverage, eligibility.
FR-3 system shall integrate with external KYC services and reject failures.
FR-13 fallout shall be classified, routed to teams, tracked to resolution.

Business Rules. BR-1 enterprise services above $50,000 require manager
approval. BR-2 fiber orders require feasibility verification. BR-3 failed
KYC cancels the order. BR-4 three provisioning failures escalate to ops.

Non-Functional Requirements. Availability 99.99%. 95% of API responses
under 2 seconds. Support 10 million subscribers, 1 million monthly orders.
Security MFA, RBAC, encryption at rest and in transit, audit logging.
Compliance GDPR, ISO 27001, PCI-DSS.

Acceptance Criteria. Given coverage is available, When the customer submits
a valid order, Then the order shall be accepted and installation scheduled.
"""


def _post(path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _stream(path: str, body: dict | None = None, token: str | None = None) -> None:
    headers = {"Accept": "text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST" if data else "GET")
    t0 = time.monotonic()
    last_step = None
    with urllib.request.urlopen(req, timeout=120) as r:
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
            dt = (time.monotonic() - t0) * 1000.0
            step = ev.get("step", "?")
            status = ev.get("status", "?")
            pct = ev.get("percent", "")
            headline = (ev.get("headline") or "")[:64]
            tag = "  " if step == last_step else "> "
            print(f"{dt:7.0f} ms  {tag}{step:<14} {status:<7} {pct:>3}%  {headline}")
            last_step = step
            if status == "complete":
                break


def main() -> None:
    auth = _post("/auth/guest", {})
    token = auth["access_token"]
    print(f"  · guest token acquired")

    print()
    print(f"{'elapsed':>7}      {'step':<14} {'status':<7} {'pct':>4}  headline")
    print("-" * 90)
    # Capture quality + story events so we can show the fixed outputs.
    events: list[dict] = []
    headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    req = urllib.request.Request(f"{BASE}/demo/run",
                                  data=json.dumps({"requirement": PRD, "use_ai": False}).encode("utf-8"),
                                  headers=headers, method="POST")
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as r:
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
            events.append(ev)
            dt = (time.monotonic() - t0) * 1000.0
            step = ev.get("step", "?"); status = ev.get("status", "?")
            pct = ev.get("percent", ""); headline = (ev.get("headline") or "")[:64]
            print(f"{dt:7.0f} ms     {step:<14} {status:<7} {pct:>3}%  {headline}")
            if status == "complete":
                break
    print("-" * 90)

    # Spotlight the dimensions the user's last run showed regressions on.
    print()
    print("==== QUALITY STEP DETAIL (was '4% F') ====")
    q = next((e for e in events if e.get("step") == "quality" and e.get("status") == "done"), None)
    if q:
        a = q.get("artifact") or {}
        print(f"  overall_score: {a.get('overall_score')}    grade: {a.get('grade')}")
        print(f"  clarity={a.get('clarity')} completeness={a.get('completeness')} testability={a.get('testability')} ambiguity={a.get('ambiguity')}")
        print(f"  highlight_gaps: {a.get('highlight_gaps')}")

    print()
    print("==== STORIES STEP DETAIL (was 'I want Place ...') ====")
    s = next((e for e in events if e.get("step") == "stories" and e.get("status") == "done"), None)
    if s:
        a = s.get("artifact") or {}
        story_count = a.get("story_count") or len(a.get("stories") or [])
        task_count = a.get("task_count")
        print(f"  Stories: {story_count}   Tasks: {task_count}   (target >= 5x ratio)")
        for story in (a.get("stories") or [])[:3]:
            persona = story.get("persona") or "?"
            goal = story.get("goal") or "?"
            benefit = story.get("benefit") or "?"
            print(f"    - As a {persona}, I want {goal}, so that {benefit}.")

    print()
    print("==== ARCHITECTURE STEP DETAIL (was 'not visible') ====")
    arch = next((e for e in events if e.get("step") == "architecture" and e.get("status") == "done"), None)
    if arch:
        a = arch.get("artifact") or {}
        print(f"  headline: {arch.get('headline')}")
        for layer in (a.get("layers") or [])[:6]:
            items = layer.get("items") or []
            print(f"    {layer.get('name', '?'):<18} : {', '.join(items[:5])}{'...' if len(items) > 5 else ''}")

    print()
    print("==== APIS STEP DETAIL (was 'not visible') ====")
    apis = next((e for e in events if e.get("step") == "apis" and e.get("status") == "done"), None)
    if apis:
        a = apis.get("artifact") or {}
        print(f"  headline: {apis.get('headline')}")
        for c in (a.get("contracts") or [])[:8]:
            print(f"    {c.get('method', '?'):<6} {c.get('endpoint', '?')}")

    print()
    print("==== JIRA STEP DETAIL (was '11 tasks for 11 stories') ====")
    jira = next((e for e in events if e.get("step") == "jira" and e.get("status") == "done"), None)
    if jira:
        print(f"  headline: {jira.get('headline')}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTPError {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
        raise
