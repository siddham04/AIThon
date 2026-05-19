"""Anthropic Messages API wrapper with retries and streaming helpers."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from anthropic import APIConnectionError, AsyncAnthropic, InternalServerError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ai.prompts.artifact_prompt import ARTIFACT_SYSTEM, artifact_user_message
from ai.prompts.chat_prompt import CHAT_SYSTEM

from ..config import get_settings

logger = logging.getLogger("helix.ai")

_RETRYABLE = (APIConnectionError, RateLimitError, InternalServerError)


def _safe_json(text: str) -> Dict[str, Any]:
    text = text.strip()
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
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from Anthropic. Raw=%s", text[:800])
        return {}


class AIService:
    def __init__(self) -> None:
        s = get_settings()
        key = (s.anthropic_api_key or "").strip()
        self._enabled = bool(key)
        self._model = (s.anthropic_model or "claude-3-5-sonnet-20241022").strip()
        self._client: Optional[AsyncAnthropic] = (
            AsyncAnthropic(api_key=key) if self._enabled else None
        )
        if not self._enabled:
            logger.info("Anthropic API key not set; AIService disabled.")

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    async def _messages_create(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
    ) -> str:
        assert self._client is not None
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts: List[str] = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("AIService not configured (missing ANTHROPIC_API_KEY)")
        raw = await self._messages_create(system=system, user=user, max_tokens=max_tokens)
        return _safe_json(raw)

    async def stream_text(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        if not self.enabled:
            raise RuntimeError("AIService not configured (missing ANTHROPIC_API_KEY)")
        assert self._client is not None
        attempt = 0
        last_exc: Optional[BaseException] = None
        while attempt < 3:
            attempt += 1
            try:
                async with self._client.messages.stream(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
                return
            except _RETRYABLE as exc:
                last_exc = exc
                await asyncio.sleep(min(30.0, 2.0 ** attempt))
        if last_exc:
            raise last_exc

    async def stream_chat(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        if not self.enabled:
            raise RuntimeError("AIService not configured (missing ANTHROPIC_API_KEY)")
        assert self._client is not None
        attempt = 0
        last_exc: Optional[BaseException] = None
        while attempt < 3:
            attempt += 1
            try:
                async with self._client.messages.stream(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
                return
            except _RETRYABLE as exc:
                last_exc = exc
                await asyncio.sleep(min(30.0, 2.0 ** attempt))
        if last_exc:
            raise last_exc

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
