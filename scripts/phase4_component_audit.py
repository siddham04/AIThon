#!/usr/bin/env python3
"""Phase 4 — find orphan frontend modules and API paths."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "helix-frontend" / "src"
BACKEND = REPO / "helix-backend" / "app"

ROUTED_PAGES = {
    "Landing",
    "Login",
    "Register",
    "MissionControl",
    "WorkspacePage",
    "DeliveryPackage",
    "Settings",
    "WinningDemoScreen",
}


def read_files(exts: tuple[str, ...]) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for ext in exts:
        for p in SRC.rglob(f"*{ext}"):
            if "node_modules" in str(p):
                continue
            try:
                out[p] = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
    return out


def rel(p: Path) -> str:
    return str(p.relative_to(SRC)).replace("\\", "/")


def main() -> None:
    files = read_files((".jsx", ".js"))
    all_src = "\n".join(files.values())

    # Pages
    pages = sorted(SRC.glob("pages/*.jsx"))
    orphan_pages: list[str] = []
    reachable_pages: list[str] = []
    for p in pages:
        name = p.stem
        if name in ROUTED_PAGES:
            reachable_pages.append(rel(p))
            continue
        pat = re.compile(rf"pages/{re.escape(name)}|['\"]/{re.escape(name)}['\"]")
        refs = sum(1 for f, c in files.items() if f != p and pat.search(c))
        orphan_pages.append(rel(p))

    # Components
    comps = sorted(SRC.glob("components/**/*.jsx"))
    unused_components: list[str] = []
    used_components: list[str] = []
    for p in comps:
        r = rel(p)
        stem = p.stem
        imported = False
        for f, c in files.items():
            if f == p:
                continue
            if r.replace(".jsx", "") in c or f"/{stem}'" in c or f'/{stem}"' in c:
                imported = True
                break
        (used_components if imported else unused_components).append(r)

    # Libs
    libs = sorted(SRC.glob("lib/*.js"))
    unused_libs: list[str] = []
    for p in libs:
        r = rel(p)
        if not any(r.replace(".js", "") in c for f, c in files.items() if f != p):
            unused_libs.append(r)

    # Hooks
    hooks = sorted(SRC.glob("hooks/*.js"))
    hook_usage: dict[str, str] = {}
    for p in hooks:
        name = p.stem
        users = [
            rel(f)
            for f, c in files.items()
            if f != p and name in c and "hooks/" in c or f"use{name[3:]}" in c
        ]
        hook_usage[rel(p)] = users[:8]

    # Stores
    store_usage = {
        "useAuthStore": len(re.findall(r"useAuthStore", all_src)),
        "useProjectStore": len(re.findall(r"useProjectStore", all_src)),
        "useArtifactStore": len(re.findall(r"useArtifactStore", all_src)),
    }

    # API paths from frontend
    api_paths = sorted(set(re.findall(r"api\.(?:get|post|put|patch|delete)\(\s*[`'](/[^`'?]+)", all_src)))
    # Backend routes
    backend_paths: list[str] = []
    for route_file in (BACKEND / "api" / "routes").glob("*.py"):
        text = route_file.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'@router\.(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)', text):
            backend_paths.append(m.group(1))

    # Normalize backend to /api/... style (prefix from main.py is manual)
    PREFIX_MAP = {
        "artifacts": "/api/artifacts",
        "projects": "/api/projects",
        "demo": "/api/demo",
        "ingestion": "/api/ingest",
        "ingest": "/api/ingest",
    }

    # Extract frontend-used API prefixes
    fe_api = set()
    for p in api_paths:
        fe_api.add(p.split("{")[0].rstrip("/") or p)

    report = {
        "routed_pages": reachable_pages,
        "orphan_pages": orphan_pages,
        "orphan_page_count": len(orphan_pages),
        "unused_components": unused_components,
        "unused_component_count": len(unused_components),
        "unused_libs": unused_libs,
        "hook_usage": hook_usage,
        "store_usage": store_usage,
        "frontend_api_paths": api_paths,
        "frontend_api_count": len(api_paths),
    }

    out_json = REPO / "docs" / "phase4-audit-data.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Routed pages: {len(reachable_pages)}")
    print(f"Orphan pages: {len(orphan_pages)}")
    print(f"Unused components (heuristic): {len(unused_components)}")
    print(f"Unused libs: {len(unused_libs)}")
    print(f"Frontend API calls: {len(api_paths)}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()
