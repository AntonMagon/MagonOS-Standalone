"""Popup and overlay suppression for browser-driven supplier discovery.

Runtime role: Clears blocking consent/newsletter/chat overlays before
extraction runs on rendered pages.
Inputs: Playwright page object plus optional override selectors.
Outputs: Event log entries describing what was dismissed or hidden.
Does not: navigate pages or persist debug artifacts.
"""
from __future__ import annotations


DEFAULT_DISMISS_SELECTORS = (
    "button:has-text('Accept')",
    "button:has-text('I agree')",
    "button:has-text('OK')",
    "button:has-text('Close')",
    "[aria-label='Close']",
    ".cookie-accept",
    ".cookie-consent-accept",
    ".newsletter-popup .close",
    ".modal .close",
)


class PopupOverlayController:
    """Dismiss common overlays and hide sticky blockers on rendered pages."""

    def handle(self, page, selectors: list[str] | None = None) -> list[str]:
        event_log: list[str] = []
        for selector in selectors or list(DEFAULT_DISMISS_SELECTORS):
            try:
                locator = page.locator(selector)
                if locator.count():
                    locator.first.click(timeout=1500)
                    page.wait_for_timeout(200)
                    event_log.append(f"popup_clicked:{selector}")
            except Exception:
                continue
        try:
            page.evaluate(
                """
                () => {
                    for (const selector of ['.chat-widget', '.intercom-lightweight-app', '.sticky-banner', '.cookie-banner']) {
                        for (const node of document.querySelectorAll(selector)) {
                            node.style.display = 'none';
                        }
                    }
                }
                """
            )
            event_log.append("popup_hidden:generic_overlays")
        except Exception:
            pass
        return event_log
