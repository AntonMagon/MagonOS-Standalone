from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import ArchiveMixin, Base, TimestampMixin, new_uuid, utc_now

# RU: Foundation schema первой волны держит Draft/Request/Offer/Order раздельно и не схлопывает их в один универсальный record.
# RU: Модельный слой также хранит role-scoped и audit-ready сущности, на которые опираются timeline, причины и уведомления.

class RoleDefinition(Base, TimestampMixin):
    __tablename__ = "users_access_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())


class UserAccount(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "users_access_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    default_role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserRoleBinding(Base, TimestampMixin):
    __tablename__ = "users_access_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_code", name="uq_users_access_user_roles"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users_access_users.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)


class AuthSession(Base, TimestampMixin):
    __tablename__ = "users_access_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users_access_users.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    remote_addr: Mapped[str | None] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Company(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    public_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str] = mapped_column(String(8), default="VN", nullable=False)
    public_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    internal_status: Mapped[str] = mapped_column(String(32), default="prospect", nullable=False)
    public_note: Mapped[str | None] = mapped_column(Text())
    internal_note: Mapped[str | None] = mapped_column(Text())
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class CompanyContact(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "company_contacts"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_company_contact_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    role_label: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified", nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text())


class CompanyAddress(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "company_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(128), default="main", nullable=False)
    raw_address: Mapped[str | None] = mapped_column(Text())
    normalized_address: Mapped[str | None] = mapped_column(Text())
    city: Mapped[str | None] = mapped_column(String(128))
    district: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    country_code: Mapped[str] = mapped_column(String(8), default="VN", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Supplier(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_status: Mapped[str] = mapped_column(String(32), default="discovered", nullable=False)
    integration_key: Mapped[str | None] = mapped_column(String(255))
    public_summary: Mapped[str | None] = mapped_column(Text())
    internal_note: Mapped[str | None] = mapped_column(Text())


class SupplierSourceRegistry(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "supplier_source_registries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_layer: Mapped[str] = mapped_column(String(32), default="raw", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupplierRawIngest(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "supplier_raw_ingests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    source_registry_id: Mapped[str] = mapped_column(ForeignKey("supplier_source_registries.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ingest_status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(255))
    trigger_mode: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    normalized_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    merged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_detail: Mapped[str | None] = mapped_column(Text())
    requested_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class SupplierRawRecord(Base, TimestampMixin):
    __tablename__ = "supplier_raw_records"
    __table_args__ = (UniqueConstraint("ingest_id", "source_fingerprint", name="uq_supplier_raw_record_ingest_fp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    source_registry_id: Mapped[str] = mapped_column(ForeignKey("supplier_source_registries.id"), nullable=False)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("supplier_raw_ingests.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(Text(), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    raw_status: Mapped[str] = mapped_column(String(32), default="ingested", nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_email: Mapped[str | None] = mapped_column(String(255))
    raw_phone: Mapped[str | None] = mapped_column(String(64))
    raw_address: Mapped[str | None] = mapped_column(Text())
    raw_capability_summary: Mapped[str | None] = mapped_column(Text())
    source_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    dedup_fingerprint: Mapped[str | None] = mapped_column(String(255))
    raw_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class SupplierCompany(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "supplier_companies"
    __table_args__ = (UniqueConstraint("company_id", name="uq_supplier_company_company"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    source_registry_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_source_registries.id"))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_status: Mapped[str] = mapped_column(String(32), default="discovered", nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="discovered", nullable=False)
    dedup_status: Mapped[str] = mapped_column(String(32), default="clear", nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    canonical_email: Mapped[str | None] = mapped_column(String(255))
    canonical_phone: Mapped[str | None] = mapped_column(String(64))
    capability_summary: Mapped[str | None] = mapped_column(Text())
    capabilities_json: Mapped[list | None] = mapped_column(JSON)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 4))
    contact_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    capability_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trusted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_reason: Mapped[str | None] = mapped_column(String(255))


class SupplierSite(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "supplier_sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    supplier_company_id: Mapped[str] = mapped_column(ForeignKey("supplier_companies.id"), nullable=False)
    address_id: Mapped[str | None] = mapped_column(ForeignKey("company_addresses.id"))
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="discovered", nullable=False)
    capability_summary: Mapped[str | None] = mapped_column(Text())
    current_load_percent: Mapped[int | None] = mapped_column(Integer)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SupplierNormalizationResult(Base, TimestampMixin):
    __tablename__ = "supplier_normalization_results"
    __table_args__ = (UniqueConstraint("ingest_id", "raw_record_id", name="uq_supplier_norm_ingest_raw"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("supplier_raw_ingests.id"), nullable=False)
    raw_record_id: Mapped[str] = mapped_column(ForeignKey("supplier_raw_records.id"), nullable=False)
    normalized_status: Mapped[str] = mapped_column(String(32), default="normalized", nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    canonical_email: Mapped[str | None] = mapped_column(String(255))
    canonical_phone: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(255))
    address_text: Mapped[str | None] = mapped_column(Text())
    city: Mapped[str | None] = mapped_column(String(128))
    district: Mapped[str | None] = mapped_column(String(128))
    country_code: Mapped[str] = mapped_column(String(8), default="VN", nullable=False)
    capability_summary: Mapped[str | None] = mapped_column(Text())
    capabilities_json: Mapped[list | None] = mapped_column(JSON)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 4))
    dedup_fingerprint: Mapped[str | None] = mapped_column(String(255))
    supplier_company_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_companies.id"))
    normalization_payload_json: Mapped[dict | None] = mapped_column(JSON)


class SupplierDedupCandidate(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "supplier_dedup_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("supplier_raw_ingests.id"), nullable=False)
    normalization_result_id: Mapped[str] = mapped_column(ForeignKey("supplier_normalization_results.id"), nullable=False)
    matched_supplier_company_id: Mapped[str] = mapped_column(ForeignKey("supplier_companies.id"), nullable=False)
    candidate_status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False)
    suggested_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    signals_json: Mapped[dict | None] = mapped_column(JSON)


class SupplierMergeDecision(Base, TimestampMixin):
    __tablename__ = "supplier_merge_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    dedup_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_dedup_candidates.id"))
    normalization_result_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_normalization_results.id"))
    supplier_company_id: Mapped[str] = mapped_column(ForeignKey("supplier_companies.id"), nullable=False)
    decision_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text())
    decided_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupplierVerificationEvent(Base, TimestampMixin):
    __tablename__ = "supplier_verification_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    supplier_company_id: Mapped[str] = mapped_column(ForeignKey("supplier_companies.id"), nullable=False)
    supplier_site_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_sites.id"))
    verification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_trust_level: Mapped[str | None] = mapped_column(String(32))
    new_trust_level: Mapped[str | None] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    verified_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SupplierRatingSnapshot(Base, TimestampMixin):
    __tablename__ = "supplier_rating_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    supplier_company_id: Mapped[str] = mapped_column(ForeignKey("supplier_companies.id"), nullable=False)
    supplier_site_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_sites.id"))
    quality_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    trust_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    load_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    overall_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    current_load_percent: Mapped[int | None] = mapped_column(Integer)
    source_label: Mapped[str | None] = mapped_column(String(255))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CatalogItem(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "catalog_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id"))
    supplier_company_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_companies.id"))
    public_title: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_title: Mapped[str | None] = mapped_column(String(255))
    public_description: Mapped[str | None] = mapped_column(Text())
    internal_description: Mapped[str | None] = mapped_column(Text())
    category_code: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    category_label: Mapped[str] = mapped_column(String(255), default="General", nullable=False)
    tags_json: Mapped[list | None] = mapped_column(JSON)
    option_summaries_json: Mapped[list | None] = mapped_column(JSON)
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    list_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    pricing_mode: Mapped[str] = mapped_column(String(32), default="estimate", nullable=False)
    pricing_summary: Mapped[str | None] = mapped_column(Text())
    pricing_note: Mapped[str | None] = mapped_column(Text())
    catalog_mode: Mapped[str] = mapped_column(String(32), default="rfq", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    translations_json: Mapped[dict | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DraftRequest(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "draft_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    catalog_item_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"))
    submitted_request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id"))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(64))
    guest_company_name: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text())
    item_service_context: Mapped[str | None] = mapped_column(Text())
    city: Mapped[str | None] = mapped_column(String(128))
    geo_json: Mapped[dict | None] = mapped_column(JSON)
    source_channel: Mapped[str] = mapped_column(String(32), default="web_public", nullable=False)
    public_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    internal_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    draft_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    intake_channel: Mapped[str] = mapped_column(String(32), default="web", nullable=False)
    locale_code: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    requested_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    last_autosaved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_customer_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_transition_reason: Mapped[str | None] = mapped_column(Text())
    last_transition_reason_code: Mapped[str | None] = mapped_column(String(128))
    last_transition_note: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestRecord(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_ref: Mapped[str | None] = mapped_column(String(32), unique=True)
    draft_request_id: Mapped[str | None] = mapped_column(ForeignKey("draft_requests.id"))
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"))
    catalog_item_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(64))
    guest_company_name: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text())
    item_service_context: Mapped[str | None] = mapped_column(Text())
    source_channel: Mapped[str] = mapped_column(String(32), default="web_public", nullable=False)
    city: Mapped[str | None] = mapped_column(String(128))
    geo_json: Mapped[dict | None] = mapped_column(JSON)
    request_status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    locale_code: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    requested_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    intake_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    last_transition_reason_code: Mapped[str | None] = mapped_column(String(128))
    last_transition_note: Mapped[str | None] = mapped_column(Text())


class RequiredFieldState(Base, TimestampMixin):
    __tablename__ = "required_fields_state"
    __table_args__ = (UniqueConstraint("owner_type", "owner_id", "field_name", name="uq_required_field_state_owner_field"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    field_status: Mapped[str] = mapped_column(String(32), default="missing", nullable=False)
    message: Mapped[str | None] = mapped_column(Text())
    current_value: Mapped[str | None] = mapped_column(Text())
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntakeFileLink(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "intake_file_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(Text(), nullable=False)
    file_kind: Mapped[str] = mapped_column(String(32), default="external_link", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="role", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class RequestReason(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "request_reasons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    reason_kind: Mapped[str] = mapped_column(String(32), default="reason", nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestClarificationCycle(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "request_clarification_cycles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    cycle_index: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    opened_reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    opened_note: Mapped[str | None] = mapped_column(Text())
    opened_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    closed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestFollowUpItem(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "request_follow_up_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    clarification_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("request_clarification_cycles.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text())
    follow_up_status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_reason_code: Mapped[str | None] = mapped_column(String(128))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OfferRecord(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    request_ref: Mapped[str] = mapped_column(String(32), nullable=False)
    current_version_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offer_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    terms_text: Mapped[str | None] = mapped_column(Text())
    scenario_type: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    supplier_ref: Mapped[str | None] = mapped_column(String(64))
    public_summary: Mapped[str | None] = mapped_column(Text())
    transition_reason: Mapped[str] = mapped_column(Text(), nullable=False)


class OfferVersion(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "offer_versions"
    __table_args__ = (UniqueConstraint("offer_id", "version_no", name="uq_offer_versions_offer_version_no"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    terms_text: Mapped[str | None] = mapped_column(Text())
    scenario_type: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    supplier_ref: Mapped[str | None] = mapped_column(String(64))
    public_summary: Mapped[str | None] = mapped_column(Text())
    change_reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text())
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OfferConfirmationRecord(Base, TimestampMixin):
    __tablename__ = "offer_confirmation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), nullable=False)
    offer_version_id: Mapped[str] = mapped_column(ForeignKey("offer_versions.id"), nullable=False)
    confirmation_action: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OfferComparisonMetadata(Base, TimestampMixin):
    __tablename__ = "offer_comparison_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), nullable=False)
    offer_version_id: Mapped[str] = mapped_column(ForeignKey("offer_versions.id"), nullable=False)
    comparison_title: Mapped[str | None] = mapped_column(String(255))
    comparison_rank: Mapped[int | None] = mapped_column(Integer)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    highlights_json: Mapped[list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class OfferCriticalChangeResetReason(Base, TimestampMixin):
    __tablename__ = "offer_critical_change_reset_reasons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), nullable=False)
    previous_offer_version_id: Mapped[str] = mapped_column(ForeignKey("offer_versions.id"), nullable=False)
    new_offer_version_id: Mapped[str] = mapped_column(ForeignKey("offer_versions.id"), nullable=False)
    previous_confirmation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class OrderRecord(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), nullable=False)
    offer_version_id: Mapped[str] = mapped_column(ForeignKey("offer_versions.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    customer_refs_json: Mapped[dict | None] = mapped_column(JSON)
    supplier_refs_json: Mapped[list | None] = mapped_column(JSON)
    internal_owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    order_status: Mapped[str] = mapped_column(String(32), default="awaiting_payment", nullable=False)
    payment_state: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    logistics_state: Mapped[str] = mapped_column(String(32), default="planning", nullable=False)
    readiness_state: Mapped[str] = mapped_column(String(32), default="not_ready", nullable=False)
    refund_state: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    dispute_state: Mapped[str] = mapped_column(String(32), default="clear", nullable=False)
    public_status: Mapped[str] = mapped_column(String(32), default="accepted", nullable=False)
    acceptance_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    last_transition_reason_code: Mapped[str | None] = mapped_column(String(128))
    last_transition_note: Mapped[str | None] = mapped_column(Text())


class OrderLine(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "order_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    catalog_item_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"))
    line_type: Mapped[str] = mapped_column(String(32), default="catalog_service", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1, nullable=False)
    unit_label: Mapped[str] = mapped_column(String(32), default="lot", nullable=False)
    line_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    line_status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    planned_supplier_ref: Mapped[str | None] = mapped_column(String(64))
    planned_stage_refs_json: Mapped[list | None] = mapped_column(JSON)
    readiness_state: Mapped[str] = mapped_column(String(32), default="not_ready", nullable=False)
    delivery_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    refund_state: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    dispute_state: Mapped[str] = mapped_column(String(32), default="clear", nullable=False)
    last_transition_reason_code: Mapped[str | None] = mapped_column(String(128))
    last_transition_note: Mapped[str | None] = mapped_column(Text())


class PaymentRecord(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "payment_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    payment_state: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    payment_ref: Mapped[str | None] = mapped_column(String(128))
    provider_ref: Mapped[str | None] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(Text())
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_transition_reason_code: Mapped[str | None] = mapped_column(String(128))


class InternalLedgerEntry(Base, TimestampMixin):
    __tablename__ = "internal_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    payment_record_id: Mapped[str | None] = mapped_column(ForeignKey("payment_records.id"))
    entry_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_state: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class FileAsset(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "files_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="attachment", nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_extension: Mapped[str | None] = mapped_column(String(16))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    current_version_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    check_state: Mapped[str] = mapped_column(String(32), default="checking", nullable=False)
    # RU: legacy-колонка visibility сохранена ради совместимости старой схемы, но source-of-truth для нового контура — visibility_scope.
    legacy_visibility: Mapped[str] = mapped_column("visibility", String(32), default="internal", nullable=False)
    visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    final_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latest_version_id: Mapped[str | None] = mapped_column(ForeignKey("file_versions.id"))
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class FileVersion(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "file_versions"
    __table_args__ = (UniqueConstraint("file_asset_id", "version_no", name="uq_file_versions_asset_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("files_media.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_extension: Mapped[str | None] = mapped_column(String(16))
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="attachment", nullable=False)
    check_state: Mapped[str] = mapped_column(String(32), default="checking", nullable=False)
    visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    final_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class FileCheck(Base, TimestampMixin):
    __tablename__ = "file_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("files_media.id"), nullable=False)
    file_version_id: Mapped[str] = mapped_column(ForeignKey("file_versions.id"), nullable=False)
    check_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    check_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str | None] = mapped_column(Text())
    details_json: Mapped[dict | None] = mapped_column(JSON)
    checked_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class Document(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files_media.id"))
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # RU: legacy-колонка visibility тоже держится для обратной совместимости миграций и старых строк.
    legacy_visibility: Mapped[str] = mapped_column("visibility", String(32), default="internal", nullable=False)
    visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    current_version_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_version_no: Mapped[int | None] = mapped_column(Integer)
    sent_state: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class DocumentVersion(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version_status: Mapped[str] = mapped_column(String(32), default="published", nullable=False)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("files_media.id"), nullable=False)
    file_version_id: Mapped[str] = mapped_column(ForeignKey("file_versions.id"), nullable=False)
    sent_state: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text())
    visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    generated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


# RU: Оставляем совместимые алиасы, чтобы существующие импорт-пути не ломались в соседних модулях, пока контур полностью переводится на FileAsset/Document.
MediaFile = FileAsset
DocumentRecord = Document


class CommunicationThread(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "comms_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    last_message_preview: Mapped[str | None] = mapped_column(Text())
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class ReasonCodeCatalog(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "reason_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    default_visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RuleDefinition(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "rules_engine_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_kind: Mapped[str] = mapped_column(String(32), default="transition_guard", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latest_version_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    config_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class RuleVersion(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "rules_engine_rule_versions"
    __table_args__ = (UniqueConstraint("rule_definition_id", "version_no", name="uq_rule_version_per_rule"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    rule_definition_id: Mapped[str] = mapped_column(ForeignKey("rules_engine_rules.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    explainability_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))


class NotificationRule(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "notification_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    rule_definition_id: Mapped[str | None] = mapped_column(ForeignKey("rules_engine_rules.id"))
    rule_version_id: Mapped[str | None] = mapped_column(ForeignKey("rules_engine_rule_versions.id"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="inbox", nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    min_interval_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class EscalationHint(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "escalation_hints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[str | None] = mapped_column(String(64))
    reason_code: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    sla_minutes: Mapped[int | None] = mapped_column(Integer)
    overdue_after_minutes: Mapped[int | None] = mapped_column(Integer)
    dashboard_bucket: Mapped[str] = mapped_column(String(64), default="attention", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_code: Mapped[str | None] = mapped_column(String(32))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text())
    visibility: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    payload_json: Mapped[dict | None] = mapped_column(JSON)


class MessageEvent(Base, TimestampMixin, ArchiveMixin):
    __tablename__ = "message_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entry_kind: Mapped[str] = mapped_column(String(32), default="event", nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="system", nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), default="system", nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users_access_users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message_type: Mapped[str | None] = mapped_column(String(64))
    visibility_scope: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text())
    dedupe_key: Mapped[str | None] = mapped_column(String(255))
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    source_audit_event_id: Mapped[str | None] = mapped_column(ForeignKey("audit_events.id"))
    parent_message_id: Mapped[str | None] = mapped_column(ForeignKey("message_events.id"))
