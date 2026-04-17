# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations.foundation import get_storage_adapter
from .audit import record_audit_event
from .codes import reserve_code
from .models import (
    Document,
    DocumentVersion,
    FileAsset,
    FileCheck,
    FileVersion,
    OfferRecord,
    OrderRecord,
    RequestRecord,
    UserAccount,
)
from .security import AuthContext, ROLE_ADMIN, ROLE_OPERATOR
from .settings import FoundationSettings, load_settings

ALLOWED_OWNER_TYPES = {"request", "offer", "order"}
ALLOWED_FILE_TYPES = {"attachment", "brief", "artwork", "document_generated", "invoice_like", "internal_job"}
ALLOWED_VISIBILITY_SCOPES = {"internal", "operator", "customer", "public", "admin"}
ALLOWED_EXTENSIONS = {
    "pdf",
    "txt",
    "md",
    "doc",
    "docx",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "zip",
    "csv",
    "xlsx",
}

DOCUMENT_TEMPLATES = {
    "offer_proposal": {
        "document_type": "offer_proposal",
        "title_prefix": "Коммерческое предложение",
        "visibility_scope": "customer",
    },
    "offer_confirmation": {
        "document_type": "offer_confirmation",
        "title_prefix": "Подтверждение предложения",
        "visibility_scope": "customer",
    },
    "invoice_like": {
        "document_type": "invoice_like",
        "title_prefix": "Базовый счёт",
        "visibility_scope": "customer",
    },
    "internal_job": {
        "document_type": "internal_job",
        "title_prefix": "Внутреннее задание",
        "visibility_scope": "internal",
    },
}


@dataclass(slots=True)
class OwnerRef:
    owner_type: str
    owner_id: str
    owner_code: str
    request_id: str | None = None
    request_code: str | None = None
    request_customer_ref: str | None = None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FileDocumentService:
    def __init__(self, session: Session, settings: FoundationSettings | None = None):
        self.session = session
        self.settings = settings or load_settings()
        self.storage = get_storage_adapter(self.settings)

    def _get_request(self, request_code: str) -> RequestRecord:
        item = self.session.scalar(select(RequestRecord).where(RequestRecord.code == request_code, RequestRecord.deleted_at.is_(None)))
        if item is None:
            raise LookupError("request_not_found")
        return item

    def _get_offer(self, offer_code: str) -> OfferRecord:
        item = self.session.scalar(select(OfferRecord).where(OfferRecord.code == offer_code, OfferRecord.deleted_at.is_(None)))
        if item is None:
            raise LookupError("offer_not_found")
        return item

    def _get_order(self, order_code: str) -> OrderRecord:
        item = self.session.scalar(select(OrderRecord).where(OrderRecord.code == order_code, OrderRecord.deleted_at.is_(None)))
        if item is None:
            raise LookupError("order_not_found")
        return item

    def resolve_owner(self, owner_type: str, owner_code: str) -> OwnerRef:
        if owner_type not in ALLOWED_OWNER_TYPES:
            raise HTTPException(status_code=422, detail="owner_type_invalid")
        if owner_type == "request":
            request = self._get_request(owner_code)
            return OwnerRef(
                owner_type=owner_type,
                owner_id=request.id,
                owner_code=request.code,
                request_id=request.id,
                request_code=request.code,
                request_customer_ref=request.customer_ref,
            )
        if owner_type == "offer":
            offer = self._get_offer(owner_code)
            request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
            return OwnerRef(
                owner_type=owner_type,
                owner_id=offer.id,
                owner_code=offer.code,
                request_id=request.id if request else offer.request_id,
                request_code=request.code if request else None,
                request_customer_ref=request.customer_ref if request else None,
            )
        order = self._get_order(owner_code)
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == order.request_id))
        return OwnerRef(
            owner_type=owner_type,
            owner_id=order.id,
            owner_code=order.code,
            request_id=request.id if request else order.request_id,
            request_code=request.code if request else None,
            request_customer_ref=request.customer_ref if request else None,
        )

    def _file_asset_by_code(self, asset_code: str) -> FileAsset:
        item = self.session.scalar(
            select(FileAsset).where(FileAsset.code == asset_code, FileAsset.deleted_at.is_(None), FileAsset.archived_at.is_(None))
        )
        if item is None:
            raise LookupError("file_asset_not_found")
        return item

    def _document_by_code(self, document_code: str) -> Document:
        item = self.session.scalar(
            select(Document).where(Document.code == document_code, Document.deleted_at.is_(None), Document.archived_at.is_(None))
        )
        if item is None:
            raise LookupError("document_not_found")
        return item

    def _file_version_by_code(self, version_code: str) -> FileVersion:
        item = self.session.scalar(select(FileVersion).where(FileVersion.code == version_code, FileVersion.deleted_at.is_(None)))
        if item is None:
            raise LookupError("file_version_not_found")
        return item

    def _document_version_by_code(self, version_code: str) -> DocumentVersion:
        item = self.session.scalar(select(DocumentVersion).where(DocumentVersion.code == version_code, DocumentVersion.deleted_at.is_(None)))
        if item is None:
            raise LookupError("document_version_not_found")
        return item

    def _build_storage_key(self, *, owner: OwnerRef, asset_code: str, version_no: int, filename: str) -> str:
        safe_name = filename.replace("/", "-").replace("\\", "-").replace(" ", "_")
        return f"{owner.owner_type}/{owner.owner_code}/{asset_code}/v{version_no}/{safe_name}"

    def _automatic_checks(self, *, filename: str, mime_type: str | None, content: bytes) -> list[dict[str, object]]:
        extension = Path(filename).suffix.lower().lstrip(".")
        checks = [
            {
                "check_kind": "presence",
                "check_state": "passed" if content else "failed",
                "reason_code": "file_presence_ok" if content else "file_missing_content",
                "message": None if content else "Uploaded content is empty.",
            },
            {
                "check_kind": "size",
                "check_state": "passed" if len(content) <= self.settings.max_upload_bytes else "failed",
                "reason_code": "file_size_ok" if len(content) <= self.settings.max_upload_bytes else "file_size_limit_exceeded",
                "message": None if len(content) <= self.settings.max_upload_bytes else f"File exceeds {self.settings.max_upload_bytes} bytes.",
            },
            {
                "check_kind": "extension",
                "check_state": "passed" if extension in ALLOWED_EXTENSIONS else "failed",
                "reason_code": "file_extension_ok" if extension in ALLOWED_EXTENSIONS else "file_extension_not_allowed",
                "message": None if extension in ALLOWED_EXTENSIONS else f"Extension .{extension or 'unknown'} is not allowed.",
            },
            {
                "check_kind": "type",
                "check_state": "passed" if mime_type and "/" in mime_type else "failed",
                "reason_code": "file_type_ok" if mime_type and "/" in mime_type else "file_type_missing",
                "message": None if mime_type and "/" in mime_type else "MIME type is missing or invalid.",
            },
        ]
        auto_failed = any(item["check_state"] == "failed" for item in checks)
        checks.append(
            {
                "check_kind": "manual_review",
                "check_state": "blocked" if auto_failed else "pending_review",
                "reason_code": "file_manual_review_blocked" if auto_failed else "file_manual_review_required",
                "message": "Automatic checks failed." if auto_failed else "Operator manual review is required.",
            }
        )
        return checks

    def _write_checks(
        self,
        *,
        asset: FileAsset,
        version: FileVersion,
        checks: list[dict[str, object]],
        auth: AuthContext | None,
    ) -> list[FileCheck]:
        items: list[FileCheck] = []
        for payload in checks:
            item = FileCheck(
                code=reserve_code(self.session, "file_checks", "FCK"),
                file_asset_id=asset.id,
                file_version_id=version.id,
                check_kind=str(payload["check_kind"]),
                check_state=str(payload["check_state"]),
                reason_code=str(payload["reason_code"]),
                message=_clean(payload.get("message") if isinstance(payload, dict) else None),
                details_json=payload.get("details_json") if isinstance(payload, dict) else None,
                checked_by_user_id=auth.user_id if auth else None,
            )
            self.session.add(item)
            items.append(item)
        self.session.flush()
        return items

    def _set_asset_snapshot(self, *, asset: FileAsset, version: FileVersion) -> None:
        asset.original_name = version.original_name
        asset.storage_key = version.storage_key
        asset.storage_backend = version.storage_backend
        asset.mime_type = version.mime_type
        asset.file_extension = version.file_extension
        asset.byte_size = version.byte_size
        asset.current_version_no = version.version_no
        asset.check_state = version.check_state
        asset.legacy_visibility = version.visibility_scope
        asset.visibility_scope = version.visibility_scope
        asset.final_flag = version.final_flag
        asset.latest_version_id = version.id

    def _create_file_version(
        self,
        *,
        asset: FileAsset,
        owner: OwnerRef,
        filename: str,
        content: bytes,
        mime_type: str,
        auth: AuthContext,
        file_type: str,
        visibility_scope: str,
        initial_check_state: str | None = None,
        initial_final_flag: bool = False,
    ) -> tuple[FileVersion, list[FileCheck]]:
        version_no = asset.current_version_no + 1 if asset.id else 1
        storage_key = self._build_storage_key(owner=owner, asset_code=asset.code, version_no=version_no, filename=filename)
        stored = self.storage.save_bytes(storage_key=storage_key, content=content)
        extension = Path(filename).suffix.lower().lstrip(".") or None
        version = FileVersion(
            code=reserve_code(self.session, "file_versions", "FVR"),
            file_asset_id=asset.id,
            version_no=version_no,
            original_name=filename,
            storage_key=stored.storage_key,
            storage_backend=stored.backend,
            mime_type=mime_type,
            file_extension=extension,
            byte_size=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            file_type=file_type,
            check_state=initial_check_state or "pending_review",
            visibility_scope=visibility_scope,
            final_flag=initial_final_flag,
            created_by_user_id=auth.user_id,
        )
        self.session.add(version)
        self.session.flush()
        if initial_check_state:
            checks = [
                FileCheck(
                    code=reserve_code(self.session, "file_checks", "FCK"),
                    file_asset_id=asset.id,
                    file_version_id=version.id,
                    check_kind="system_generate",
                    check_state=initial_check_state,
                    reason_code="system_generated_document",
                    message="System-generated document version.",
                    checked_by_user_id=auth.user_id,
                )
            ]
            for item in checks:
                self.session.add(item)
            self.session.flush()
        else:
            checks = self._write_checks(asset=asset, version=version, checks=self._automatic_checks(filename=filename, mime_type=mime_type, content=content), auth=auth)
            if any(item.check_state == "failed" for item in checks):
                version.check_state = "failed"
            else:
                version.check_state = "pending_review"
        self._set_asset_snapshot(asset=asset, version=version)
        return version, checks

    def list_files_for_owner(self, owner_type: str, owner_id: str) -> list[FileAsset]:
        return self.session.scalars(
            select(FileAsset)
            .where(FileAsset.owner_type == owner_type, FileAsset.owner_id == owner_id, FileAsset.deleted_at.is_(None), FileAsset.archived_at.is_(None))
            .order_by(FileAsset.created_at.asc())
        ).all()

    def list_documents_for_owner(self, owner_type: str, owner_id: str) -> list[Document]:
        return self.session.scalars(
            select(Document)
            .where(Document.owner_type == owner_type, Document.owner_id == owner_id, Document.deleted_at.is_(None), Document.archived_at.is_(None))
            .order_by(Document.created_at.asc())
        ).all()

    def list_file_versions(self, asset_id: str) -> list[FileVersion]:
        return self.session.scalars(
            select(FileVersion).where(FileVersion.file_asset_id == asset_id, FileVersion.deleted_at.is_(None)).order_by(FileVersion.version_no.asc())
        ).all()

    def list_document_versions(self, document_id: str) -> list[DocumentVersion]:
        return self.session.scalars(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id, DocumentVersion.deleted_at.is_(None)).order_by(DocumentVersion.version_no.asc())
        ).all()

    def list_file_checks(self, version_id: str) -> list[FileCheck]:
        return self.session.scalars(
            select(FileCheck).where(FileCheck.file_version_id == version_id).order_by(FileCheck.created_at.asc())
        ).all()

    def upload_file_asset(
        self,
        *,
        owner_type: str,
        owner_code: str,
        filename: str,
        content: bytes,
        mime_type: str,
        file_type: str,
        visibility_scope: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> tuple[FileAsset, FileVersion, list[FileCheck]]:
        if file_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(status_code=422, detail="file_type_invalid")
        if visibility_scope not in ALLOWED_VISIBILITY_SCOPES:
            raise HTTPException(status_code=422, detail="visibility_scope_invalid")
        owner = self.resolve_owner(owner_type, owner_code)
        asset = FileAsset(
            code=reserve_code(self.session, "files_media", "FIL"),
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            file_type=file_type,
            title=filename,
            original_name=filename,
            storage_key="pending",
            storage_backend=self.settings.storage_backend,
            mime_type=mime_type,
            file_extension=Path(filename).suffix.lower().lstrip(".") or None,
            byte_size=len(content),
            current_version_no=0,
            check_state="pending_review",
            legacy_visibility=visibility_scope,
            visibility_scope=visibility_scope,
            final_flag=False,
            uploaded_by_user_id=auth.user_id,
        )
        self.session.add(asset)
        self.session.flush()
        version, checks = self._create_file_version(
            asset=asset,
            owner=owner,
            filename=filename,
            content=content,
            mime_type=mime_type,
            auth=auth,
            file_type=file_type,
            visibility_scope=visibility_scope,
        )
        record_audit_event(
            self.session,
            module_name="files_media",
            action="file_uploaded",
            entity_type="file_asset",
            entity_id=asset.id,
            entity_code=asset.code,
            auth=auth,
            reason=reason_code,
            payload_json={"owner_type": owner.owner_type, "owner_code": owner.owner_code, "version_code": version.code, "note": _clean(note)},
        )
        return asset, version, checks

    def add_file_version(
        self,
        *,
        asset_code: str,
        filename: str,
        content: bytes,
        mime_type: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> tuple[FileAsset, FileVersion, list[FileCheck]]:
        asset = self._file_asset_by_code(asset_code)
        owner = self.resolve_owner(asset.owner_type, self.owner_code_for_asset(asset))
        current = self.session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id))
        if current is not None:
            current.version_status = "superseded"
            current.final_flag = False
        asset.final_flag = False
        version, checks = self._create_file_version(
            asset=asset,
            owner=owner,
            filename=filename,
            content=content,
            mime_type=mime_type,
            auth=auth,
            file_type=asset.file_type,
            visibility_scope=asset.visibility_scope,
        )
        record_audit_event(
            self.session,
            module_name="files_media",
            action="file_version_created",
            entity_type="file_asset",
            entity_id=asset.id,
            entity_code=asset.code,
            auth=auth,
            reason=reason_code,
            payload_json={"version_code": version.code, "note": _clean(note)},
        )
        return asset, version, checks

    def review_latest_file(
        self,
        *,
        asset_code: str,
        target_state: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> tuple[FileAsset, FileVersion]:
        if target_state not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="file_review_state_invalid")
        asset = self._file_asset_by_code(asset_code)
        version = self.session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id))
        if version is None:
            raise HTTPException(status_code=409, detail="file_version_missing")
        manual_check = self.session.scalar(
            select(FileCheck).where(FileCheck.file_version_id == version.id, FileCheck.check_kind == "manual_review").order_by(FileCheck.created_at.desc())
        )
        if manual_check is None:
            raise HTTPException(status_code=409, detail="manual_review_check_missing")
        manual_check.check_state = target_state
        manual_check.reason_code = reason_code
        manual_check.message = _clean(note)
        manual_check.checked_by_user_id = auth.user_id
        version.check_state = target_state
        asset.check_state = target_state
        if target_state == "rejected":
            version.final_flag = False
            asset.final_flag = False
        record_audit_event(
            self.session,
            module_name="files_media",
            action="file_reviewed",
            entity_type="file_asset",
            entity_id=asset.id,
            entity_code=asset.code,
            auth=auth,
            reason=reason_code,
            payload_json={"version_code": version.code, "target_state": target_state, "note": _clean(note)},
        )
        return asset, version

    def finalize_file(
        self,
        *,
        asset_code: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> tuple[FileAsset, FileVersion]:
        asset = self._file_asset_by_code(asset_code)
        version = self.session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id))
        if version is None:
            raise HTTPException(status_code=409, detail="file_version_missing")
        if version.check_state != "approved":
            raise HTTPException(status_code=409, detail="file_not_ready_for_final")
        version.final_flag = True
        asset.final_flag = True
        record_audit_event(
            self.session,
            module_name="files_media",
            action="file_finalized",
            entity_type="file_asset",
            entity_id=asset.id,
            entity_code=asset.code,
            auth=auth,
            reason=reason_code,
            payload_json={"version_code": version.code, "note": _clean(note)},
        )
        return asset, version

    def archive_file_asset(
        self,
        *,
        asset_code: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> FileAsset:
        # RU: Archive выводит файл из активных списков, но не уничтожает версии и историю аудита.
        asset = self._file_asset_by_code(asset_code)
        asset.archived_at = _utc_now()
        asset.archived_reason = reason_code
        asset.final_flag = False
        record_audit_event(
            self.session,
            module_name="files_media",
            action="file_archived",
            entity_type="file_asset",
            entity_id=asset.id,
            entity_code=asset.code,
            auth=auth,
            reason=reason_code,
            payload_json={"note": _clean(note)},
        )
        return asset

    def owner_code_for_asset(self, asset: FileAsset) -> str:
        return self.owner_code_from_ref(asset.owner_type, asset.owner_id)

    def owner_code_for_document(self, document: Document) -> str:
        return self.owner_code_from_ref(document.owner_type, document.owner_id)

    def owner_code_from_ref(self, owner_type: str, owner_id: str) -> str:
        if owner_type == "request":
            request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == owner_id))
            return request.code
        if owner_type == "offer":
            offer = self.session.scalar(select(OfferRecord).where(OfferRecord.id == owner_id))
            return offer.code
        order = self.session.scalar(select(OrderRecord).where(OrderRecord.id == owner_id))
        return order.code

    def _render_document_text(self, *, template_key: str, owner: OwnerRef) -> tuple[str, str, str, dict[str, object]]:
        template = DOCUMENT_TEMPLATES.get(template_key)
        if template is None:
            raise HTTPException(status_code=422, detail="document_template_invalid")
        if owner.owner_type == "request":
            request = self._get_request(owner.owner_code)
            body = (
                f"# {template['title_prefix']}\n\n"
                f"- Request: {request.code}\n"
                f"- Customer ref: {request.customer_ref or 'n/a'}\n"
                f"- Customer: {request.customer_name or request.customer_email or 'n/a'}\n"
                f"- City: {request.city or 'n/a'}\n"
                f"- Summary: {request.summary or request.item_service_context or 'n/a'}\n"
                f"- Deadline: {request.requested_deadline_at.isoformat() if request.requested_deadline_at else 'n/a'}\n"
            )
            title = f"{template['title_prefix']} {request.code}"
            return title, "text/markdown", body, {"request_code": request.code, "customer_ref": request.customer_ref}
        if owner.owner_type == "offer":
            offer = self._get_offer(owner.owner_code)
            body = (
                f"# {template['title_prefix']}\n\n"
                f"- Offer: {offer.code}\n"
                f"- Request ref: {offer.request_ref}\n"
                f"- Status: {offer.offer_status}\n"
                f"- Confirmation: {offer.confirmation_state}\n"
                f"- Amount: {offer.amount or 'n/a'} {offer.currency_code}\n"
                f"- Lead time: {offer.lead_time_days or 'n/a'}\n"
                f"- Terms: {offer.terms_text or 'n/a'}\n"
            )
            title = f"{template['title_prefix']} {offer.code}"
            return title, "text/markdown", body, {"offer_code": offer.code, "request_ref": offer.request_ref}
        order = self._get_order(owner.owner_code)
        body = (
            f"# {template['title_prefix']}\n\n"
            f"- Order: {order.code}\n"
            f"- Status: {order.order_status}\n"
            f"- Payment: {order.payment_state}\n"
            f"- Logistics: {order.logistics_state}\n"
            f"- Readiness: {order.readiness_state}\n"
            f"- Customer refs: {order.customer_refs_json or {}}\n"
            f"- Supplier refs: {order.supplier_refs_json or []}\n"
        )
        title = f"{template['title_prefix']} {order.code}"
        return title, "text/markdown", body, {"order_code": order.code, "request_id": order.request_id}

    def generate_document(
        self,
        *,
        owner_type: str,
        owner_code: str,
        template_key: str,
        title: str | None,
        visibility_scope: str | None,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
        replace_document_code: str | None = None,
    ) -> tuple[Document, DocumentVersion, FileAsset, FileVersion]:
        owner = self.resolve_owner(owner_type, owner_code)
        rendered_title, mime_type, body, payload = self._render_document_text(template_key=template_key, owner=owner)
        template = DOCUMENT_TEMPLATES[template_key]
        filename = f"{(title or rendered_title).replace(' ', '_')}.md"
        content = body.encode("utf-8")
        if visibility_scope is None:
            visibility_scope = str(template["visibility_scope"])
        if visibility_scope not in ALLOWED_VISIBILITY_SCOPES:
            raise HTTPException(status_code=422, detail="visibility_scope_invalid")
        if template_key == "internal_job" and visibility_scope in {"customer", "public"}:
            raise HTTPException(status_code=422, detail="document_visibility_invalid_for_template")

        if replace_document_code:
            document = self._document_by_code(replace_document_code)
            if document.owner_type != owner_type or document.owner_id != owner.owner_id:
                raise HTTPException(status_code=409, detail="document_owner_mismatch")
            asset = self.session.scalar(select(FileAsset).where(FileAsset.id == document.file_id))
            if asset is None:
                raise HTTPException(status_code=409, detail="document_file_asset_missing")
            current_version = self.session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id))
            if current_version is not None:
                current_version.version_status = "replaced"
                current_version.final_flag = False
            previous_doc_version = self.session.scalar(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document.id, DocumentVersion.version_no == document.current_version_no, DocumentVersion.deleted_at.is_(None))
            )
            if previous_doc_version is not None:
                previous_doc_version.version_status = "replaced"
                previous_doc_version.replaced_at = _utc_now()
            file_version, _ = self._create_file_version(
                asset=asset,
                owner=owner,
                filename=filename,
                content=content,
                mime_type=mime_type,
                auth=auth,
                file_type="document_generated",
                visibility_scope=visibility_scope,
                initial_check_state="approved",
                initial_final_flag=True,
            )
            doc_version_no = document.current_version_no + 1
            document.current_version_no = doc_version_no
            document.published_version_no = doc_version_no
            document.sent_state = "draft"
            document.confirmation_state = "pending"
            document.file_id = asset.id
            document.legacy_visibility = visibility_scope
            document.visibility_scope = visibility_scope
            document.title = title or rendered_title
            doc_version = DocumentVersion(
                code=reserve_code(self.session, "document_versions", "DVN"),
                document_id=document.id,
                version_no=doc_version_no,
                version_status="published",
                file_asset_id=asset.id,
                file_version_id=file_version.id,
                sent_state="draft",
                confirmation_state="pending",
                published_at=file_version.created_at or _utc_now(),
                reason_code=reason_code,
                note=_clean(note),
                visibility_scope=visibility_scope,
                payload_json=payload,
                generated_by_user_id=auth.user_id,
            )
            self.session.add(doc_version)
            self.session.flush()
            record_audit_event(
                self.session,
                module_name="documents",
                action="document_replaced",
                entity_type="document",
                entity_id=document.id,
                entity_code=document.code,
                auth=auth,
                reason=reason_code,
                payload_json={"document_version_code": doc_version.code, "file_version_code": file_version.code, "note": _clean(note)},
            )
            return document, doc_version, asset, file_version

        asset = FileAsset(
            code=reserve_code(self.session, "files_media", "FIL"),
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            file_type="document_generated",
            title=title or rendered_title,
            original_name=filename,
            storage_key="pending",
            storage_backend=self.settings.storage_backend,
            mime_type=mime_type,
            file_extension="md",
            byte_size=len(content),
            current_version_no=0,
            check_state="approved",
            legacy_visibility=visibility_scope,
            visibility_scope=visibility_scope,
            final_flag=True,
            uploaded_by_user_id=auth.user_id,
        )
        self.session.add(asset)
        self.session.flush()
        file_version, _ = self._create_file_version(
            asset=asset,
            owner=owner,
            filename=filename,
            content=content,
            mime_type=mime_type,
            auth=auth,
            file_type="document_generated",
            visibility_scope=visibility_scope,
            initial_check_state="approved",
            initial_final_flag=True,
        )
        document = Document(
            code=reserve_code(self.session, "documents", "DOC"),
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            file_id=asset.id,
            document_type=str(template["document_type"]),
            template_key=template_key,
            title=title or rendered_title,
            legacy_visibility=visibility_scope,
            visibility_scope=visibility_scope,
            current_version_no=1,
            published_version_no=1,
            sent_state="draft",
            confirmation_state="pending",
            created_by_user_id=auth.user_id,
        )
        self.session.add(document)
        self.session.flush()
        doc_version = DocumentVersion(
            code=reserve_code(self.session, "document_versions", "DVN"),
            document_id=document.id,
            version_no=1,
            version_status="published",
            file_asset_id=asset.id,
            file_version_id=file_version.id,
            sent_state="draft",
            confirmation_state="pending",
            published_at=file_version.created_at or _utc_now(),
            reason_code=reason_code,
            note=_clean(note),
            visibility_scope=visibility_scope,
            payload_json=payload,
            generated_by_user_id=auth.user_id,
        )
        self.session.add(doc_version)
        self.session.flush()
        record_audit_event(
            self.session,
            module_name="documents",
            action="document_generated",
            entity_type="document",
            entity_id=document.id,
            entity_code=document.code,
            auth=auth,
            reason=reason_code,
            payload_json={"document_version_code": doc_version.code, "file_version_code": file_version.code, "template_key": template_key},
        )
        return document, doc_version, asset, file_version

    def transition_document(
        self,
        *,
        document_code: str,
        action: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> tuple[Document, DocumentVersion]:
        if action not in {"send", "confirm"}:
            raise HTTPException(status_code=422, detail="document_action_invalid")
        document = self._document_by_code(document_code)
        version = self.session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id, DocumentVersion.version_no == document.current_version_no, DocumentVersion.deleted_at.is_(None))
        )
        if version is None:
            raise HTTPException(status_code=409, detail="document_current_version_missing")
        if action == "send":
            if version.version_status not in {"published", "sent"}:
                raise HTTPException(status_code=409, detail="document_not_ready_to_send")
            version.sent_state = "sent"
            version.version_status = "sent"
            version.sent_at = _utc_now()
            document.sent_state = "sent"
            audit_action = "document_sent"
        else:
            if version.sent_state != "sent":
                raise HTTPException(status_code=409, detail="document_not_sent")
            version.confirmation_state = "confirmed"
            version.version_status = "confirmed"
            version.confirmed_at = _utc_now()
            document.confirmation_state = "confirmed"
            audit_action = "document_confirmed"
        record_audit_event(
            self.session,
            module_name="documents",
            action=audit_action,
            entity_type="document",
            entity_id=document.id,
            entity_code=document.code,
            auth=auth,
            reason=reason_code,
            payload_json={"document_version_code": version.code, "note": _clean(note)},
        )
        return document, version

    def archive_document(
        self,
        *,
        document_code: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> Document:
        # RU: Document archive повторяет мягкое архивирование: hide from active views, keep history for audit/timeline.
        document = self._document_by_code(document_code)
        document.archived_at = _utc_now()
        document.archived_reason = reason_code
        current_version = self.session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id, DocumentVersion.version_no == document.current_version_no, DocumentVersion.deleted_at.is_(None))
        )
        if current_version is not None and current_version.version_status not in {"replaced", "archived"}:
            current_version.version_status = "archived"
        record_audit_event(
            self.session,
            module_name="documents",
            action="document_archived",
            entity_type="document",
            entity_id=document.id,
            entity_code=document.code,
            auth=auth,
            reason=reason_code,
            payload_json={"document_version_code": current_version.code if current_version else None, "note": _clean(note)},
        )
        return document

    def list_request_related_files(self, request: RequestRecord, *, customer_visible_only: bool) -> list[FileAsset]:
        offer_ids = list(self.session.scalars(select(OfferRecord.id).where(OfferRecord.request_id == request.id, OfferRecord.deleted_at.is_(None))).all())
        order_ids = list(self.session.scalars(select(OrderRecord.id).where(OrderRecord.request_id == request.id, OrderRecord.deleted_at.is_(None))).all())
        assets = self.session.scalars(
            select(FileAsset).where(FileAsset.deleted_at.is_(None), FileAsset.archived_at.is_(None)).order_by(FileAsset.created_at.asc())
        ).all()
        allowed_visibility = {"customer", "public"} if customer_visible_only else ALLOWED_VISIBILITY_SCOPES
        return [
            item
            for item in assets
            if item.visibility_scope in allowed_visibility
            and (
                (item.owner_type == "request" and item.owner_id == request.id)
                or (item.owner_type == "offer" and item.owner_id in offer_ids)
                or (item.owner_type == "order" and item.owner_id in order_ids)
            )
        ]

    def list_request_related_documents(self, request: RequestRecord, *, customer_visible_only: bool) -> list[Document]:
        offer_ids = list(self.session.scalars(select(OfferRecord.id).where(OfferRecord.request_id == request.id, OfferRecord.deleted_at.is_(None))).all())
        order_ids = list(self.session.scalars(select(OrderRecord.id).where(OrderRecord.request_id == request.id, OrderRecord.deleted_at.is_(None))).all())
        documents = self.session.scalars(
            select(Document).where(Document.deleted_at.is_(None), Document.archived_at.is_(None)).order_by(Document.created_at.asc())
        ).all()
        allowed_visibility = {"customer", "public"} if customer_visible_only else ALLOWED_VISIBILITY_SCOPES
        return [
            item
            for item in documents
            if item.visibility_scope in allowed_visibility
            and (
                (item.owner_type == "request" and item.owner_id == request.id)
                or (item.owner_type == "offer" and item.owner_id in offer_ids)
                or (item.owner_type == "order" and item.owner_id in order_ids)
            )
        ]

    def get_operator_download_path(self, *, version_code: str, document_version: bool = False) -> tuple[str, str]:
        if document_version:
            doc_version = self._document_version_by_code(version_code)
            file_version = self.session.scalar(select(FileVersion).where(FileVersion.id == doc_version.file_version_id))
            if file_version is None:
                raise HTTPException(status_code=404, detail="file_version_not_found")
        else:
            file_version = self._file_version_by_code(version_code)
        return self.storage.absolute_path(storage_key=file_version.storage_key), file_version.original_name

    def get_public_download_path(self, *, customer_ref: str, version_code: str, document_version: bool = False) -> tuple[str, str]:
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.customer_ref == customer_ref, RequestRecord.deleted_at.is_(None)))
        if request is None:
            raise HTTPException(status_code=404, detail="request_not_found")
        if document_version:
            doc_version = self._document_version_by_code(version_code)
            document = self.session.scalar(select(Document).where(Document.id == doc_version.document_id))
            if document is None:
                raise HTTPException(status_code=404, detail="document_not_found")
            allowed = self.list_request_related_documents(request, customer_visible_only=True)
            if document.id not in {item.id for item in allowed}:
                raise HTTPException(status_code=403, detail="document_download_forbidden")
            file_version = self.session.scalar(select(FileVersion).where(FileVersion.id == doc_version.file_version_id))
            if file_version is None:
                raise HTTPException(status_code=404, detail="file_version_not_found")
        else:
            file_version = self._file_version_by_code(version_code)
            asset = self.session.scalar(select(FileAsset).where(FileAsset.id == file_version.file_asset_id))
            if asset is None:
                raise HTTPException(status_code=404, detail="file_asset_not_found")
            allowed = self.list_request_related_files(request, customer_visible_only=True)
            if asset.id not in {item.id for item in allowed}:
                raise HTTPException(status_code=403, detail="file_download_forbidden")
        return self.storage.absolute_path(storage_key=file_version.storage_key), file_version.original_name

    def list_document_templates(self) -> list[dict[str, str]]:
        return [
            {
                "template_key": key,
                "document_type": str(value["document_type"]),
                "title_prefix": str(value["title_prefix"]),
                "visibility_scope": str(value["visibility_scope"]),
            }
            for key, value in DOCUMENT_TEMPLATES.items()
        ]

    def get_user_by_id(self, user_id: str | None) -> UserAccount | None:
        if not user_id:
            return None
        return self.session.scalar(select(UserAccount).where(UserAccount.id == user_id, UserAccount.deleted_at.is_(None)))


def can_manage_files_or_documents(auth: AuthContext) -> bool:
    return auth.role_code in {ROLE_OPERATOR, ROLE_ADMIN}
