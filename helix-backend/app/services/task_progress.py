from __future__ import annotations

import json
import threading
import time
from typing import Any

from ..config import get_settings

_lock = threading.Lock()
_memory: dict[str, dict[str, Any]] = {}


def _redis():
    try:
        import redis

        url = get_settings().redis_url
        r = redis.Redis.from_url(url, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def set_task_progress(task_id: str, percent: int, status: str, message: str) -> None:
    payload = {
        "percent": max(0, min(100, int(percent))),
        "status": status,
        "message": message,
        "ts": time.time(),
    }
    r = _redis()
    if r:
        r.setex(f"helix:task:{task_id}", 86400, json.dumps(payload))
        return
    with _lock:
        _memory[task_id] = payload


def get_task_progress(task_id: str) -> dict[str, Any]:
    r = _redis()
    if r:
        raw = r.get(f"helix:task:{task_id}")
        if raw:
            return json.loads(raw)
        return {"percent": 0, "status": "unknown", "message": "No task state"}
    with _lock:
        return _memory.get(
            task_id, {"percent": 0, "status": "unknown", "message": "No task state"}
        )
