# RU: Этот модуль даёт оператору только explainable status/test path для LLM и не превращает первую волну в "AI-first" runtime.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..dependencies import get_container, require_roles, FoundationContainer
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from ...integrations.foundation.llm import get_llm_adapter

router = APIRouter(tags=["LLM"])


class LlmPreviewPayload(BaseModel):
    page_url: str = Field(min_length=3)
    query: str = Field(min_length=2)
    text_blob: str = Field(min_length=20)


@router.get("/api/v1/operator/llm/status")
def llm_status(
    _: AuthContext = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
    container: FoundationContainer = Depends(get_container),
) -> dict[str, object]:
    adapter = get_llm_adapter()
    health = adapter.health()
    return {
        "enabled": container.settings.llm_enabled,
        "provider": container.settings.llm_provider,
        "model": container.settings.llm_model,
        "configured": adapter.configured,
        "health": {
            "ok": health.ok,
            "adapter": health.adapter,
            "detail": health.detail,
            "payload": health.payload or {},
        },
    }


@router.post("/api/v1/operator/llm/extract-preview")
def llm_extract_preview(
    payload: LlmPreviewPayload,
    _: AuthContext = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
) -> dict[str, object]:
    adapter = get_llm_adapter()
    if not adapter.configured:
        raise HTTPException(status_code=409, detail="llm_not_configured")
    preview = adapter.extract_supplier_preview(
        page_url=payload.page_url,
        query=payload.query,
        text_blob=payload.text_blob,
    )
    return {
        "adapter": preview.adapter,
        "model": preview.model,
        "raw_text": preview.raw_text,
        "parsed_json": preview.parsed_json,
    }
