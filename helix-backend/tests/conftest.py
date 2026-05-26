"""Pytest config — force offline / mock mode for every backend test.

Helix's golden-domain pipeline test must NEVER call out to Azure
OpenAI or Anthropic; that would make CI flaky on network errors,
take ~30 minutes per run, and (most importantly) return
LLM-generated acceptance-criteria IDs like ``AC1/AC2/AC3`` that
don't exist in ``project.source_clauses`` — which makes
``test_every_artifact_cites_a_clause`` fail at 0% coverage even
though the mock pipeline works fine.

Two-layer defense:

  1. Set ``HELIX_USE_AI=false`` and blank every Azure / Anthropic
     key in ``os.environ`` *before* any ``app.*`` module is
     imported. The new ``Settings.helix_use_ai`` field is consulted
     by ``AIService.enabled`` so every direct ``get_ai_service()``
     call (test_architect, ambiguity, chat, etc.) routes to the
     deterministic mock fallback.

  2. Invalidate the ``get_settings()`` ``lru_cache`` so any module
     that imported and cached settings earlier in the interpreter
     life (e.g. a pre-pytest IDE inspection) gets refreshed.
"""
from __future__ import annotations

import os

# Empty (not popped) — pydantic-settings honors env > dotenv, so this
# overrides whatever lives in helix-backend/.env (or the developer's
# PowerShell session) without us having to physically delete the keys.
for _k in (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OAI_KEY",
    "AZURE_OAI_ENDPOINT",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
):
    os.environ[_k] = ""

# Kill-switch + speed flag. helix_use_ai is now a first-class field
# in Settings; AIService.enabled = is_configured AND helix_use_ai,
# so this single env wins even when Azure creds are present.
os.environ["HELIX_USE_AI"] = "false"
os.environ["HELIX_DEMO_FAST"] = "true"
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./helix_test.db")

# Defensive: bust any cached Settings instance. If a tool imported
# app.config before pytest collected this conftest (rare but possible
# with editor plugins / coverage tooling), the @lru_cache(maxsize=1)
# on get_settings() would otherwise hand out a Settings built from
# the developer's real .env. Clearing it is a no-op when the cache is
# empty and cheap when it isn't.
try:  # pragma: no cover - defensive
    from app.config import get_settings as _get_settings

    _get_settings.cache_clear()
except Exception:
    # If app.config can't import yet (e.g. backend deps not installed
    # in this venv) we simply rely on the env-var precedence above.
    pass
