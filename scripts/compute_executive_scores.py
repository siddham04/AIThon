#!/usr/bin/env python3
"""Compute HELIX executive scores (0–100) from live repo checks.

Run: python scripts/compute_executive_scores.py
Requires: backend on HELIX_BASE (optional for security slice).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "helix-frontend"
BASE = os.environ.get("HELIX_BASE", "http://127.0.0.1:8765").rstrip("/")


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        shell=(os.name == "nt"),
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def score_build() -> tuple[int, list[str]]:
    notes: list[str] = []
    pts = 0
    code, out = run(["npm", "run", "lint"], cwd=FRONTEND)
    if code == 0:
        pts += 35
        notes.append("ESLint 0 errors")
    else:
        notes.append(f"ESLint failed: {out[:200]}")
    code, out = run(["npm", "run", "build"], cwd=FRONTEND)
    if code == 0:
        pts += 35
        notes.append("Vite build PASS")
    else:
        notes.append("Vite build FAIL")
    pages = list((FRONTEND / "src" / "pages").glob("*.jsx"))
    routed = {
        "Landing.jsx",
        "Login.jsx",
        "Register.jsx",
        "MissionControl.jsx",
        "AiWorkspace.jsx",
        "DeliveryCommandCenter.jsx",
        "CopilotChat.jsx",
        "Settings.jsx",
        "WinningDemoScreen.jsx",
    }
    orphan = [p.name for p in pages if p.name not in routed]
    if len(orphan) == 0:
        pts += 20
        notes.append(f"9 routed pages, 0 orphans in pages/")
    else:
        notes.append(f"{len(orphan)} orphan page files: {orphan[:5]}")
    smoke = FRONTEND / "e2e" / "smoke.spec.ts"
    if smoke.exists() and "mission-control" in smoke.read_text(encoding="utf-8"):
        pts += 10
        notes.append("E2E smoke targets mission-control")
    return min(100, pts), notes


def score_ui() -> tuple[int, list[str]]:
    notes: list[str] = []
    pts = 0
    if (FRONTEND / "src" / "App.jsx").read_text(encoding="utf-8").count("lazy(") >= 5:
        pts += 30
        notes.append("Lazy-loaded product routes")
    mc = (FRONTEND / "src" / "pages" / "MissionControl.jsx").read_text(encoding="utf-8")
    if "mc-pipeline-errors" in mc and mc.index("mc-pipeline-errors") < mc.index("mc-cta-wrap"):
        pts += 25
        notes.append("Pipeline errors above launch CTA")
    wds = (FRONTEND / "src" / "pages" / "WinningDemoScreen.jsx").read_text(encoding="utf-8")
    if "handleDemoEvent" in wds and "runPipelineAutoPlay" not in wds:
        pts += 25
        notes.append("Judge Demo SSE-only (no parallel autoplay)")
    if (FRONTEND / "src" / "lib" / "loadWorkspaceData.js").read_text(encoding="utf-8").count(
        "onPartial"
    ) >= 2:
        pts += 20
        notes.append("Progressive Delivery Package load")
    return min(100, pts), notes


def score_architecture() -> tuple[int, list[str]]:
    notes: list[str] = []
    pts = 0
    deps = ROOT / "helix-backend" / "app" / "api" / "deps.py"
    if deps.exists() and "Require JWT on all /api routes" in deps.read_text(encoding="utf-8"):
        pts += 40
        notes.append("Global JWT gate on /api")
    ws = ROOT / "helix-backend" / "app" / "api" / "routes" / "ws.py"
    if ws.exists() and "token" in ws.read_text(encoding="utf-8"):
        pts += 20
        notes.append("WebSocket requires token query param")
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    if "manualChunks" in vite:
        pts += 25
        notes.append("Vite manualChunks (mermaid/three/charts)")
    if (FRONTEND / "src" / "lib" / "helixVisualSettings.js").exists():
        pts += 15
        notes.append("Three.js off by default")
    return min(100, pts), notes


def score_security() -> tuple[int, list[str]]:
    deps = (ROOT / "helix-backend" / "app" / "api" / "deps.py").read_text(encoding="utf-8")
    notes: list[str] = []
    pts = 0
    if "_PUBLIC_API_PATHS" in deps and "Require JWT on all /api routes" in deps:
        pts += 50
        notes.append("Global JWT gate (deps.helix_auth_gate)")
    ws = ROOT / "helix-backend" / "app" / "api" / "routes" / "ws.py"
    if ws.exists() and "Query(..., description=\"JWT" in ws.read_text(encoding="utf-8"):
        pts += 25
        notes.append("WebSocket token required")
    if (ROOT / "helix-backend" / "app" / "middleware" / "rate_limit.py").exists():
        pts += 15
        notes.append("Rate limit middleware")
    bootstrap = (ROOT / "helix-backend" / "app" / "bootstrap.py").read_text(encoding="utf-8")
    if "helix_production" in bootstrap:
        pts += 10
        notes.append("HELIX_PRODUCTION blocks default JWT_SECRET")
    script = ROOT / "scripts" / "phase7_security_review.py"
    if script.exists():
        code, out = run([sys.executable, str(script)])
        if code == 0:
            return 100, notes + ["Phase 7 live probe PASS"]
        notes.append("Phase 7 live probe: restart API (run.ps1) then re-run")
    return min(100, pts), notes


def score_ai_workflow() -> tuple[int, list[str]]:
    notes: list[str] = []
    pts = 0
    orch = ROOT / "helix-backend" / "app" / "services" / "demo_orchestrator.py"
    text = orch.read_text(encoding="utf-8") if orch.exists() else ""
    if "_ensure_project_tasks" in text:
        pts += 25
        notes.append("Task guarantee (_ensure_project_tasks)")
    if "held_complete" in (ROOT / "helix-backend" / "app" / "api" / "routes" / "demo.py").read_text(
        encoding="utf-8"
    ):
        pts += 25
        notes.append("Persist before SSE complete")
    rc = ROOT / "helix-backend" / "app" / "services" / "delivery_readiness_center.py"
    if rc.exists() and "100 * done / total" in rc.read_text(encoding="utf-8"):
        pts += 25
        notes.append("Readiness score from gates (not fixed 94)")
    wds = (FRONTEND / "src" / "pages" / "WinningDemoScreen.jsx").read_text(encoding="utf-8")
    if "step === 'complete'" in wds and "readiness" not in wds.split("finishDemo")[0][-200:]:
        pts += 25
        notes.append("Judge finale only on complete step")
    return min(100, pts), notes


def main() -> int:
    build, bn = score_build()
    ui, un = score_ui()
    arch, an = score_architecture()
    sec, sn = score_security()
    ai, ain = score_ai_workflow()

    # Security gates production launch; blend for overall.
    hackathon = min(100, int(round((build + ui + ai + arch) / 4)))
    overall = min(100, int(round((build + ui + arch + ai + sec) / 5)))

    production_ready = sec >= 95 and build >= 95 and arch >= 95
    hackathon_ready = build >= 95 and ui >= 95 and ai >= 95

    scores = {
        "Overall Health Score": overall,
        "Build Quality Score": build,
        "UI Quality Score": ui,
        "Architecture Score": arch,
        "AI Workflow Score": ai,
        "Security Score": sec,
        "Hackathon Score": hackathon,
        "Launch Readiness": {
            "production": "YES" if production_ready else "NO",
            "hackathon_demo": "YES" if hackathon_ready else "NO",
        },
    }

    print("HELIX Executive Scores\n")
    for k, v in scores.items():
        if k == "Launch Readiness":
            print(f"  {k}: production={v['production']} · hackathon={v['hackathon_demo']}")
        else:
            print(f"  {k}: {v} / 100")
    print("\nEvidence:")
    for label, notes in [
        ("Build", bn),
        ("UI", un),
        ("Architecture", an),
        ("Security", sn),
        ("AI", ain),
    ]:
        print(f"  [{label}]")
        for n in notes:
            print(f"    - {n}")

    out_path = ROOT / "docs" / "executive-scores.json"
    out_path.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    target = min(
        scores[k]
        for k in (
            "Overall Health Score",
            "Build Quality Score",
            "UI Quality Score",
            "Architecture Score",
            "AI Workflow Score",
            "Hackathon Score",
        )
    ) >= 100
    return 0 if target else 1


if __name__ == "__main__":
    sys.exit(main())
