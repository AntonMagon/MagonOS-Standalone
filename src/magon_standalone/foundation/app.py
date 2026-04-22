from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from magon_standalone.observability import init_backend_observability

from .dependencies import FoundationContainer
from .db import create_session_factory
from .legacy_bridge import create_legacy_mount
from .logging_utils import configure_logging
from .modules import MODULE_ROUTERS
from .observability import TelemetryState, telemetry_middleware
from .settings import FoundationSettings, load_settings
from .workflow_support import RuleViolation


def _database_health(container: FoundationContainer) -> dict[str, object]:
    session = container.session_factory()
    try:
        session.execute(text("SELECT 1"))
        return {"ok": True, "url": container.settings.database_url}
    except Exception as exc:
        return {"ok": False, "url": container.settings.database_url, "detail": str(exc)}
    finally:
        session.close()


def _redis_health(container: FoundationContainer) -> dict[str, object]:
    url = container.settings.redis_url
    if not url:
        return {"ok": True, "mode": "disabled"}
    try:
        import redis

        client = redis.Redis.from_url(url)
        client.ping()
        return {"ok": True, "mode": "redis", "url": url}
    except Exception as exc:
        return {"ok": False, "mode": "redis", "url": url, "detail": str(exc)}


def _celery_health(container: FoundationContainer) -> dict[str, object]:
    broker = container.settings.celery_broker_url
    backend = container.settings.celery_result_backend
    if broker.startswith("memory://"):
        return {"ok": True, "broker": broker, "backend": backend, "mode": "in_memory"}
    return {"ok": True, "broker": broker, "backend": backend, "mode": "configured"}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield


def create_app(settings: FoundationSettings | None = None) -> FastAPI:
    # RU: App собираем явно, чтобы optional-контуры вроде legacy mount и новых модулей включались только по понятным правилам.
    actual_settings = settings or load_settings()
    if actual_settings.system_mode not in {"normal", "test", "maintenance", "emergency"}:
        raise RuntimeError(f"foundation_system_mode_invalid:{actual_settings.system_mode}")
    configure_logging(actual_settings.log_level)
    init_backend_observability()

    session_factory = create_session_factory(actual_settings)
    telemetry = TelemetryState()
    container = FoundationContainer(settings=actual_settings, session_factory=session_factory, telemetry=telemetry)

    app = FastAPI(
        title="Magon Foundation API",
        version="0.1.0",
        lifespan=_lifespan,
    )
    app.state.container = container

    @app.exception_handler(RuleViolation)
    async def _handle_rule_violation(_, exc: RuleViolation):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "explainability": exc.explainability})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _telemetry(request, call_next):
        return await telemetry_middleware(request, call_next, telemetry)

    @app.middleware("http")
    async def _system_mode_guard(request, call_next):
        # RU: System mode guard блокирует write-paths в maintenance/emergency до входа в доменные модули.
        path = request.url.path
        mode = actual_settings.system_mode
        health_or_meta = path.startswith("/health") or path.startswith("/observability") or path.startswith("/api/v1/meta")
        auth_safe = path in {"/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/me"}
        if mode == "maintenance" and request.method not in {"GET", "HEAD", "OPTIONS"} and not (health_or_meta or auth_safe):
            return JSONResponse(status_code=503, content={"detail": "system_in_maintenance_mode", "system_mode": mode})
        if mode == "emergency" and not (health_or_meta or path == "/health"):
            return JSONResponse(status_code=503, content={"detail": "system_in_emergency_mode", "system_mode": mode})
        return await call_next(request)

    for router in MODULE_ROUTERS:
        app.include_router(router)

    @app.get("/health/live", tags=["Health"])
    def health_live() -> dict[str, object]:
        return {"status": "ok", "service": actual_settings.app_name, "env": actual_settings.env_name, "system_mode": actual_settings.system_mode}

    @app.get("/health/ready", tags=["Health"])
    def health_ready() -> dict[str, object]:
        db_health = _database_health(container)
        redis_health = _redis_health(container)
        celery_health = _celery_health(container)
        overall_ok = bool(db_health["ok"]) and bool(redis_health["ok"]) and bool(celery_health["ok"])
        return {
            "status": "ok" if overall_ok else "degraded",
            "checks": {
                "database": db_health,
                "redis": redis_health,
                "celery": celery_health,
                "legacy_mount_enabled": actual_settings.legacy_enabled,
                "system_mode": actual_settings.system_mode,
            },
        }

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, object]:
        ready = health_ready()
        return {
            "status": ready["status"],
            "service": actual_settings.app_name,
            "env": actual_settings.env_name,
            "system_mode": actual_settings.system_mode,
            "database_url": actual_settings.database_url,
            "legacy_enabled": actual_settings.legacy_enabled,
        }

    @app.get("/observability/summary", tags=["Observability"])
    def observability_summary() -> dict[str, object]:
        return {
            "service": actual_settings.app_name,
            "env": actual_settings.env_name,
            "system_mode": actual_settings.system_mode,
            "telemetry": telemetry.snapshot(),
            "logging": {"level": actual_settings.log_level},
            "error_reporting": {"sentry_enabled": bool(actual_settings.sentry_dsn)},
        }

    @app.get("/api/v1/meta/modules", tags=["Meta"])
    def module_registry() -> dict[str, object]:
        return {
            "architecture": "modular_monolith",
            "modules": [
                "UsersAccess",
                "Companies",
                "Suppliers",
                "Catalog",
                "DraftsRequests",
                "Offers",
                "Orders",
                "FilesMedia",
                "Documents",
                "LLM",
                "Comms",
                "RulesEngine",
                "AuditDashboards",
            ],
            "legacy_mount_enabled": actual_settings.legacy_enabled,
            "system_mode": actual_settings.system_mode,
        }

    @app.get("/api/v1/meta/system-mode", tags=["Meta"])
    def system_mode() -> dict[str, object]:
        return {
            "system_mode": actual_settings.system_mode,
            "write_blocked": actual_settings.system_mode in {"maintenance", "emergency"},
            "read_blocked": actual_settings.system_mode == "emergency",
        }

    if actual_settings.legacy_enabled:
        # RU: Legacy WSGI монтируем последним, чтобы новые FastAPI health/auth/module routes выигрывали матчинг, а старый `/ui/*` контур оставался совместимым.
        app.mount("/", create_legacy_mount(actual_settings))

    return app
