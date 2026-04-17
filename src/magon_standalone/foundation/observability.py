# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter
from typing import Awaitable, Callable
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response

LOGGER = logging.getLogger("magon.foundation")


@dataclass(slots=True)
class TelemetryState:
    started_at: float = field(default_factory=perf_counter)
    request_count: int = 0
    error_count: int = 0
    route_hits: Counter[str] = field(default_factory=Counter)
    method_hits: Counter[str] = field(default_factory=Counter)

    def snapshot(self) -> dict[str, object]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "route_hits": dict(self.route_hits),
            "method_hits": dict(self.method_hits),
        }


async def telemetry_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    telemetry: TelemetryState,
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        telemetry.request_count += 1
        telemetry.error_count += 1
        telemetry.route_hits[request.url.path] += 1
        telemetry.method_hits[request.method] += 1
        LOGGER.exception("foundation.request_failed path=%s request_id=%s", request.url.path, request_id)
        raise
    telemetry.request_count += 1
    telemetry.route_hits[request.url.path] += 1
    telemetry.method_hits[request.method] += 1
    response.headers["x-request-id"] = request_id
    duration_ms = round((perf_counter() - started) * 1000, 2)
    LOGGER.info("foundation.request method=%s path=%s status=%s duration_ms=%s request_id=%s", request.method, request.url.path, response.status_code, duration_ms, request_id)
    return response
