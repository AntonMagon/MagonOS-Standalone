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
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

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
        best_name = ""
        website = ""
        address = ""
        city = ""
        region = ""
        services: list[str] = []
        products: list[str] = []
        contact_persons: list[str] = []
        evidence_payloads: list[RawEvidencePayload] = []

        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            text_blob = _text(soup.get_text(" ", strip=True))
            collected_blob.append(text_blob)
            best_name = best_name or _text(
                (soup.select_one("h1") or soup.select_one("title") or {}).get_text(" ", strip=True)  # type: ignore[union-attr]
                if (soup.select_one("h1") or soup.select_one("title"))
                else ""
            )
            website = website or f"https://{_domain(page_url)}"
            if not address:
                address = self._first_address_like(text_blob)
            if not city:
                city = self._guess_city(text_blob)
            if not region:
                region = city
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
        record: RawCompanyRecord = {
            "source_type": "company_site",
            "source_url": source_url,
            "source_page_type": "company_site",
            "company_name": best_name or _domain(source_url).split(".")[0].replace("-", " ").title(),
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
            "parser_confidence": 0.76 if best_name else 0.58,
            "source_confidence": 0.72,
            "extraction_method": "deterministic",
            "extraction_confidence": 0.76 if best_name else 0.58,
            "scenario_key": route["scenario_key"],
            "execution_reasons": list(route.get("reasons") or []),
            "execution_flags": dict(route.get("execution_flags") or {}),
            "raw_evidence_refs": [item["evidence_ref"] for item in evidence_payloads],
            "evidence_payloads": evidence_payloads,
            "capabilities_text": "; ".join(_capability_labels(blob)),
            "raw_payload": {"page_urls": [url for url, _html in pages]},
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
        soup = BeautifulSoup(html, "html.parser")
        company_name = _text((soup.select_one("h1") or soup.select_one("title") or {}).get_text(" ", strip=True) if (soup.select_one("h1") or soup.select_one("title")) else "")  # type: ignore[union-attr]
        categories = _capability_labels(extraction_blob)
        record: RawCompanyRecord = {
            "source_type": "directory" if route["scenario_key"] != "COMPANY_SITE" else "company_site",
            "source_url": page_url,
            "source_page_type": "directory",
            "company_name": company_name or query.title(),
            "website": "",
            "address_text": self._first_address_like(extraction_blob),
            "city": self._guess_city(extraction_blob),
            "country": "Vietnam",
            "country_code": "VN",
            "phones": _phones_from_text(extraction_blob),
            "emails": _emails_from_text(extraction_blob),
            "categories": categories,
            "labels": categories,
            "services": categories,
            "products": [],
            "parser_confidence": 0.52,
            "source_confidence": 0.55,
            "extraction_method": "ai_assisted",
            "extraction_confidence": 0.52,
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
                    "metadata": {"fallback": "crawl4ai_markdown_or_plaintext"},
                }
            ],
            "capabilities_text": "; ".join(categories),
            "raw_payload": {"fallback_query": query},
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
            title = card.select_one("div.fs-5.fw-semibold a[href]")
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
            evidence_ref = f"card:{hashlib.sha1(company_url.encode('utf-8')).hexdigest()[:12]}"
            row: RawCompanyRecord = {
                "source_type": "directory",
                "source_url": company_url,
                "source_page_type": "directory",
                "source_domain": _domain(company_url),
                "company_name": _text(title.get_text(" ", strip=True)),
                "website": website,
                "domain": _domain(website or company_url),
                "address_text": self._first_address_like(text_blob),
                "city": self._guess_city(text_blob),
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
    def _guess_city(blob: str) -> str:
        lowered = blob.lower()
        if "ho chi minh" in lowered or "tp ho chi minh" in lowered:
            return "Ho Chi Minh City"
        if "ha noi" in lowered:
            return "Ha Noi"
        if "da nang" in lowered:
            return "Da Nang"
        return ""

    @staticmethod
    def _first_address_like(blob: str) -> str:
        for segment in re.split(r"[|;]", blob):
            cleaned = _text(segment)
            if any(token in cleaned.lower() for token in ("district", "quan", "ward", "street", "industrial", "city", "kcn", "park")):
                return cleaned
        return ""

    @staticmethod
    def _bullet_candidates(soup: BeautifulSoup, keywords: tuple[str, ...]) -> list[str]:
        values: list[str] = []
        for selector in ("li", "p", "h2", "h3"):
            for node in soup.select(selector):
                text = _text(node.get_text(" ", strip=True))
                if any(keyword in text.lower() for keyword in keywords):
                    values.append(text)
        return values[:10]
