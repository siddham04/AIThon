"""Thin wrapper around Azure OpenAI with structured-output helpers.

Uses the OpenAI Python SDK's AzureOpenAI client. Falls back to a deterministic
mock when no key is configured so the UI is fully demo-able offline.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from openai import AsyncAzureOpenAI

from ..config import get_settings

logger = logging.getLogger("helix.llm")

_LLM_MAX_ATTEMPTS = 3
_LLM_RETRY_BASE_SEC = 0.75


async def _retry_llm(coro_factory, *, label: str = "llm"):
    """Retry transient Azure OpenAI failures with exponential backoff."""
    last: Exception | None = None
    for attempt in range(1, _LLM_MAX_ATTEMPTS + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last = exc
            if attempt >= _LLM_MAX_ATTEMPTS:
                break
            delay = _LLM_RETRY_BASE_SEC * (2 ** (attempt - 1))
            logger.warning(
                "%s attempt %s/%s failed (%s); retry in %.1fs",
                label,
                attempt,
                _LLM_MAX_ATTEMPTS,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    assert last is not None
    raise last


class LLMService:
    def __init__(self) -> None:
        s = get_settings()
        # Mirror AIService: honor the HELIX_USE_AI kill-switch even when
        # Azure keys are present. Without this, agents that call through
        # this service (decomposer, solution_architect, etc.) bypass the
        # use_ai=False parameter threaded through run_demo and hit the
        # live LLM whenever the developer has Azure keys in .env or
        # leaked into their shell session — which (a) makes the golden
        # contract take 30+ minutes and (b) causes connection errors
        # when running scripts offline.
        self._enabled = s.is_configured and getattr(s, "helix_use_ai", True)
        self._deployment = s.azure_openai_deployment
        if self._enabled:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=s.azure_openai_endpoint,
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
            )
        else:
            self._client = None
            logger.warning(
                "Azure OpenAI not configured; LLMService running in MOCK mode."
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: Optional[str] = None,
        max_completion_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """Call the model and parse a JSON response."""
        if not self._enabled or self._client is None:
            raise RuntimeError("LLMService not configured")

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if schema_hint:
            messages.insert(
                1,
                {
                    "role": "system",
                    "content": (
                        "Respond with JSON ONLY (no markdown fences). "
                        "It must conform to this schema:\n" + schema_hint
                    ),
                },
            )

        # o-series models use `max_completion_tokens` and don't accept temperature.
        kwargs: Dict[str, Any] = {
            "model": self._deployment,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "max_completion_tokens": max_completion_tokens,
        }

        resp = await _retry_llm(
            lambda: self._client.chat.completions.create(**kwargs),
            label="chat_json",
        )

        content = resp.choices[0].message.content or "{}"
        parsed = _safe_json(content)
        if not parsed and (content or "").strip() not in ("", "{}"):
            logger.warning(
                "chat_json: unparseable model output (%d chars)",
                len(content),
            )
        return parsed

    async def chat_text(
        self,
        system: str,
        user: str,
        *,
        history: Optional[List[Dict[str, str]]] = None,
        max_completion_tokens: int = 1500,
    ) -> str:
        if not self._enabled or self._client is None:
            raise RuntimeError("LLMService not configured")

        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        resp = await _retry_llm(
            lambda: self._client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
            ),
            label="chat_text",
        )
        return resp.choices[0].message.content or ""

    async def chat_json_with_fallback(
        self,
        agent: str,
        project: "Project",
        system: str,
        user: str,
        *,
        schema_hint: Optional[str] = None,
        max_completion_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """Azure JSON mode when configured; deterministic mock otherwise."""
        if self._enabled and self._client is not None:
            return await self.chat_json(
                system,
                user,
                schema_hint=schema_hint,
                max_completion_tokens=max_completion_tokens,
            )
        from .mock_agents import synthetic_json

        return synthetic_json(agent, project)

    async def chat_text_with_fallback(
        self,
        project: "Project",
        system: str,
        user_message: str,
        *,
        history: Optional[List[Dict[str, str]]] = None,
        max_completion_tokens: int = 1500,
    ) -> str:
        if self._enabled and self._client is not None:
            return await self.chat_text(
                system,
                user_message,
                history=history,
                max_completion_tokens=max_completion_tokens,
            )
        from .mock_agents import mock_chat_reply

        return mock_chat_reply(project, user_message)


def _safe_json(text: str) -> Dict[str, Any]:
    """Robust JSON parse that tolerates code fences and trailing commentary."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # Find the first { and last } to bound the JSON
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        settings = get_settings()
        if settings.helix_debug:
            logger.error("Failed to parse JSON from LLM. Raw=%s", text[:500])
        else:
            logger.error("Failed to parse JSON from LLM (%d chars)", len(text))
        return {}


_singleton: Optional[LLMService] = None


def get_llm() -> LLMService:
    global _singleton
    if _singleton is None:
        _singleton = LLMService()
    return _singleton
