"""Wall-clock benchmark: sequential vs parallel pipeline batching.

Runs the full ``run_demo`` orchestrator twice over the same prose PRD
— once with ``HELIX_DEMO_PARALLEL=false`` (everything serial), once
with the default parallel batches — and prints the wall-clock + the
per-step timings so we can prove the parallelism actually pays off
without sacrificing artifact counts (i.e. quality).
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

os.environ["HELIX_USE_AI"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite:///./helix_bench.db")
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")
for _k in (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OAI_KEY",
    "AZURE_OAI_ENDPOINT",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
):
    os.environ[_k] = ""

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND)

from app.config import get_settings  # noqa: E402
from app.models import Project  # noqa: E402
from app.services.ingestion import split_into_clauses  # noqa: E402
from app.services.demo_orchestrator import run_demo  # noqa: E402


PRD = """\
Telecom Order Management Platform (TOMP) Version 1.0
The Telecom Order Management Platform will provide a centralized solution for
managing customer orders across mobile, broadband, and enterprise lines.
The platform will automate the complete order lifecycle from order capture
through provisioning, activation, billing, fulfillment, and assurance.
The system should support both B2C and B2B customers.
Current order fulfillment suffers from manual order processing, fragmented
systems, high error rates, and a poor customer experience. Sales agents must
re-key data into five systems and provisioning takes 48-72 hours on average.
Customers must be able to place orders via web, mobile, IVR, and assisted-
agent channels.
The system must reserve resources (numbers, SIM, IP ranges) at order capture
and decrement inventory atomically.
The order workflow must support modify, suspend, resume, and cancel actions
with full audit trail and SLA monitoring.
Billing must be generated within 24h of activation and synchronize with the
revenue management platform.
The system must produce real-time order status dashboards for ops, sales, and
executive users.
Compliance: PII fields must be encrypted at rest; consent and retention
windows must be tracked per customer.
Performance: p95 order-capture latency under 2 seconds; throughput 5,000
orders/hour at peak.
Availability: 99.95% uptime with disaster recovery RPO 5 min, RTO 30 min.
"""


def _hr(title: str) -> None:
    print()
    print("=" * 76)
    print(f" {title}")
    print("=" * 76)


def _build_project() -> Project:
    clauses = split_into_clauses(PRD)
    return Project(
        id="proj_bench",
        name="Telecom Order Management Platform (TOMP)",
        raw_input=PRD,
        source_clauses=clauses,
    )


async def _measure_one(*, parallel: bool) -> tuple[float, dict[str, int], dict[str, int]]:
    """One full run; returns wall-clock ms, per-step elapsed, artifact counts."""
    os.environ["HELIX_DEMO_PARALLEL"] = "true" if parallel else "false"
    get_settings.cache_clear()

    project = _build_project()
    per_step: dict[str, int] = {}
    t0 = time.monotonic()
    async for event in run_demo(project, use_ai=False):
        if event.get("status") == "done":
            per_step[event.get("step", "?")] = int(event.get("elapsed_ms") or 0)
    elapsed = (time.monotonic() - t0) * 1000.0

    counts = {
        "stories": len(project.stories or []),
        "tasks": len(project.tasks or []),
        "test_cases": len(project.test_cases or []),
        "risks": len(project.risks or []),
        "ambiguities": len(project.ambiguities or []),
        "jira_backlog": 1 if project.jira_backlog else 0,
        "readiness": 1 if project.delivery_readiness else 0,
        "api_contracts": len((project.api_contract_suite.contracts if project.api_contract_suite else []) or []),
    }
    return elapsed, per_step, counts


async def _measure(label: str, *, parallel: bool, runs: int) -> tuple[float, dict[str, int], dict[str, int]]:
    """Average wall-clock over `runs` iterations; takes the LAST per-step
    and counts as representative (they should be identical run-to-run in
    mock mode)."""
    samples: list[float] = []
    per_step: dict[str, int] = {}
    counts: dict[str, int] = {}
    for _ in range(runs):
        ms, per_step, counts = await _measure_one(parallel=parallel)
        samples.append(ms)
    avg_ms = sum(samples) / len(samples)
    best_ms = min(samples)

    _hr(f"{label}")
    print(f"  wall-clock avg-of-{runs}: {avg_ms:8.1f} ms   (best: {best_ms:.1f} ms)")
    print(f"  artifacts:  stories={counts['stories']}  tasks={counts['tasks']}  "
          f"tests={counts['test_cases']}  risks={counts['risks']}  "
          f"ambig={counts['ambiguities']}  api={counts['api_contracts']}  "
          f"jira={counts['jira_backlog']}  readiness={counts['readiness']}")
    print(f"  per-step (last run):")
    for name, ms in per_step.items():
        bar = "#" * max(1, ms // 5)
        print(f"    {name:<14} {ms:>6} ms  {bar}")
    return avg_ms, per_step, counts


async def main() -> None:
    runs = 3  # mock mode is sub-millisecond per step; average a few to smooth noise
    seq_ms, seq, seq_counts = await _measure("SEQUENTIAL (HELIX_DEMO_PARALLEL=false)", parallel=False, runs=runs)
    par_ms, par, par_counts = await _measure("PARALLEL   (HELIX_DEMO_PARALLEL=true)",  parallel=True,  runs=runs)

    _hr("Summary")
    print(f"  sequential avg wall-clock: {seq_ms:>8.1f} ms")
    print(f"  parallel   avg wall-clock: {par_ms:>8.1f} ms")
    if par_ms > 0:
        speedup = seq_ms / par_ms
        saved = seq_ms - par_ms
        print(f"  speedup:                   {speedup:.2f}x  ({saved:,.1f} ms saved per run)")

    print()
    same = seq_counts == par_counts
    print(f"  artifact counts identical: {'YES (quality preserved)' if same else 'NO — DIFF DETECTED'}")
    if not same:
        for k in sorted(set(seq_counts) | set(par_counts)):
            if seq_counts.get(k) != par_counts.get(k):
                print(f"    {k}: seq={seq_counts.get(k)}  par={par_counts.get(k)}")


if __name__ == "__main__":
    asyncio.run(main())
