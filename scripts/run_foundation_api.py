#!/usr/bin/env python3
from __future__ import annotations

import argparse

import uvicorn

from magon_standalone.foundation.app import create_app
from magon_standalone.foundation.settings import load_settings


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Run Magon Foundation FastAPI")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    args = parser.parse_args()

    # RU: Foundation server поднимаем отдельным entrypoint, чтобы новый FastAPI-контур не ломал старый scripts/run_api.py и legacy smoke-путь.
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level=settings.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
