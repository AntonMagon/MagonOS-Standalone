"""Live runtime readiness helpers for supplier parsing.

Runtime role: Proves that the live parsing stack can actually import and
launch its browser runtime instead of only loading config.
Inputs: Scenario config plus local env/browser/runtime state.
Outputs: Deterministic readiness payloads and a shared browser launch helper.
Does not: discover suppliers, parse fields, or persist ingest state.
"""
from __future__ import annotations

import importlib.util
import os
import time
from dataclasses import dataclass
from typing import Any

from .scenario_config import CONFIG_PATH, ScenarioConfig


@dataclass(frozen=True)
class LiveRuntimeProbe:
    ok: bool
    detail: str
    payload: dict[str, Any]


_PROBE_CACHE: tuple[float, LiveRuntimeProbe] | None = None
_PROBE_TTL_SECONDS = 30.0


def load_playwright_sync_api():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by runtime probe tests
        raise RuntimeError("playwright_not_installed") from exc
    return sync_playwright, PlaywrightTimeoutError


def launch_browser(playwright: Any) -> tuple[Any, str]:
    forced_channel = os.getenv("MAGON_SUPPLIER_BROWSER_CHANNEL", "").strip()
    attempts: list[dict[str, str]] = []
    candidates: list[tuple[str, dict[str, Any]]] = []
    if forced_channel:
        candidates.append((f"channel:{forced_channel}", {"channel": forced_channel, "headless": True}))
    else:
        # RU: Сначала пробуем встроенный Chromium, а потом локальный Chrome channel, чтобы live parsing не падал только из-за одного browser backend.
        candidates.extend(
            [
                ("chromium", {"headless": True}),
                ("channel:chrome", {"channel": "chrome", "headless": True}),
            ]
        )

    for label, kwargs in candidates:
        try:
            return playwright.chromium.launch(**kwargs), label
        except Exception as exc:  # pragma: no cover - depends on local browser runtime
            attempts.append({"mode": label, "error": str(exc)[:240]})
    joined = "; ".join(f"{item['mode']}={item['error']}" for item in attempts) or "no_browser_launch_attempts"
    raise RuntimeError(f"browser_launch_failed:{joined}")


def probe_live_runtime(config: ScenarioConfig | None = None, *, force_refresh: bool = False) -> LiveRuntimeProbe:
    global _PROBE_CACHE
    now = time.monotonic()
    if not force_refresh and _PROBE_CACHE and (now - _PROBE_CACHE[0]) < _PROBE_TTL_SECONDS:
        return _PROBE_CACHE[1]

    try:
        actual_config = config or ScenarioConfig.load()
    except Exception as exc:
        probe = LiveRuntimeProbe(
            ok=False,
            detail="live_config_unavailable",
            payload={"error": str(exc)[:300]},
        )
        _PROBE_CACHE = (now, probe)
        return probe

    payload: dict[str, Any] = {
        "config_path": str(CONFIG_PATH),
        "playwright_browsers_path": actual_config.playwright_browser_path(),
        "crawl4ai_base_directory": actual_config.crawl4ai_base_directory(),
        "forced_browser_channel": os.getenv("MAGON_SUPPLIER_BROWSER_CHANNEL", "").strip() or None,
        "playwright_module_available": bool(importlib.util.find_spec("playwright.sync_api")),
    }
    if not payload["playwright_module_available"]:
        probe = LiveRuntimeProbe(ok=False, detail="missing_playwright_package", payload=payload)
        _PROBE_CACHE = (now, probe)
        return probe

    try:
        sync_playwright, _playwright_timeout_error = load_playwright_sync_api()
    except Exception as exc:
        probe = LiveRuntimeProbe(
            ok=False,
            detail="playwright_import_failed",
            payload={**payload, "error": str(exc)[:300]},
        )
        _PROBE_CACHE = (now, probe)
        return probe

    try:
        with sync_playwright() as playwright:
            browser, launch_mode = launch_browser(playwright)
            browser.close()
    except Exception as exc:
        probe = LiveRuntimeProbe(
            ok=False,
            detail="browser_launch_failed",
            payload={**payload, "error": str(exc)[:400]},
        )
        _PROBE_CACHE = (now, probe)
        return probe

    probe = LiveRuntimeProbe(
        ok=True,
        detail="live_parsing_ready",
        payload={**payload, "browser_launch_mode": launch_mode},
    )
    _PROBE_CACHE = (now, probe)
    return probe
