"""Scenario-aware extraction and strict supplier schema enforcement.

Runtime role: Converts raw page snapshots into schema-valid supplier payloads
using deterministic, heuristic, and Crawl4AI-assisted fallback extraction.
Inputs: HTML snapshots, page URLs, route decisions, and per-domain hints.
Outputs: RawCompanyRecord rows ready for normalization and raw evidence storage.
Does not: select scenarios, manage pagination, or persist extracted suppliers.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import unicodedata
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..integrations.foundation.llm import get_llm_adapter
from .contracts import RawCompanyRecord, RawEvidencePayload, ScenarioRouteDecision
from .scenario_config import ScenarioConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "").lower()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _ascii_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_lookup(value: str | None) -> str:
    lowered = _ascii_text(_text(value)).lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _dedupe_texts(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in values:
        cleaned = _text(item)
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _capability_labels(blob: str) -> list[str]:
    lowered = blob.lower()
    labels: list[str] = []
    for token in (
        "packaging",
        "bao bì",
        "box",
        "carton",
        "corrugated",
        "label",
        "offset",
        "flexo",
        "promotional",
        "souvenir",
        "wide format",
    ):
        if token in lowered and token not in labels:
            labels.append(token)
    return labels


def _emails_from_text(blob: str) -> list[str]:
    return sorted(set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", blob, re.I)))


def _phones_from_text(blob: str) -> list[str]:
    found = []
    for match in re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", blob):
        digits = "".join(ch for ch in match if ch.isdigit())
        if len(digits) < 8:
            continue
        if digits.startswith("84"):
            found.append(f"+{digits}")
        elif digits.startswith("0"):
            found.append(f"+84{digits[1:]}")
        else:
            found.append(f"+{digits}")
    return sorted(set(found))


def _social_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    found = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        lowered = href.lower()
        if any(token in lowered for token in ("facebook.com", "linkedin.com", "zalo.me", "instagram.com", "youtube.com")):
            found.append(urljoin(base_url, href))
    return list(dict.fromkeys(found))


def _messengers_from_links(links: list[str], blob: str) -> list[str]:
    values = []
    lowered = blob.lower()
    for token in ("zalo", "whatsapp", "wechat", "telegram", "messenger"):
        if token in lowered or any(token in link.lower() for link in links):
            values.append(token)
    return list(dict.fromkeys(values))


_LOCATION_REPLACEMENTS = (
    (r"\btp\.?\s*hcm\b", "ho chi minh city"),
    (r"\btp\.?\s*ho\s*chi\s*minh\b", "ho chi minh city"),
    (r"\btphcm\b", "ho chi minh city"),
    (r"\bho\s*chi\s*minh\b", "ho chi minh city"),
    (r"\btp\.?\s*ha\s*noi\b", "ha noi"),
    (r"\bha\s*noi\b", "ha noi"),
    (r"\btp\.?\s*da\s*nang\b", "da nang"),
    (r"\bda\s*nang\b", "da nang"),
    (r"\bbien\s*hoa\b", "bien hoa"),
    (r"\bbinh\s*duong\b", "binh duong"),
    (r"\bdong\s*nai\b", "dong nai"),
    (r"\bthu\s*dau\s*mot\b", "thu dau mot"),
)


class SupplierSchemaValidator:
    """Enforce the repo's supplier extraction contract before persistence."""

    @staticmethod
    def ensure(record: RawCompanyRecord) -> RawCompanyRecord:
        if not record.get("company_name"):
            raise ValueError("company_name is required for extracted supplier rows")
        if not record.get("source_url"):
            raise ValueError("source_url is required for extracted supplier rows")

        timestamp = _now_iso()
        record["source_domain"] = record.get("source_domain") or _domain(record["source_url"])
        record["domain"] = record.get("domain") or _domain(record.get("website") or record["source_url"])
        record["supplier_id"] = record.get("supplier_id") or hashlib.sha1(
            f"{record['source_url']}|{record['company_name']}|{record.get('domain', '')}".encode("utf-8")
        ).hexdigest()
        record["website"] = (record.get("website") or "").strip()
        record["supplier_type"] = record.get("supplier_type") or "supplier"
        record["country"] = record.get("country") or "Vietnam"
        record["country_code"] = record.get("country_code") or "VN"
        record["region"] = record.get("region") or ""
        record["city"] = record.get("city") or ""
        record["address_text"] = record.get("address_text") or ""
        record["phones"] = list(dict.fromkeys(record.get("phones") or ([] if not record.get("phone") else [record["phone"]])))
        record["emails"] = list(dict.fromkeys(record.get("emails") or ([] if not record.get("email") else [record["email"]])))
        record["phone"] = record.get("phone") or (record["phones"][0] if record["phones"] else "")
        record["email"] = record.get("email") or (record["emails"][0] if record["emails"] else "")
        record["categories"] = list(dict.fromkeys(record.get("categories") or record.get("labels") or []))
        record["labels"] = list(dict.fromkeys(record.get("labels") or record["categories"]))
        record["services"] = list(dict.fromkeys(record.get("services") or []))
        record["products"] = list(dict.fromkeys(record.get("products") or []))
        record["contact_persons"] = list(dict.fromkeys(record.get("contact_persons") or []))
        record["messengers"] = list(dict.fromkeys(record.get("messengers") or []))
        record["social_links"] = list(dict.fromkeys(record.get("social_links") or []))
        record["languages"] = list(dict.fromkeys(record.get("languages") or []))
        record["raw_evidence_refs"] = list(dict.fromkeys(record.get("raw_evidence_refs") or []))
        record["evidence_payloads"] = list(record.get("evidence_payloads") or [])
        record["source_page_type"] = record.get("source_page_type") or "unknown"
        record["extraction_method"] = record.get("extraction_method") or "deterministic"
        record["extraction_confidence"] = float(record.get("extraction_confidence") or record.get("parser_confidence") or 0.0)
        record["parser_confidence"] = float(record.get("parser_confidence") or record["extraction_confidence"] or 0.0)
        record["source_confidence"] = float(record.get("source_confidence") or record["parser_confidence"] or 0.0)
        record["fetch_status"] = record.get("fetch_status") or "ok"
        record["discovered_at"] = record.get("discovered_at") or timestamp
        record["extracted_at"] = record.get("extracted_at") or timestamp
        record["fetched_at"] = record.get("fetched_at") or timestamp
        record["scenario_key"] = record.get("scenario_key") or "SIMPLE_DIRECTORY"
        record["execution_reasons"] = list(record.get("execution_reasons") or [])
        record["execution_flags"] = dict(record.get("execution_flags") or {})
        record["raw_payload"] = dict(record.get("raw_payload") or {})
        return record


class ScenarioExtractionEngine:
    """Extract suppliers from directory and company pages with explicit fallbacks."""

    def __init__(self, config: ScenarioConfig):
        self._config = config

    def extract_directory_page(
        self,
        html: str,
        *,
        page_url: str,
        query: str,
        route: ScenarioRouteDecision,
    ) -> list[RawCompanyRecord]:
        deterministic = self._extract_directory_deterministic(html, page_url, query, route)
        if deterministic:
            return deterministic
        heuristic = self._extract_directory_heuristic(html, page_url, query, route)
        if heuristic:
            return heuristic
        return self.extract_ai_assisted(page_url=page_url, html=html, route=route, query=query)

    def extract_company_site(
        self,
        pages: list[tuple[str, str]],
        *,
        source_url: str,
        route: ScenarioRouteDecision,
    ) -> list[RawCompanyRecord]:
        collected_blob = []
        website = ""
        services: list[str] = []
        products: list[str] = []
        contact_persons: list[str] = []
        evidence_payloads: list[RawEvidencePayload] = []
        legal_name_candidates: list[str] = []
        brand_candidates: list[str] = []
        address_candidates: list[str] = []
        city_candidates: list[str] = []

        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            text_blob = _text(soup.get_text(" ", strip=True))
            page_lines = self._page_lines(soup)
            context_sections = self._context_sections(soup)
            collected_blob.append(text_blob)
            website = website or f"https://{_domain(page_url)}"
            legal_name_candidates.extend(self._company_name_candidates(soup, page_lines, context_sections))
            brand_candidates.extend(self._brand_candidates(soup, page_lines, source_url=page_url))
            address_candidates.extend(self._address_candidates(page_lines, context_sections))
            city_candidates.extend(
                item for item in (self._guess_city("\n".join(page_lines)), self._guess_city("\n".join(context_sections))) if item
            )
            services.extend(self._bullet_candidates(soup, keywords=("service", "services", "dịch vụ", "printing", "packaging")))
            products.extend(self._bullet_candidates(soup, keywords=("product", "products", "sản phẩm", "label", "box", "packaging")))
            contact_persons.extend(re.findall(r"(?:Mr|Ms|Mrs|Anh|Chị)\.?\s+[A-ZÀ-ỹ][A-Za-zÀ-ỹ\s]{2,30}", text_blob))
            evidence_payloads.append(
                {
                    "evidence_ref": f"site:{hashlib.sha1(page_url.encode('utf-8')).hexdigest()[:12]}",
                    "source_url": page_url,
                    "scenario_key": route["scenario_key"],
                    "evidence_type": "page_text",
                    "content": text_blob[: self._config.settings().evidence_char_limit],
                    "metadata": {"title": _text((soup.select_one('title') or {}).get_text(' ', strip=True) if soup.select_one('title') else "")},  # type: ignore[union-attr]
                }
            )

        blob = "\n".join(collected_blob)
        legal_name = self._pick_best_company_name(legal_name_candidates)
        brand_name = self._pick_best_brand_name(brand_candidates, legal_name, source_url=source_url)
        address = self._pick_best_address(address_candidates)
        city = self._pick_best_city(city_candidates, address, blob)
        region = city
        record: RawCompanyRecord = {
            "source_type": "company_site",
            "source_url": source_url,
            "source_page_type": "company_site",
            "company_name": self._compose_company_name(brand_name, legal_name, source_url=source_url),
            "website": website,
            "domain": _domain(website or source_url),
            "address_text": address,
            "city": city,
            "region": region,
            "country": "Vietnam",
            "country_code": "VN",
            "phones": _phones_from_text(blob),
            "emails": _emails_from_text(blob),
            "services": list(dict.fromkeys(services))[:10],
            "products": list(dict.fromkeys(products))[:10],
            "categories": _capability_labels(blob),
            "labels": _capability_labels(blob),
            "contact_persons": list(dict.fromkeys(contact_persons))[:5],
            "social_links": _social_links(BeautifulSoup(pages[0][1], "html.parser"), source_url) if pages else [],
            "messengers": _messengers_from_links(_social_links(BeautifulSoup(pages[0][1], "html.parser"), source_url) if pages else [], blob),
            "parser_confidence": 0.82 if legal_name else 0.64,
            "source_confidence": 0.72,
            "extraction_method": "deterministic",
            "extraction_confidence": 0.82 if legal_name else 0.64,
            "scenario_key": route["scenario_key"],
            "execution_reasons": list(route.get("reasons") or []),
            "execution_flags": dict(route.get("execution_flags") or {}),
            "raw_evidence_refs": [item["evidence_ref"] for item in evidence_payloads],
            "evidence_payloads": evidence_payloads,
            "capabilities_text": "; ".join(_capability_labels(blob)),
            "raw_payload": {
                "page_urls": [url for url, _html in pages],
                "legal_name_candidates": _dedupe_texts(legal_name_candidates)[:8],
                "brand_candidates": _dedupe_texts(brand_candidates)[:8],
                "address_candidates": _dedupe_texts(address_candidates)[:8],
            },
        }
        return [SupplierSchemaValidator.ensure(record)]

    def extract_ai_assisted(
        self,
        *,
        page_url: str,
        html: str,
        route: ScenarioRouteDecision,
        query: str,
    ) -> list[RawCompanyRecord]:
        markdown = self._crawl4ai_markdown(page_url) if page_url.startswith("http") else ""
        extraction_blob = markdown or _text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        if not extraction_blob:
            return []
        llm_preview = None
        llm_error = ""
        try:
            llm_adapter = get_llm_adapter()
            if llm_adapter.configured:
                llm_preview = llm_adapter.extract_supplier_preview(page_url=page_url, query=query, text_blob=extraction_blob)
        except Exception as exc:
            # RU: LLM-fallback не должен ронять parsing-контур; при ошибке остаёмся на explainable plaintext path.
            llm_error = _text(str(exc))[:300]
        soup = BeautifulSoup(html, "html.parser")
        company_name = _text((soup.select_one("h1") or soup.select_one("title") or {}).get_text(" ", strip=True) if (soup.select_one("h1") or soup.select_one("title")) else "")  # type: ignore[union-attr]
        llm_json = llm_preview.parsed_json if llm_preview else {}
        categories = list(dict.fromkeys(llm_json.get("categories") or _capability_labels(extraction_blob)))
        record: RawCompanyRecord = {
            "source_type": "directory" if route["scenario_key"] != "COMPANY_SITE" else "company_site",
            "source_url": page_url,
            "source_page_type": "directory",
            "company_name": _text(llm_json.get("company_name")) or company_name or query.title(),
            "website": _text(llm_json.get("website")),
            "address_text": _text(llm_json.get("address_text")) or self._first_address_like(extraction_blob),
            "city": _text(llm_json.get("city")) or self._guess_city(extraction_blob),
            "country": _text(llm_json.get("country")) or "Vietnam",
            "country_code": "VN",
            "phones": list(dict.fromkeys(llm_json.get("phones") or _phones_from_text(extraction_blob))),
            "emails": list(dict.fromkeys(llm_json.get("emails") or _emails_from_text(extraction_blob))),
            "categories": categories,
            "labels": categories,
            "services": list(dict.fromkeys(llm_json.get("services") or categories)),
            "products": list(dict.fromkeys(llm_json.get("products") or [])),
            "contact_persons": list(dict.fromkeys(llm_json.get("contact_persons") or [])),
            "parser_confidence": float(llm_json.get("confidence") or 0.52),
            "source_confidence": 0.55,
            "extraction_method": "ai_assisted",
            "extraction_confidence": float(llm_json.get("confidence") or 0.52),
            "scenario_key": "AI_ASSISTED_EXTRACTION",
            "execution_reasons": list(route.get("reasons") or []) + ["deterministic and heuristic extraction were weak"],
            "execution_flags": dict(route.get("execution_flags") or {}),
            "raw_evidence_refs": [f"ai:{hashlib.sha1(page_url.encode('utf-8')).hexdigest()[:12]}"],
            "evidence_payloads": [
                {
                    "evidence_ref": f"ai:{hashlib.sha1(page_url.encode('utf-8')).hexdigest()[:12]}",
                    "source_url": page_url,
                    "scenario_key": "AI_ASSISTED_EXTRACTION",
                    "evidence_type": "page_text",
                    "content": extraction_blob[: self._config.settings().evidence_char_limit],
                    "metadata": {
                        "fallback": "openai_responses" if llm_preview else "crawl4ai_markdown_or_plaintext",
                        "llm_model": llm_preview.model if llm_preview else "",
                        "llm_error": llm_error,
                    },
                }
            ],
            "capabilities_text": "; ".join(categories),
            "raw_payload": {
                "fallback_query": query,
                "llm_adapter": llm_preview.adapter if llm_preview else "",
                "llm_explanation": _text(llm_json.get("explanation")),
                "llm_error": llm_error,
            },
        }
        return [SupplierSchemaValidator.ensure(record)]

    def _extract_directory_deterministic(
        self,
        html: str,
        page_url: str,
        query: str,
        route: ScenarioRouteDecision,
    ) -> list[RawCompanyRecord]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.yp_noidunglistings")
        if not cards:
            return []
        rows: list[RawCompanyRecord] = []
        for card in cards:
            title = None
            for selector in (
                "div.fs-5.fw-semibold a[href*='/lgs/']",
                "div.fs-5.fw-semibold a[href]",
                "a[href*='/lgs/']",
                "h2 a[href*='/lgs/']",
                "h2 a[href]",
            ):
                title = card.select_one(selector)
                if title:
                    break
            if not title:
                continue
            company_url = urljoin(page_url, title.get("href", "").strip())
            text_blob = _text(card.get_text(" ", strip=True))
            phones = _phones_from_text(text_blob)
            emails = _emails_from_text(text_blob)
            website_node = card.select_one("a.text-success[href^='http']")
            website = website_node.get("href", "").strip() if website_node else ""
            capability_node = card.select_one("span.yp_nganh_text")
            capability_text = _text(capability_node.get_text(" ", strip=True) if capability_node else "")
            address_nodes = [
                _text(node.get_text(" ", strip=True))
                for node in card.select("i.fa-location-arrow + small, i.fa-location-arrow ~ small, .yp_diachi_logo p small, .yp_diachi_logo p")
            ]
            address_candidates = [self._extract_labeled_address(item) or self._extract_plain_address(item) for item in address_nodes + [text_blob]]
            address = self._pick_best_address(address_candidates)
            city = self._guess_city(address or text_blob)
            evidence_ref = f"card:{hashlib.sha1(company_url.encode('utf-8')).hexdigest()[:12]}"
            row: RawCompanyRecord = {
                "source_type": "directory",
                "source_url": company_url,
                "source_page_type": "directory",
                "source_domain": _domain(company_url),
                "company_name": _text(title.get_text(" ", strip=True)),
                "website": website,
                "domain": _domain(website or company_url),
                "address_text": address,
                "city": city,
                "country": "Vietnam",
                "country_code": "VN",
                "phones": phones,
                "emails": emails,
                "categories": _capability_labels(capability_text),
                "labels": _capability_labels(capability_text),
                "services": _capability_labels(capability_text),
                "products": [],
                "parser_confidence": 0.84 if website else 0.76,
                "source_confidence": 0.78 if website else 0.7,
                "extraction_method": "deterministic",
                "extraction_confidence": 0.84 if website else 0.76,
                "scenario_key": route["scenario_key"],
                "execution_reasons": list(route.get("reasons") or []),
                "execution_flags": dict(route.get("execution_flags") or {}),
                "raw_evidence_refs": [evidence_ref],
                "evidence_payloads": [
                    {
                        "evidence_ref": evidence_ref,
                        "source_url": company_url,
                        "scenario_key": route["scenario_key"],
                        "evidence_type": "card_block",
                        "content": text_blob[: self._config.settings().evidence_char_limit],
                        "metadata": {"listing_url": page_url, "query": query},
                    }
                ],
                "capabilities_text": capability_text,
                "raw_payload": {"listing_url": page_url, "query": query},
            }
            rows.append(SupplierSchemaValidator.ensure(row))
        return rows

    def _extract_directory_heuristic(
        self,
        html: str,
        page_url: str,
        query: str,
        route: ScenarioRouteDecision,
    ) -> list[RawCompanyRecord]:
        soup = BeautifulSoup(html, "html.parser")
        candidates = soup.select(".listing-card, .supplier-card, article, .result, .card")
        rows: list[RawCompanyRecord] = []
        for card in candidates[:25]:
            anchors = card.select("a[href]")
            name_anchor = None
            for anchor in anchors:
                text = _text(anchor.get_text(" ", strip=True))
                if len(text) >= 5 and not text.lower().startswith(("read more", "details", "next")):
                    name_anchor = anchor
                    break
            if not name_anchor:
                continue
            text_blob = _text(card.get_text(" ", strip=True))
            if not text_blob:
                continue
            company_url = urljoin(page_url, name_anchor.get("href", "").strip())
            evidence_ref = f"heur:{hashlib.sha1((company_url + text_blob[:80]).encode('utf-8')).hexdigest()[:12]}"
            rows.append(
                SupplierSchemaValidator.ensure(
                    {
                        "source_type": "directory",
                        "source_url": company_url,
                        "source_page_type": "directory",
                        "company_name": _text(name_anchor.get_text(" ", strip=True)),
                        "website": "",
                        "address_text": self._first_address_like(text_blob),
                        "city": self._guess_city(text_blob),
                        "country": "Vietnam",
                        "country_code": "VN",
                        "phones": _phones_from_text(text_blob),
                        "emails": _emails_from_text(text_blob),
                        "categories": _capability_labels(text_blob),
                        "labels": _capability_labels(text_blob),
                        "services": _capability_labels(text_blob),
                        "products": [],
                        "parser_confidence": 0.58,
                        "source_confidence": 0.56,
                        "extraction_method": "heuristic",
                        "extraction_confidence": 0.58,
                        "scenario_key": route["scenario_key"],
                        "execution_reasons": list(route.get("reasons") or []) + ["heuristic repeated-block extraction"],
                        "execution_flags": dict(route.get("execution_flags") or {}),
                        "raw_evidence_refs": [evidence_ref],
                        "evidence_payloads": [
                            {
                                "evidence_ref": evidence_ref,
                                "source_url": company_url,
                                "scenario_key": route["scenario_key"],
                                "evidence_type": "card_block",
                                "content": text_blob[: self._config.settings().evidence_char_limit],
                                "metadata": {"listing_url": page_url, "query": query},
                            }
                        ],
                        "capabilities_text": "; ".join(_capability_labels(text_blob)),
                        "raw_payload": {"listing_url": page_url, "query": query},
                    }
                )
            )
        return rows

    def _crawl4ai_markdown(self, url: str) -> str:
        os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", self._config.crawl4ai_base_directory())
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        except Exception:
            return ""

        async def _run() -> str:
            async with AsyncWebCrawler(base_directory=self._config.crawl4ai_base_directory()) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        page_timeout=self._config.settings().browser_timeout_ms,
                        remove_overlay_elements=True,
                        remove_consent_popups=True,
                        magic=True,
                        verbose=False,
                    ),
                )
                if hasattr(result, "_results"):
                    result = list(result)[0]
                markdown = getattr(result, "markdown", None)
                if markdown is None:
                    return ""
                return getattr(markdown, "raw_markdown", str(markdown))

        try:
            return asyncio.run(_run())
        except Exception:
            return ""

    @staticmethod
    def _page_lines(soup: BeautifulSoup) -> list[str]:
        lines = [_text(item) for item in soup.stripped_strings]
        return [item for item in _dedupe_texts(lines) if item]

    @staticmethod
    def _context_sections(soup: BeautifulSoup) -> list[str]:
        selectors = (
            "address",
            "[class*='contact']",
            "[id*='contact']",
            "[class*='footer']",
            "[id*='footer']",
            "[class*='address']",
            "[id*='address']",
            "[class*='info']",
            "[id*='info']",
            "[itemtype*='Organization']",
            "[itemtype*='LocalBusiness']",
        )
        values: list[str] = []
        for selector in selectors:
            for node in soup.select(selector):
                text = _text(node.get_text(" ", strip=True))
                if text:
                    values.append(text)
        return _dedupe_texts(values)

    @staticmethod
    def _looks_like_company_name(candidate: str) -> bool:
        lookup = _normalize_lookup(candidate)
        if not lookup or len(lookup) < 10:
            return False
        if not any(token in lookup for token in ("cong ty", "company", "co ltd", "tnhh", "trach nhiem huu han", "co phan", "jsc", "mtv")):
            return False
        if any(
            phrase in lookup
            for phrase in (
                "cong ty chung toi",
                "cong ty chuyen",
                "cong ty in gia re",
                "cong ty quang cao dep chuyen",
                "profile cong ty",
            )
        ):
            return False
        return True

    @staticmethod
    def _clean_company_candidate(candidate: str) -> str:
        cleaned = _text(candidate)
        cleaned = re.sub(
            r"^(?:liên hệ(?: footer)?|giới thiệu|trụ sở chính|chi nhánh(?:\s+\w+)?|kính chào quý khách!?|sản phẩm|về)\s*-\s*",
            "",
            cleaned,
            flags=re.I,
        )
        company_hits = [match.start() for match in re.finditer(r"\bcông ty\b|\bcompany\b", cleaned, flags=re.I)]
        if len(company_hits) > 1:
            cleaned = cleaned[company_hits[-1] :]
        cleaned = re.sub(r"^(?:liên hệ ngay:|copyright.*?về|©\s*bản quyền thuộc về)\s*", "", cleaned, flags=re.I)
        cleaned = re.split(
            r"\b(?:địa chỉ|hotline|email|website|mst|mã số thuế|điện thoại|phone|gpkd|văn phòng|vp|xưởng sản xuất|xưởng|tuyển dụng)\b\s*[:\-]?",
            cleaned,
            maxsplit=1,
            flags=re.I,
        )[0]
        cleaned = re.split(
            r"\b(?:là đơn vị|được thành lập|đã được thành lập|cam kết|tối ưu hóa|với sức mạnh|bạn cần trợ giúp)\b",
            cleaned,
            maxsplit=1,
            flags=re.I,
        )[0]
        if re.match(r"(?i)^công ty\s*,", cleaned):
            return ""
        address_start = re.search(
            r"\b(?:số\s+)?\d{1,5}[/-]?[A-Za-z0-9]*\b(?=.*(?:phường|p\.|quận|q\.|tp\b|thành phố|district|ward|city))",
            cleaned,
            flags=re.I,
        )
        if address_start:
            cleaned = cleaned[: address_start.start()]
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -|,:")
        return cleaned

    def _company_name_candidates(self, soup: BeautifulSoup, page_lines: list[str], context_sections: list[str]) -> list[str]:
        values: list[str] = []
        for selector in ("[itemprop='name']", "meta[property='og:site_name']", "meta[property='og:title']"):
            for node in soup.select(selector):
                text = _text(node.get("content") if node.name == "meta" else node.get_text(" ", strip=True))
                if text and self._looks_like_company_name(text):
                    values.append(text)
        for source in context_sections + page_lines:
            for match in re.findall(r"(?:CÔNG TY|Công Ty|công ty|Company)[^.\n]{0,180}", source):
                cleaned = self._clean_company_candidate(match)
                if self._looks_like_company_name(cleaned):
                    values.append(cleaned)
        return _dedupe_texts(values)

    @staticmethod
    def _company_name_score(candidate: str) -> tuple[int, int]:
        lookup = _normalize_lookup(candidate)
        score = 0
        if any(token in lookup for token in ("tnhh", "trach nhiem huu han", "co phan", "jsc", "mtv")):
            score += 6
        if "sx tm" in lookup or "san xuat" in lookup:
            score += 2
        if "&" in candidate or "-" in candidate:
            score += 1
        if any(token in lookup for token in ("dia chi", "hotline", "email", "website")):
            score -= 4
        return score, len(lookup)

    def _pick_best_company_name(self, candidates: list[str]) -> str:
        cleaned = [self._clean_company_candidate(item) for item in candidates if self._clean_company_candidate(item)]
        valid = [item for item in _dedupe_texts(cleaned) if self._looks_like_company_name(item)]
        if not valid:
            return ""
        return max(valid, key=self._company_name_score)

    @staticmethod
    def _clean_brand_candidate(candidate: str) -> str:
        cleaned = _text(candidate)
        if " - " in cleaned:
            cleaned = cleaned.split(" - ", 1)[0]
        cleaned = re.split(r"\b(?:địa chỉ|sđt|hotline|email|website)\b\s*[:\-]?", cleaned, maxsplit=1, flags=re.I)[0]
        return cleaned.strip(" -|,:")

    def _brand_candidates(self, soup: BeautifulSoup, page_lines: list[str], *, source_url: str) -> list[str]:
        values: list[str] = []
        for selector in ("h1", "title", "meta[property='og:site_name']", "meta[property='og:title']"):
            for node in soup.select(selector):
                text = _text(node.get("content") if node.name == "meta" else node.get_text(" ", strip=True))
                if text:
                    values.append(text)
        values.append(_domain(source_url).split(".")[0].replace("-", " "))
        candidates: list[str] = []
        for item in values:
            cleaned = self._clean_brand_candidate(item)
            lookup = _normalize_lookup(cleaned)
            if not cleaned or any(
                phrase in lookup
                for phrase in (
                    "trang vang",
                    "danh muc san pham",
                    "san pham dich vu",
                    "lich tet",
                    "trang chu",
                    "page not found",
                    "gia re tai xuong",
                    "dich vu",
                    "lay ngay",
                    "lien he",
                    "gioi thieu",
                    "thong tin lien he",
                    "chuyen cung cap",
                    "dam bao chat luong",
                    "don vi san xuat",
                    "uy tin",
                    "so 1",
                )
            ):
                continue
            if len(cleaned) > 48:
                continue
            if lookup in {_normalize_lookup(_domain(source_url)), _normalize_lookup(_domain(source_url).split(".")[0])} and "." in cleaned:
                continue
            candidates.append(cleaned)
        return _dedupe_texts(candidates)

    @staticmethod
    def _pick_best_brand_name(candidates: list[str], legal_name: str, *, source_url: str) -> str:
        valid: list[str] = []
        legal_lookup = _normalize_lookup(legal_name)
        for item in candidates:
            lookup = _normalize_lookup(item)
            if not lookup or lookup == legal_lookup:
                continue
            if lookup in {_normalize_lookup(_domain(source_url)), _normalize_lookup(_domain(source_url).split(".")[0])}:
                continue
            if len(item) > 48:
                continue
            valid.append(item)
        if not valid:
            return ""
        return min(valid, key=len)

    @staticmethod
    def _compose_company_name(brand_name: str, legal_name: str, *, source_url: str) -> str:
        if legal_name:
            return legal_name
        if brand_name:
            return brand_name
        return _domain(source_url).split(".")[0].replace("-", " ").title()

    def _address_candidates(self, page_lines: list[str], context_sections: list[str]) -> list[str]:
        labeled_entries: list[tuple[int, int, str]] = []
        plain_values: list[str] = []
        for source in context_sections + page_lines:
            if not source:
                continue
            labeled_entries.extend(self._extract_labeled_address_entries(source))
            plain = self._extract_plain_address(source)
            if plain:
                plain_values.append(plain)
        # RU: если на странице есть явно размеченный адрес, берем только его ветку,
        # иначе project/news контент снова начинает побеждать реальный контактный блок.
        if labeled_entries:
            ordered_candidates: list[str] = []
            for _priority, _index, candidate in sorted(labeled_entries, key=lambda value: (value[0], value[1])):
                if candidate not in ordered_candidates:
                    ordered_candidates.append(candidate)
            return ordered_candidates
        return _dedupe_texts(plain_values)

    def _pick_best_address(self, candidates: list[str]) -> str:
        valid = [item for item in candidates if self._address_score(item) > 0]
        if not valid:
            return ""
        indexed = list(enumerate(valid))
        return max(indexed, key=lambda pair: (self._address_score(pair[1]), -pair[0]))[1]

    def _pick_best_city(self, candidates: list[str], address: str, blob: str) -> str:
        address_city = self._guess_city(address)
        if address_city:
            return address_city
        for item in candidates:
            if item:
                return item
        return self._guess_city(address or blob)

    def _address_score(self, candidate: str) -> int:
        lookup = _normalize_lookup(candidate)
        if not lookup:
            return 0
        if len(candidate) < 12:
            return 0
        if re.search(r"\b[a-z0-9-]+\.(?:vn|com|net|org)\b", candidate, flags=re.I):
            return 0
        if any(
            phrase in lookup
            for phrase in (
                "gio hang",
                "dat in",
                "gia xuong",
                "noi bat",
                "xem chi tiet",
                "du an",
                "khuyen mai",
                "chinh sach",
                "lien ket",
                "ban quyen",
                "quy trinh",
                "trang chu",
                "danh muc",
                "san pham",
                "dich vu",
                "bar",
                "karaoke",
                "spa",
                "bao li xi",
                "lich tet",
                "poster",
                "catalogue",
                "menu",
                "media",
                "copyright",
                "all rights reserved",
                "tuyen dung",
            )
        ):
            return 0
        street_tokens = ("duong", "street", "road", "ngo", "hem", "alley", "kcn", "khu ", "khu pho", "kp", "phuong", "p ", "p.", "ward", "so ", "lo ", "ap ")
        region_tokens = (
            "quan",
            "district",
            "q ",
            "q.",
            "tp",
            "city",
            "ho chi minh",
            "ha noi",
            "da nang",
            "binh duong",
            "dong nai",
            "bien hoa",
            "thu dau mot",
        )
        has_number = bool(re.search(r"\d", candidate))
        has_street = any(token in lookup for token in street_tokens)
        has_region = any(token in lookup for token in region_tokens)
        has_commas = candidate.count(",") >= 2
        if not ((has_number and has_street) or (has_number and has_region and has_commas)):
            return 0
        score = 0
        if has_number:
            score += 4
        if has_street:
            score += 4
        if has_region:
            score += 2
        if has_commas:
            score += 2
        score += min(
            3,
            sum(1 for token in ("thu dau mot", "binh duong", "dong nai", "da nang", "ha noi", "ho chi minh", "bien hoa") if token in lookup),
        )
        if any(token in lookup for token in ("email", "website", "hotline", "zalo", "fanpage", "gpkd", "mst", "ma so thue")):
            score -= 6
        if len(candidate) > 220:
            score -= 3
        return score

    def _extract_labeled_address_entries(self, source: str) -> list[tuple[int, int, str]]:
        cleaned = _text(source)
        if not cleaned:
            return []
        label_pattern = re.compile(
            r"(?:địa chỉ(?:\s*cửa hàng)?|address|trụ sở|văn phòng|vp|office|chi nhánh(?:\s*-\s*xưởng sản xuất)?|xưởng sản xuất|xưởng)\s*[:\-]?\s*",
            flags=re.I,
        )
        matches = list(label_pattern.finditer(cleaned))
        weighted_results: list[tuple[int, int, str]] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
            tail = cleaned[start:end]
            tail = re.split(
                r"\b(?:hotline|email|website|mst|mã số thuế|liên hệ|zalo|fanpage|đt|điện thoại|phone|gpkd)\b",
                tail,
                maxsplit=1,
                flags=re.I,
            )[0]
            candidate = self._extract_plain_address(tail)
            if candidate:
                label_lookup = _normalize_lookup(match.group(0))
                priority = 2 if any(token in label_lookup for token in ("cua hang", "xuong", "chi nhanh")) else 1
                if any(token in label_lookup for token in ("tru so", "van phong", "vp")):
                    priority = 0
                elif "dia chi" in label_lookup:
                    priority = min(priority, 1)
                weighted_results.append((priority, index, candidate))
        return weighted_results

    def _extract_labeled_addresses(self, source: str) -> list[str]:
        weighted_results = self._extract_labeled_address_entries(source)
        ordered = [item for _priority, _index, item in sorted(weighted_results, key=lambda value: (value[0], value[1]))]
        return _dedupe_texts(ordered)

    def _extract_labeled_address(self, source: str) -> str:
        return next(iter(self._extract_labeled_addresses(source)), "")

    def _extract_plain_address(self, source: str) -> str:
        cleaned = _text(source)
        if not cleaned:
            return ""
        if any(token in _normalize_lookup(cleaned) for token in ("email", "website")) and len(cleaned) > 220:
            return ""
        match = re.search(
            r"((?:số|lô|a\d|b\d|\d{1,5}|kp\.?\s*\d+|khu phố\s*\d+|đường|duong|road|street|ấp|kcn)[^|]{8,220})",
            cleaned,
            flags=re.I,
        )
        if match:
            candidate = match.group(1)
        else:
            candidate = cleaned
        candidate = re.split(
            r"\b(?:hotline|email|website|mst|mã số thuế|zalo|fanpage|giỏ hàng|mua thêm|thanh toán|đt|điện thoại|phone|gpkd|liên hệ|lh|gửi|copyright|all rights reserved)\b",
            candidate,
            maxsplit=1,
            flags=re.I,
        )[0]
        candidate = re.split(r"\.\s*(?:công ty|company)\b", candidate, maxsplit=1, flags=re.I)[0]
        candidate = candidate.strip(" -|,:")
        return candidate if self._address_score(candidate) > 0 else ""

    @staticmethod
    def _guess_city(blob: str) -> str:
        lookup = _normalize_lookup(blob)
        for pattern, replacement in _LOCATION_REPLACEMENTS:
            if re.search(pattern, lookup):
                if replacement == "ho chi minh city":
                    return "Ho Chi Minh City"
                if replacement == "ha noi":
                    return "Ha Noi"
                if replacement == "da nang":
                    return "Da Nang"
                if replacement == "binh duong":
                    return "Binh Duong"
                if replacement == "dong nai":
                    return "Dong Nai"
                if replacement == "bien hoa":
                    return "Bien Hoa"
                if replacement == "thu dau mot":
                    return "Thu Dau Mot"
        return ""

    def _first_address_like(self, blob: str) -> str:
        return self._pick_best_address([self._extract_labeled_address(blob), self._extract_plain_address(blob)])

    @staticmethod
    def _bullet_candidates(soup: BeautifulSoup, keywords: tuple[str, ...]) -> list[str]:
        values: list[str] = []
        for selector in ("li", "p", "h2", "h3"):
            for node in soup.select(selector):
                text = _text(node.get_text(" ", strip=True))
                if any(keyword in text.lower() for keyword in keywords):
                    values.append(text)
        return values[:10]
