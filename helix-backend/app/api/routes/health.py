from __future__ import annotations

from fastapi import APIRouter

from ...services.ai_service import get_ai_service
from ...services.llm import get_llm

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    llm = get_llm()
    ai = get_ai_service()
    return {
        "status": "ok",
        "llm_configured": llm.enabled,
        "azure_openai_configured": llm.enabled,
        "anthropic_configured": ai.enabled,
        "version": "0.2.0",
    }
