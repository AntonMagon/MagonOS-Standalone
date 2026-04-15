"""Reusable pagination helpers for static and browser-driven listing pages.

Runtime role: Expands directory/listing seeds into bounded page sequences.
Inputs: Current page URL/HTML or a Playwright page plus strategy hints.
Outputs: Ordered page snapshots with canonical URLs.
Does not: parse supplier fields or select scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class StaticPageSnapshot:
    url: str
    html: str


class PaginationController:
    """Handle next-link, numbered, load-more, and infinite-scroll traversal."""

    def collect_static_pages(
        self,
        start_url: str,
        initial_html: str,
        fetch_page,
        *,
        max_pages: int,
        pagination_selector: str | None = None,
    ) -> list[StaticPageSnapshot]:
        pages = [StaticPageSnapshot(url=start_url, html=initial_html)]
        visited = {start_url}
        current_url = start_url
        current_html = initial_html
        while len(pages) < max_pages:
            next_url = self._find_next_static_url(current_url, current_html, pagination_selector)
            if not next_url or next_url in visited:
                break
            visited.add(next_url)
            next_html = fetch_page(next_url)
            pages.append(StaticPageSnapshot(url=next_url, html=next_html))
            current_url, current_html = next_url, next_html
        return pages

    def collect_browser_pages(
        self,
        page,
        *,
        max_pages: int,
        max_scroll_steps: int,
        load_more_selector: str | None = None,
        next_selector: str | None = None,
    ) -> list[dict]:
        pages: list[dict] = [{"url": page.url, "html": page.content()}]
        visited = {page.url}

        if load_more_selector:
            for _index in range(max_pages - 1):
                try:
                    locator = page.locator(load_more_selector)
                    if not locator.count():
                        break
                    locator.first.click(timeout=2_500)
                    page.wait_for_timeout(800)
                    pages.append({"url": page.url, "html": page.content()})
                except Exception:
                    break
            return pages

        if max_scroll_steps:
            for _step in range(max_scroll_steps):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(350)
            pages[0]["html"] = page.content()

        while len(pages) < max_pages:
            try:
                selector = next_selector or "a[rel='next'], a.next, .pagination a.next"
                locator = page.locator(selector)
                if not locator.count():
                    break
                locator.first.click(timeout=2_500)
                page.wait_for_timeout(800)
            except Exception:
                break
            if page.url in visited:
                break
            visited.add(page.url)
            pages.append({"url": page.url, "html": page.content()})
        return pages

    @staticmethod
    def _find_next_static_url(current_url: str, html: str, pagination_selector: str | None = None) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        selector = pagination_selector or "a[rel='next'], a.next, .pagination a.next"
        node = soup.select_one(selector)
        if node and node.get("href"):
            return urljoin(current_url, node["href"])

        numbered_links = []
        for link in soup.select(".pagination a[href]"):
            href = link.get("href", "").strip()
            text = link.get_text(" ", strip=True)
            if href and text.isdigit():
                numbered_links.append(urljoin(current_url, href))
        for candidate in numbered_links:
            if candidate != current_url:
                return candidate
        return None
