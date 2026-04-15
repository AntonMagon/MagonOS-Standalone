"""Fixture-backed discovery helper for standalone verification.

Runtime role: Loads raw discovery rows from a local JSON fixture so the
portable pipeline can be exercised without network or Odoo.
"""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import RawCompanyRecord
from .interfaces import DiscoveryService


class FixtureDiscoveryService(DiscoveryService):
    """Replay raw discovery rows from one local JSON fixture file."""

    def __init__(self, fixture_path: str | Path):
        self._fixture_path = Path(fixture_path)

    def discover(self, query: str, country_code: str) -> list[RawCompanyRecord]:
        _ = (query, country_code)
        return json.loads(self._fixture_path.read_text(encoding="utf-8"))
