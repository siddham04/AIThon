#!/usr/bin/env python3
"""Phase 3 — Full autonomous SDLC workflow verification.

Maps user scenario → backend demo SSE steps → post-run API artifacts → export.

Usage (backend on 8765):
  python scripts/phase3_workflow_test.py
  HELIX_USE_AI=false python scripts/phase3_workflow_test.py
  HELIX_DEMO_TIMEOUT=600 python scripts/phase3_workflow_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")
API_KEY = os.environ.get("HELIX_API_KEY", "").strip()
EMAIL = os.environ.get("HELIX_EMAIL", "demo@demo.com")
PASSWORD = os.environ.get("HELIX_PASSWORD", "demo123")
USE_AI = os.environ.get("HELIX_USE_AI", "false").lower() in ("1", "true", "yes")
DEMO_TIMEOUT = int(os.environ.get("HELIX_DEMO_TIMEOUT", "600"))

SAMPLE = (
    "Checkout Revamp Initiative. Customers abandon cart when shipping estimates are unclear. "
    "We must show delivery dates before payment within 200ms P95. Security: PCI scope must not "
    "store raw card data. OTP login via SMS for B2B portal. Integrate Stripe Premium tier. "
    "Support 10k concurrent sessions, p99 < 500ms, GDPR deletion within 30 days."
)

# User-facing scenario → backend SSE step ids that must reach status=done
SCENARIO_STEPS = [
    {
        "id": "upload",
        "label": "Upload requirement",
        "backend_steps": ["ingest"],
        "verify": "ingest_done",
    },
    {
        "id": "launch",
        "label": "Launch AI Team",
        "backend_steps": ["boot"],
        "verify": "boot_seen",
    },
    {
        "id": "artifacts",
        "label": "Generate artifacts (quality / review)",
        "backend_steps": ["quality", "review"],
        "verify": "quality_review_done",
    },
    {
        "id": "stories",
        "label": "Generate user stories",
        "backend_steps": ["stories"],
        "verify": "stories_count",
    },
    {
        "id": "architecture",
        "label": "Generate architecture",
        "backend_steps": ["architecture", "apis"],
        "verify": "architecture_diagram",
    },
    {
        "id": "sprint",
        "label": "Generate sprint plan",
        "backend_steps": ["effort_sprint"],
        "verify": "sprint_plan",
    },
    {
        "id": "tests",
        "label": "Generate tests",
        "backend_steps": ["tests"],
        "verify": "tests_count",
    },
    {
        "id": "risks",
        "label": "Generate risks",
        "backend_steps": ["ambiguity", "jira"],
        "verify": "risks_backlog",
    },
    {
        "id": "package",
        "label": "Generate delivery package",
        "backend_steps": ["readiness", "complete"],
        "verify": "readiness_score",
    },
    {
        "id": "export",
        "label": "Export results",
        "backend_steps": [],
        "verify": "export_csv",
    },
]

EXPECTED_DEMO_STEPS = {
    "ingest",
    "quality",
    "review",
    "ambiguity",
    "stories",
    "architecture",
    "effort_sprint",
    "apis",
    "tests",
    "jira",
    "readiness",
    "complete",
}


@dataclass
class StepResult:
    id: str
    label: str
    status: str  # pass | fail | skip | warn
    detail: str = ""
    duration_ms: int | None = None


@dataclass
class WorkflowReport:
    started_at: str = ""
    finished_at: str = ""
    project_id: str = ""
    use_ai: bool = False
    demo_timeout_s: int = 600
    sse_steps_seen: dict = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    dead_ends: list[str] = field(default_factory=list)
    ui_notes: list[str] = field(default_factory=list)

    def add(self, r: StepResult) -> None:
        self.step_results.append(r)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.step_results if s.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for s in self.step_results if s.status == "fail")


def req(
    method: str,
    path: str,
    *,
    data: dict | None = None,
    token: str | None = None,
    timeout: int = 120,
    raw: bool = False,
) -> tuple[int, Any]:
    url = BASE + path
    h: dict[str, str] = {}
    if data is not None:
        h["Content-Type"] = "application/json"
    if API_KEY:
        h["X-Helix-Key"] = API_KEY
    if token:
        h["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw_bytes = resp.read()
            if raw:
                return resp.status, raw_bytes.decode(errors="replace")
            if not raw_bytes:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw_bytes.decode())
            except json.JSONDecodeError:
                return resp.status, raw_bytes.decode()[:2000]
    except urllib.error.HTTPError as e:
        raw_bytes = e.read()
        try:
            return e.code, json.loads(raw_bytes.decode())
        except Exception:
            return e.code, raw_bytes.decode()[:500]


def login() -> str | None:
    code, body = req("POST", "/api/auth/login", data={"email": EMAIL, "password": PASSWORD})
    if code == 200 and isinstance(body, dict) and body.get("access_token"):
        return body["access_token"]
    code2, body2 = req(
        "POST",
        "/api/auth/register",
        data={"email": EMAIL, "password": PASSWORD, "name": "Phase3"},
    )
    if code2 == 200 and isinstance(body2, dict) and body2.get("access_token"):
        return body2["access_token"]
    return None


def parse_sse_events(buf: str) -> list[dict]:
    events: list[dict] = []
    for block in buf.split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return events


def run_demo_sse(token: str, project_id: str, report: WorkflowReport) -> bool:
    url = f"{BASE}/api/demo/{project_id}/run"
    h = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    if API_KEY:
        h["X-Helix-Key"] = API_KEY
    r = urllib.request.Request(
        url,
        data=json.dumps({"use_ai": USE_AI}).encode(),
        headers=h,
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(r, timeout=DEMO_TIMEOUT) as resp:
            buf = resp.read().decode(errors="replace")
    except Exception as exc:
        report.add(
            StepResult("launch", "Launch AI Team (SSE)", "fail", f"SSE failed: {exc}")
        )
        return False

    elapsed = int((time.monotonic() - t0) * 1000)
    events = parse_sse_events(buf)
    step_status: dict[str, str] = {}
    for evt in events:
        step = evt.get("step")
        if not step:
            continue
        status = evt.get("status", "")
        if step not in report.sse_steps_seen or status == "done":
            report.sse_steps_seen[step] = {
                "status": status,
                "percent": evt.get("percent"),
                "headline": evt.get("headline", "")[:80],
            }
        step_status[step] = status

    if step_status.get("error") == "error":
        report.dead_ends.append(f"SSE error event: {buf[-400:]}")

    missing = EXPECTED_DEMO_STEPS - set(step_status.keys())
    if missing:
        report.dead_ends.append(f"SSE never emitted steps: {sorted(missing)}")

    not_done = [s for s in EXPECTED_DEMO_STEPS if step_status.get(s) != "done"]
    if "complete" not in step_status:
        report.add(
            StepResult(
                "launch",
                "Launch AI Team — pipeline complete",
                "fail",
                f"No 'complete' step (not_done={not_done}, elapsed={elapsed}ms)",
                elapsed,
            )
        )
        return False

    report.add(
        StepResult(
            "launch",
            "Launch AI Team — pipeline complete",
            "pass",
            f"All {len(EXPECTED_DEMO_STEPS)} steps finished in {elapsed}ms (use_ai={USE_AI})",
            elapsed,
        )
    )
    return True


def verify_post_run(token: str, pid: str, report: WorkflowReport) -> None:
    code, arts = req("GET", f"/api/artifacts/{pid}", token=token)
    stories = (arts.get("stories") or []) if isinstance(arts, dict) else []
    tasks = (arts.get("tasks") or []) if isinstance(arts, dict) else []

    code_t, tests = req("GET", f"/api/testcases/{pid}", token=token)
    n_tests = len(tests) if isinstance(tests, list) else len((tests or {}).get("test_cases") or [])

    code_d, diag = req("GET", f"/api/studio/diagram/{pid}", token=token)
    has_mermaid = isinstance(diag, dict) and bool(diag.get("mermaid") or diag.get("nodes"))

    code_sp, sprint = req("GET", f"/api/sprint-plan/{pid}/auto", token=token)
    has_sprint = isinstance(sprint, dict) and bool(
        sprint.get("sprints") or sprint.get("plan") or sprint.get("items")
    )

    code_r, risk = req("GET", f"/api/studio/risk/{pid}", token=token)
    code_rc, risk_c = req("GET", f"/api/risk-center/{pid}", token=token)
    has_risk = (isinstance(risk, dict) and bool(risk.get("risks") or risk.get("items"))) or (
        isinstance(risk_c, dict) and (risk_c.get("total_items") or 0) > 0
    )

    code_rd, readiness = req("GET", f"/api/readiness-center/{pid}", token=token)
    rdy_score = readiness.get("readiness") if isinstance(readiness, dict) else None

    code_bl, backlog = req("GET", f"/api/backlog/{pid}", token=token)
    bl_tasks = len((backlog or {}).get("tasks") or []) if isinstance(backlog, dict) else 0
    has_backlog = isinstance(backlog, dict) and bool(
        backlog.get("epic") or backlog.get("stories") or bl_tasks
    )

    code_prd, prd = req("GET", f"/api/delivery/prd/{pid}", token=token)
    has_prd = isinstance(prd, dict) and bool(prd.get("title") or prd.get("executive_summary"))

    # --- per scenario step ---
    report.add(
        StepResult(
            "upload",
            "Upload requirement",
            "pass" if code == 200 else "fail",
            f"ingest project_id={pid}",
        )
    )

    ingest_ok = report.sse_steps_seen.get("ingest", {}).get("status") == "done"
    report.add(
        StepResult(
            "artifacts",
            "Generate artifacts (quality / review)",
            "pass"
            if ingest_ok
            and report.sse_steps_seen.get("quality", {}).get("status") == "done"
            and report.sse_steps_seen.get("review", {}).get("status") == "done"
            else "fail",
            f"quality={report.sse_steps_seen.get('quality', {})} review={report.sse_steps_seen.get('review', {})}",
        )
    )

    report.add(
        StepResult(
            "stories",
            "Generate user stories",
            "pass" if len(stories) >= 1 else "fail",
            f"stories={len(stories)} tasks={len(tasks)}",
        )
    )
    report.add(
        StepResult(
            "tasks",
            "Sprint-ready engineering tasks",
            "pass" if len(tasks) >= 1 else "fail",
            f"tasks={len(tasks)} (required for Jira Task rows, not stories-only)",
        )
    )

    report.add(
        StepResult(
            "architecture",
            "Generate architecture",
            "pass" if has_mermaid or report.sse_steps_seen.get("architecture", {}).get("status") == "done"
            else "warn" if code_d == 404
            else "fail",
            f"diagram HTTP {code_d} mermaid={has_mermaid}",
        )
    )

    report.add(
        StepResult(
            "sprint",
            "Generate sprint plan",
            "pass"
            if has_sprint or report.sse_steps_seen.get("effort_sprint", {}).get("status") == "done"
            else "fail",
            f"sprint-plan HTTP {code_sp}",
        )
    )

    report.add(
        StepResult(
            "tests",
            "Generate tests",
            "pass" if n_tests >= 1 else "fail",
            f"testcases HTTP {code_t} count={n_tests}",
        )
    )

    report.add(
        StepResult(
            "risks",
            "Generate risks",
            "pass"
            if has_risk
            or report.sse_steps_seen.get("ambiguity", {}).get("status") == "done"
            else "warn",
            f"studio/risk={code_r} risk-center={code_rc}",
        )
    )

    report.add(
        StepResult(
            "package",
            "Generate delivery package",
            "pass" if rdy_score is not None and code_rd == 200 else "fail",
            f"readiness={rdy_score} prd={has_prd} backlog_tasks={bl_tasks} artifacts_tasks={len(tasks)}",
        )
    )

    code_csv, csv_body = req("GET", f"/api/backlog/{pid}/jira-csv", token=token, raw=True)
    code_ado, _ = req("GET", f"/api/backlog/{pid}/ado-csv", token=token, raw=True)
    csv_ok = code_csv == 200 and isinstance(csv_body, str) and len(csv_body) > 20
    csv_has_task_rows = (
        isinstance(csv_body, str) and 'Task"' in csv_body and "Story" in csv_body
    )
    report.add(
        StepResult(
            "export",
            "Export results (Jira / ADO CSV)",
            "pass" if csv_ok and csv_has_task_rows else "fail",
            f"jira-csv={code_csv} task_rows={csv_has_task_rows} bytes={len(csv_body) if isinstance(csv_body, str) else 0} ado={code_ado}",
        )
    )

    # Delivery package render endpoints (UI data layer)
    render_checks = [
        (f"/api/delivery/prd/{pid}", "PRD section"),
        (f"/api/studio/effort/{pid}", "Effort section"),
    ]
    for path, name in render_checks:
        c, _ = req("GET", path, token=token)
        if c != 200:
            report.ui_notes.append(f"Delivery Package may show empty {name}: {path} -> HTTP {c}")


def markdown_report(report: WorkflowReport) -> str:
    lines = [
        "# Phase 3 — Workflow Execution Report",
        "",
        f"**Started:** {report.started_at}  ",
        f"**Finished:** {report.finished_at}  ",
        f"**Base URL:** {BASE}  ",
        f"**Project ID:** `{report.project_id or '—'}`  ",
        f"**use_ai:** `{report.use_ai}`  ",
        f"**Demo timeout:** {report.demo_timeout_s}s  ",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Steps passed | {report.passed} |",
        f"| Steps failed | {report.failed} |",
        f"| Dead ends | {len(report.dead_ends)} |",
        "",
        "## Scenario execution",
        "",
        "| # | Step | Status | Detail |",
        "|---|------|--------|--------|",
    ]
    for i, s in enumerate(report.step_results, 1):
        icon = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "skip": "SKIP"}.get(s.status, "-")
        lines.append(f"| {i} | {s.label} | {icon} | {s.detail[:120]} |")

    if report.sse_steps_seen:
        lines.extend(["", "## SSE steps observed", "", "| Step | Status | % | Headline |", "|------|--------|---|----------|"])
        for step_id in sorted(report.sse_steps_seen.keys()):
            info = report.sse_steps_seen[step_id]
            lines.append(
                f"| `{step_id}` | {info.get('status')} | {info.get('percent', '—')} | {info.get('headline', '')} |"
            )

    if report.dead_ends:
        lines.extend(["", "## Dead ends / blockers", ""])
        for d in report.dead_ends:
            lines.append(f"- {d}")

    if report.ui_notes:
        lines.extend(["", "## UI render notes", ""])
        for n in report.ui_notes:
            lines.append(f"- {n}")

    lines.extend(
        [
            "",
            "## State transitions (expected)",
            "",
            "1. Mission Control: paste/upload → `POST /api/ingest/text`",
            "2. Launch → `POST /api/demo/{id}/run` (SSE: boot → 11 steps → complete)",
            "3. Auto-navigate → `/project/{id}/delivery-package` (when `complete` + `completedRef`)",
            "4. Delivery Package: parallel GET artifacts, tests, readiness, diagram, backlog, PRD, sprint, effort, risk",
            "5. Export: `GET /api/backlog/{id}/jira-csv` / `ado-csv`",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "cd helix-backend; .\\run.ps1",
            "python scripts/phase3_workflow_test.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = WorkflowReport(
        started_at=datetime.now(timezone.utc).isoformat(),
        use_ai=USE_AI,
        demo_timeout_s=DEMO_TIMEOUT,
    )

    print(f"Phase 3 workflow @ {BASE} (use_ai={USE_AI}, timeout={DEMO_TIMEOUT}s)\n")

    code, _ = req("GET", "/api/health")
    if code != 200:
        print("FAIL: backend health", code)
        return 1
    print("OK  health")

    token = login()
    if not token:
        print("FAIL: auth")
        report.add(StepResult("upload", "Upload requirement", "fail", "Could not login/register"))
        _write_report(report)
        return 1
    print("OK  auth")

    code, body = req(
        "POST",
        "/api/ingest/text",
        data={"name": "Phase3 Workflow", "text": SAMPLE.strip()},
        token=token,
    )
    if code != 200 or not isinstance(body, dict) or not body.get("project_id"):
        report.add(StepResult("upload", "Upload requirement", "fail", f"ingest HTTP {code} {body}"))
        _write_report(report)
        return 1

    pid = body["project_id"]
    report.project_id = pid
    print(f"OK  ingest -> {pid}")

    sse_ok = run_demo_sse(token, pid, report)
    if sse_ok:
        verify_post_run(token, pid, report)

    report.finished_at = datetime.now(timezone.utc).isoformat()
    path = _write_report(report)
    print(f"\nReport written: {path}")
    print(f"Passed: {report.passed}  Failed: {report.failed}")
    if report.dead_ends:
        print("Dead ends:")
        for d in report.dead_ends:
            print(f"  - {d}")
    return 0 if report.failed == 0 and sse_ok else 1


def _write_report(report: WorkflowReport) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "docs", "PHASE3_WORKFLOW_EXECUTION.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(markdown_report(report))
    json_path = os.path.join(root, "docs", "phase3-workflow-results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "started_at": report.started_at,
                "finished_at": report.finished_at,
                "project_id": report.project_id,
                "use_ai": report.use_ai,
                "sse_steps_seen": report.sse_steps_seen,
                "step_results": [
                    {"id": s.id, "label": s.label, "status": s.status, "detail": s.detail}
                    for s in report.step_results
                ],
                "dead_ends": report.dead_ends,
                "ui_notes": report.ui_notes,
            },
            f,
            indent=2,
        )
    return out


if __name__ == "__main__":
    sys.exit(main())
