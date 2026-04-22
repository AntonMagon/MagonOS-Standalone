# RU: LLM adapter первой волны держим в integrations-слое, чтобы supplier parsing не тащил vendor-specific код прямо в доменный сервис.
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .base import IntegrationResult


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _limit(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


@dataclass(slots=True)
class LlmExtractionPreview:
    adapter: str
    model: str
    raw_text: str
    parsed_json: dict[str, Any]


class OpenAILlmAdapter:
    adapter_name = "openai_responses"

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_input_chars: int | None = None,
    ):
        self.enabled = enabled if enabled is not None else os.getenv("MAGON_FOUNDATION_LLM_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model if model is not None else os.getenv("MAGON_FOUNDATION_LLM_MODEL", "gpt-5.2")
        self.base_url = base_url if base_url is not None else os.getenv("MAGON_FOUNDATION_LLM_BASE_URL", "")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else float(os.getenv("MAGON_FOUNDATION_LLM_TIMEOUT_SECONDS", "20"))
        self.max_input_chars = max_input_chars if max_input_chars is not None else int(os.getenv("MAGON_FOUNDATION_LLM_MAX_INPUT_CHARS", "12000"))

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.api_key and self.model)

    def health(self) -> IntegrationResult:
        if not self.enabled:
            return IntegrationResult(ok=False, adapter=self.adapter_name, detail="llm_disabled", payload={"enabled": False, "configured": False, "model": self.model})
        if not self.api_key:
            return IntegrationResult(ok=False, adapter=self.adapter_name, detail="missing_openai_api_key", payload={"enabled": True, "configured": False, "model": self.model})
        return IntegrationResult(
            ok=True,
            adapter=self.adapter_name,
            detail="llm_ready",
            payload={
                "enabled": True,
                "configured": True,
                "model": self.model,
                "base_url": self.base_url or "https://api.openai.com/v1",
                "timeout_seconds": self.timeout_seconds,
                "max_input_chars": self.max_input_chars,
            },
        )

    def extract_supplier_preview(self, *, page_url: str, query: str, text_blob: str) -> LlmExtractionPreview:
        if not self.configured:
            raise RuntimeError("llm_not_configured")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None, timeout=self.timeout_seconds)
        compact_blob = _limit(_clean(text_blob), self.max_input_chars)
        instructions = (
            "You extract supplier facts for a print and packaging sourcing operator. "
            "Return one compact JSON object only. "
            "Use keys: company_name, website, address_text, city, country, phones, emails, "
            "categories, services, products, contact_persons, confidence, explanation. "
            "Do not invent data; use empty arrays or empty strings when the source is weak."
        )
        input_text = (
            f"query: {query}\n"
            f"page_url: {page_url}\n"
            "source_text:\n"
            f"{compact_blob}"
        )
        response = client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_text,
        )
        raw_text = _clean(getattr(response, "output_text", ""))
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError("llm_response_not_object")
        return LlmExtractionPreview(adapter=self.adapter_name, model=self.model, raw_text=raw_text, parsed_json=parsed)


def get_llm_adapter() -> OpenAILlmAdapter:
    return OpenAILlmAdapter()
