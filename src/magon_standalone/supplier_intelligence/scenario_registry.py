"""Scenario registry and concrete executors for supplier discovery.

Runtime role: Maps scenario keys to executable runtime behaviors for
directory/company-site crawling and extraction.
Inputs: Page seeds, route decisions, fetched HTML/browser snapshots.
Outputs: Raw supplier rows plus optional follow-up seeds and metrics.
Does not: choose scenarios or persist entities.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import requests

from .browser_runtime import PlaywrightBrowserRuntime
from .contracts import PageSeed, RawCompanyRecord, ScenarioRouteDecision
from .extraction_engine import ScenarioExtractionEngine
from .pagination_controller import PaginationController
from .popup_controller import PopupOverlayController
from .scenario_config import ScenarioConfig


LOGGER = logging.getLogger(__name__)
USER_AGENT = "MagonOSBot/0.2 (+scenario-discovery)"


def _query_variants(query: str) -> list[str]:
    normalized = " ".join((query or "").split()).strip().lower()
    variants: list[str] = []
    for candidate in (
        normalized,
        "printing" if "printing" in normalized else "",
        "packaging" if "packaging" in normalized or "bao b" in normalized else "",
        "label printing" if "label" in normalized else "",
    ):
        if candidate and candidate not in variants:
            variants.append(candidate)
    compact = [token for token in normalized.split() if token not in {"vietnam", "viet", "nam"}]
    if compact:
        reduced = " ".join(compact[:2])
        if reduced and reduced not in variants:
            variants.append(reduced)
    return variants[:4]


@dataclass(frozen=True)
class ScenarioExecutionResult:
    records: list[RawCompanyRecord]
    follow_up_seeds: list[PageSeed]
    pages_visited: int
    escalation_count: int
    low_confidence_count: int
    block_detected: bool = False


class YellowPagesSeedProvider:
    """Generate bounded live search seeds for Vietnam supplier discovery."""

    base_url = "https://www.yellowpages.vn/search.asp"

    def __init__(self, locations: tuple[str, ...] | None = None):
        self._locations = locations or ("", "Ho Chi Minh", "Ha Noi")

    def discover_seeds(self, query: str, country_code: str) -> list[PageSeed]:
        if country_code.upper() != "VN":
            return []
        discovered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        seeds: list[PageSeed] = []
        for variant in _query_variants(query):
            for where in self._locations:
                params = urlencode({"keyword": variant, "where": where})
                seeds.append(
                    {
                        "url": f"{self.base_url}?{params}",
                        "query": query,
                        "country_code": country_code,
                        "source_type": "directory",
                        "source_domain": "yellowpages.vn",
                        "page_type_hint": "directory",
                        "discovered_at": discovered_at,
                        "metadata": {"seed_variant": variant, "where": where},
                    }
                )
        return seeds


class BaseScenarioExecutor:
    """Shared HTTP/browser helpers for concrete scenario executors."""

    def __init__(self, config: ScenarioConfig, extraction_engine: ScenarioExtractionEngine):
        self._config = config
        self._settings = config.settings()
        self._extract = extraction_engine
        self._pagination = PaginationController()
        self._popup_controller = PopupOverlayController()
        self._browser = PlaywrightBrowserRuntime(config)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    def _fetch_html(self, url: str) -> str:
        response = self._session.get(url, timeout=self._settings.request_timeout_seconds)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
        return response.text

    def _follow_up_company_seeds(self, records: list[RawCompanyRecord], *, query: str, country_code: str) -> list[PageSeed]:
        seeds: list[PageSeed] = []
        for row in records:
            website = row.get("website") or ""
            if not website:
                continue
            seeds.append(
                {
                    "url": website,
                    "query": query,
                    "country_code": country_code,
                    "source_type": "company_site",
                    "source_domain": urlparse(website).netloc.replace("www.", "").lower(),
                    "page_type_hint": "company_site",
                    "discovered_at": row.get("discovered_at"),
                    "metadata": {"origin_source_url": row.get("source_url")},
                }
            )
        return seeds[: self._settings.max_follow_up_company_pages]


class SimpleDirectoryExecutor(BaseScenarioExecutor):
    """Parse static listing pages without a browser and follow plain pagination."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str) -> ScenarioExecutionResult:
        override = self._config.domain_override(seed.get("source_domain", ""))
        pages = self._pagination.collect_static_pages(
            seed["url"],
            initial_html,
            self._fetch_html,
            max_pages=int(override.get("max_pages_per_seed", self._settings.max_pages_per_seed)),
            pagination_selector=route.get("execution_flags", {}).get("pagination_selector"),
        )
        records: list[RawCompanyRecord] = []
        low_confidence = 0
        escalation_count = 0
        for page in pages:
            extracted = self._extract.extract_directory_page(
                page.html,
                page_url=page.url,
                query=seed["query"],
                route=route,
            )
            if extracted and max(float(item.get("extraction_confidence") or 0.0) for item in extracted) < self._settings.low_confidence_threshold:
                low_confidence += len(extracted)
            if any(item.get("extraction_method") == "ai_assisted" for item in extracted):
                escalation_count += 1
            records.extend(extracted)
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=self._follow_up_company_seeds(records, query=seed["query"], country_code=seed["country_code"]),
            pages_visited=len(pages),
            escalation_count=escalation_count,
            low_confidence_count=low_confidence,
        )


class JsDirectoryExecutor(BaseScenarioExecutor):
    """Render listing pages with Playwright and handle JS pagination/load-more."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str | None = None) -> ScenarioExecutionResult:
        override = self._config.domain_override(seed.get("source_domain", ""))
        snapshot = self._browser.fetch(
            seed["url"],
            timeout_ms=self._settings.browser_timeout_ms,
            wait_for_selector=route.get("execution_flags", {}).get("wait_for_selector"),
            popup_controller=self._popup_controller,
            scroll_steps=self._settings.max_scroll_steps,
            screenshot_name=f"{seed.get('source_domain', 'page')}-directory.png",
        )
        with sync_page(snapshot) as payload:
            pages = self._pagination.collect_browser_pages(
                payload["page"],
                max_pages=int(override.get("max_pages_per_seed", self._settings.max_pages_per_seed)),
                max_scroll_steps=self._settings.max_scroll_steps,
                load_more_selector=route.get("execution_flags", {}).get("load_more_selector"),
                next_selector=route.get("execution_flags", {}).get("pagination_selector"),
            )
        records: list[RawCompanyRecord] = []
        low_confidence = 0
        escalation_count = 0
        for page in pages:
            extracted = self._extract.extract_directory_page(
                page["html"],
                page_url=page["url"],
                query=seed["query"],
                route=route,
            )
            if extracted and max(float(item.get("extraction_confidence") or 0.0) for item in extracted) < self._settings.low_confidence_threshold:
                low_confidence += len(extracted)
            if any(item.get("extraction_method") == "ai_assisted" for item in extracted):
                escalation_count += 1
            for item in extracted:
                if snapshot.screenshot_ref:
                    item.setdefault("raw_evidence_refs", []).append(snapshot.screenshot_ref)
                    item.setdefault("evidence_payloads", []).append(
                        {
                            "evidence_ref": snapshot.screenshot_ref,
                            "source_url": page["url"],
                            "scenario_key": route["scenario_key"],
                            "evidence_type": "screenshot",
                            "content": "",
                            "metadata": {"final_url": snapshot.final_url, "event_log": snapshot.event_log},
                        }
                    )
            records.extend(extracted)
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=self._follow_up_company_seeds(records, query=seed["query"], country_code=seed["country_code"]),
            pages_visited=len(pages),
            escalation_count=escalation_count,
            low_confidence_count=low_confidence,
            block_detected=snapshot.challenge_detected,
        )


class CompanySiteExecutor(BaseScenarioExecutor):
    """Crawl a limited set of internal company pages and build one supplier entity."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str) -> ScenarioExecutionResult:
        override = self._config.domain_override(seed.get("source_domain", ""))
        allow_paths = override.get("allow_paths", ["/", "/about", "/about-us", "/contact", "/contact-us", "/services", "/products"])
        deny_paths = set(override.get("deny_paths", []))
        pages: list[tuple[str, str]] = [(seed["url"], initial_html)]
        for path in allow_paths[: self._settings.max_follow_up_company_pages]:
            if path in deny_paths:
                continue
            target_url = urljoin(seed["url"], path)
            if target_url == seed["url"]:
                continue
            try:
                pages.append((target_url, self._fetch_html(target_url)))
            except Exception:
                continue
        records = self._extract.extract_company_site(pages, source_url=seed["url"], route=route)
        low_confidence = sum(
            1 for item in records if float(item.get("extraction_confidence") or 0.0) < self._settings.low_confidence_threshold
        )
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=[],
            pages_visited=len(pages),
            escalation_count=0,
            low_confidence_count=low_confidence,
        )


class JsCompanySiteExecutor(BaseScenarioExecutor):
    """Render supplier-owned sites in the browser before extracting company facts."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str | None = None) -> ScenarioExecutionResult:
        override = self._config.domain_override(seed.get("source_domain", ""))
        allow_paths = override.get("allow_paths", ["/", "/about", "/about-us", "/contact", "/contact-us", "/services", "/products"])
        deny_paths = set(override.get("deny_paths", []))
        # RU: Dynamic supplier sites должны обходиться тем же browser-session с внутренними страницами about/contact/services, иначе теряем реальные телефоны, адреса и capability blocks.
        target_urls: list[str] = [seed["url"]]
        for path in allow_paths[: self._settings.max_follow_up_company_pages]:
            if path in deny_paths:
                continue
            target_url = urljoin(seed["url"], path)
            if target_url not in target_urls:
                target_urls.append(target_url)
        screenshot_prefix = f"{seed.get('source_domain', 'company-site')}-company"
        snapshots = self._browser.fetch_many(
            target_urls,
            timeout_ms=self._settings.browser_timeout_ms,
            popup_controller=self._popup_controller,
            scroll_steps=min(self._settings.max_scroll_steps, 2),
            screenshot_prefix=screenshot_prefix,
        )
        pages = [(snapshot.final_url, snapshot.html) for snapshot in snapshots if snapshot.html]
        if not pages:
            return ScenarioExecutionResult(
                records=[],
                follow_up_seeds=[],
                pages_visited=len(snapshots),
                escalation_count=0,
                low_confidence_count=0,
                block_detected=any(snapshot.event_log and "timeout" not in snapshot.event_log and snapshot.challenge_detected for snapshot in snapshots),
            )
        records = self._extract.extract_company_site(pages, source_url=seed["url"], route=route)
        for item in records:
            for snapshot in snapshots:
                if snapshot.screenshot_ref:
                    item.setdefault("raw_evidence_refs", []).append(snapshot.screenshot_ref)
                    item.setdefault("evidence_payloads", []).append(
                        {
                            "evidence_ref": snapshot.screenshot_ref,
                            "source_url": snapshot.final_url,
                            "scenario_key": route["scenario_key"],
                            "evidence_type": "screenshot",
                            "content": "",
                            "metadata": {"title": snapshot.title, "event_log": snapshot.event_log},
                        }
                    )
        low_confidence = sum(
            1 for item in records if float(item.get("extraction_confidence") or 0.0) < self._settings.low_confidence_threshold
        )
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=[],
            pages_visited=len(pages),
            escalation_count=0,
            low_confidence_count=low_confidence,
            block_detected=any(snapshot.challenge_detected for snapshot in snapshots),
        )


class HardDynamicExecutor(BaseScenarioExecutor):
    """Use full browser execution for challenged or highly dynamic pages."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str | None = None) -> ScenarioExecutionResult:
        snapshot = self._browser.fetch(
            seed["url"],
            timeout_ms=self._settings.browser_timeout_ms,
            popup_controller=self._popup_controller,
            scroll_steps=self._settings.max_scroll_steps,
            screenshot_name=f"{seed.get('source_domain', 'page')}-blocked.png",
        )
        if seed.get("page_type_hint") == "company_site":
            records = self._extract.extract_company_site([(snapshot.final_url, snapshot.html)], source_url=seed["url"], route=route)
        else:
            records = self._extract.extract_directory_page(snapshot.html, page_url=snapshot.final_url, query=seed["query"], route=route)
        for item in records:
            if snapshot.screenshot_ref:
                item.setdefault("raw_evidence_refs", []).append(snapshot.screenshot_ref)
                item.setdefault("evidence_payloads", []).append(
                    {
                        "evidence_ref": snapshot.screenshot_ref,
                        "source_url": snapshot.final_url,
                        "scenario_key": route["scenario_key"],
                        "evidence_type": "screenshot",
                        "content": "",
                        "metadata": {"challenge_detected": snapshot.challenge_detected, "event_log": snapshot.event_log},
                    }
                )
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=self._follow_up_company_seeds(records, query=seed["query"], country_code=seed["country_code"]),
            pages_visited=1,
            escalation_count=sum(1 for item in records if item.get("extraction_method") == "ai_assisted"),
            low_confidence_count=sum(1 for item in records if float(item.get("extraction_confidence") or 0.0) < self._settings.low_confidence_threshold),
            block_detected=snapshot.challenge_detected,
        )


class AiAssistedExtractionExecutor(BaseScenarioExecutor):
    """Run Crawl4AI-assisted fallback when deterministic extraction is weak."""

    def execute(self, seed: PageSeed, route: ScenarioRouteDecision, initial_html: str) -> ScenarioExecutionResult:
        records = self._extract.extract_ai_assisted(
            page_url=seed["url"],
            html=initial_html,
            route=route,
            query=seed["query"],
        )
        return ScenarioExecutionResult(
            records=records,
            follow_up_seeds=[],
            pages_visited=1,
            escalation_count=1 if records else 0,
            low_confidence_count=len(records),
        )


class ScenarioRegistry:
    """Resolve and execute scenario keys through one shared executor map."""

    def __init__(self, config: ScenarioConfig):
        extraction = ScenarioExtractionEngine(config)
        self._executors = {
            "SIMPLE_DIRECTORY": SimpleDirectoryExecutor(config, extraction),
            "JS_DIRECTORY": JsDirectoryExecutor(config, extraction),
            "COMPANY_SITE": CompanySiteExecutor(config, extraction),
            "JS_COMPANY_SITE": JsCompanySiteExecutor(config, extraction),
            "HARD_DYNAMIC_OR_BLOCKED": HardDynamicExecutor(config, extraction),
            "AI_ASSISTED_EXTRACTION": AiAssistedExtractionExecutor(config, extraction),
        }

    def execute(self, route: ScenarioRouteDecision, seed: PageSeed, initial_html: str) -> ScenarioExecutionResult:
        executor = self._executors[route["scenario_key"]]
        return executor.execute(seed, route, initial_html)


class sync_page:
    """Open a second browser session only long enough to paginate rendered listings."""

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._page = self._browser.new_page()
        self._page.goto(self.snapshot.final_url, wait_until="domcontentloaded", timeout=30_000)
        return {"page": self._page}

    def __exit__(self, exc_type, exc, tb):
        self._page.close()
        self._browser.close()
        self._playwright.stop()
        return False
