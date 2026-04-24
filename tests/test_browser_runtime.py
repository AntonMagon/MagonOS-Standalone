from __future__ import annotations

import unittest
from unittest.mock import patch

from magon_standalone.supplier_intelligence.browser_runtime import PlaywrightBrowserRuntime
from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"

    def goto(self, _url: str, wait_until: str, timeout: int) -> None:
        raise RuntimeError("dns_failed")

    def new_page(self):  # pragma: no cover - compatibility guard
        return self

    def close(self) -> None:
        return None


class _FakeBrowser:
    def new_page(self) -> _FakePage:
        return _FakePage()

    def close(self) -> None:
        return None


class _FakePlaywright:
    chromium = object()


class _FakeSyncContext:
    def __enter__(self) -> _FakePlaywright:
        return _FakePlaywright()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class TestBrowserRuntime(unittest.TestCase):
    # RU: Browser runtime обязан переживать обычные navigation errors вроде DNS failure и отдавать пустой snapshot вместо аварийного падения всего live parsing.
    def test_fetch_many_captures_generic_navigation_errors(self) -> None:
        config = ScenarioConfig(
            defaults={"browser_timeout_ms": 1000},
            domain_overrides={},
        )
        runtime = PlaywrightBrowserRuntime(config)

        with patch(
            "magon_standalone.supplier_intelligence.browser_runtime.load_playwright_sync_api",
            return_value=(lambda: _FakeSyncContext(), TimeoutError),
        ), patch(
            "magon_standalone.supplier_intelligence.browser_runtime.launch_browser",
            return_value=(_FakeBrowser(), "chromium"),
        ):
            snapshots = runtime.fetch_many(["https://broken.example.com"], timeout_ms=1000)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].html, "")
        self.assertTrue(any(entry.startswith("error:RuntimeError:dns_failed") for entry in snapshots[0].event_log))


if __name__ == "__main__":
    unittest.main()
