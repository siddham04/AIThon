from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services.task_progress import get_task_progress

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def progress_ws(websocket: WebSocket, task_id: str) -> None:
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
