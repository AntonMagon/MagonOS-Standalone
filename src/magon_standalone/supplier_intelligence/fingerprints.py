"""Deterministic raw-record fingerprint helpers.

These helpers are portable and intentionally live outside the old Odoo-bound
discovery fan-out service so scenario-driven discovery can stamp raw keys
without importing addon runtime modules.
"""
from __future__ import annotations

import hashlib

from .contracts import RawCompanyRecord


def source_fingerprint(record: RawCompanyRecord) -> str:
    """Build one stable fingerprint for a raw source row."""
    key = "|".join(
        [
            record.get("source_type", ""),
            record.get("source_url", ""),
            record.get("external_id", ""),
            record.get("company_name", ""),
            record.get("website", ""),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def candidate_fingerprint(record: RawCompanyRecord) -> str:
    """Build one bounded fingerprint for raw-company dedup before normalization."""
    website = (record.get("website") or "").lower().replace("https://", "").replace("http://", "").strip("/")
    phone = "".join(ch for ch in (record.get("phone") or "") if ch.isdigit())
    name = (record.get("company_name") or "").lower().replace("co.,", "").replace("co", "").strip()
    key = f"{name}|{website}|{phone}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
