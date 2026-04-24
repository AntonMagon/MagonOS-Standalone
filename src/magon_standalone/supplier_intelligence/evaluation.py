"""Live evaluation contour for supplier parsing quality.

Runtime role: Runs one reproducible URL-level parsing pass against labeled
supplier samples and scores extracted fields.
Inputs: Evaluation dataset manifest plus live HTTP/browser parsing runtime.
Outputs: Aggregate quality metrics, per-sample evidence, and scenario/source
breakdowns.
Does not: mutate foundation entities or seed supplier registries.
RU: Этот модуль держит отдельный измеримый quality contour, чтобы parsing принимался по метрикам, а не по smoke/fixture ощущению готовности.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .contracts import PageSeed, RawCompanyRecord
from .normalization_service import BasicNormalizationService
from .scenario_config import ScenarioConfig
from .scenario_profiler import HeuristicPageProfiler
from .scenario_registry import ScenarioRegistry
from .scenario_router import ScenarioDecisionRouter

USER_AGENT = "MagonOSBot/0.2 (+supplier-evaluation)"
FIELD_NAMES = (
    "supplier_name",
    "website",
    "phone",
    "email",
    "address",
    "city_region",
    "category",
    "capabilities",
)


@dataclass(frozen=True)
class FieldScore:
    coverage: bool
    exact_match: bool
    partial_match: bool
    expected: Any
    actual: Any


def load_dataset(dataset_path: str | Path) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


class SupplierParsingEvaluator:
    def __init__(self, config: ScenarioConfig | None = None):
        self._config = config or ScenarioConfig.load()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._profiler = HeuristicPageProfiler()
        self._router = ScenarioDecisionRouter(self._config)
        self._registry = ScenarioRegistry(self._config)

    def evaluate_dataset(
        self,
        dataset: dict[str, Any],
        *,
        evidence_dir: str | Path | None = None,
        sample_ids: set[str] | None = None,
        max_samples: int | None = None,
    ) -> dict[str, Any]:
        selected_samples = []
        for item in dataset.get("samples") or []:
            if sample_ids and item.get("sample_id") not in sample_ids:
                continue
            selected_samples.append(item)
            if max_samples and len(selected_samples) >= max_samples:
                break

        # RU: Summary строится только по реально прогнанным samples, чтобы holdout/canonical subset запускались тем же кодом без ручной постобработки.
        results = [self.evaluate_sample(sample, evidence_dir=evidence_dir) for sample in selected_samples]
        return {
            "dataset_name": dataset.get("dataset_name") or "supplier_parsing_eval",
            "dataset_version": dataset.get("dataset_version") or "",
            "sample_count": len(results),
            "summary": self._summarize(results),
            "samples": results,
        }

    def evaluate_sample(self, sample: dict[str, Any], *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
        seed = self._sample_seed(sample)
        sample_id = str(sample.get("sample_id") or "sample")
        evidence_path = self._evidence_path(sample_id, evidence_dir)
        try:
            response = self._session.get(
                seed["url"],
                timeout=self._config.settings().request_timeout_seconds,
                allow_redirects=True,
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding or "utf-8"
            html = response.text
            status_code = response.status_code
        except Exception as exc:
            result = {
                "sample_id": sample_id,
                "source_class": sample.get("source_class"),
                "url": seed["url"],
                "query": seed["query"],
                "status": "fetch_failed",
                "error": str(exc)[:400],
                "scenario_key": None,
                "pages_visited": 0,
                "record_count": 0,
                "extraction_success": False,
                "field_scores": {},
                "browser_used": False,
                "expected_fields": dict(sample.get("expected") or {}),
                "extracted_fields": {},
                "failed_fields": list(FIELD_NAMES),
                "evidence_path": str(evidence_path) if evidence_path else None,
            }
            self._write_evidence(sample_id, result, evidence_dir)
            return result

        profile = self._profiler.profile(seed, html, status_code=status_code)
        route = self._router.route(seed, profile)
        execution_result = self._registry.execute(route, seed, html)
        matched_record = self._best_record_match(execution_result.records, sample.get("expected") or {})
        field_scores = self._field_scores(matched_record, sample.get("expected") or {})
        extraction_success = bool(
            matched_record
            and field_scores["supplier_name"].partial_match
            and (
                field_scores["website"].partial_match
                or field_scores["phone"].partial_match
                or field_scores["email"].partial_match
            )
        )
        browser_used = bool(
            str(route.get("scenario_key") or "").startswith("JS_")
            or profile.get("browser_required")
            or (route.get("execution_flags") or {}).get("force_render")
        )
        extracted_fields = {
            "supplier_name": actual_or_empty(matched_record, "company_name"),
            "website": actual_or_empty(matched_record, "website"),
            "phone": actual_or_empty(matched_record, "phones"),
            "email": actual_or_empty(matched_record, "emails"),
            "address": actual_or_empty(matched_record, "address_text"),
            "city_region": actual_or_empty(matched_record, "city") or actual_or_empty(matched_record, "region"),
            "category": actual_or_empty(matched_record, "categories"),
            "capabilities": _record_capabilities(matched_record or {}),
        }
        failed_fields = [
            field_name
            for field_name, score in field_scores.items()
            if _expected_present(score.expected) and not score.exact_match
        ]
        result = {
            "sample_id": sample_id,
            "source_class": sample.get("source_class"),
            "url": seed["url"],
            "query": seed["query"],
            "status": "ok",
            "http_status_code": status_code,
            "scenario_key": route.get("scenario_key"),
            "route_reasons": list(route.get("reasons") or []),
            "scenario_confidence": route.get("confidence"),
            "page_profile": profile,
            "pages_visited": execution_result.pages_visited,
            "block_detected": execution_result.block_detected,
            "record_count": len(execution_result.records),
            "extraction_success": extraction_success,
            "browser_used": browser_used,
            "expected_fields": dict(sample.get("expected") or {}),
            "extracted_fields": extracted_fields,
            "failed_fields": failed_fields,
            "evidence_path": str(evidence_path) if evidence_path else None,
            "matched_record": matched_record,
            "field_scores": {
                key: {
                    "coverage": value.coverage,
                    "exact_match": value.exact_match,
                    "partial_match": value.partial_match,
                    "expected": value.expected,
                    "actual": value.actual,
                }
                for key, value in field_scores.items()
            },
        }
        self._write_evidence(sample_id, result, evidence_dir)
        return result

    def _sample_seed(self, sample: dict[str, Any]) -> PageSeed:
        source_class = str(sample.get("source_class") or "simple_supplier_site")
        url = str(sample.get("url") or "")
        return {
            "url": url,
            "query": str(sample.get("query") or "printing packaging vietnam"),
            "country_code": str(sample.get("country_code") or "VN"),
            "source_type": "directory" if source_class == "directory_listing" else "company_site",
            "source_domain": urlparse(url).netloc.replace("www.", "").lower(),
            "page_type_hint": "directory" if source_class == "directory_listing" else "company_site",
            "metadata": {"sample_id": sample.get("sample_id"), "source_class": source_class},
        }

    def _best_record_match(self, records: list[RawCompanyRecord], expected: dict[str, Any]) -> dict[str, Any] | None:
        if not records:
            return None
        scored = sorted(
            ((self._record_match_score(item, expected), item) for item in records),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return dict(scored[0][1])

    def _record_match_score(self, record: RawCompanyRecord, expected: dict[str, Any]) -> float:
        website_score = 1.0 if _normalize_domain(expected.get("website")) == _normalize_domain(record.get("website") or record.get("source_url")) else 0.0
        phone_score = 1.0 if _phones_match(expected.get("phone"), record) else 0.0
        email_score = 1.0 if _emails_match(expected.get("email"), record) else 0.0
        name_score = _similarity(expected.get("supplier_name"), record.get("company_name"))
        address_score = _similarity(expected.get("address"), record.get("address_text"))
        return (
            3.0 * website_score
            + 2.0 * phone_score
            + 2.0 * email_score
            + 2.5 * name_score
            + 1.5 * address_score
        )

    def _field_scores(self, record: dict[str, Any] | None, expected: dict[str, Any]) -> dict[str, FieldScore]:
        actual = record or {}
        actual_capabilities = _record_capabilities(actual)
        expected_capabilities = _normalize_capability_values(expected.get("capabilities"))
        expected_category_values = _normalize_capability_values([expected.get("category")]) if expected.get("category") else []
        expected_category = expected_category_values[0] if expected_category_values else ""
        scores = {
            "supplier_name": _normalized_string_score(
                expected.get("supplier_name"),
                actual.get("company_name"),
                normalizer=_normalize_company_name_text,
                partial_threshold=0.5,
            ),
            "website": _website_score(expected.get("website"), actual.get("website") or actual.get("source_url")),
            "phone": _phone_score(expected.get("phone"), actual),
            "email": _email_score(expected.get("email"), actual),
            "address": _normalized_string_score(
                expected.get("address"),
                actual.get("address_text"),
                normalizer=_normalize_address_text,
                partial_threshold=0.65,
            ),
            "city_region": _string_score(expected.get("city_region"), actual.get("city") or actual.get("region"), partial_threshold=0.8),
            "category": _capability_score(expected_category, actual_capabilities),
            "capabilities": _capability_list_score(expected_capabilities, actual_capabilities),
        }
        return scores

    def _summarize(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        field_metrics: dict[str, dict[str, float | int]] = {}
        for field_name in FIELD_NAMES:
            field_entries = [item.get("field_scores", {}).get(field_name) or {} for item in results]
            available_entries = [item for item in field_entries if _expected_present(item.get("expected"))]
            coverage_count = sum(1 for item in available_entries if item.get("coverage"))
            exact_count = sum(1 for item in available_entries if item.get("exact_match"))
            partial_count = sum(1 for item in available_entries if item.get("partial_match"))
            total = len(available_entries) or 1
            field_metrics[field_name] = {
                "available_count": len(available_entries),
                "coverage_count": coverage_count,
                "exact_match_count": exact_count,
                "partial_match_count": partial_count,
                "coverage_rate": round(coverage_count / total, 4),
                "exact_match_rate": round(exact_count / total, 4),
                "partial_match_rate": round(partial_count / total, 4),
            }

        extraction_success_count = sum(1 for item in results if item.get("extraction_success"))
        breakdowns = {
            "source_class_breakdown": _breakdown(results, "source_class"),
            "scenario_breakdown": _breakdown(results, "scenario_key"),
            "company_site_breakdown": _company_site_breakdown(results),
        }
        return {
            "extraction_success_count": extraction_success_count,
            "extraction_success_rate": round(extraction_success_count / (len(results) or 1), 4),
            "field_metrics": field_metrics,
            "failed_samples": _failed_samples(results),
            "failed_samples_by_class": _failed_samples_by_class(results),
            **breakdowns,
        }

    @staticmethod
    def _write_evidence(sample_id: str, payload: dict[str, Any], evidence_dir: str | Path | None) -> None:
        target_path = SupplierParsingEvaluator._evidence_path(sample_id, evidence_dir)
        if not target_path:
            return
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _evidence_path(sample_id: str, evidence_dir: str | Path | None) -> Path | None:
        if not evidence_dir:
            return None
        target_dir = Path(evidence_dir)
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", sample_id)
        return target_dir / f"{safe_id}.json"


def _breakdown(results: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        group_key = str(item.get(key) or "unknown")
        groups.setdefault(group_key, []).append(item)
    return {
        name: {
            "sample_count": len(items),
            "extraction_success_count": sum(1 for item in items if item.get("extraction_success")),
            "extraction_success_rate": round(
                sum(1 for item in items if item.get("extraction_success")) / (len(items) or 1),
                4,
            ),
        }
        for name, items in sorted(groups.items())
    }


def _company_site_breakdown(results: list[dict[str, Any]]) -> dict[str, Any]:
    scoped = [item for item in results if item.get("scenario_key") in {"COMPANY_SITE", "JS_COMPANY_SITE"}]
    return {
        "sample_count": len(scoped),
        "extraction_success_count": sum(1 for item in scoped if item.get("extraction_success")),
        "extraction_success_rate": round(
            sum(1 for item in scoped if item.get("extraction_success")) / (len(scoped) or 1),
            4,
        ),
        "failed_samples": _failed_samples(scoped),
    }


def _failed_samples(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    for item in results:
        failed_fields = list(item.get("failed_fields") or [])
        if item.get("extraction_success") and not failed_fields:
            continue
        failed.append(
            {
                "sample_id": item.get("sample_id"),
                "source_class": item.get("source_class"),
                "scenario_key": item.get("scenario_key"),
                "browser_used": bool(item.get("browser_used")),
                "failed_fields": failed_fields,
                "extraction_success": bool(item.get("extraction_success")),
                "evidence_path": item.get("evidence_path"),
            }
        )
    return failed


def _failed_samples_by_class(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in _failed_samples(results):
        grouped.setdefault(str(item.get("source_class") or "unknown"), []).append(item)
    return grouped


def actual_or_empty(record: dict[str, Any] | None, key: str) -> Any:
    if not record:
        return [] if key in {"phones", "emails", "categories"} else ""
    return record.get(key) or ([] if key in {"phones", "emails", "categories"} else "")


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _expected_present(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    return bool(_normalize_text(value))


def _normalize_tokens(value: Any) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalize_text(value).lower()) if token}


def _ascii_text(value: Any) -> str:
    raw = str(value or "").replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", raw)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_company_name_text(value: Any) -> str:
    raw = re.sub(r"\s+", " ", _ascii_text(value).lower()).strip()
    raw = re.sub(r"^(?:lien he(?: footer)?|gioi thieu|tru so chinh|chi nhanh(?:\s+\w+)?|kinh chao quy khach!?|san pham|ve)\s*-\s*", "", raw)
    parts = [item.strip(" -|,:") for item in re.split(r"\s*-\s*", raw) if item.strip(" -|,:")]
    legal_parts = [item for item in parts if any(token in item for token in ("cong ty", "tnhh", "trach nhiem huu han", "co phan", "company", "jsc", "cp"))]
    if legal_parts:
        raw = legal_parts[0]
    raw = re.split(r"\b(?:dia chi|hotline|email|website|mst|ma so thue|dien thoai|phone|gpkd|van phong|vp|xuong san xuat|xuong|tuyen dung)\b", raw, maxsplit=1)[0]
    raw = re.sub(r"\btrach nhiem huu han\b", "tnhh", raw)
    raw = re.sub(r"\bco phan\b", "cp", raw)
    raw = re.sub(r"\bthuong mai\b", "tm", raw)
    raw = re.sub(r"\bdich vu\b", "dv", raw)
    raw = re.sub(r"\bsan xuat\b", "sx", raw)
    raw = re.sub(r"\([^)]*\)", "", raw)
    return re.sub(r"[^a-z0-9]+", " ", raw).strip()


def _normalize_address_text(value: Any) -> str:
    raw = re.sub(r"\s+", " ", _ascii_text(value).lower()).strip()
    raw = re.split(r"\b(?:lh|lien he|gui|hotline|email|website|sdt|dien thoai|phone|copyright|all rights reserved)\b", raw, maxsplit=1)[0]
    raw = re.sub(r"\((?:tphcm|tp hcm|tp ho chi minh|cong lo cu|so cu\s*\d+)\)", " ", raw)
    for pattern, replacement in (
        (r"\btphcm\b", "tp ho chi minh"),
        (r"\btp\.?\s*hcm\b", "tp ho chi minh"),
        (r"\btp\.?\s*ho\s*chi\s*minh\b", "tp ho chi minh"),
        (r"\bthanh pho\b", "tp"),
        (r"(^|[\s,(])p\.\s*(?=[a-z0-9])", r"\1phuong "),
        (r"(^|[\s,(])q\.\s*(?=[a-z0-9])", r"\1quan "),
        (r"(^|[\s,(])kp\.\s*(?=[a-z0-9])", r"\1khu pho "),
        (r"(^|[\s,(])đ\.\s*(?=[a-z0-9])", r"\1duong "),
        (r"\bkcn\b", "khu cong nghiep"),
    ):
        raw = re.sub(pattern, replacement, raw)
    raw = re.sub(r"\bq(?=\d)", "quan ", raw)
    raw = re.sub(r"\bp(?=\d)", "phuong ", raw)
    candidates: list[str] = []
    for match in re.finditer(r"(?:lo|to|so|\d{1,5}[/-]?[a-z0-9]*|duong|khu pho|khu cong nghiep)", raw):
        candidate = raw[match.start() : match.start() + 240]
        if any(token in candidate for token in ("quan", "phuong", "tp", "binh duong", "dong nai", "ha noi", "da nang", "nghe an", "bien hoa", "thu dau mot")):
            candidates.append(candidate)
    if candidates:
        raw = max(candidates, key=len)
    tokens = [token for token in re.split(r"[^a-z0-9]+", raw) if token]
    normalized_tokens: list[str] = []
    skip_next = 0
    for index, token in enumerate(tokens):
        if skip_next:
            skip_next -= 1
            continue
        if token == "khu" and index + 1 < len(tokens) and tokens[index + 1] == "pho":
            skip_next = 1
            continue
        if token == "so" and index + 1 < len(tokens) and tokens[index + 1] == "cu":
            skip_next = 1
            continue
        if token in {"phuong", "quan", "tp", "tinh", "so", "lo", "to", "duong"}:
            continue
        normalized_tokens.append(token)
    return " ".join(normalized_tokens).strip()


def _similarity(left: Any, right: Any) -> float:
    left_tokens = _normalize_tokens(left)
    right_tokens = _normalize_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens.intersection(right_tokens)) / max(len(left_tokens), len(right_tokens))


def _normalize_domain(value: Any) -> str:
    raw = _normalize_text(value).lower()
    if not raw:
        return ""
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    return urlparse(raw).netloc.replace("www.", "").strip().lower()


def _normalize_phone(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("84"):
        return digits
    if digits.startswith("0"):
        return f"84{digits[1:]}"
    return digits


def _normalize_email(value: Any) -> str:
    return _normalize_text(value).lower()


def _website_score(expected: Any, actual: Any) -> FieldScore:
    expected_domain = _normalize_domain(expected)
    actual_domain = _normalize_domain(actual)
    return FieldScore(
        coverage=bool(actual_domain),
        exact_match=bool(expected_domain and expected_domain == actual_domain),
        partial_match=bool(expected_domain and expected_domain == actual_domain),
        expected=expected_domain,
        actual=actual_domain,
    )


def _string_score(expected: Any, actual: Any, *, partial_threshold: float = 0.75) -> FieldScore:
    expected_value = _normalize_text(expected)
    actual_value = _normalize_text(actual)
    similarity = _similarity(expected_value, actual_value)
    return FieldScore(
        coverage=bool(actual_value),
        exact_match=bool(expected_value and expected_value.lower() == actual_value.lower()),
        partial_match=bool(expected_value and similarity >= partial_threshold),
        expected=expected_value,
        actual=actual_value,
    )


def _normalized_string_score(expected: Any, actual: Any, *, normalizer, partial_threshold: float = 0.75) -> FieldScore:
    expected_value = _normalize_text(expected)
    actual_value = _normalize_text(actual)
    canonical_expected = normalizer(expected_value)
    canonical_actual = normalizer(actual_value)
    similarity = _similarity(canonical_expected, canonical_actual)
    return FieldScore(
        coverage=bool(actual_value),
        exact_match=bool(canonical_expected and canonical_expected == canonical_actual),
        partial_match=bool(canonical_expected and similarity >= partial_threshold),
        expected=expected_value,
        actual=actual_value,
    )


def _phone_score(expected: Any, actual_record: dict[str, Any]) -> FieldScore:
    expected_phone = _normalize_phone(expected)
    actual_values = [_normalize_phone(actual_record.get("phone"))] + [_normalize_phone(item) for item in actual_record.get("phones") or []]
    actual_values = [item for item in actual_values if item]
    exact = bool(expected_phone and expected_phone in actual_values)
    partial = exact or bool(expected_phone and any(item.endswith(expected_phone[-8:]) for item in actual_values if len(expected_phone) >= 8))
    return FieldScore(
        coverage=bool(actual_values),
        exact_match=exact,
        partial_match=partial,
        expected=expected_phone,
        actual=actual_values,
    )


def _email_score(expected: Any, actual_record: dict[str, Any]) -> FieldScore:
    expected_email = _normalize_email(expected)
    actual_values = [_normalize_email(actual_record.get("email"))] + [_normalize_email(item) for item in actual_record.get("emails") or []]
    actual_values = [item for item in actual_values if item]
    exact = bool(expected_email and expected_email in actual_values)
    partial = exact or bool(
        expected_email
        and any(item.split("@")[-1] == expected_email.split("@")[-1] for item in actual_values if "@" in item and "@" in expected_email)
    )
    return FieldScore(
        coverage=bool(actual_values),
        exact_match=exact,
        partial_match=partial,
        expected=expected_email,
        actual=actual_values,
    )


def _phones_match(expected: Any, record: dict[str, Any]) -> bool:
    return _phone_score(expected, record).partial_match


def _emails_match(expected: Any, record: dict[str, Any]) -> bool:
    return _email_score(expected, record).partial_match


def _normalize_capability_values(values: Any) -> list[str]:
    records: list[str] = []
    if isinstance(values, str):
        source_values = [values]
    else:
        source_values = list(values or [])
    for item in source_values:
        tokens = BasicNormalizationService._extract_capabilities(  # type: ignore[attr-defined]
            {
                "capabilities_text": _normalize_text(item),
                "labels": [_normalize_text(item)],
                "categories": [_normalize_text(item)],
                "services": [_normalize_text(item)],
                "products": [_normalize_text(item)],
            }
        )
        for token in tokens:
            if token not in records:
                records.append(token)
    return records


def _record_capabilities(record: dict[str, Any]) -> list[str]:
    merged = _normalize_capability_values(record.get("categories") or [])
    for key in ("labels", "services", "products"):
        for token in _normalize_capability_values(record.get(key) or []):
            if token not in merged:
                merged.append(token)
    for token in _normalize_capability_values(record.get("capabilities_text") or ""):
        if token not in merged:
            merged.append(token)
    return merged


def _capability_score(expected_category: str, actual_capabilities: list[str]) -> FieldScore:
    return FieldScore(
        coverage=bool(actual_capabilities),
        exact_match=bool(expected_category and expected_category in actual_capabilities),
        partial_match=bool(expected_category and expected_category in actual_capabilities),
        expected=expected_category,
        actual=actual_capabilities,
    )


def _capability_list_score(expected_capabilities: list[str], actual_capabilities: list[str]) -> FieldScore:
    expected_set = set(expected_capabilities)
    actual_set = set(actual_capabilities)
    intersection = sorted(expected_set.intersection(actual_set))
    return FieldScore(
        coverage=bool(actual_set),
        exact_match=bool(expected_set and expected_set.issubset(actual_set)),
        partial_match=bool(intersection),
        expected=sorted(expected_set),
        actual=sorted(actual_set),
    )
