#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _alive(url: str, timeout: float = 10.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def _wait_for(url: str, attempts: int = 60, sleep_seconds: float = 1.0) -> bool:
    for _ in range(attempts):
        if _alive(url):
            return True
        time.sleep(sleep_seconds)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe launcher watchdog for the standalone platform.")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8091", help="Foundation backend base URL.")
    parser.add_argument("--web-url", default="http://127.0.0.1:3000", help="Foundation web base URL.")
    parser.add_argument("--force-restart", action="store_true", help="Restart even if the runtime already looks healthy.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    launcher = repo_root / "Start_Platform.command"
    backend_ready_url = f"{args.backend_url}/health/ready"
    web_login_url = f"{args.web_url}/login"

    backend_alive = _alive(backend_ready_url)
    web_alive = _alive(web_login_url)
    payload = {
        "backend_alive": backend_alive,
        "web_alive": web_alive,
        "force_restart": args.force_restart,
        "action": "noop",
    }

    if backend_alive and web_alive and not args.force_restart:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    command = [str(launcher), "--detach", "--no-open", "--keep-db", "--no-seed"]
    # RU: Авто-watchdog не должен стирать локальную БД или снова насаживать demo seed;
    # его задача — мягко вернуть живой runtime, если launcher или web/backend умерли.
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    payload["action"] = "restart"
    payload["command"] = " ".join(command)
    payload["returncode"] = completed.returncode
    payload["stdout"] = completed.stdout[-2000:]
    payload["stderr"] = completed.stderr[-2000:]

    if completed.returncode != 0:
        print(json.dumps(payload, ensure_ascii=False))
        return completed.returncode

    backend_ready = _wait_for(backend_ready_url)
    web_ready = _wait_for(web_login_url)
    payload["backend_ready"] = backend_ready
    payload["web_ready"] = web_ready
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if backend_ready and web_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
