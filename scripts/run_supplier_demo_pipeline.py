# RU: Файл входит в проверенный контур первой волны.
#!/usr/bin/env python3
from __future__ import annotations

import argparse

from magon_standalone.foundation.db import create_session_factory, session_scope
from magon_standalone.foundation.security import AuthContext, ROLE_ADMIN
from magon_standalone.foundation.settings import load_settings
from magon_standalone.foundation.supplier_services import SupplierPipelineService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the wave1 supplier demo pipeline against the configured foundation database.")
    parser.add_argument("--source-code", default="SRC-00001")
    parser.add_argument("--idempotency-key", default="demo-pipeline-manual")
    parser.add_argument("--reason-code", default="demo_supplier_pipeline")
    args = parser.parse_args()

    settings = load_settings()
    session_factory = create_session_factory(settings)
    with session_scope(session_factory) as session:
        service = SupplierPipelineService(session)
        summary = service.run_ingest(
            source_registry_code=args.source_code,
            idempotency_key=args.idempotency_key,
            auth=AuthContext(user_id=None, role_code=ROLE_ADMIN, email="system@local", full_name="Demo Pipeline"),
            reason_code=args.reason_code,
            trigger_mode="script",
        )
        print(
            {
                "ingest_code": summary.ingest_code,
                "status": summary.ingest_status,
                "source_registry_code": summary.source_registry_code,
                "raw_count": summary.raw_count,
                "normalized_count": summary.normalized_count,
                "merged_count": summary.merged_count,
                "candidate_count": summary.candidate_count,
                "replayed": summary.replayed,
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
