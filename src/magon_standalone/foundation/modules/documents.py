# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..file_document_services import FileDocumentService
from ..models import Document, DocumentVersion
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import document_version_view, document_view

router = APIRouter(tags=["Documents"])


class DocumentGeneratePayload(BaseModel):
    owner_type: str
    owner_code: str
    template_key: str = Field(min_length=3)
    title: str | None = None
    visibility_scope: str | None = None
    reason_code: str = Field(min_length=3)
    note: str | None = None


class DocumentActionPayload(BaseModel):
    reason_code: str = Field(min_length=3)
    note: str | None = None


@router.get("/api/v1/operator/document-templates")
def list_document_templates(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    return {"items": FileDocumentService(session).list_document_templates()}


@router.get("/api/v1/operator/documents")
def list_documents(
    owner_type: str | None = None,
    owner_code: str | None = None,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    if owner_type and owner_code:
        owner = service.resolve_owner(owner_type, owner_code)
        items = service.list_documents_for_owner(owner.owner_type, owner.owner_id)
    else:
        items = session.scalars(select(Document).where(Document.deleted_at.is_(None)).order_by(Document.created_at.asc())).all()
    payload = []
    for item in items:
        current_version = session.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == item.id,
                DocumentVersion.version_no == item.current_version_no,
                DocumentVersion.deleted_at.is_(None),
            )
        )
        payload.append(
            document_view(
                item,
                current_version=current_version,
                download_url=f"/platform-api/api/v1/operator/document-versions/{current_version.code}/download" if current_version else None,
            )
        )
    return {"items": payload}


@router.get("/api/v1/operator/documents/{document_code}")
def operator_document_detail(
    document_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        item = service._document_by_code(document_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    versions = service.list_document_versions(item.id)
    current_version = versions[-1] if versions else None
    return {
        "item": document_view(
            item,
            current_version=current_version,
            download_url=f"/platform-api/api/v1/operator/document-versions/{current_version.code}/download" if current_version else None,
        ),
        "versions": [
            document_version_view(version, download_url=f"/platform-api/api/v1/operator/document-versions/{version.code}/download") for version in versions
        ],
    }


@router.post("/api/v1/operator/documents/generate")
def generate_document(
    payload: DocumentGeneratePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    document, document_version, _, _ = service.generate_document(
        owner_type=payload.owner_type,
        owner_code=payload.owner_code,
        template_key=payload.template_key,
        title=payload.title,
        visibility_scope=payload.visibility_scope,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
    )
    return {
        "item": document_view(
            document,
            current_version=document_version,
            download_url=f"/platform-api/api/v1/operator/document-versions/{document_version.code}/download",
        )
    }


@router.post("/api/v1/operator/documents/{document_code}/send")
def send_document(
    document_code: str,
    payload: DocumentActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        document, version = service.transition_document(document_code=document_code, action="send", auth=auth, reason_code=payload.reason_code, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": document_view(document, current_version=version, download_url=f"/platform-api/api/v1/operator/document-versions/{version.code}/download")}


@router.post("/api/v1/operator/documents/{document_code}/confirm")
def confirm_document(
    document_code: str,
    payload: DocumentActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        document, version = service.transition_document(document_code=document_code, action="confirm", auth=auth, reason_code=payload.reason_code, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": document_view(document, current_version=version, download_url=f"/platform-api/api/v1/operator/document-versions/{version.code}/download")}


@router.post("/api/v1/operator/documents/{document_code}/replace")
def replace_document(
    document_code: str,
    payload: DocumentActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        current = service._document_by_code(document_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    owner_code = service.owner_code_for_document(current)
    document, version, _, _ = service.generate_document(
        owner_type=current.owner_type,
        owner_code=owner_code,
        template_key=current.template_key,
        title=current.title,
        visibility_scope=current.visibility_scope,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
        replace_document_code=document_code,
    )
    return {"item": document_view(document, current_version=version, download_url=f"/platform-api/api/v1/operator/document-versions/{version.code}/download")}


@router.get("/api/v1/operator/document-versions/{version_code}/download")
def download_document_version(
    version_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> FileResponse:
    service = FileDocumentService(session)
    path, filename = service.get_operator_download_path(version_code=version_code, document_version=True)
    return FileResponse(path, filename=filename)


@router.get("/api/v1/public/requests/{customer_ref}/documents/{version_code}/download")
def public_download_document_version(customer_ref: str, version_code: str, session: Session = Depends(get_db)) -> FileResponse:
    service = FileDocumentService(session)
    path, filename = service.get_public_download_path(customer_ref=customer_ref, version_code=version_code, document_version=True)
    return FileResponse(path, filename=filename)
