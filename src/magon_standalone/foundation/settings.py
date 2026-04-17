from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class FoundationSettings:
    app_name: str
    env_name: str
    system_mode: str
    host: str
    port: int
    database_url: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    storage_backend: str
    storage_local_root: str
    storage_public_base_url: str
    max_upload_bytes: int
    sentry_dsn: str
    legacy_enabled: bool
    legacy_db_path: str
    legacy_default_query: str
    legacy_default_country: str
    legacy_integration_token: str
    default_admin_email: str
    default_admin_password: str
    default_operator_email: str
    default_operator_password: str
    default_customer_email: str
    default_customer_password: str
    request_timeout_seconds: float
    log_level: str

    @property
    def repo_root(self) -> Path:
        return _repo_root()

    @property
    def is_local(self) -> bool:
        return self.env_name == "local"

    @property
    def is_test(self) -> bool:
        return self.env_name == "test"


def load_settings() -> FoundationSettings:
    repo_root = _repo_root()
    local_sqlite = f"sqlite+pysqlite:///{repo_root / 'data' / 'foundation.sqlite3'}"
    env_name = _env("MAGON_ENV", "local")
    redis_url = _env("MAGON_FOUNDATION_REDIS_URL", "")
    broker_url = _env("MAGON_FOUNDATION_CELERY_BROKER_URL", redis_url or "memory://")
    result_backend = _env("MAGON_FOUNDATION_CELERY_RESULT_BACKEND", redis_url or "cache+memory://")

    return FoundationSettings(
        app_name=_env("MAGON_FOUNDATION_APP_NAME", "magon-foundation"),
        env_name=env_name,
        # RU: System mode фиксируем как явный operational switch первой волны, чтобы maintenance/emergency не оставались только в документации.
        system_mode=_env("MAGON_FOUNDATION_SYSTEM_MODE", "test" if env_name == "test" else "normal").strip().lower(),
        host=_env("MAGON_FOUNDATION_HOST", "0.0.0.0"),
        port=int(_env("MAGON_FOUNDATION_PORT", "8091")),
        database_url=_env("MAGON_FOUNDATION_DATABASE_URL", local_sqlite),
        redis_url=redis_url,
        celery_broker_url=broker_url,
        celery_result_backend=result_backend,
        storage_backend=_env("MAGON_FOUNDATION_STORAGE_BACKEND", "local"),
        storage_local_root=_env("MAGON_FOUNDATION_STORAGE_LOCAL_ROOT", str(repo_root / "data" / "file-assets")),
        storage_public_base_url=_env("MAGON_FOUNDATION_STORAGE_PUBLIC_BASE_URL", ""),
        max_upload_bytes=int(_env("MAGON_FOUNDATION_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))),
        sentry_dsn=_env("MAGON_SENTRY_DSN", ""),
        # RU: Wave1 foundation по умолчанию стартует без legacy WSGI-моста; старый контур включается только явным opt-in через env.
        legacy_enabled=_env_bool("MAGON_FOUNDATION_LEGACY_ENABLED", False),
        legacy_db_path=_env("MAGON_STANDALONE_DB_PATH", str(repo_root / "data" / "platform.sqlite3")),
        legacy_default_query=_env("MAGON_STANDALONE_DEFAULT_QUERY", "printing packaging vietnam"),
        legacy_default_country=_env("MAGON_STANDALONE_DEFAULT_COUNTRY", "VN"),
        legacy_integration_token=_env("MAGON_STANDALONE_INTEGRATION_TOKEN", ""),
        default_admin_email=_env("MAGON_FOUNDATION_DEFAULT_ADMIN_EMAIL", "admin@example.com"),
        default_admin_password=_env("MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD", "admin123"),
        default_operator_email=_env("MAGON_FOUNDATION_DEFAULT_OPERATOR_EMAIL", "operator@example.com"),
        default_operator_password=_env("MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD", "operator123"),
        default_customer_email=_env("MAGON_FOUNDATION_DEFAULT_CUSTOMER_EMAIL", "customer@example.com"),
        default_customer_password=_env("MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD", "customer123"),
        request_timeout_seconds=float(_env("MAGON_FOUNDATION_REQUEST_TIMEOUT_SECONDS", "5")),
        log_level=_env("MAGON_FOUNDATION_LOG_LEVEL", "INFO").upper(),
    )
