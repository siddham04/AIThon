"""Request-ID + structured access/error log for production debugging."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

log = logging.getLogger("helix.request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Attach an `X-Request-ID` to every response and emit a single access log line.

    Logs `5xx` and unhandled exceptions with the request id so backend traces
    can be correlated with the response the client received.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = (request.headers.get("x-request-id") or uuid.uuid4().hex)[:32]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover — safety net
            duration_ms = int((time.perf_counter() - start) * 1000)
            log.exception(
                "request_failed rid=%s method=%s path=%s duration_ms=%d err=%s",
                rid,
                request.method,
                request.url.path,
                duration_ms,
                exc,
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = rid

        if response.status_code >= 500:
            log.error(
                "%s %s -> %d rid=%s duration_ms=%d",
                request.method,
                request.url.path,
                response.status_code,
                rid,
                duration_ms,
            )
        elif response.status_code >= 400 and request.url.path.startswith("/api/"):
            log.info(
                "%s %s -> %d rid=%s duration_ms=%d",
                request.method,
                request.url.path,
                response.status_code,
                rid,
                duration_ms,
            )

        return response
