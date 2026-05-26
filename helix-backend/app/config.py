"""Configuration loaded from environment variables.

Supports two naming conventions so it works with whatever .env the
user has (the hackathon-provided template uses `AZURE_OAI_*` / `PLANNING_MODEL`,
while the OpenAI/Azure docs use `AZURE_OPENAI_*`):

  AZURE_OAI_ENDPOINT     |  AZURE_OPENAI_ENDPOINT
  AZURE_OAI_KEY          |  AZURE_OPENAI_API_KEY
  PLANNING_MODEL         |  AZURE_OPENAI_DEPLOYMENT

We also probe ``../.env`` so a single ``.env`` checked into the repo root
(next to ``docker-compose.yml``) works regardless of whether the API is
launched from the repo root or from the ``helix-backend/`` folder.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_BACKEND_ROOT)

# Load order: backend-local .env first, then repo-root .env. Pydantic-Settings
# applies later files on top of earlier ones, and OS-level env vars trump both
# — so a developer can keep the master Azure key in the repo-root file and
# override per-shell when needed.
_ENV_FILES: tuple[str, ...] = (
    os.path.join(_BACKEND_ROOT, ".env"),
    os.path.join(_REPO_ROOT, ".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    azure_openai_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OAI_ENDPOINT",
        ),
    )
    azure_openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_API_KEY",
            "AZURE_OAI_KEY",
        ),
    )
    azure_openai_deployment: str = Field(
        default="o3",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_DEPLOYMENT",
            "PLANNING_MODEL",
        ),
    )
    azure_openai_api_version: str = Field(
        default="2024-12-01-preview",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OAI_API_VERSION",
        ),
    )

    helix_cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    )
    helix_cors_origin_regex: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HELIX_CORS_ORIGIN_REGEX",
            "helix_cors_origin_regex",
        ),
        description=(
            "Optional regex for extra allowed browser origins when the UI is on a "
            "different host than the API (e.g. Vercel: https://.*.vercel.app with dots escaped for regex)."
        ),
    )
    helix_debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("HELIX_DEBUG", "helix_debug"),
    )
    # Global AI kill-switch. When False, AIService.enabled returns False
    # regardless of whether Azure keys are configured — every agent that
    # checks ai.enabled drops to the deterministic mock / heuristic
    # fallback. This is what the golden + adversarial pytest contracts
    # set (via tests/conftest.py) so the suite NEVER touches the live
    # LLM even when the developer has Azure keys in their .env.
    helix_use_ai: bool = Field(
        default=True,
        validation_alias=AliasChoices("HELIX_USE_AI"),
        description=(
            "Set to false to force the deterministic mock + heuristic "
            "fallback chain even when Azure OpenAI keys are configured. "
            "Used by the test suite and by Render Free deploys."
        ),
    )
    helix_allow_insecure_jwt: bool = Field(
        default=False,
        validation_alias=AliasChoices("HELIX_ALLOW_INSECURE_JWT"),
        description="Allow default JWT_SECRET for local dev only (never in production).",
    )
    helix_hackathon_auth: bool = Field(
        default=True,
        validation_alias=AliasChoices("HELIX_HACKATHON_AUTH"),
        description="Guest accounts + login auto-register (off when HELIX_PRODUCTION=1).",
    )
    helix_max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        validation_alias=AliasChoices("HELIX_MAX_UPLOAD_BYTES"),
    )

    helix_data_dir: str = Field(
        default=".helix-data",
        validation_alias=AliasChoices("HELIX_DATA_DIR"),
    )
    helix_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("HELIX_API_KEY"),
    )
    helix_demo_email: str = Field(
        default="demo@demo.com",
        validation_alias=AliasChoices("HELIX_DEMO_EMAIL", "HELIX_DEMO_USER"),
        description="Email for the auto-seeded demo account (startup + scripts/seed.py).",
    )
    helix_demo_password: str = Field(
        default="demo123",
        validation_alias=AliasChoices("HELIX_DEMO_PASSWORD"),
        description="Password for the auto-seeded demo account.",
    )
    jira_webhook_url: str = Field(
        default="",
        validation_alias=AliasChoices("HELIX_JIRA_WEBHOOK_URL", "JIRA_WEBHOOK_URL"),
    )
    # JIRA REST (Phase 5) — Cloud: email + API token as password
    jira_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("JIRA_BASE_URL", "jira_base_url"),
    )
    jira_email: str = Field(
        default="",
        validation_alias=AliasChoices("JIRA_EMAIL", "jira_email"),
    )
    jira_token: str = Field(
        default="",
        validation_alias=AliasChoices("JIRA_TOKEN", "jira_token", "JIRA_API_TOKEN"),
    )
    jira_project_key: str = Field(
        default="",
        validation_alias=AliasChoices("JIRA_PROJECT_KEY", "jira_project_key"),
    )
    jira_epic_link_field: str = Field(
        default="",
        validation_alias=AliasChoices(
            "JIRA_EPIC_LINK_FIELD",
            "jira_epic_link_field",
        ),
        description="Classic Jira: custom field id for Epic Link, e.g. customfield_10014",
    )
    github_token: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_TOKEN", "github_token", "GH_TOKEN"),
    )
    github_repo: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_REPO", "github_repo"),
        description="owner/repository",
    )

    # --- Phase 2: Anthropic, DB, Redis, JWT, Mongo ---
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "anthropic_model"),
    )
    db_url: str = Field(
        default="sqlite:///./helix.db",
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL", "POSTGRES_URL", "db_url"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    jwt_secret: str = Field(
        default="change-me-in-production-use-openssl-rand",
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    helix_jwt_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias=AliasChoices("HELIX_JWT_EXPIRE_MINUTES"),
        description="Access token TTL; rotate JWT_SECRET to revoke all tokens.",
    )
    mongo_url: str = Field(
        default="",
        validation_alias=AliasChoices("MONGO_URL", "MONGODB_URL", "mongo_url"),
    )
    helix_default_developers: int = Field(
        default=4,
        validation_alias=AliasChoices("HELIX_DEFAULT_DEVELOPERS"),
        description="Default team size for delivery cost estimates.",
    )
    helix_hourly_rate_usd: float = Field(
        default=75.0,
        validation_alias=AliasChoices("HELIX_HOURLY_RATE_USD"),
        description="Blended hourly rate for cost estimates.",
    )
    helix_hours_per_dev_week: float = Field(
        default=40.0,
        validation_alias=AliasChoices("HELIX_HOURS_PER_DEV_WEEK"),
    )
    helix_points_per_dev_per_sprint: int = Field(
        default=12,
        validation_alias=AliasChoices("HELIX_POINTS_PER_DEV_PER_SPRINT"),
    )
    helix_cost_per_story_point_usd: float = Field(
        default=135.0,
        validation_alias=AliasChoices("HELIX_COST_PER_STORY_POINT_USD"),
        description="Management cost rollup: story_points × this rate (89 pts ≈ $12,050).",
    )
    helix_export_model_label: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HELIX_EXPORT_MODEL_LABEL",
            "HELIX_EXPORT_AUDIT_MODEL",
        ),
        description="Shown in Markdown export audit footer (falls back to deployment name).",
    )
    helix_demo_fast: bool = Field(
        default=True,
        validation_alias=AliasChoices("HELIX_DEMO_FAST", "helix_demo_fast"),
        description="When true, demo SSE uses heuristics (use_ai=false) for ~3–4 min judge timing.",
    )
    helix_showcase_project_id: str = Field(
        default="proj_demo_seed01",
        validation_alias=AliasChoices(
            "HELIX_SHOWCASE_PROJECT_ID",
            "helix_showcase_project_id",
        ),
        description="Pre-baked backup project id (scripts/seed.py).",
    )
    helix_rate_limit_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices("HELIX_RATE_LIMIT_PER_MINUTE"),
        description="POST rate limit per client per minute on /generate, /analyze, /demo (0=off).",
    )
    helix_demo_parallel: bool = Field(
        default=True,
        validation_alias=AliasChoices("HELIX_DEMO_PARALLEL", "helix_demo_parallel"),
        description="Run independent demo orchestrator steps in parallel batches.",
    )
    helix_production: bool = Field(
        default=False,
        validation_alias=AliasChoices("HELIX_PRODUCTION", "helix_production"),
        description="When true, refuse startup if JWT_SECRET is still the insecure default.",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.helix_cors_origins.split(",") if o.strip()]

    @property
    def allow_hackathon_auth(self) -> bool:
        if self.helix_production:
            return False
        return bool(self.helix_hackathon_auth)

    @property
    def is_configured(self) -> bool:
        # NOTE: this stays a pure "do we have credentials?" check so
        # diagnostic UIs and health endpoints can still say
        # "Azure is configured but disabled". The runtime kill-switch
        # lives in AIService.enabled (which also consults helix_use_ai).
        endpoint = self.azure_openai_endpoint.strip()
        key = self.azure_openai_api_key.strip()
        if not endpoint or not key:
            return False
        # Reject obvious placeholder values
        if "your-resource" in endpoint or "your-key" in key:
            return False
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
