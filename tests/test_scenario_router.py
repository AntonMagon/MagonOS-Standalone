from __future__ import annotations

import unittest

from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig
from magon_standalone.supplier_intelligence.scenario_router import ScenarioDecisionRouter


class TestScenarioDecisionRouter(unittest.TestCase):
    # RU: Эти тесты фиксируют, что supplier-owned company site уходит в browser-aware сценарий, когда router видит render-required профиль или force_render override.
    def test_company_site_with_browser_requirement_routes_to_js_company_site(self) -> None:
        router = ScenarioDecisionRouter(ScenarioConfig(defaults={}, domain_overrides={}))

        route = router.route(
            {"url": "https://example.com", "source_domain": "example.com", "page_type_hint": "company_site"},
            {
                "source_domain": "example.com",
                "page_type": "company_site",
                "browser_required": True,
                "profile_confidence": 0.8,
            },
        )

        self.assertEqual(route["scenario_key"], "JS_COMPANY_SITE")
        self.assertIn("AI_ASSISTED_EXTRACTION", route["escalation_policy"])

    def test_company_site_force_render_override_routes_to_js_company_site(self) -> None:
        router = ScenarioDecisionRouter(
            ScenarioConfig(
                defaults={},
                domain_overrides={"example.com": {"force_render": True}},
            )
        )

        route = router.route(
            {"url": "https://example.com", "source_domain": "example.com", "page_type_hint": "company_site"},
            {
                "source_domain": "example.com",
                "page_type": "company_site",
                "browser_required": False,
                "profile_confidence": 0.6,
            },
        )

        self.assertEqual(route["scenario_key"], "JS_COMPANY_SITE")


if __name__ == "__main__":
    unittest.main()
