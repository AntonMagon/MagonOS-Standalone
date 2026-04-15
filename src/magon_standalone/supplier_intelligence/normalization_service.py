"""Normalization and lightweight enrichment for discovered suppliers.

Runtime role: Transforms raw discovery rows into canonical company payloads.
Inputs: RawCompanyRecord lists.
Outputs: NormalizedCompanyRecord lists ready for dedup/scoring.
Does not: fetch external data or persist canonical entities directly.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .contracts import NormalizedCompanyRecord, RawCompanyRecord
from .interfaces import EnrichmentService, NormalizationService

# Keep capability extraction deterministic and file-local so new adapters feed text, not canonical codes.
_CAPABILITY_MAP = {
    "offset": "PRINT_OFFSET",
    "flexo": "PRINT_FLEXO",
    "corrugated": "PACK_CORRUGATED",
    "carton": "PACK_CORRUGATED",
    "label": "LABEL_SELF_ADHESIVE",
    "souvenir": "PROMO_SOUVENIR",
    "promotional": "PROMO_SOUVENIR",
    "wide": "WIDE_FORMAT",
}


class BasicNormalizationService(NormalizationService):
    """Map raw discovery rows into canonical company payloads."""

    def normalize(self, records: list[RawCompanyRecord]) -> list[NormalizedCompanyRecord]:
        """Normalize raw rows without touching persistence or routing state."""
        normalized: list[NormalizedCompanyRecord] = []
        for row in records:
            name = self._clean_name(row.get("company_name") or "")
            website = self._normalize_website(row.get("website") or "")
            canonical_email = ((row.get("email") or "") or ((row.get("emails") or [""])[0])).strip().lower() or None
            canonical_phone = self._normalize_phone((row.get("phone") or "") or ((row.get("phones") or [""])[0])) or None
            capabilities = self._extract_capabilities(row)
            key = self._company_key(name, website, canonical_phone, row.get("source_fingerprint") or "")
            normalized.append(
                {
                    "canonical_key": key,
                    "canonical_name": name,
                    "legal_name": self._clean_name(row.get("legal_name") or "") or name,
                    "brand_alias": self._clean_name(row.get("brand_alias") or "") or None,
                    "canonical_phone": canonical_phone,
                    "canonical_email": canonical_email,
                    "website": website,
                    "address_text": (row.get("address_text") or "").strip(),
                    "city": (row.get("city") or "").strip() or self._guess_city(row.get("address_text") or ""),
                    "district": (row.get("district") or "").strip(),
                    "country_code": "VN",
                    "capabilities": capabilities,
                    "confidence": float(row.get("parser_confidence") or 0.0),
                    "parser_confidence": float(row.get("parser_confidence") or 0.0),
                    "source_confidence": float(row.get("source_confidence") or 0.0),
                    "normalized_at": row.get("normalized_at") or row.get("extracted_at"),
                    "provenance": [row.get("source_url") or ""],
                    "review_status": "new",
                    "source_fingerprint": row.get("source_fingerprint") or "",
                    "dedup_fingerprint": row.get("candidate_dedup_fingerprint") or "",
                }
            )
        return normalized

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = re.sub(r"\s+", " ", name).strip()
        return cleaned.title()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(ch for ch in phone if ch.isdigit())
        if not digits:
            return ""
        if digits.startswith("84"):
            return f"+{digits}"
        if digits.startswith("0"):
            return f"+84{digits[1:]}"
        return f"+{digits}"

    @staticmethod
    def _normalize_website(website: str) -> str:
        # Strip paths and query strings so routing and dedup compare one stable company domain.
        raw = website.strip().lower()
        if not raw:
            return ""
        if not raw.startswith("http"):
            raw = f"https://{raw}"
        parsed = urlparse(raw)
        netloc = parsed.netloc.replace("www.", "")
        return f"https://{netloc}"

    @staticmethod
    def _guess_city(address: str) -> str:
        # Keep city guessing conservative; a wrong city is more harmful than an empty city.
        lowered = address.lower()
        if "ho chi minh" in lowered or "tp ho chi minh" in lowered:
            return "Ho Chi Minh City"
        if "ha noi" in lowered:
            return "Ha Noi"
        if "da nang" in lowered:
            return "Da Nang"
        return ""

    @staticmethod
    def _extract_capabilities(record: RawCompanyRecord) -> list[str]:
        blob = " ".join(
            [
                record.get("capabilities_text") or "",
                " ".join(record.get("labels") or []),
                " ".join(record.get("categories") or []),
                " ".join(record.get("services") or []),
                " ".join(record.get("products") or []),
            ]
        ).lower()
        found: list[str] = []
        for token, code in _CAPABILITY_MAP.items():
            if token in blob and code not in found:
                found.append(code)
        return found

    @staticmethod
    def _company_key(name: str, website: str, phone: str | None, source_fingerprint: str) -> str:
        base = website or phone or name.lower().replace(" ", "-")
        clean = re.sub(r"[^a-z0-9+-]", "", base.lower())[:60]
        suffix = re.sub(r"[^a-z0-9]", "", source_fingerprint.lower())[:12]
        return f"{clean}-{suffix}" if suffix else clean


class BasicEnrichmentService(EnrichmentService):
    """Apply lightweight confidence enrichment to normalized records."""

    def enrich(self, records: list[NormalizedCompanyRecord]) -> list[NormalizedCompanyRecord]:
        """Bump confidence only from evidence already present in the normalized payload."""
        enriched: list[NormalizedCompanyRecord] = []
        for row in records:
            confidence = max(float(row.get("confidence") or 0.0), 0.1)
            if row.get("website"):
                confidence = min(confidence + 0.05, 1.0)
            if row.get("canonical_email"):
                confidence = min(confidence + 0.05, 1.0)
            if row.get("capabilities"):
                confidence = min(confidence + 0.05, 1.0)
            row["confidence"] = round(confidence, 4)
            enriched.append(row)
        return enriched
