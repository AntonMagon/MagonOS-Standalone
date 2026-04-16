from __future__ import annotations

import os
from typing import Any, Callable

_BACKEND_SENTRY_INITIALIZED = False
_BACKEND_SENTRY_ENABLED = False


def _float_env(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return float(raw)


def backend_sentry_options() -> dict[str, Any] | None:
    dsn = os.environ.get("MAGON_SENTRY_DSN") or os.environ.get("NEXT_PUBLIC_MAGON_SENTRY_DSN")
    if not dsn:
        return None

    options: dict[str, Any] = {
        "dsn": dsn,
        "environment": os.environ.get("MAGON_SENTRY_ENV") or "local",
        "release": os.environ.get("MAGON_SENTRY_RELEASE"),
        "send_default_pii": False,
    }

    traces_sample_rate = _float_env("MAGON_SENTRY_TRACES_SAMPLE_RATE")
    if traces_sample_rate is not None:
        options["traces_sample_rate"] = traces_sample_rate

    profiles_sample_rate = _float_env("MAGON_SENTRY_PROFILES_SAMPLE_RATE")
    if profiles_sample_rate is not None:
        options["profiles_sample_rate"] = profiles_sample_rate

    return options


def init_backend_observability() -> bool:
    global _BACKEND_SENTRY_INITIALIZED, _BACKEND_SENTRY_ENABLED
    if _BACKEND_SENTRY_INITIALIZED:
        return _BACKEND_SENTRY_ENABLED

    _BACKEND_SENTRY_INITIALIZED = True
    options = backend_sentry_options()
    if not options:
        return False

    try:
        import sentry_sdk
    except ImportError:
        return False

    # RU: Backend Sentry включаем только по env DSN, чтобы локальный standalone runtime не требовал внешнего сервиса по умолчанию.
    sentry_sdk.init(**options)
    _BACKEND_SENTRY_ENABLED = True
    return True


def wrap_wsgi_app(app: Callable) -> Callable:
    if not init_backend_observability():
        return app

    try:
        from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
    except ImportError:
        return app

    # RU: WSGI middleware вешаем только после успешного init, чтобы capture request errors/perf не ломал старый server path.
    return SentryWsgiMiddleware(app)
