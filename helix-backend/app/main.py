"""Helix FastAPI application — Phase 2 routers."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.deps import helix_auth_gate
from .api.routes import (
    ambiguity,
    artifacts,
    auth,
    chat,
    export,
    health,
    ingestion,
    projects,
    requirement_versions,
    testcases,
    ws,
)
from .bootstrap import ensure_demo_user
from .config import get_settings
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_demo_user()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.helix_debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    app = FastAPI(
        title="Helix — Intelligent SDLC Copilot",
        description=(
            "Multi-agent AI platform that turns raw requirements into a "
            "traceable graph of stories, tasks, tests, ambiguities, and risks."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    app.include_router(ws.router, prefix="/api", tags=["ws"])

    @app.get("/")
    async def root() -> dict:
        return {
            "name": "Helix — Intelligent SDLC Copilot",
            "tagline": "From idea to impact, with provenance.",
            "docs": "/docs",
        }

    @app.get("/health")
    async def root_health_probe() -> dict:
        """Minimal probe for legacy clients expecting GET /health (full probe: GET /api/health)."""
        return {"status": "ok"}

    return app


app = create_app()
