from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .celery_app import run_supplier_ingest
from .codes import reserve_code
from .models import SupplierRawIngest, SupplierSourceRegistry
from .settings import load_settings

DEFAULT_SCHEDULE_INTERVAL_MINUTES = 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _config_bool(config: dict | None, key: str, default: bool) -> bool:
    value = (config or {}).get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _config_int(config: dict | None, key: str, default: int) -> int:
    value = (config or {}).get(key)
    if value in {None, ""}:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


@dataclass(slots=True)
class SupplierSourceScheduleState:
    enabled: bool
    interval_minutes: int
    reason_code: str
    classification_mode: str
    llm_enabled: bool
    active: bool
    due_now: bool
    next_run_at: datetime | None
    last_event_at: datetime | None
    skip_reason: str | None


def build_supplier_source_schedule_state(
    registry: SupplierSourceRegistry,
    latest_ingest: SupplierRawIngest | None = None,
) -> SupplierSourceScheduleState:
    # RU: Состояние расписания считаем детерминированно из source config и последнего ingest без отдельного скрытого state-store.
    config = registry.config_json or {}
    llm_enabled = load_settings().llm_enabled
    enabled = _config_bool(config, "schedule_enabled", registry.adapter_key == "scenario_live")
    interval_minutes = _config_int(config, "schedule_interval_minutes", DEFAULT_SCHEDULE_INTERVAL_MINUTES)
    reason_code = str(config.get("schedule_reason_code") or "scheduled_supplier_ingest")
    classification_mode = str(
        config.get("classification_mode")
        or ("ai_assisted_fallback" if registry.adapter_key == "scenario_live" else "deterministic_only")
    )

    last_event_at = None
    if latest_ingest is not None:
        last_event_at = latest_ingest.finished_at or latest_ingest.started_at or latest_ingest.created_at

    active = bool(latest_ingest and latest_ingest.ingest_status in {"queued", "running"})
    next_run_at = None if last_event_at is None else last_event_at + timedelta(minutes=interval_minutes)
    due_now = enabled and not active and (next_run_at is None or next_run_at <= _utc_now())

    skip_reason = None
    if not enabled:
        skip_reason = "schedule_disabled"
    elif active:
        skip_reason = "ingest_already_active"
    elif not due_now:
        skip_reason = "interval_not_elapsed"

    return SupplierSourceScheduleState(
        enabled=enabled,
        interval_minutes=interval_minutes,
        reason_code=reason_code,
        classification_mode=classification_mode,
        llm_enabled=llm_enabled,
        active=active,
        due_now=due_now,
        next_run_at=next_run_at,
        last_event_at=last_event_at,
        skip_reason=skip_reason,
    )


def build_scheduled_idempotency_key(registry_code: str, interval_minutes: int, now: datetime | None = None) -> str:
    current = now or _utc_now()
    bucket = int(current.timestamp()) // (interval_minutes * 60)
    return f"scheduled:{registry_code}:{bucket}"


def enqueue_due_supplier_sources(session: Session) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    _ensure_default_supplier_sources(session)
    registries = session.scalars(
        select(SupplierSourceRegistry)
        .where(SupplierSourceRegistry.enabled.is_(True))
        .order_by(SupplierSourceRegistry.created_at.asc())
    ).all()

    for registry in registries:
        latest_ingest = session.scalar(
            select(SupplierRawIngest)
            .where(SupplierRawIngest.source_registry_id == registry.id)
            .order_by(SupplierRawIngest.created_at.desc())
        )
        schedule = build_supplier_source_schedule_state(registry, latest_ingest)
        if not schedule.due_now:
            results.append(
                {
                    "source_registry_code": registry.code,
                    "adapter_key": registry.adapter_key,
                    "scheduled": False,
                    "status": "skipped",
                    "skip_reason": schedule.skip_reason,
                    "classification_mode": schedule.classification_mode,
                    "llm_enabled": schedule.llm_enabled,
                    "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
                }
            )
            continue

        idempotency_key = build_scheduled_idempotency_key(registry.code, schedule.interval_minutes)
        ingest = session.scalar(select(SupplierRawIngest).where(SupplierRawIngest.idempotency_key == idempotency_key))
        if ingest is not None:
            results.append(
                {
                    "source_registry_code": registry.code,
                    "adapter_key": registry.adapter_key,
                    "scheduled": False,
                    "status": "duplicate_window",
                    "skip_reason": "window_already_enqueued",
                    "classification_mode": schedule.classification_mode,
                    "llm_enabled": schedule.llm_enabled,
                    "ingest_code": ingest.code,
                    "task_id": ingest.task_id,
                }
            )
            continue

        ingest = SupplierRawIngest(
            code=reserve_code(session, "supplier_raw_ingests", "ING"),
            source_registry_id=registry.id,
            idempotency_key=idempotency_key,
            ingest_status="queued",
            reason_code=schedule.reason_code,
            trigger_mode="scheduler_job",
            adapter_key=registry.adapter_key,
            requested_by_user_id=None,
        )
        session.add(ingest)
        session.flush()

        task = run_supplier_ingest.delay(
            registry.code,
            idempotency_key,
            schedule.reason_code,
            "scheduler_job",
        )
        ingest.task_id = task.id
        session.flush()

        results.append(
            {
                "source_registry_code": registry.code,
                "adapter_key": registry.adapter_key,
                "scheduled": True,
                "status": "queued",
                "classification_mode": schedule.classification_mode,
                "llm_enabled": schedule.llm_enabled,
                "ingest_code": ingest.code,
                "task_id": task.id,
                "idempotency_key": idempotency_key,
            }
        )

    return results


def _ensure_default_supplier_sources(session: Session) -> None:
    fixture = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "fixture_json"))
    if fixture is None:
        fixture = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Fixture VN suppliers",
            adapter_key="fixture_json",
            source_layer="raw",
            enabled=True,
            config_json={
                "source_label": "fixture_vn_suppliers",
                "schedule_enabled": False,
                "classification_mode": "deterministic_only",
            },
        )
        session.add(fixture)

    live = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "scenario_live"))
    if live is None:
        live = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Live parsing VN suppliers",
            adapter_key="scenario_live",
            source_layer="raw",
            enabled=True,
            config_json={
                "query": "printing packaging vietnam",
                "country": "VN",
                "source_label": "live_parsing_vn_suppliers",
                "schedule_enabled": True,
                "schedule_interval_minutes": 60,
                "schedule_reason_code": "scheduled_supplier_ingest",
                "classification_mode": "ai_assisted_fallback",
            },
        )
        session.add(live)

    session.flush()
