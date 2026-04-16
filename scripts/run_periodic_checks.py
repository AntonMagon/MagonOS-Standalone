#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
from pathlib import Path

from magon_standalone.periodic_checks import build_lock_skip_payload, build_payload, build_result


def _run(command: list[str], repo_root: Path) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _alive(url: str) -> bool:
    completed = subprocess.run(
        ["curl", "-fsS", "--max-time", "5", url],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run periodic MagonOS repo checks and persist their status.")
    parser.add_argument("--mode", default="manual", choices=["manual", "launchd"], help="Execution mode label.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    cache_dir = repo_root / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    status_path = cache_dir / "periodic-checks-status.json"
    log_path = cache_dir / "periodic-checks.log"
    lock_path = cache_dir / "periodic-checks.lock"
    backend_url = os.environ.get("MAGON_PLATFORM_BACKEND_URL", "http://127.0.0.1:8091")
    web_url = os.environ.get("MAGON_PLATFORM_WEB_URL", "http://127.0.0.1:3000")

    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            payload = build_lock_skip_payload(args.mode, lock_path)
            status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"\n== periodic-checks {payload['generated_at']} ({args.mode}) ==\n")
                log_file.write("$ periodic-lock-skip\n")
                log_file.write(str(payload["results"][0]["stdout"]))
                log_file.write("returncode=0\n")
            print(f"Updated {status_path}")
            return 0

        results: list[dict[str, object]] = []

        # RU: Периодический контур intentionally легче полного verify: он держит sync/smoke/perf под контролем без тяжёлого тестового прогона каждые 30 минут.
        results.append(_run(["./.venv/bin/python", "scripts/sync_operating_docs.py"], repo_root))
        results.append(_run(["./.venv/bin/python", "scripts/update_project_visual_map.py"], repo_root))

        backend_alive = _alive(f"{backend_url}/health")
        web_alive = _alive(f"{web_url}/")
        if backend_alive and web_alive:
            results.append(_run(["./scripts/platform_smoke_check.sh", backend_url, web_url], repo_root))
            results.append(_run(["./scripts/run_perf_suite.sh", "smoke"], repo_root))
        else:
            # RU: Периодический runner не должен падать только потому, что локальная платформа сейчас не поднята; это нормальный idle-state машины.
            results.append(
                build_result(
                    "platform-runtime-skip",
                    0,
                    stdout=f"Skipped platform smoke/perf because runtime is not live on {backend_url} and {web_url}\n",
                )
            )

        payload = build_payload(args.mode, results)
        status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n== periodic-checks {payload['generated_at']} ({args.mode}) ==\n")
            for item in results:
                log_file.write(f"$ {item['command']}\n")
                if item["stdout"]:
                    log_file.write(str(item["stdout"]))
                    if not str(item["stdout"]).endswith("\n"):
                        log_file.write("\n")
                if item["stderr"]:
                    log_file.write(str(item["stderr"]))
                    if not str(item["stderr"]).endswith("\n"):
                        log_file.write("\n")
                log_file.write(f"returncode={item['returncode']}\n")

        print(f"Updated {status_path}")
        return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
