"""Pytest config — force offline / mock mode for every backend test.

Helix's golden-domain pipeline test must NEVER call out to Azure
OpenAI or Anthropic; that would make CI flaky on network errors and
quota limits.

We force mock mode by setting the relevant env vars to empty strings
**before any ``app.*`` module is imported**. Empty values take
precedence over any ``helix-backend/.env`` file that pydantic-settings
would otherwise read (env > dotenv in pydantic-settings priority).
"""
from __future__ import annotations

import os

# Empty (not popped) — pydantic-settings honors env > dotenv, so this
# overrides whatever lives in helix-backend/.env.
for _k in (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OAI_KEY",
    "AZURE_OAI_ENDPOINT",
    "ANTHROPIC_API_KEY",
):
    os.environ[_k] = ""

os.environ["HELIX_USE_AI"] = "false"
os.environ["HELIX_DEMO_FAST"] = "true"
os.environ.setdefault("HELIX_ALLOW_INSECURE_JWT", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./helix_test.db")
