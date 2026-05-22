from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import get_settings
from ...services.ai_service import get_ai_service
from ...services.llm import get_llm
from ...sqla_models import User
from ..deps import get_current_user

router = APIRouter()

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-openssl-rand"


@router.get("/health")
async def health() -> dict:
    """Public liveness probe — no LLM or auth configuration details."""
    return {"status": "ok", "version": "0.2.1"}


@router.get("/health/detail")
async def health_detail(_user: User = Depends(get_current_user)) -> dict:
    """Authenticated operators only — deployment diagnostics."""
    llm = get_llm()
    ai = get_ai_service()
    settings = get_settings()
    insecure_jwt = settings.jwt_secret.strip() == _INSECURE_JWT_DEFAULT
    return {
        "status": "ok",
        "llm_configured": llm.enabled,
        "azure_openai_configured": llm.enabled,
        "ai_service_configured": ai.enabled,
        "version": "0.2.1",
        "demo_fast": settings.helix_demo_fast,
        "showcase_project_id": settings.helix_showcase_project_id,
        "auth": {
            "jwt_required_on_api": True,
            "jwt_secret_configured": not insecure_jwt,
            "rate_limit_per_minute": settings.helix_rate_limit_per_minute,
            "hackathon_auth": settings.allow_hackathon_auth,
        },
    }
