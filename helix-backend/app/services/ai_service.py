"""LLM service wrapper backed by Azure OpenAI.

This is the high-level service used by chat, ambiguity, test-architect,
estimator, and artifact-generation flows. It exposes the same public
surface the rest of the codebase already calls (``complete_json``,
``stream_text``, ``stream_chat``, ``generate_artifacts``,
``stream_artifacts``, ``chat_system_with_context``) but routes every
request through Azure OpenAI using the credentials in ``.env``
(``AZURE_OAI_ENDPOINT`` / ``AZURE_OAI_KEY`` / ``PLANNING_MODEL``).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AsyncAzureOpenAI,
    BadRequestError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai.prompts.artifact_prompt import ARTIFACT_SYSTEM, artifact_user_message
from ai.prompts.chat_prompt import CHAT_SYSTEM

from ..config import get_settings
from .prompt_guard import wrap_untrusted_user_text
from .sensitive_scan import enforce_no_secrets_in_prompt

logger = logging.getLogger("helix.ai")

# Transient Azure / network failures we should retry on. ``BadRequestError``
# is intentionally excluded — those are caller bugs (bad payload / unsupported
# parameter for the deployment) and retrying won't help.
_RETRYABLE = (APIConnectionError, RateLimitError, APIStatusError, APIError)


def _safe_json(text: str) -> Dict[str, Any]:
    """Tolerant JSON parse — strips code fences and trailing prose."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        settings = get_settings()
        if settings.helix_debug:
            logger.error("Failed to parse JSON from Azure OpenAI. Raw=%s", text[:800])
        else:
            logger.error(
                "Failed to parse JSON from Azure OpenAI (%d chars)", len(text or "")
            )
        return {}


def _prepare_user_prompt(user: str, *, label: str = "input") -> str:
    enforce_no_secrets_in_prompt(user)
    return wrap_untrusted_user_text(user, label=label)


class AIService:
    """Async Azure-OpenAI client with retries and streaming helpers."""

    def __init__(self) -> None:
        s = get_settings()
        self._enabled = s.is_configured
        self._deployment = (s.azure_openai_deployment or "o3").strip() or "o3"
        self._client: Optional[AsyncAzureOpenAI] = None
        if self._enabled:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=s.azure_openai_endpoint,
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
            )
        else:
            logger.info(
                "Azure OpenAI not configured; AIService disabled. "
                "Set AZURE_OAI_ENDPOINT and AZURE_OAI_KEY in .env."
            )

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    # ------------------------------------------------------------------ #
    # JSON completion
    # ------------------------------------------------------------------ #

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    async def _chat_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
    ) -> str:
        assert self._client is not None
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = await self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content or "{}"

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError(
                "AIService not configured (missing AZURE_OAI_KEY / AZURE_OAI_ENDPOINT)"
            )
        user_msg = _prepare_user_prompt(user)
        raw = await self._chat_json(system=system, user=user_msg, max_tokens=max_tokens)
        return _safe_json(raw)

    async def complete_text(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
    ) -> str:
        """Plain-text (non-JSON) single-shot completion.

        Useful for outputs that are NOT JSON — e.g. Mermaid diagrams,
        SQL, code, markdown. Concatenates the streaming response.
        """
        if not self.enabled:
            raise RuntimeError(
                "AIService not configured (missing AZURE_OAI_KEY / AZURE_OAI_ENDPOINT)"
            )
        user_msg = _prepare_user_prompt(user)
        chunks: List[str] = []
        async for piece in self.stream_text(system, user_msg, max_tokens=max_tokens):
            chunks.append(piece)
        return "".join(chunks).strip()

    # ------------------------------------------------------------------ #
    # Streaming
    # ------------------------------------------------------------------ #

    async def stream_text(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async for piece in self.stream_chat(
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
        ):
            yield piece

    async def stream_chat(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        if not self.enabled:
            raise RuntimeError(
                "AIService not configured (missing AZURE_OAI_KEY / AZURE_OAI_ENDPOINT)"
            )
        assert self._client is not None
        prepared: List[Dict[str, str]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user" and content:
                content = _prepare_user_prompt(content, label="chat")
            prepared.append({"role": role, "content": content})
        full_messages = [{"role": "system", "content": system}, *prepared]

        attempt = 0
        last_exc: Optional[BaseException] = None
        while attempt < 3:
            attempt += 1
            try:
                async for piece in self._iter_stream(full_messages, max_tokens):
                    yield piece
                return
            except _RETRYABLE as exc:
                last_exc = exc
                await asyncio.sleep(min(30.0, 2.0**attempt))
        if last_exc:
            raise last_exc

    async def _iter_stream(
        self,
        full_messages: List[Dict[str, str]],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream tokens; gracefully fall back to non-streaming when the
        Azure deployment rejects ``stream=true`` (some o-series tiers do)."""
        assert self._client is not None
        try:
            stream = await self._client.chat.completions.create(
                model=self._deployment,
                messages=full_messages,
                max_completion_tokens=max_tokens,
                stream=True,
            )
        except BadRequestError as exc:
            if "stream" not in str(exc).lower():
                raise
            logger.info(
                "Azure deployment %s rejected stream=true; falling back to chunked non-streaming",
                self._deployment,
            )
            resp = await self._client.chat.completions.create(
                model=self._deployment,
                messages=full_messages,
                max_completion_tokens=max_tokens,
            )
            text = resp.choices[0].message.content or ""
            chunk = max(1, len(text) // 24 or 1)
            for i in range(0, len(text), chunk):
                yield text[i : i + chunk]
                await asyncio.sleep(0.005)
            return

        async for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta
            piece = getattr(delta, "content", None)
            if piece:
                yield piece

    # ------------------------------------------------------------------ #
    # Convenience helpers (kept identical to the previous Anthropic API)
    # ------------------------------------------------------------------ #

    async def generate_artifacts(self, text: str) -> Dict[str, Any]:
        user = artifact_user_message(text)
        return await self.complete_json(ARTIFACT_SYSTEM, user, max_tokens=8192)

    async def stream_artifacts(self, text: str) -> AsyncIterator[str]:
        user = artifact_user_message(text)
        async for chunk in self.stream_text(ARTIFACT_SYSTEM, user, max_tokens=8192):
            yield chunk

    def chat_system_with_context(self, workspace_json: str) -> str:
        return (
            f"{CHAT_SYSTEM}\n\n"
            "Workspace artifacts (JSON). Use only this context unless the user asks general SDLC advice:\n"
            f"{workspace_json}"
        )


_singleton: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _singleton
    if _singleton is None:
        _singleton = AIService()
    return _singleton
