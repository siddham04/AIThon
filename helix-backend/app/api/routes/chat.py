from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...agents.chat import ChatAgent, _project_context
from ...database import SessionLocal
from ...models import ChatMessage
from ...schemas.chat import ChatRequestBody
from ...services.ai_service import get_ai_service
from ...services.project_bridge import ensure_project_row
from ...services.store import get_store
from ...sqla_models import User
from ..deps import get_current_user
from ..route_helpers import get_owned_project_row, load_project_graph

router = APIRouter()


@router.post("/{project_id}")
async def chat_stream(
    project_id: str,
    body: ChatRequestBody,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    uid = user.id
    db0 = SessionLocal()
    try:
        u0 = db0.merge(user)
        row = get_owned_project_row(db0, u0, project_id)
        project = load_project_graph(db0, row)
    finally:
        db0.close()

    prefix_lines: list[str] = []
    for turn in body.history[-16:]:
        prefix_lines.append(f"{turn.role.upper()}: {turn.content}")
    prefix = "\n".join(prefix_lines)
    user_turn = f"{prefix}\n\nUSER:\n{body.message}" if prefix else body.message

    async def events() -> AsyncIterator[str]:
        user_msg = ChatMessage(role="user", content=body.message.strip())
        project.chat_history.append(user_msg)
        ai = get_ai_service()
        try:
            if ai.enabled:
                system = ai.chat_system_with_context(_project_context(project))
                msgs = [
                    {"role": m.role, "content": m.content}
                    for m in project.chat_history[:-1]
                ]
                msgs.append({"role": "user", "content": user_turn})
                pieces: list[str] = []
                async for piece in ai.stream_chat(system=system, messages=msgs):
                    pieces.append(piece)
                    yield f"data: {json.dumps({'token': piece})}\n\n"
                text = "".join(pieces)
                cites = list(
                    set(
                        re.findall(
                            r"(?:story|task|test|amb|risk|clause)_[a-z0-9]{4,}",
                            text,
                        )
                    )
                )
                reply = ChatMessage(
                    role="assistant", content=text, citations=cites
                )
            else:
                agent = ChatAgent()
                reply = await agent.reply(project, user_turn)
                text = reply.content or ""
                chunk = max(1, len(text) // 24 or 1)
                for i in range(0, len(text), chunk):
                    piece = text[i : i + chunk]
                    yield f"data: {json.dumps({'token': piece})}\n\n"
                    await asyncio.sleep(0.01)
            project.chat_history.append(reply)
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return
        dbw = SessionLocal()
        try:
            u2 = dbw.get(User, uid)
            if u2 is None:
                yield f"event: error\ndata: {json.dumps({'error': 'user missing'})}\n\n"
                return
            ensure_project_row(dbw, project, uid)
            dbw.commit()
        finally:
            dbw.close()
        store = get_store()
        if await store.get(project_id):
            await store.update(project)
        else:
            await store.create(project)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
