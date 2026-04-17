# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..file_document_services import FileDocumentService
from ..models import FileAsset, FileVersion
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import file_asset_view, file_check_view, file_version_view

router = APIRouter(tags=["FilesMedia"])


class FileReviewPayload(BaseModel):
    target_state: str
    reason_code: str = Field(min_length=3)
    note: str | None = None


class FileFinalizePayload(BaseModel):
    reason_code: str = Field(min_length=3)
    note: str | None = None


@router.get("/api/v1/operator/files")
def list_files(
    owner_type: str | None = None,
    owner_code: str | None = None,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    if owner_type and owner_code:
        owner = service.resolve_owner(owner_type, owner_code)
        items = service.list_files_for_owner(owner.owner_type, owner.owner_id)
    else:
        items = session.scalars(
            select(FileAsset).where(FileAsset.deleted_at.is_(None), FileAsset.archived_at.is_(None)).order_by(FileAsset.created_at.asc())
        ).all()
    payload = []
    for item in items:
        latest_version = session.scalar(select(FileVersion).where(FileVersion.id == item.latest_version_id)) if item.latest_version_id else None
        checks = service.list_file_checks(latest_version.id) if latest_version else []
        payload.append(file_asset_view(item, latest_version=latest_version, checks=checks))
    return {"items": payload}


@router.get("/api/v1/operator/files/{asset_code}")
def operator_file_detail(
    asset_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        asset = service._file_asset_by_code(asset_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    versions = service.list_file_versions(asset.id)
    latest_version = versions[-1] if versions else None
    checks = service.list_file_checks(latest_version.id) if latest_version else []
    return {
        "item": file_asset_view(asset, latest_version=latest_version, checks=checks, download_url=f"/platform-api/api/v1/operator/file-versions/{latest_version.code}/download" if latest_version else None),
        "versions": [file_version_view(item) for item in versions],
        "checks": [file_check_view(item) for item in checks],
    }


@router.post("/api/v1/operator/files/upload")
async def upload_file(
    owner_type: str = Form(...),
    owner_code: str = Form(...),
    file_type: str = Form("attachment"),
    visibility_scope: str = Form("internal"),
    reason_code: str = Form(...),
    note: str | None = Form(default=None),
    upload: UploadFile = File(...),
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    content = await upload.read()
    asset, version, checks = service.upload_file_asset(
        owner_type=owner_type,
        owner_code=owner_code,
        filename=upload.filename or "upload.bin",
        content=content,
        mime_type=upload.content_type or "application/octet-stream",
        file_type=file_type,
        visibility_scope=visibility_scope,
        auth=auth,
        reason_code=reason_code,
        note=note,
    )
    return {"item": file_asset_view(asset, latest_version=version, checks=checks)}


@router.post("/api/v1/operator/files/{asset_code}/versions")
async def upload_file_version(
    asset_code: str,
    reason_code: str = Form(...),
    note: str | None = Form(default=None),
    upload: UploadFile = File(...),
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    content = await upload.read()
    try:
        asset, version, checks = service.add_file_version(
            asset_code=asset_code,
            filename=upload.filename or "upload.bin",
            content=content,
            mime_type=upload.content_type or "application/octet-stream",
            auth=auth,
            reason_code=reason_code,
            note=note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": file_asset_view(asset, latest_version=version, checks=checks)}


@router.post("/api/v1/operator/files/{asset_code}/review")
def review_file(
    asset_code: str,
    payload: FileReviewPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        asset, version = service.review_latest_file(
            asset_code=asset_code,
            target_state=payload.target_state,
            auth=auth,
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    checks = service.list_file_checks(version.id)
    return {"item": file_asset_view(asset, latest_version=version, checks=checks)}


@router.post("/api/v1/operator/files/{asset_code}/finalize")
def finalize_file(
    asset_code: str,
    payload: FileFinalizePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = FileDocumentService(session)
    try:
        asset, version = service.finalize_file(asset_code=asset_code, auth=auth, reason_code=payload.reason_code, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    checks = service.list_file_checks(version.id)
    return {"item": file_asset_view(asset, latest_version=version, checks=checks)}


@router.post("/api/v1/operator/files/{asset_code}/archive")
def archive_file(
    asset_code: str,
    payload: FileFinalizePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    # RU: Archive endpoint убирает файл из активных списков, но не ломает download/audit trail для истории.
    service = FileDocumentService(session)
    try:
        asset = service.archive_file_asset(asset_code=asset_code, auth=auth, reason_code=payload.reason_code, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    latest_version = session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id)) if asset.latest_version_id else None
    checks = service.list_file_checks(latest_version.id) if latest_version else []
    return {"item": file_asset_view(asset, latest_version=latest_version, checks=checks)}


@router.get("/api/v1/operator/file-versions/{version_code}/download")
def download_file_version(
    version_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> FileResponse:
    service = FileDocumentService(session)
    path, filename = service.get_operator_download_path(version_code=version_code, document_version=False)
    return FileResponse(path, filename=filename)


@router.get("/api/v1/public/requests/{customer_ref}/files/{version_code}/download")
def public_download_file_version(customer_ref: str, version_code: str, session: Session = Depends(get_db)) -> FileResponse:
    service = FileDocumentService(session)
    path, filename = service.get_public_download_path(customer_ref=customer_ref, version_code=version_code, document_version=False)
    return FileResponse(path, filename=filename)
