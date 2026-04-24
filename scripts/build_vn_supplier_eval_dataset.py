#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# RU: Dataset builder использует тот же routing/extraction vocabulary, чтобы benchmark не жил отдельно от реального parsing contour.
from magon_standalone.supplier_intelligence.evaluation import _normalize_capability_values
from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig
from magon_standalone.supplier_intelligence.scenario_profiler import HeuristicPageProfiler
from magon_standalone.supplier_intelligence.scenario_router import ScenarioDecisionRouter

USER_AGENT = "MagonOSBot/0.2 (+supplier-eval-dataset)"
SEARCH_QUERIES = (
    ("printing", ""),
    ("printing", "Ho Chi Minh"),
    ("printing", "Ha Noi"),
    ("packaging", ""),
    ("packaging", "Ho Chi Minh"),
    ("packaging", "Ha Noi"),
    ("in ấn", ""),
    ("bao bì", ""),
    ("nhãn mác", ""),
    ("hộp giấy", ""),
    ("thùng carton", ""),
    ("sticker", ""),
    ("in tem nhãn", ""),
    ("decal", ""),
    ("bao bì giấy", ""),
    ("thùng carton", "Ho Chi Minh"),
    ("offset", ""),
    ("flexo", ""),
)
TARGET_COUNTS = {
    "directory_listing": 15,
    "simple_supplier_site": 15,
    "js_heavy_supplier_site": 5,
}


def _fetch(session: requests.Session, url: str) -> tuple[str, int]:
    response = session.get(url, timeout=12, allow_redirects=True)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response.text, response.status_code


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _extract_city(blob: str) -> str:
    lowered = blob.lower()
    if any(token in lowered for token in ("tp. hồ chí minh", "tphcm", "ho chi minh", "hồ chí minh")):
        return "Ho Chi Minh City"
    if any(token in lowered for token in ("hà nội", "ha noi")):
        return "Ha Noi"
    if any(token in lowered for token in ("đà nẵng", "da nang")):
        return "Da Nang"
    return ""


def _extract_phone(blob: str) -> str:
    for match in re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", blob):
        digits = "".join(ch for ch in match if ch.isdigit())
        if len(digits) < 8:
            continue
        if digits.startswith("84"):
            return f"+{digits}"
        if digits.startswith("0"):
            return f"+84{digits[1:]}"
        return f"+{digits}"
    return ""


def _extract_email(blob: str) -> str:
    values = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", blob, re.I)
    return values[0].lower() if values else ""


def _extract_address(blob: str) -> str:
    for segment in re.split(r"[|;]", blob):
        cleaned = _normalize_text(segment)
        lowered = cleaned.lower()
        if any(token in lowered for token in ("district", "quan", "ward", "street", "industrial", "city", "kcn", "park", "tp.", "phường", "quận", "hà nội", "hồ chí minh")):
            return cleaned
    return ""


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _is_relevant_candidate(*, supplier_name: str, capability_text: str, text_blob: str, website: str) -> bool:
    lowered = " ".join([supplier_name, capability_text, text_blob, website]).lower()
    include_tokens = (
        "bao b",
        "pack",
        "label",
        "nhãn",
        "decal",
        "sticker",
        "tem",
        "print",
        "in ",
        "offset",
        "flexo",
        "carton",
        "hộp",
        "corrugated",
    )
    exclude_tokens = (
        "bê tông",
        "betong",
        "nam châm",
        "magnet",
        "keo dán",
        "adhesive",
        "truyền thông",
        "media",
        "golf",
    )
    return any(token in lowered for token in include_tokens) and not any(token in lowered for token in exclude_tokens)


def _parse_search_cards(session: requests.Session) -> list[dict]:
    base_url = "https://www.yellowpages.vn/search.asp"
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for query, where in SEARCH_QUERIES:
        search_url = f"{base_url}?{urlencode({'keyword': query, 'where': where})}"
        try:
            html, _status_code = _fetch(session, search_url)
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.yp_noidunglistings"):
            title = card.select_one("div.fs-5.fw-semibold a[href]")
            if not title:
                continue
            supplier_name = _normalize_text(title.get_text(" ", strip=True))
            detail_url = urljoin(search_url, title.get("href", "").strip())
            website_node = card.select_one("a.text-success[href^='http']")
            website = _normalize_text(website_node.get("href", "").strip() if website_node else "")
            text_blob = _normalize_text(card.get_text(" ", strip=True))
            capability_node = card.select_one("span.yp_nganh_text")
            capability_text = _normalize_text(capability_node.get_text(" ", strip=True) if capability_node else "")
            if not _is_relevant_candidate(
                supplier_name=supplier_name,
                capability_text=capability_text,
                text_blob=text_blob,
                website=website,
            ):
                continue
            key = (supplier_name.lower(), website.lower() or detail_url.lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "supplier_name": supplier_name,
                    "detail_url": detail_url,
                    "directory_url": search_url,
                    "website": website,
                    "phone": _extract_phone(text_blob),
                    "email": _extract_email(text_blob),
                    "address": _extract_address(text_blob),
                    "city_region": _extract_city(text_blob),
                    "category": "",
                    "capabilities": _normalize_capability_values([capability_text]),
                    "capability_text": capability_text,
                }
            )
    return candidates


def _enrich_from_detail_pages(session: requests.Session, candidates: list[dict]) -> None:
    for item in candidates:
        try:
            html, _status_code = _fetch(session, item["detail_url"])
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        text_blob = _normalize_text(soup.get_text(" ", strip=True))
        if not item["website"]:
            websites = [href.strip() for href in [node.get("href", "") for node in soup.select("a[href^='http']")] if href.strip()]
            if websites:
                item["website"] = websites[0]
        item["phone"] = item["phone"] or _extract_phone(text_blob)
        item["email"] = item["email"] or _extract_email(text_blob)
        item["address"] = item["address"] or _extract_address(text_blob)
        item["city_region"] = item["city_region"] or _extract_city(text_blob)
        if not item["capabilities"]:
            headings = " ".join(node.get_text(" ", strip=True) for node in soup.select("h1, h2, h3, strong"))
            item["capabilities"] = _normalize_capability_values([headings, text_blob[:1000]])
    candidates[:] = [
        item
        for item in candidates
        if item.get("website")
        and "yellowpages.vn" not in item["website"].lower()
        and _is_relevant_candidate(
            supplier_name=item["supplier_name"],
            capability_text=item.get("capability_text") or " ".join(item.get("capabilities") or []),
            text_blob=item.get("address") or "",
            website=item.get("website") or "",
        )
    ]
    for item in candidates:
        item["category"] = item["capabilities"][0] if item["capabilities"] else ""


def _classify_company_sites(session: requests.Session, candidates: list[dict]) -> None:
    config = ScenarioConfig.load()
    profiler = HeuristicPageProfiler()
    router = ScenarioDecisionRouter(config)
    simple_count = 0
    js_count = 0
    for item in candidates:
        if simple_count >= TARGET_COUNTS["simple_supplier_site"] + 5 and js_count >= TARGET_COUNTS["js_heavy_supplier_site"] + 3:
            break
        website = item.get("website") or ""
        if not website:
            item["source_class"] = None
            item["route_scenario"] = None
            continue
        try:
            html, status_code = _fetch(session, website)
        except Exception:
            item["source_class"] = None
            item["route_scenario"] = None
            continue
        seed = {
            "url": website,
            "query": "printing packaging vietnam",
            "country_code": "VN",
            "source_type": "company_site",
            "source_domain": urlparse(website).netloc.replace("www.", "").lower(),
            "page_type_hint": "company_site",
        }
        profile = profiler.profile(seed, html, status_code=status_code)
        route = router.route(seed, profile)
        scenario_key = route["scenario_key"]
        item["route_scenario"] = scenario_key
        if scenario_key in {"JS_COMPANY_SITE", "HARD_DYNAMIC_OR_BLOCKED"}:
            item["source_class"] = "js_heavy_supplier_site"
            js_count += 1
        elif scenario_key == "COMPANY_SITE":
            item["source_class"] = "simple_supplier_site"
            simple_count += 1
        else:
            item["source_class"] = None


def _select_samples(candidates: list[dict]) -> list[dict]:
    selected: list[dict] = []
    directory_per_seed: dict[str, int] = defaultdict(int)
    site_selected: set[str] = set()

    for item in candidates:
        if len([row for row in selected if row["source_class"] == "directory_listing"]) >= TARGET_COUNTS["directory_listing"]:
            break
        if directory_per_seed[item["directory_url"]] >= 5:
            continue
        directory_per_seed[item["directory_url"]] += 1
        selected.append(
            {
                "sample_id": f"dir-{_slug(item['supplier_name'])}",
                "source_class": "directory_listing",
                "url": item["directory_url"],
                "query": "printing packaging vietnam",
                "country_code": "VN",
                "expected": {
                    "supplier_name": item["supplier_name"],
                    "website": item["website"],
                    "phone": item["phone"],
                    "email": item["email"],
                    "address": item["address"],
                    "city_region": item["city_region"],
                    "category": item["category"],
                    "capabilities": item["capabilities"],
                },
                "notes": {"label_source": item["detail_url"]},
            }
        )

    for class_name in ("simple_supplier_site", "js_heavy_supplier_site"):
        for item in candidates:
            if item.get("source_class") != class_name:
                continue
            if not item.get("website"):
                continue
            if item["website"] in site_selected:
                continue
            if len([row for row in selected if row["source_class"] == class_name]) >= TARGET_COUNTS[class_name]:
                break
            site_selected.add(item["website"])
            selected.append(
                {
                    "sample_id": f"{'js' if class_name.startswith('js') else 'site'}-{_slug(item['supplier_name'])}",
                    "source_class": class_name,
                    "url": item["website"],
                    "query": "printing packaging vietnam",
                    "country_code": "VN",
                    "expected": {
                        "supplier_name": item["supplier_name"],
                        "website": item["website"],
                        "phone": item["phone"],
                        "email": item["email"],
                        "address": item["address"],
                        "city_region": item["city_region"],
                        "category": item["category"],
                        "capabilities": item["capabilities"],
                    },
                    "notes": {"label_source": item["detail_url"], "route_scenario": item.get("route_scenario")},
                }
            )

    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Vietnam supplier parsing evaluation dataset from live YellowPages seeds")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "evaluation" / "supplier_parsing" / "vn_wave1" / "manifest.json"),
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    candidates = _parse_search_cards(session)
    _enrich_from_detail_pages(session, candidates)
    _classify_company_sites(session, candidates)
    samples = _select_samples(candidates)
    payload = {
        "dataset_name": "vn_supplier_parsing_wave1",
        "dataset_version": "2026-04-23",
        "source_note": "Live-labeled Vietnam supplier samples bootstrapped from YellowPages directory pages and corresponding supplier websites.",
        "sample_count": len(samples),
        "samples": samples,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "sample_count": len(samples)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
