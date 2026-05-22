#!/usr/bin/env python3
"""Smoke test: ingest sample brief, run analyze, assert non-empty artifacts.

Usage (from repo root, backend running on 8765):
  python scripts/smoke_demo.py

Or with custom base URL:
  HELIX_BASE=http://127.0.0.1:8765 HELIX_API_KEY=secret python scripts/smoke_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")
API_KEY = os.environ.get("HELIX_API_KEY", "").strip()

SAMPLE = """
Checkout Revamp Initiative.

Customers abandon cart when shipping estimates are unclear.
We must show delivery dates before payment within 200ms P95.
Security: PCI scope must not store raw card data.
Maybe add loyalty points later — TBD with marketing.
"""


def req(
    method: str,
    path: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, bytes]:
    url = BASE + path
    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    if API_KEY:
        h.setdefault("X-Helix-Key", API_KEY)
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> int:
    code, raw = req("GET", "/api/health")
    print("health", code, raw.decode()[:500])
    if code != 200:
        return 1

    code, raw = req(
        "POST",
        "/api/ingest/text",
        data={"name": "Smoke Demo", "text": SAMPLE.strip()},
    )
    if code != 200:
        print("ingest failed", code, raw.decode())
        return 1
    proj = json.loads(raw.decode())
    pid = proj["id"]
    print("ingested project", pid)

    code, raw = req("POST", f"/api/projects/{pid}/analyze")
    if code != 200:
        print("analyze failed", code, raw.decode())
        return 1
    final = json.loads(raw.decode())

    n_stories = len(final.get("stories") or [])
    n_tasks = len(final.get("tasks") or [])
    n_tests = len(final.get("test_cases") or [])
    n_amb = len(final.get("ambiguities") or [])
    n_risk = len(final.get("risks") or [])
    print(
        f"artifacts stories={n_stories} tasks={n_tasks} tests={n_tests} "
        f"ambiguities={n_amb} risks={n_risk}"
    )

    if n_stories < 1 or n_tasks < 1 or n_tests < 1:
        print("FAIL: expected non-empty stories, tasks, and tests (demo/mock path).")
        return 2
    print("OK smoke demo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
