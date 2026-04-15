"""Scenario-driven discovery orchestration for live supplier ingestion.

Runtime role: Replaces the old universal live parser with routing-driven page
execution across directory and company-site scenarios.
Inputs: Discovery query/country plus repo config and runtime executors.
Outputs: RawCompanyRecord rows enriched with scenario/evidence metadata.
Does not: normalize, deduplicate, score, or persist records directly.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from urllib.parse import urlparse

import requests

from .contracts import PageSeed, RawCompanyRecord
from .fingerprints import candidate_fingerprint, source_fingerprint
from .interfaces import DiscoveryService
from .scenario_config import ScenarioConfig
from .scenario_profiler import HeuristicPageProfiler
from .scenario_registry import ScenarioRegistry, YellowPagesSeedProvider
from .scenario_router import ScenarioDecisionRouter


LOGGER = logging.getLogger(__name__)


class ScenarioDrivenDiscoveryService(DiscoveryService):
    """Run discovery through seed generation, profiling, routing, and scenario execution."""

    def __init__(self, config: ScenarioConfig | None = None):
        self._config = config or ScenarioConfig.load()
        self._seed_provider = YellowPagesSeedProvider()
        self._profiler = HeuristicPageProfiler()
        self._router = ScenarioDecisionRouter(self._config)
        self._registry = ScenarioRegistry(self._config)
        self._session = requests.Session()

    def discover(self, query: str, country_code: str) -> list[RawCompanyRecord]:
        queue = deque(self._seed_provider.discover_seeds(query, country_code))
        visited_urls: set[str] = set()
        records: list[RawCompanyRecord] = []
        settings = self._config.settings()
        company_followups_scheduled = 0

        while queue:
            seed = queue.popleft()
            if seed["url"] in visited_urls:
                continue
            visited_urls.add(seed["url"])
            override = self._config.domain_override(seed.get("source_domain", ""))
            try:
                html, status_code = self._fetch_seed_html(seed)
            except Exception as exc:
                LOGGER.warning("scenario.seed_fetch_failed url=%s error=%s", seed["url"], exc)
                continue
            profile = self._profiler.profile(seed, html, status_code=status_code)
            route = self._router.route(seed, profile)
            LOGGER.info(
                "scenario.route url=%s scenario=%s reasons=%s confidence=%s",
                seed["url"],
                route["scenario_key"],
                ",".join(route.get("reasons") or []),
                route.get("confidence"),
            )
            result = self._registry.execute(route, seed, html)
            for row in result.records:
                row["source_fingerprint"] = source_fingerprint(row)
                row["candidate_dedup_fingerprint"] = candidate_fingerprint(row)
                row.setdefault("raw_payload", {}).update(
                    {
                        "page_profile": profile,
                        "scenario_route": route,
                        "pages_visited": result.pages_visited,
                        "escalation_count": result.escalation_count,
                        "low_confidence_count": result.low_confidence_count,
                        "block_detected": result.block_detected,
                    }
                )
                records.append(row)
            for follow_up_seed in result.follow_up_seeds:
                if follow_up_seed.get("page_type_hint") == "company_site":
                    if company_followups_scheduled >= settings.max_follow_up_company_pages:
                        continue
                follow_up_domain_override = self._config.domain_override(follow_up_seed.get("source_domain", ""))
                allowed = follow_up_domain_override.get("allow_paths") or override.get("allow_paths") or ["/"]
                denied = set(follow_up_domain_override.get("deny_paths") or [])
                parsed_path = urlparse(follow_up_seed["url"]).path or "/"
                if denied and any(parsed_path.startswith(path) for path in denied):
                    continue
                if allowed and not any(parsed_path.startswith(path) or path == "/" for path in allowed):
                    continue
                if follow_up_seed["url"] not in visited_urls:
                    queue.append(follow_up_seed)
                    if follow_up_seed.get("page_type_hint") == "company_site":
                        company_followups_scheduled += 1
            throttle = float(route.get("execution_flags", {}).get("throttle_seconds") or settings.request_delay_seconds)
            if throttle:
                time.sleep(throttle)
        return records

    def _fetch_seed_html(self, seed: PageSeed) -> tuple[str, int]:
        response = self._session.get(
            seed["url"],
            timeout=self._config.settings().request_timeout_seconds,
            headers={"User-Agent": "MagonOSBot/0.2 (+scenario-discovery)"},
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
        return response.text, response.status_code
