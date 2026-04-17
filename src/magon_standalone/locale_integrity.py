from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path


RU_SOURCE_FILES = (
    "apps/web/messages/ru.json",
    "docs/ru/current-project-state.md",
    "docs/ru/visuals/project-map.md",
    "docs/ru/visuals/project-map.json",
)

RU_RUNTIME_ROUTES = (
    "/",
    "/dashboard",
    "/ops-workbench",
    "/project-map",
)

FORBIDDEN_RU_LEAKS = (
    "company",
    "commercial/customer context",
    "opportunity",
    "quote intent / rfq boundary",
    "supplier intelligence pipeline",
    "review queue",
    "routing / qualification decisions",
    "feedback ledger / projection",
    "workforce estimation",
    "customer/account identity",
    "opportunity/lead ownership",
    "rfq / quote boundary",
    "automations",
)

DISCOURAGED_RU_COPY = (
    "automation loops",
    "verified changes",
    "scope guard",
    "worklog",
    "technical log",
    "project-memory dump",
    "runtime/dashboard",
)


def detect_forbidden_leaks(text: str, forbidden_terms: tuple[str, ...] = FORBIDDEN_RU_LEAKS) -> list[str]:
    lowered = text.casefold()
    matches = [term for term in forbidden_terms if term in lowered]
    return sorted(set(matches))


def detect_discouraged_copy(text: str, discouraged_terms: tuple[str, ...] = DISCOURAGED_RU_COPY) -> list[str]:
    lowered = text.casefold()
    # RU: Здесь режем не только чистые английские утечки, но и кривые полуинженерные формулировки, которые не должны попадать в русский docs/UI слой.
    matches = [term for term in discouraged_terms if term in lowered]
    return sorted(set(matches))


def _iter_string_values(payload: object) -> list[str]:
    if isinstance(payload, dict):
        values: list[str] = []
        for value in payload.values():
            values.extend(_iter_string_values(value))
        return values
    if isinstance(payload, list):
        values: list[str] = []
        for item in payload:
            values.extend(_iter_string_values(item))
        return values
    if isinstance(payload, str):
        return [payload]
    return []


def extract_visible_text(html_text: str) -> str:
    without_scripts = re.sub(r"<script\b[^>]*>.*?</script>", " ", html_text, flags=re.I | re.S)
    without_styles = re.sub(r"<style\b[^>]*>.*?</style>", " ", without_scripts, flags=re.I | re.S)
    without_tags = re.sub(r"<[^>]+>", " ", without_styles)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def source_text_for_scan(relative_path: str, text: str) -> str:
    if relative_path == "apps/web/messages/ru.json":
        return "\n".join(_iter_string_values(json.loads(text)))
    if relative_path == "docs/ru/visuals/project-map.json":
        payload = json.loads(text)
        allowed_blocks = (
            payload.get("validated_contour_ru", []),
            payload.get("owned_capabilities_ru", []),
            payload.get("danger_overlap_ru", []),
            payload.get("out_of_scope_ru", []),
        )
        return "\n".join(item for block in allowed_blocks for item in block if isinstance(item, str))
    if relative_path == "docs/ru/visuals/project-map.md":
        # RU: В markdown-карте проверяем только реальный русскоязычный контур, а не mermaid ids и не автоматом подставленные worklog-значения из project memory.
        # RU: Mermaid и automated context values не считаем user-facing русским источником, иначе guard будет путать node ids и worklog-строки с реальной локализацией.
        without_code = re.sub(r"```.*?```", " ", text, flags=re.S)
        visible_part = without_code.split("## Активный контекст", 1)[0]
        return visible_part
    return text


def scan_source_files(repo_root: Path, relative_paths: tuple[str, ...] = RU_SOURCE_FILES) -> list[str]:
    issues: list[str] = []
    for relative_path in relative_paths:
        path = repo_root / relative_path
        text = source_text_for_scan(relative_path, path.read_text(encoding="utf-8"))
        matches = detect_forbidden_leaks(text)
        for match in matches:
            issues.append(f"{relative_path}: forbidden English locale leak `{match}`")
        discouraged = detect_discouraged_copy(text)
        for match in discouraged:
            issues.append(f"{relative_path}: discouraged Russian copy phrase `{match}`")
    return issues


def fetch_visible_text(url: str, timeout_seconds: int = 20) -> str:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return extract_visible_text(payload)


def scan_runtime_routes(
    base_url: str,
    routes: tuple[str, ...] = RU_RUNTIME_ROUTES,
    fetcher=fetch_visible_text,
) -> list[str]:
    issues: list[str] = []
    normalized_base = base_url.rstrip("/")
    for route in routes:
        url = f"{normalized_base}{route}"
        visible_text = fetcher(url)
        matches = detect_forbidden_leaks(visible_text)
        for match in matches:
            issues.append(f"{url}: forbidden English locale leak `{match}`")
        discouraged = detect_discouraged_copy(visible_text)
        for match in discouraged:
            issues.append(f"{url}: discouraged Russian copy phrase `{match}`")
    return issues


def dump_source_snapshot(repo_root: Path) -> str:
    payload = {}
    for relative_path in RU_SOURCE_FILES:
        path = repo_root / relative_path
        if path.suffix == ".json":
            payload[relative_path] = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload[relative_path] = path.read_text(encoding="utf-8")
    return json.dumps(payload, ensure_ascii=False, indent=2)
