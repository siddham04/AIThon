"""End-to-end SSE smoke: hit the running backend, ingest a tiny PRD, launch
the demo pipeline, and print every SSE event with timing so we can prove
the orchestrator streams progress (no UI required)."""
from __future__ import annotations

import json
import sys
import time
import urllib.request


BASE = "http://127.0.0.1:8000/api"

PRD = (
    "Telecom Order Management Platform. Customers must place orders via web, "
    "mobile, IVR. Provisioning under 30 minutes. p95 order capture < 2s, "
    "throughput 5000 orders/hour. PII encrypted at rest. 99.95% uptime."
)


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
    # Use the dev-mode guest token endpoint
    auth = _post("/auth/guest", {})
    token = auth["access_token"]
    print(f"  · guest token acquired")

    print()
    print(f"{'elapsed':>7}      {'step':<14} {'status':<7} {'pct':>4}  headline")
    print("-" * 80)
    _stream("/demo/run", body={"requirement": PRD, "use_ai": False}, token=token)
    print("-" * 80)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTPError {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
        raise
