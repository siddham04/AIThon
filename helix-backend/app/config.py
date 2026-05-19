"""Configuration loaded from environment variables.

Supports two naming conventions so it works with whatever .env the
user has (the hackathon-provided template uses `AZURE_OAI_*` / `PLANNING_MODEL`,
while the OpenAI/Azure docs use `AZURE_OPENAI_*`):

  AZURE_OAI_ENDPOINT     |  AZURE_OPENAI_ENDPOINT
  AZURE_OAI_KEY          |  AZURE_OPENAI_API_KEY
  PLANNING_MODEL         |  AZURE_OPENAI_DEPLOYMENT
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    helix_debug: bool = True

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
    mongo_url: str = Field(
        default="",
        validation_alias=AliasChoices("MONGO_URL", "MONGODB_URL", "mongo_url"),
    )
    helix_export_model_label: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HELIX_EXPORT_MODEL_LABEL",
            "HELIX_EXPORT_AUDIT_MODEL",
        ),
        description="Shown in Markdown export audit footer (falls back to deployment name).",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.helix_cors_origins.split(",") if o.strip()]

    @property
    def is_configured(self) -> bool:
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
