#!/usr/bin/env python3
"""Minimal golden-brief evaluation (Phase 5 starter).

Runs the analyze pipeline against canned briefs and checks minimum artifact counts.
Requires backend running locally or set HELIX_BASE.

  python scripts/eval_golden.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")
API_KEY = os.environ.get("HELIX_API_KEY", "").strip()

GOLDEN = [
    {
        "name": "Perf + security",
        "text": "API must authenticate JWTs. P95 latency under 120ms at 500 RPS. Store audit logs for 90 days.",
        "min": {"stories": 1, "tasks": 1, "tests": 2, "ambiguities": 0, "risks": 1},
    },
    {
        "name": "Ambiguous brief",
        "text": "Make checkout faster. Maybe add discounts. GDPR important.",
        "min": {"stories": 1, "tasks": 1, "tests": 2, "ambiguities": 1, "risks": 1},
    },
    {
        "name": "Conflicting constraints",
        "text": "Dashboard must load in under 50ms. Include a 4K video preview on the landing hero. "
        "Mobile users on 3G are the primary audience.",
        "min": {"stories": 1, "tasks": 1, "tests": 1, "ambiguities": 1, "risks": 1},
    },
    {
        "name": "Minimal viable feature",
        "text": "Add a logout button that clears the session cookie and redirects to /login.",
        "min": {"stories": 1, "tasks": 1, "tests": 1, "ambiguities": 0, "risks": 0},
    },
    {
        "name": "Mixed language snippet",
        "text": "Users need export to Excel. Les colonnes doivent inclure date et montant. "
        "PCI: ne pas stocker le PAN.",
        "min": {"stories": 1, "tasks": 1, "tests": 1, "ambiguities": 0, "risks": 1},
    },
]


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-Helix-Key"] = API_KEY
    req = urllib.request.Request(
        BASE + path, data=data, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    failed = 0
    for g in GOLDEN:
        proj = post("/api/projects/ingest-text", {"name": g["name"], "text": g["text"]})
        pid = proj["id"]
        final = post(f"/api/projects/{pid}/analyze")
        for k, min_v in g["min"].items():
            got = len(final.get(k) or [])
            if got < min_v:
                print(f"FAIL {g['name']}: {k} got {got} want >= {min_v}")
                failed += 1
            else:
                print(f"ok  {g['name']}: {k}={got}")
        metrics = final.get("metrics") or {}
        if metrics:
            cite = metrics.get("citation_item_rate")
            if cite is not None:
                print(f"    {g['name']}: citation_item_rate={cite}")
        timings = final.get("last_pipeline_timings_ms")
        if timings:
            print(f"    {g['name']}: pipeline_timings_ms keys={list(timings.keys())}")
    if failed:
        print(f"\n{failed} check(s) failed")
        return 1
    print("\nAll golden checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
