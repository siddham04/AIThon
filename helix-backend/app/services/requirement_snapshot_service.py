"""Persist requirement text snapshots in MongoDB for version history."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def append_snapshot(project_id: str, text: str) -> dict[str, Any] | None:
    """Insert one snapshot. Returns inserted doc or None if Mongo unavailable."""
    settings = get_settings()
    url = (settings.mongo_url or "").strip()
    if not url or not text.strip():
        return None
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except Exception:
        return None

    client = AsyncIOMotorClient(url)
    try:
        db = client.get_default_database()
        col = db["requirement_snapshots"]
        doc = {
            "project_id": project_id,
            "text": text,
            "created_at": _utcnow(),
        }
        res = await col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return doc
    except Exception:
        return None
    finally:
        client.close()


async def list_snapshots(project_id: str, limit: int = 50) -> list[dict[str, Any]]:
    settings = get_settings()
    url = (settings.mongo_url or "").strip()
    if not url:
        return []
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except Exception:
        return []

    client = AsyncIOMotorClient(url)
    try:
        db = client.get_default_database()
        col = db["requirement_snapshots"]
        cur = (
            col.find({"project_id": project_id})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        out: list[dict[str, Any]] = []
        async for row in cur:
            ts = row.get("created_at")
            out.append(
                {
                    "id": str(row["_id"]),
                    "text": row.get("text") or "",
                    "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                }
            )
        return out
    except Exception:
        return []
    finally:
        client.close()
