from __future__ import annotations

from celery import Celery

from .db import create_session_factory, session_scope
from .security import AuthContext, ROLE_ADMIN
from .supplier_services import SupplierPipelineService
from .settings import load_settings


def create_celery() -> Celery:
    settings = load_settings()
    app = Celery("magon_foundation", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
    app.conf.task_default_queue = "magon.foundation"
    if settings.is_test or settings.celery_broker_url.startswith("memory://"):
        # RU: Для local/test memory-broker сценариев Celery выполняем eagerly, чтобы enqueue-path реально проверялся без внешнего worker.
        app.conf.task_always_eager = True
        app.conf.task_store_eager_result = True
    return app


celery_app = create_celery()


@celery_app.task(name="magon.foundation.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="magon.foundation.suppliers.run_ingest")
def run_supplier_ingest(
    source_registry_code: str,
    idempotency_key: str,
    reason_code: str = "scheduled_supplier_ingest",
    trigger_mode: str = "job",
) -> dict[str, object]:
    settings = load_settings()
    session_factory = create_session_factory(settings)
    with session_scope(session_factory) as session:
        service = SupplierPipelineService(session)
        summary = service.run_ingest(
            source_registry_code=source_registry_code,
            idempotency_key=idempotency_key,
            auth=AuthContext(user_id=None, role_code=ROLE_ADMIN, email="system@local", full_name="System Worker"),
            reason_code=reason_code,
            trigger_mode=trigger_mode,
        )
        return {
            "ingest_code": summary.ingest_code,
            "ingest_status": summary.ingest_status,
            "source_registry_code": summary.source_registry_code,
            "raw_count": summary.raw_count,
            "normalized_count": summary.normalized_count,
            "merged_count": summary.merged_count,
            "candidate_count": summary.candidate_count,
            "replayed": summary.replayed,
        }
