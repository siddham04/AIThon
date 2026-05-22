"""WebSocket progress — requires valid JWT (no anonymous task snooping)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ...services.security import decode_token
from ...services.task_progress import get_task_progress

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def progress_ws(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(..., min_length=10, description="JWT access token"),
) -> None:
    payload = decode_token((token or "").strip())
    if not payload or "sub" not in payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            msg = get_task_progress(task_id)
            await websocket.send_json(msg)
            st = str(msg.get("status") or "")
            if st in ("done", "error"):
                return
            await asyncio.sleep(0.4)
    except WebSocketDisconnect:
        return
