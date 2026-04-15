"""Playwright execution wrapper for JS-heavy and blocked supplier pages.

Runtime role: Provides bounded browser fetches for scenario executors that
cannot rely on plain HTTP.
Inputs: URL, timeout and scroll options, popup controller.
Outputs: Rendered HTML snapshots plus optional screenshot references.
Does not: decide scenarios, parse suppliers, or persist evidence by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .scenario_config import ScenarioConfig


@dataclass(frozen=True)
class BrowserPageSnapshot:
    url: str
    final_url: str
    html: str
    title: str
    screenshot_ref: str | None
    challenge_detected: bool
    event_log: list[str]


class PlaywrightBrowserRuntime:
    """Execute one bounded browser session and return a rendered page snapshot."""

    def __init__(self, config: ScenarioConfig):
        self._config = config

    def fetch(
        self,
        url: str,
        *,
        timeout_ms: int,
        wait_for_selector: str | None = None,
        popup_controller=None,
        scroll_steps: int = 0,
        screenshot_name: str | None = None,
    ) -> BrowserPageSnapshot:
        event_log: list[str] = []
        screenshot_ref = None
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                event_log.append(f"goto:{page.url}")
                if popup_controller:
                    event_log.extend(popup_controller.handle(page))
                if wait_for_selector:
                    try:
                        page.wait_for_selector(wait_for_selector, timeout=min(timeout_ms, 10_000))
                        event_log.append(f"wait_for_selector:{wait_for_selector}")
                    except PlaywrightTimeoutError:
                        event_log.append(f"wait_for_selector_timeout:{wait_for_selector}")
                for _step in range(max(scroll_steps, 0)):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(350)
                html = page.content()
                if screenshot_name:
                    target_dir = Path(self._config.crawl4ai_base_directory()) / "screenshots"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    screenshot_path = target_dir / screenshot_name
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    screenshot_ref = str(screenshot_path)
                challenge_detected = any(
                    marker in html.lower()
                    for marker in (
                        "verify you are human",
                        "cf-challenge",
                        "captcha",
                        "access denied",
                        "attention required",
                    )
                )
                return BrowserPageSnapshot(
                    url=url,
                    final_url=page.url,
                    html=html,
                    title=page.title(),
                    screenshot_ref=screenshot_ref,
                    challenge_detected=challenge_detected,
                    event_log=event_log,
                )
            finally:
                page.close()
                browser.close()
