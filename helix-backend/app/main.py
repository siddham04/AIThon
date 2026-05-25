"""Helix FastAPI application — Phase 2 routers."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .api.deps import helix_auth_gate
from .api.routes import (
    ambiguity,
    artifacts,
    assistant,
    auth,
    backlog,
    chat,
    command_center,
    control_tower,
    delivery,
    demo,
    executive,
    devstudio,
    export,
    forecast,
    health,
    impact,
    ingestion,
    insights,
    meeting,
    projects,
    quality,
    readiness_center,
    requirement_diff,
    requirement_versions,
    risk_center,
    review_board,
    sprint_plan,
    studio,
    testcases,
    traceability,
    ws,
)
from .bootstrap import (
    ensure_demo_user,
    ensure_showcase_on_startup,
    warn_insecure_jwt_secret,
)
from .config import get_settings
from .database import init_db
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_log import RequestLogMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    warn_insecure_jwt_secret()
    ensure_demo_user()
    ensure_showcase_on_startup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.helix_debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    expose_docs = settings.helix_debug and not settings.helix_production
    app = FastAPI(
        title="Helix — Intelligent SDLC Copilot",
        description=(
            "Multi-agent AI platform that turns raw requirements into a "
            "traceable graph of stories, tasks, tests, ambiguities, and risks."
        ),
        version="0.2.1",
        lifespan=lifespan,
        docs_url="/docs" if expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_docs else None,
    )

    _rx = (settings.helix_cors_origin_regex or "").strip()
    if _rx:
        if settings.helix_production:
            logging.getLogger("helix.main").warning(
                "HELIX_CORS_ORIGIN_REGEX is set in production — use a tight pattern with allow_credentials"
            )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_origin_regex=_rx,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLogMiddleware)

    gate = [Depends(helix_auth_gate)]

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(projects.router, prefix="/api/projects", dependencies=gate, tags=["projects"])
    app.include_router(
        requirement_versions.router,
        prefix="/api/projects",
        dependencies=gate,
        tags=["requirement-versions"],
    )
    app.include_router(ingestion.router, prefix="/api/ingest", dependencies=gate, tags=["ingest"])
    app.include_router(artifacts.router, prefix="/api/artifacts", dependencies=gate, tags=["artifacts"])
    app.include_router(testcases.router, prefix="/api/testcases", dependencies=gate, tags=["testcases"])
    app.include_router(ambiguity.router, prefix="/api/ambiguity", dependencies=gate, tags=["ambiguity"])
    app.include_router(chat.router, prefix="/api/chat", dependencies=gate, tags=["chat"])
    app.include_router(export.router, prefix="/api/export", dependencies=gate, tags=["export"])
    app.include_router(
        insights.router, prefix="/api/insights", dependencies=gate, tags=["insights"]
    )
    app.include_router(
        control_tower.router,
        prefix="/api/control-tower",
        dependencies=gate,
        tags=["control-tower"],
    )
    app.include_router(
        command_center.router,
        prefix="/api/command-center",
        dependencies=gate,
        tags=["command-center"],
    )
    app.include_router(
        executive.router,
        prefix="/api/executive",
        dependencies=gate,
        tags=["executive"],
    )
    app.include_router(
        review_board.router,
        prefix="/api/review-board",
        dependencies=gate,
        tags=["review-board"],
    )
    app.include_router(
        quality.router,
        prefix="/api/quality",
        dependencies=gate,
        tags=["quality"],
    )
    app.include_router(
        impact.router,
        prefix="/api/impact",
        dependencies=gate,
        tags=["impact"],
    )
    app.include_router(
        backlog.router,
        prefix="/api/backlog",
        dependencies=gate,
        tags=["backlog"],
    )
    app.include_router(
        sprint_plan.router,
        prefix="/api/sprint-plan",
        dependencies=gate,
        tags=["sprint-plan"],
    )
    app.include_router(
        studio.router,
        prefix="/api/studio",
        dependencies=gate,
        tags=["studio"],
    )
    app.include_router(
        devstudio.router,
        prefix="/api/devstudio",
        dependencies=gate,
        tags=["devstudio"],
    )
    app.include_router(
        forecast.router,
        prefix="/api/forecast",
        dependencies=gate,
        tags=["forecast"],
    )
    app.include_router(
        meeting.router,
        prefix="/api/meeting",
        dependencies=gate,
        tags=["meeting"],
    )
    app.include_router(
        requirement_diff.router,
        prefix="/api/diff",
        dependencies=gate,
        tags=["diff"],
    )
    app.include_router(
        traceability.router,
        prefix="/api/traceability",
        dependencies=gate,
        tags=["traceability"],
    )
    app.include_router(
        risk_center.router,
        prefix="/api/risk-center",
        dependencies=gate,
        tags=["risk-center"],
    )
    app.include_router(
        readiness_center.router,
        prefix="/api/readiness-center",
        dependencies=gate,
        tags=["readiness-center"],
    )
    app.include_router(
        assistant.router,
        prefix="/api/assistant",
        dependencies=gate,
        tags=["assistant"],
    )
    app.include_router(
        delivery.router,
        prefix="/api/delivery",
        dependencies=gate,
        tags=["delivery"],
    )
    app.include_router(
        demo.router,
        prefix="/api/demo",
        dependencies=gate,
        tags=["demo"],
    )
    app.include_router(ws.router, prefix="/api", tags=["ws"])

    serve_spa = os.environ.get("HELIX_SERVE_SPA", "").lower() in ("1", "true", "yes")
    static_dir = (os.environ.get("HELIX_STATIC_DIR") or "").strip()
    spa_index = (
        os.path.join(static_dir, "index.html")
        if static_dir and os.path.isdir(static_dir)
        else ""
    )
    spa_ready = serve_spa and static_dir and os.path.isfile(spa_index)

    if not spa_ready:

        @app.get("/")
        async def root() -> dict:
            """API-only mode: Helix UI runs on Vite (default http://localhost:5173)."""
            return {
                "name": "Helix — Intelligent SDLC Copilot",
                "tagline": "From idea to impact, with provenance.",
                "api_health": "/api/health",
                "docs": "/docs",
                "ui": "http://localhost:5173",
                "hint": "Open the UI URL above. This port (8765) is the REST API only.",
            }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    async def root_health_probe() -> dict:
        """Minimal probe for legacy clients expecting GET /health (full probe: GET /api/health)."""
        return {"status": "ok"}

    if spa_ready:
        from starlette.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=static_dir, html=True), name="spa")
    elif serve_spa and static_dir:
        logging.getLogger("helix.main").warning(
            "HELIX_SERVE_SPA is set but %s is missing — serving API JSON at / instead.",
            spa_index or static_dir,
        )

    return app


app = create_app()
