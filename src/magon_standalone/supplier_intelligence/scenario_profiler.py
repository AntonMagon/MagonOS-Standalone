"""Page/domain profiling for scenario-driven supplier discovery.

Runtime role: Turns raw page snapshots into routing signals for scenario
selection and escalation.
Inputs: Page seed plus fetched HTML.
Outputs: PageProfile payloads consumed by the scenario router.
Does not: execute scenarios or normalize extracted suppliers.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .contracts import PageProfile, PageSeed


class HeuristicPageProfiler:
    """Profile page type, rendering needs, and anti-bot risk from live HTML."""

    def profile(self, seed: PageSeed, html: str, status_code: int = 200) -> PageProfile:
        soup = BeautifulSoup(html, "html.parser")
        url = seed["url"]
        domain = self._domain(url)
        lowered = html.lower()
        page_type = self._page_type(seed, soup, lowered)
        pagination_mode = self._pagination_mode(soup, lowered)
        js_dependency = self._js_dependency(lowered, soup)
        repeated_blocks = self._repeated_card_blocks(soup)
        structured_data = bool(soup.select_one("script[type='application/ld+json']"))
        contact_density = self._contact_density(lowered)
        anti_bot = self._anti_bot_likelihood(lowered, status_code)
        browser_required = js_dependency or pagination_mode in {"load_more", "infinite_scroll"}
        xhr_candidate = any(marker in lowered for marker in ("graphql", "__next_data__", "api/", "fetch("))

        confidence = 0.35
        if page_type != "unknown":
            confidence += 0.2
        if repeated_blocks:
            confidence += 0.1
        if structured_data:
            confidence += 0.1
        if anti_bot < 0.25:
            confidence += 0.1
        confidence = min(confidence, 0.95)

        return {
            "url": url,
            "source_domain": domain,
            "page_type": page_type,
            "js_dependency": js_dependency,
            "repeated_card_blocks": repeated_blocks,
            "pagination_mode": pagination_mode,
            "structured_data_available": structured_data,
            "contact_density": round(contact_density, 4),
            "anti_bot_likelihood": round(anti_bot, 4),
            "browser_required": browser_required,
            "xhr_candidate": xhr_candidate,
            "profile_confidence": round(confidence, 4),
            "signals": {
                "status_code": status_code,
                "script_count": len(soup.select("script")),
                "mailtos": lowered.count("mailto:"),
                "tels": lowered.count("tel:"),
            },
        }

    @staticmethod
    def _page_type(seed: PageSeed, soup: BeautifulSoup, lowered: str):
        url = seed["url"].lower()
        if url.endswith(".pdf"):
            return "pdf"
        if "yellowpages.vn/search.asp" in url or soup.select("div.yp_noidunglistings"):
            return "directory"
        if any(token in url for token in ("/contact", "/about", "/services", "/products")):
            return "company_site"
        if soup.select_one("script[type='application/ld+json']"):
            for node in soup.select("script[type='application/ld+json']"):
                text = node.get_text(strip=True)
                try:
                    payload = json.loads(text)
                except Exception:
                    continue
                payloads = payload if isinstance(payload, list) else [payload]
                for item in payloads:
                    type_name = str(item.get("@type", "")).lower()
                    if any(tag in type_name for tag in ("organization", "localbusiness", "corporation")):
                        return "company_site"
        if soup.select("a[href^='mailto:'], a[href^='tel:']"):
            return "company_site"
        if "directory" in lowered or "listing" in lowered or "suppliers" in lowered:
            return "directory"
        return seed.get("page_type_hint") or "unknown"

    @staticmethod
    def _pagination_mode(soup: BeautifulSoup, lowered: str):
        if "load more" in lowered or soup.select_one("[data-load-more], button.load-more, .load-more"):
            return "load_more"
        if "infinite-scroll" in lowered or "intersectionobserver" in lowered:
            return "infinite_scroll"
        if soup.select_one("a[rel='next'], a.next, .pagination a.next"):
            return "next_link"
        if len(soup.select(".pagination a[href]")) >= 2:
            return "numbered"
        return "none"

    @staticmethod
    def _js_dependency(lowered: str, soup: BeautifulSoup) -> bool:
        script_count = len(soup.select("script"))
        visible_text = len(re.sub(r"\s+", " ", soup.get_text(" ", strip=True)))
        return any(
            marker in lowered
            for marker in ("__next_data__", "data-reactroot", "window.__nuxt__", "id=\"app\"", "hydration")
        ) or (script_count >= 8 and visible_text < 800)

    @staticmethod
    def _repeated_card_blocks(soup: BeautifulSoup) -> bool:
        selectors = (
            "div.yp_noidunglistings",
            ".listing-card",
            ".supplier-card",
            "article",
        )
        return any(len(soup.select(selector)) >= 2 for selector in selectors)

    @staticmethod
    def _contact_density(lowered: str) -> float:
        score = 0.0
        score += min(lowered.count("mailto:"), 3) * 0.18
        score += min(lowered.count("tel:"), 3) * 0.18
        if re.search(r"\b(?:zalo|whatsapp|wechat|telegram)\b", lowered):
            score += 0.2
        return min(score, 1.0)

    @staticmethod
    def _anti_bot_likelihood(lowered: str, status_code: int) -> float:
        score = 0.0
        if status_code in {403, 429, 503}:
            score += 0.5
        for token in ("cf-challenge", "verify you are human", "captcha", "access denied", "blocked"):
            if token in lowered:
                score += 0.2
        return min(score, 1.0)

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.replace("www.", "").lower()
