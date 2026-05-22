#!/usr/bin/env python3
"""Phase 7 — probe open endpoints and JWT gate behavior (no auth header)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")

PUBLIC_OK = {
    ("GET", "/api/health"),
    ("GET", "/health"),
    ("POST", "/api/auth/guest"),
    ("GET", "/api/demo/steps"),
    ("GET", "/api/demo/showcase"),
}

SHOULD_REQUIRE_AUTH = [
    ("POST", "/api/diff/compare", {"version_a": "A", "version_b": "B", "use_ai": False}),
    ("POST", "/api/meeting/extract", {"transcript": "Sprint planning notes.", "use_ai": False}),
    (
        "POST",
        "/api/studio/effort/analyze",
        {"requirement": "Build login.", "use_ai": False},
    ),
    (
        "POST",
        "/api/devstudio/contract/generate",
        {"requirement": "GET /health", "use_ai": False},
    ),
    ("POST", "/api/quality/score", {"text": "Build login.", "use_ai": False}),
    ("GET", "/api/readiness-center/demo", None),
    ("GET", "/api/projects", None),
    ("GET", "/api/export/json/proj_fake", None),
]


def call(method: str, path: str, body: dict | None = None) -> tuple[int, str]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, (resp.read(400) or b"").decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read(400) or b"").decode(errors="replace")


def main() -> int:
    print(f"Phase 7 security probes @ {BASE}\n")
    findings: list[str] = []

    for method, path in sorted(PUBLIC_OK):
        body = None
        if "guest" in path:
            body = {}
        code, _ = call(method, path, body)
        if code >= 400 and "guest" not in path:
            findings.append(f"PUBLIC unexpected {code} {method} {path}")
        else:
            print(f"  OK public {method} {path} -> {code}")

    print("\nUnauthenticated access to protected-style routes:")
    for item in SHOULD_REQUIRE_AUTH:
        method, path = item[0], item[1]
        body = item[2] if len(item) > 2 else None
        code, _ = call(method, path, body)
        status = "OPEN" if 200 <= code < 300 else "blocked"
        print(f"  {status:7} {code} {method} {path}")
        if status == "OPEN":
            findings.append(f"OPEN_ENDPOINT {method} {path} (no Bearer token)")

    if findings:
        print("\nFindings:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("\nPASS — no open LLM or data routes without JWT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
