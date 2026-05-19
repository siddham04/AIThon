"""Version snapshots for projects (JSON files on disk).

Hackathon-friendly persistence without standing up a database.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..models import Project

logger = logging.getLogger("helix.snapshots")


def save_project_snapshot(project: Project, *, label: str = "analyze") -> Optional[str]:
    """Write `project` JSON under HELIX_DATA_DIR/snapshots/<id>/`. Returns path or None."""
    try:
        s = get_settings()
        root = Path(s.helix_data_dir).expanduser().resolve()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dest = root / "snapshots" / project.id / f"{label}-{ts}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Snapshot written: %s", dest)
        return str(dest)
    except Exception as exc:  # pragma: no cover
        logger.warning("Snapshot failed: %s", exc)
        return None
