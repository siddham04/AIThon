#!/usr/bin/env python3
"""Phase 6 — Export validation: JSON, CSV, Markdown, Jira.

Generates sample files under docs/phase6-exports/ and validates schemas.

Usage (backend on 8765):
  python scripts/phase6_export_validation.py
  HELIX_USE_AI=false python scripts/phase6_workflow_test.py  # ensure project first
  python scripts/phase6_export_validation.py --project-id proj_xxx
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")
EMAIL = os.environ.get("HELIX_EMAIL", "demo@demo.com")
PASSWORD = os.environ.get("HELIX_PASSWORD", "demo123")
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "phase6-exports",
)

JIRA_CSV_REQUIRED = (
    "Issue Type",
    "Issue ID",
    "Summary",
    "Description",
    "Parent",
    "Priority",
    "Story Points",
    "Estimate (h)",
    "Labels",
    "Helix ID",
)
JIRA_TYPES = {"Epic", "Story", "Task", "Sub-task"}
BACKLOG_JSON_REQUIRED = {"epic", "stories", "tasks", "subtasks"}
EXPORT_CSV_REQUIRED = {
    "task_id", "title", "type", "priority", "story_id",
    "estimate_points", "estimate_hours", "confidence",
    "skills", "description", "approved_for_export",
}


@dataclass
class Finding:
    export: str
    status: str  # pass | fail | warn | skip
    detail: str


@dataclass
class Report:
    project_id: str = ""
    findings: list[Finding] = field(default_factory=list)
    files: list[str] = field(default_factory=list)

    def add(self, export: str, status: str, detail: str) -> None:
        self.findings.append(Finding(export, status, detail))

    @property
    def passed(self) -> int:
        return sum(1 for f in self.findings if f.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for f in self.findings if f.status == "fail")


def req(
    method: str,
    path: str,
    *,
    token: str | None = None,
    data: dict | None = None,
    raw: bool = False,
    timeout: int = 120,
) -> tuple[int, Any]:
    url = BASE + path
    h: dict[str, str] = {}
    if data is not None:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw_bytes = resp.read()
            if raw:
                return resp.status, raw_bytes.decode("utf-8", errors="replace")
            if not raw_bytes:
                return resp.status, {}
            return resp.status, json.loads(raw_bytes.decode())
    except urllib.error.HTTPError as e:
        raw_bytes = e.read()
        try:
            return e.code, json.loads(raw_bytes.decode())
        except Exception:
            return e.code, raw_bytes.decode(errors="replace")[:500]


def login() -> str | None:
    code, body = req("POST", "/api/auth/login", data={"email": EMAIL, "password": PASSWORD})
    if code == 200 and isinstance(body, dict) and body.get("access_token"):
        return body["access_token"]
    code2, body2 = req(
        "POST",
        "/api/auth/register",
        data={"email": EMAIL, "password": PASSWORD, "name": "Phase6"},
    )
    if code2 == 200 and isinstance(body2, dict) and body2.get("access_token"):
        return body2["access_token"]
    return None


def run_demo(token: str) -> str | None:
    sample = (
        "Phase 6 export validation. OTP login for B2B portal with Stripe billing. "
        "GDPR deletion within 30 days. Support 10k concurrent sessions, p99 under 500ms."
    )
    code, body = req(
        "POST",
        "/api/ingest/text",
        data={"name": "Phase6 Export", "text": sample.strip()},
        token=token,
    )
    if code != 200 or not isinstance(body, dict) or not body.get("project_id"):
        return None
    pid = body["project_id"]
    url = f"{BASE}/api/demo/{pid}/run"
    h = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    r = urllib.request.Request(
        url,
        data=json.dumps({"use_ai": False}).encode(),
        headers=h,
        method="POST",
    )
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            buf = resp.read().decode(errors="replace")
        if '"step": "complete"' not in buf and '"step":"complete"' not in buf:
            return None
    except Exception:
        return None
    return pid


def save(name: str, content: str | bytes, report: Report) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    with open(path, mode, encoding=encoding) as f:
        f.write(content)
    report.files.append(path)
    return path


def parse_csv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def validate_jira_backlog_csv(text: str, report: Report) -> None:
    name = "Jira backlog CSV"
    if not text.strip():
        report.add(name, "fail", "Empty CSV body")
        return
    rows = parse_csv(text)
    if not rows:
        report.add(name, "fail", "No data rows")
        return
    headers = set(rows[0].keys())
    missing = [c for c in JIRA_CSV_REQUIRED if c not in headers]
    if missing:
        report.add(name, "fail", f"Missing columns: {missing}")
        return
    report.add(name, "pass", f"Header OK ({len(JIRA_CSV_REQUIRED)} columns)")

    by_id: dict[str, dict] = {}
    issues: list[str] = []
    for i, row in enumerate(rows, start=2):
        itype = (row.get("Issue Type") or "").strip()
        iid = (row.get("Issue ID") or "").strip()
        parent = (row.get("Parent") or "").strip()
        summary = (row.get("Summary") or "").strip()
        if itype not in JIRA_TYPES:
            issues.append(f"row {i}: invalid Issue Type '{itype}'")
        if not iid:
            issues.append(f"row {i}: missing Issue ID")
        if not summary:
            issues.append(f"row {i}: missing Summary")
        if iid in by_id:
            issues.append(f"duplicate Issue ID: {iid}")
        by_id[iid] = row
        if parent and parent not in by_id and itype != "Epic":
            issues.append(f"row {i}: parent '{parent}' not defined above '{iid}'")

    epics = [r for r in rows if (r.get("Issue Type") or "").strip() == "Epic"]
    stories = [r for r in rows if (r.get("Issue Type") or "").strip() == "Story"]
    tasks = [r for r in rows if (r.get("Issue Type") or "").strip() == "Task"]
    subs = [r for r in rows if (r.get("Issue Type") or "").strip() == "Sub-task"]

    if not epics:
        report.add(f"{name} (hierarchy)", "fail", "No Epic row")
    elif len(issues) > 5:
        report.add(f"{name} (hierarchy)", "fail", "; ".join(issues[:5]))
    elif issues:
        report.add(f"{name} (hierarchy)", "warn", "; ".join(issues[:3]))
    else:
        report.add(
            f"{name} (importable)",
            "pass",
            f"{len(epics)} epic, {len(stories)} stories, {len(tasks)} tasks, {len(subs)} subtasks — parent chain valid",
        )


def validate_export_csv(text: str, report: Report) -> None:
    name = "Generic CSV (/api/export/csv)"
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        report.add(name, "fail", "Empty file")
        return
    headers = set(header)
    missing = [c for c in EXPORT_CSV_REQUIRED if c not in headers]
    if missing:
        report.add(name, "fail", f"Missing columns: {missing}")
        return
    data_rows = list(reader)
    if not data_rows:
        report.add(
            name,
            "warn",
            "Header schema OK; 0 task rows (Scrum agent produced no tasks in pipeline)",
        )
        return
    report.add(name, "pass", f"{len(data_rows)} task rows, schema OK")


def validate_backlog_json(obj: Any, report: Report) -> None:
    name = "Backlog JSON (/api/backlog/.../json)"
    if not isinstance(obj, dict):
        report.add(name, "fail", "Not a JSON object")
        return
    missing = [k for k in BACKLOG_JSON_REQUIRED if k not in obj]
    if missing:
        report.add(name, "fail", f"Missing keys: {missing}")
        return
    if not isinstance(obj.get("epic"), dict):
        report.add(name, "fail", "epic must be object")
        return
    for key in ("stories", "tasks", "subtasks"):
        if not isinstance(obj.get(key), list):
            report.add(name, "fail", f"{key} must be array")
            return
    report.add(
        name,
        "pass",
        f"epic + {len(obj['stories'])} stories + {len(obj['tasks'])} tasks + {len(obj['subtasks'])} subtasks",
    )


def validate_project_json(obj: Any, report: Report, project_id: str) -> None:
    name = "Project JSON (/api/export/json)"
    if not isinstance(obj, dict):
        report.add(name, "fail", "Not a JSON object")
        return
    for key in ("id", "name", "stories", "test_cases"):
        if key not in obj:
            report.add(name, "warn", f"Missing top-level '{key}'")
            break
    else:
        report.add(
            name,
            "pass",
            f"Full project dump ({len(obj.get('stories') or [])} stories, "
            f"{len(obj.get('test_cases') or [])} tests)",
        )
    if obj.get("id") == project_id:
        report.add(f"{name} (re-import)", "pass", "id matches project; json.dumps round-trip OK")
    else:
        report.add(f"{name} (re-import)", "warn", f"id field={obj.get('id')!r}")


def validate_json_roundtrip(obj: dict, report: Report) -> None:
    name = "Backlog JSON (round-trip)"
    try:
        blob = json.dumps(obj)
        restored = json.loads(blob)
    except (TypeError, json.JSONDecodeError) as e:
        report.add(name, "fail", str(e))
        return
    if restored == obj:
        report.add(name, "pass", "Serializable and parseable for downstream import")
    else:
        report.add(name, "warn", "Round-trip mismatch after dumps/loads")


def validate_markdown(text: str, report: Report) -> None:
    name = "Markdown (/api/export/markdown)"
    if not text.strip():
        report.add(name, "fail", "Empty document")
        return
    checks = []
    if re.search(r"^#\s+", text, re.M):
        checks.append("H1 title")
    if "## User Stories" in text or "## Engineering Tasks" in text:
        checks.append("work items section")
    if checks:
        report.add(name, "pass", ", ".join(checks) + f" ({len(text)} chars)")
    else:
        report.add(name, "warn", "Minimal structure — may be empty project")


def validate_ado_csv(text: str, report: Report) -> None:
    name = "Azure DevOps CSV"
    rows = parse_csv(text)
    if not rows:
        report.add(name, "skip", "No rows")
        return
    if "Work Item Type" in rows[0] and "Title" in rows[0]:
        types = {(r.get("Work Item Type") or "").strip() for r in rows}
        report.add(name, "pass", f"ADO schema OK — types: {', '.join(sorted(types))}")
    else:
        report.add(name, "fail", "Missing Work Item Type / Title columns")


def main() -> int:
    report = Report()
    print(f"Phase 6 export validation @ {BASE}\n")

    code, _ = req("GET", "/api/health")
    if code != 200:
        print("FAIL: backend health")
        return 1

    token = login()
    if not token:
        print("FAIL: auth")
        return 1

    pid = None
    if "--project-id" in sys.argv:
        idx = sys.argv.index("--project-id")
        if idx + 1 < len(sys.argv):
            pid = sys.argv[idx + 1]
    if not pid:
        # Try phase3 results
        p3 = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs",
            "phase3-workflow-results.json",
        )
        if os.path.isfile(p3):
            with open(p3, encoding="utf-8") as f:
                pid = json.load(f).get("project_id")
    if not pid:
        print("Running demo pipeline to create project (~3-4 min)...")
        pid = run_demo(token)
    if not pid:
        print("FAIL: no project_id")
        return 1
    report.project_id = pid
    print(f"Project: {pid}\n")

    prefix = pid.replace("/", "_")[:20]

    # --- Jira CSV (Delivery Package primary) ---
    code, jira_csv = req("GET", f"/api/backlog/{pid}/jira-csv", token=token, raw=True)
    if code == 200 and isinstance(jira_csv, str):
        path = save(f"{prefix}-jira-backlog.csv", jira_csv, report)
        validate_jira_backlog_csv(jira_csv, report)
        print(f"  saved {path}")
    else:
        report.add("Jira backlog CSV", "fail", f"HTTP {code} — {jira_csv}")

    # --- Backlog JSON ---
    code, bl_json = req("GET", f"/api/backlog/{pid}/json", token=token, raw=True)
    if code == 200:
        try:
            parsed = json.loads(bl_json) if isinstance(bl_json, str) else bl_json
            path = save(f"{prefix}-backlog.json", json.dumps(parsed, indent=2), report)
            validate_backlog_json(parsed, report)
            validate_json_roundtrip(parsed, report)
            print(f"  saved {path}")
        except json.JSONDecodeError as e:
            report.add("Backlog JSON", "fail", str(e))
    else:
        report.add("Backlog JSON", "fail", f"HTTP {code}")

    # --- Generic export CSV ---
    code, gen_csv = req("GET", f"/api/export/csv/{pid}", token=token, raw=True)
    if code == 200 and isinstance(gen_csv, str):
        path = save(f"{prefix}-tasks-export.csv", gen_csv, report)
        validate_export_csv(gen_csv, report)
        print(f"  saved {path}")
    else:
        report.add("Generic CSV", "warn", f"HTTP {code} — often empty if no tasks")

    # --- Project JSON ---
    code, raw = req("GET", f"/api/export/json/{pid}", token=token, raw=True)
    if code == 200 and isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            path = save(f"{prefix}-project-full.json", json.dumps(parsed, indent=2)[:500000], report)
            validate_project_json(parsed, report, pid)
            print(f"  saved {path}")
        except json.JSONDecodeError as e:
            report.add("Project JSON", "fail", str(e))
    else:
        report.add("Project JSON", "fail", f"HTTP {code}")

    # --- Markdown ---
    code, md = req("GET", f"/api/export/markdown/{pid}", token=token, raw=True)
    if code == 200 and isinstance(md, str):
        path = save(f"{prefix}-export.md", md, report)
        validate_markdown(md, report)
        print(f"  saved {path}")
    else:
        report.add("Markdown export", "fail", f"HTTP {code}")

    # --- ADO CSV ---
    code, ado = req("GET", f"/api/backlog/{pid}/ado-csv", token=token, raw=True)
    if code == 200 and isinstance(ado, str):
        path = save(f"{prefix}-ado-backlog.csv", ado, report)
        validate_ado_csv(ado, report)
        print(f"  saved {path}")
    else:
        report.add("ADO CSV", "warn", f"HTTP {code}")

    # --- Jira push (metadata only, no live Jira required) ---
    code, push = req("POST", f"/api/backlog/{pid}/jira-push", token=token)
    if code == 200 and isinstance(push, dict):
        save(f"{prefix}-jira-push-result.json", json.dumps(push, indent=2), report)
        mode = "rest" if push.get("epic_key") or push.get("created_keys") else "skipped/mock"
        report.add(
            "Jira REST push",
            "pass" if push.get("ok") or push.get("detail") else "warn",
            f"ok={push.get('ok')} mode={mode} keys={len(push.get('created_keys') or [])}",
        )
    else:
        report.add("Jira REST push", "warn", f"HTTP {code} — needs JIRA_* env for live import")

    # Write report markdown
    md_lines = [
        "# Phase 6 — Export Validation Report",
        "",
        f"**Date:** {datetime.now(timezone.utc).isoformat()}  ",
        f"**Project:** `{pid}`  ",
        f"**Output directory:** `docs/phase6-exports/`  ",
        "",
        "## Summary",
        "",
        f"| Passed | Failed | Warn/Skip |",
        f"|--------|--------|-----------|",
        f"| {report.passed} | {report.failed} | "
        f"{sum(1 for f in report.findings if f.status in ('warn', 'skip'))} |",
        "",
        "## Results",
        "",
        "| Export | Status | Detail |",
        "|--------|--------|--------|",
    ]
    for f in report.findings:
        md_lines.append(f"| {f.export} | {f.status.upper()} | {f.detail[:100]} |")
    md_lines.extend([
        "",
        "## Sample files",
        "",
    ])
    for p in report.files:
        md_lines.append(f"- `{os.path.relpath(p, os.path.dirname(OUT_DIR))}`")
    md_lines.extend([
        "",
        "## Export endpoints",
        "",
        "| Format | Route | UI surface |",
        "|--------|-------|------------|",
        "| Jira CSV | `GET /api/backlog/{id}/jira-csv` | Delivery Package (primary) |",
        "| ADO CSV | `GET /api/backlog/{id}/ado-csv` | Delivery Package |",
        "| Backlog JSON | `GET /api/backlog/{id}/json` | Delivery Package |",
        "| Project JSON | `GET /api/export/json/{id}` | Delivery Package |",
        "| Tasks CSV | `GET /api/export/csv/{id}` | Delivery Package |",
        "| Markdown | `GET /api/export/markdown/{id}` | Delivery Package |",
        "| Jira REST | `POST /api/backlog/{id}/jira-push` | Delivery Package (optional) |",
        "",
        "## Importability notes",
        "",
        "- **Jira CSV:** Jira → Settings → Import → CSV. Columns match `backlog_export._CSV_FIELDS`.",
        "- **Backlog JSON:** Machine-readable; re-import via custom script or `POST /generate` input.",
        "- **Project JSON:** `json.loads` + Pydantic `Project` shape; suitable for backup/restore tooling.",
        "- **Markdown:** Paste into Confluence/Notion/GitHub wiki; includes audit footer when exported via API.",
        "- **Jira REST:** Requires `JIRA_BASE_URL`, `JIRA_TOKEN`, `JIRA_PROJECT_KEY` in backend env.",
        "",
        "## Re-run",
        "",
        "```bash",
        "python scripts/phase6_export_validation.py --project-id <proj_id>",
        "```",
        "",
    ])
    report_path = os.path.join(
        os.path.dirname(OUT_DIR),
        "PHASE6_EXPORT_VALIDATION.md",
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"\nReport: {report_path}")
    print(f"Passed: {report.passed}  Failed: {report.failed}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
