"""Scenario runtime configuration for live supplier discovery."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "scraping_scenarios.json"


@dataclass(frozen=True)
class ScenarioSettings:
    max_pages_per_seed: int
    max_follow_up_company_pages: int
    request_timeout_seconds: int
    browser_timeout_ms: int
    max_scroll_steps: int
    low_confidence_threshold: float
    anti_bot_threshold: float
    request_delay_seconds: float
    evidence_char_limit: int


class ScenarioConfig:
    def __init__(self, defaults: dict[str, Any], domain_overrides: dict[str, dict[str, Any]]):
        self._defaults = defaults
        self._domain_overrides = domain_overrides

    @classmethod
    def load(cls, config_path: Path | None = None) -> "ScenarioConfig":
        path = config_path or CONFIG_PATH
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(defaults=payload.get("defaults", {}), domain_overrides=payload.get("domain_overrides", {}))

    def settings(self) -> ScenarioSettings:
        return ScenarioSettings(
            max_pages_per_seed=int(self._defaults.get("max_pages_per_seed", 3)),
            max_follow_up_company_pages=int(self._defaults.get("max_follow_up_company_pages", 3)),
            request_timeout_seconds=int(self._defaults.get("request_timeout_seconds", 20)),
            browser_timeout_ms=int(self._defaults.get("browser_timeout_ms", 30000)),
            max_scroll_steps=int(self._defaults.get("max_scroll_steps", 6)),
            low_confidence_threshold=float(self._defaults.get("low_confidence_threshold", 0.6)),
            anti_bot_threshold=float(self._defaults.get("anti_bot_threshold", 0.7)),
            request_delay_seconds=float(self._defaults.get("request_delay_seconds", 1.0)),
            evidence_char_limit=int(self._defaults.get("evidence_char_limit", 8000)),
        )

    def domain_override(self, domain: str) -> dict[str, Any]:
        normalized = (domain or "").replace("www.", "").lower().strip()
        merged = dict(self._defaults)
        override = self._domain_overrides.get(normalized) or {}
        merged.update(override)
        return merged

    def playwright_browser_path(self) -> str | None:
        return os.getenv("PLAYWRIGHT_BROWSERS_PATH")

    def crawl4ai_base_directory(self) -> str:
        return os.getenv("CRAWL4_AI_BASE_DIRECTORY", str(REPO_ROOT / ".crawl4ai_runtime"))
