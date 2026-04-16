from __future__ import annotations

from datetime import datetime
from pathlib import Path


def now_timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def build_result(command: str, returncode: int, stdout: str = "", stderr: str = "") -> dict[str, object]:
    return {
        "command": command,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def build_payload(mode: str, results: list[dict[str, object]], generated_at: str | None = None) -> dict[str, object]:
    return {
        "generated_at": generated_at or now_timestamp(),
        "mode": mode,
        "ok": all(int(item["returncode"]) == 0 for item in results),
        "results": results,
    }


def build_lock_skip_payload(mode: str, lock_path: Path, generated_at: str | None = None) -> dict[str, object]:
    # RU: Skip по lock — это не failure; он фиксирует, что предыдущий periodic-run ещё жив и новый запуск не должен наслаиваться поверх него.
    return {
        "generated_at": generated_at or now_timestamp(),
        "mode": mode,
        "ok": True,
        "skipped": True,
        "results": [
            build_result(
                "periodic-lock-skip",
                0,
                stdout=f"Skipped periodic run because another run still holds {lock_path}\n",
            )
        ],
    }
