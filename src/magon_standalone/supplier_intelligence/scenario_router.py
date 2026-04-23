"""Scenario routing for page/profile-specific supplier extraction.

Runtime role: Chooses the concrete execution scenario from profiler signals and
domain overrides.
Inputs: Page seed, page profile, scenario config.
Outputs: ScenarioRouteDecision with explicit reasons and escalation policy.
Does not: fetch pages or parse supplier fields.
"""
from __future__ import annotations

from .contracts import PageProfile, PageSeed, ScenarioRouteDecision
from .scenario_config import ScenarioConfig


class ScenarioDecisionRouter:
    """Route one page into the cheapest viable scenario with explicit fallbacks."""

    def __init__(self, config: ScenarioConfig):
        self._config = config

    def route(self, seed: PageSeed, profile: PageProfile) -> ScenarioRouteDecision:
        domain_override = self._config.domain_override(profile.get("source_domain", ""))
        reasons: list[str] = []
        scenario_key = domain_override.get("forced_scenario")
        execution_flags = {
            "force_render": bool(domain_override.get("force_render")),
            "pagination_selector": domain_override.get("pagination_selector"),
            "load_more_selector": domain_override.get("load_more_selector"),
            "popup_selectors": domain_override.get("popup_selectors", []),
            "allow_paths": domain_override.get("allow_paths", []),
            "deny_paths": domain_override.get("deny_paths", []),
            "throttle_seconds": float(domain_override.get("request_delay_seconds", self._config.settings().request_delay_seconds)),
        }

        if scenario_key:
            reasons.append("domain override forced scenario")
        elif float(profile.get("anti_bot_likelihood") or 0.0) >= self._config.settings().anti_bot_threshold:
            scenario_key = "HARD_DYNAMIC_OR_BLOCKED"
            reasons.append("anti-bot or challenge signals exceed threshold")
        elif profile.get("page_type") == "company_site" and (
            profile.get("browser_required") or execution_flags["force_render"]
        ):
            # RU: Если supplier-owned сайт уже профилируется как JS-heavy, его нельзя гнать через plain requests-only executor — иначе теряем рендеренные contact/about blocks.
            scenario_key = "JS_COMPANY_SITE"
            reasons.append("company site requires rendered execution")
        elif profile.get("page_type") == "company_site":
            scenario_key = "COMPANY_SITE"
            reasons.append("page profile classified supplier-owned website")
        elif profile.get("page_type") == "directory" and (
            profile.get("browser_required") or execution_flags["force_render"]
        ):
            scenario_key = "JS_DIRECTORY"
            reasons.append("directory page requires rendered execution")
        elif profile.get("page_type") == "directory":
            scenario_key = "SIMPLE_DIRECTORY"
            reasons.append("directory page can be parsed via plain HTML")
        else:
            scenario_key = "HARD_DYNAMIC_OR_BLOCKED" if profile.get("browser_required") else "COMPANY_SITE"
            reasons.append("fallback route from mixed/unknown profile")

        escalation_policy = []
        if scenario_key in {"SIMPLE_DIRECTORY", "JS_DIRECTORY", "COMPANY_SITE", "JS_COMPANY_SITE"}:
            escalation_policy.append("AI_ASSISTED_EXTRACTION")
        if scenario_key != "HARD_DYNAMIC_OR_BLOCKED" and profile.get("browser_required"):
            escalation_policy.append("HARD_DYNAMIC_OR_BLOCKED")

        confidence = 0.55
        if reasons:
            confidence += 0.1
        confidence += float(profile.get("profile_confidence") or 0.0) * 0.3
        confidence = min(confidence, 0.97)
        return {
            "scenario_key": scenario_key,
            "reasons": reasons,
            "execution_flags": execution_flags,
            "escalation_policy": escalation_policy,
            "confidence": round(confidence, 4),
        }
