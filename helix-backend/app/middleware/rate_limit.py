"""In-memory sliding-window rate limit for expensive API paths."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..config import get_settings

_WINDOW_SEC = 60.0
_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)

_EXPENSIVE_FRAGMENTS = (
    "/generate",
    "/analyze",
    "/demo/",
    "/run",
    "/jira-push",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/guest",
    "/api/ingest/",
)


def _client_key(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return f"user:{auth[7:16]}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    if request.client:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _is_limited_path(path: str) -> bool:
    p = path.lower()
    if "/api/health" in p or p.endswith("/health"):
        return False
    return any(frag in p for frag in _EXPENSIVE_FRAGMENTS)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()
        limit = int(settings.helix_rate_limit_per_minute or 0)
        if limit <= 0 or request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        path = request.url.path
        if not _is_limited_path(path):
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        bucket = _BUCKETS[key]
        while bucket and now - bucket[0] > _WINDOW_SEC:
            bucket.popleft()

        if len(bucket) >= limit:
            return Response(
                content='{"detail":"Rate limit exceeded — retry in a minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(bucket)))
        return response
