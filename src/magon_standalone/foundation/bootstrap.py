from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit_event
from .codes import reserve_code
from .models import CatalogItem, Company, OfferRecord, RequestRecord, RoleDefinition, Supplier, SupplierCompany, SupplierSourceRegistry, UserAccount, UserRoleBinding
from .offer_services import OfferService
from .request_intake_services import RequestIntakeService
from .security import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_GUEST, ROLE_OPERATOR, AuthContext, hash_password
from .settings import FoundationSettings
from .supplier_services import SupplierPipelineService
from .workflow_support import WorkflowSupportService


# RU: Bootstrap первой волны поднимает роли, демо-компанию и базовые рабочие данные в том же standalone-контуре.
ROLE_SPECS = {
    ROLE_GUEST: ("Гость", "Публичный неавторизованный пользователь."),
    ROLE_CUSTOMER: ("Клиент", "Клиентский ролевой доступ для своих заявок и документов."),
    ROLE_OPERATOR: ("Оператор", "Операторский доступ к intake, offer и order контуру."),
    ROLE_ADMIN: ("Администратор", "Полный административный доступ к foundation-монолиту."),
}


def _ensure_catalog_item(session: Session, *, supplier: Supplier | None, supplier_company: SupplierCompany | None, public_title: str, defaults: dict[str, object]) -> None:
    item = session.scalar(select(CatalogItem).where(CatalogItem.public_title == public_title))
    if item is not None:
        return
    session.add(
        CatalogItem(
            code=reserve_code(session, "catalog_items", "CAT"),
            supplier_id=supplier.id if supplier else None,
            supplier_company_id=supplier_company.id if supplier_company else None,
            public_title=public_title,
            **defaults,
        )
    )
    session.flush()


def _ensure_role(session: Session, code: str, label: str, description: str) -> None:
    role = session.scalar(select(RoleDefinition).where(RoleDefinition.code == code))
    if role is None:
        session.add(RoleDefinition(code=code, label=label, description=description))


def _ensure_user(session: Session, *, code_prefix: str, email: str, full_name: str, password: str, role_code: str, company_id: str | None = None) -> UserAccount:
    user = session.scalar(select(UserAccount).where(UserAccount.email == email))
    if user is None:
        user = UserAccount(
            code=reserve_code(session, f"users:{code_prefix}", code_prefix),
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            default_role_code=role_code,
            company_id=company_id,
        )
        session.add(user)
        session.flush()
    binding = session.scalar(
        select(UserRoleBinding).where(UserRoleBinding.user_id == user.id, UserRoleBinding.role_code == role_code)
    )
    if binding is None:
        session.add(UserRoleBinding(user_id=user.id, role_code=role_code))
    return user


def seed_foundation(session: Session, settings: FoundationSettings) -> dict[str, str]:
    for role_code, (label, description) in ROLE_SPECS.items():
        _ensure_role(session, role_code, label, description)

    company = session.scalar(select(Company).where(Company.public_name == "Magon Demo Print"))
    if company is None:
        company = Company(
            code=reserve_code(session, "companies", "CMP"),
            public_name="Magon Demo Print",
            legal_name="Magon Demo Print Co., Ltd.",
            country_code="VN",
            public_status="active",
            internal_status="qualified",
            public_note="Публичный demo-аккаунт для foundation smoke и login flow.",
            internal_note="Создан seed-скриптом для первой волны.",
        )
        session.add(company)
        session.flush()

    supplier = session.scalar(select(Supplier).where(Supplier.display_name == "Wave1 Supplier"))
    if supplier is None:
        supplier = Supplier(
            code=reserve_code(session, "suppliers", "SUP"),
            company_id=company.id,
            display_name="Wave1 Supplier",
            supplier_status="trusted",
            public_summary="Минимальный поставщик для foundation skeleton.",
            internal_note="Seed supplier.",
        )
        session.add(supplier)
        session.flush()

    source_registry = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "fixture_json"))
    if source_registry is None:
        source_registry = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Fixture VN suppliers",
            adapter_key="fixture_json",
            source_layer="raw",
            enabled=True,
            config_json={"source_label": "fixture_vn_suppliers"},
        )
        session.add(source_registry)
        session.flush()
    live_source_registry = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "scenario_live"))
    if live_source_registry is None:
        live_source_registry = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Live parsing VN suppliers",
            adapter_key="scenario_live",
            source_layer="raw",
            enabled=True,
            config_json={
                "query": "printing packaging vietnam",
                "country": "VN",
                "source_label": "live_parsing_vn_suppliers",
            },
        )
        session.add(live_source_registry)
        session.flush()

    admin = _ensure_user(
        session,
        code_prefix="USR",
        email=settings.default_admin_email,
        full_name="Foundation Admin",
        password=settings.default_admin_password,
        role_code=ROLE_ADMIN,
        company_id=company.id,
    )
    admin_auth = AuthContext(user_id=admin.id, role_code=ROLE_ADMIN, email=admin.email, full_name=admin.full_name)
    WorkflowSupportService(session).ensure_baseline_reference_data(created_by_user_id=admin.id)
    _ensure_user(
        session,
        code_prefix="USR",
        email=settings.default_operator_email,
        full_name="Foundation Operator",
        password=settings.default_operator_password,
        role_code=ROLE_OPERATOR,
        company_id=company.id,
    )
    _ensure_user(
        session,
        code_prefix="USR",
        email=settings.default_customer_email,
        full_name="Foundation Customer",
        password=settings.default_customer_password,
        role_code=ROLE_CUSTOMER,
        company_id=company.id,
    )

    supplier_pipeline = SupplierPipelineService(session)
    seeded_supplier = session.scalar(select(Company).where(Company.public_name == "Wave1 Trusted Supplier"))
    if seeded_supplier is None:
        trusted_supplier = supplier_pipeline.create_manual_supplier(
            display_name="Wave1 Trusted Supplier",
            legal_name="Wave1 Trusted Supplier Co., Ltd.",
            canonical_email="sourcing@wave1supplier.vn",
            canonical_phone="+842837540001",
            website="https://wave1supplier.vn",
            capability_summary="PRINT_OFFSET, PACK_CORRUGATED",
            capabilities_json=["PRINT_OFFSET", "PACK_CORRUGATED"],
            address_text="Binh Tan District, Ho Chi Minh City",
            city="Ho Chi Minh City",
            district="Binh Tan",
            country_code="VN",
            auth=admin_auth,
            reason_code="foundation_seed_supplier",
        )
        supplier_pipeline.apply_trust_transition(
            supplier_code=trusted_supplier.code,
            target_trust_level="normalized",
            auth=admin_auth,
            reason_code="foundation_seed_supplier_normalized",
        )
        supplier_pipeline.apply_trust_transition(
            supplier_code=trusted_supplier.code,
            target_trust_level="contact_confirmed",
            auth=admin_auth,
            reason_code="foundation_seed_supplier_contact",
        )
        supplier_pipeline.apply_trust_transition(
            supplier_code=trusted_supplier.code,
            target_trust_level="capability_confirmed",
            auth=admin_auth,
            reason_code="foundation_seed_supplier_capability",
        )
        supplier_pipeline.apply_trust_transition(
            supplier_code=trusted_supplier.code,
            target_trust_level="trusted",
            auth=admin_auth,
            reason_code="foundation_seed_supplier_trusted",
        )

    trusted_supplier_company = session.scalar(select(SupplierCompany).where(SupplierCompany.display_name == "Wave1 Trusted Supplier"))
    _ensure_catalog_item(
        session,
        supplier=supplier,
        supplier_company=trusted_supplier_company,
        public_title="Гофрокороб под маркетплейс и доставку",
        defaults={
            "internal_title": "Wave1 Corrugated Delivery Box",
            "public_description": "Ограниченная wave1-витрина для стандартных транспортных коробов с понятным входом в расчёт и конфигурацию.",
            "internal_description": "Demo showcase item for ready/config packaging entry point.",
            "category_code": "transport-packaging",
            "category_label": "Транспортная упаковка",
            "tags_json": ["короб", "доставка", "ecommerce"],
            "option_summaries_json": ["Размер и конструкция", "Марка картона", "Одноцветная или полноцветная печать"],
            "list_price": 1850000,
            "currency_code": "VND",
            "pricing_mode": "from",
            "pricing_summary": "От базового тиража и конструкции. Финальная цена зависит от размера, картона и печати.",
            "pricing_note": "Показываем ориентир, а не обещаем финальную цену без расчёта.",
            "catalog_mode": "config",
            "visibility": "public",
            "translations_json": {
                "en": {
                    "title": "Corrugated box for delivery and marketplace shipments",
                    "description": "A limited wave1 showcase for transport boxes with a clear path into configuration and quote intake.",
                    "category_label": "Transport packaging",
                    "pricing_summary": "Starts from a base run and board type. Final price depends on size, board, and print.",
                    "option_summaries": ["Size and construction", "Board grade", "Single-color or full-color print"],
                }
            },
            "sort_order": 10,
            "is_featured": True,
        },
    )
    _ensure_catalog_item(
        session,
        supplier=supplier,
        supplier_company=trusted_supplier_company,
        public_title="Самоклеящаяся этикетка для банки и пакета",
        defaults={
            "internal_title": "Wave1 Self-Adhesive Label",
            "public_description": "Понятная карточка для этикеток с материалом, отделкой и коротким guest-входом в draft без регистрации.",
            "internal_description": "Demo showcase item for labels.",
            "category_code": "labels",
            "category_label": "Этикетки и стикеры",
            "tags_json": ["этикетка", "самоклейка", "food"],
            "option_summaries_json": ["Материал: бумага / плёнка", "Лак / ламинация", "Рулон или лист"],
            "list_price": 950000,
            "currency_code": "VND",
            "pricing_mode": "estimate",
            "pricing_summary": "Ориентирная стоимость зависит от материала, размера и отделки.",
            "pricing_note": "Подходит для быстрого запроса без полной регистрации.",
            "catalog_mode": "ready",
            "visibility": "public",
            "translations_json": {
                "en": {
                    "title": "Self-adhesive label for jars and flexible packs",
                    "description": "A clear label showcase card with material and finish options plus a short guest draft entry.",
                    "category_label": "Labels and stickers",
                    "pricing_summary": "Indicative pricing depends on material, size, and finish.",
                    "option_summaries": ["Material: paper / film", "Varnish / lamination", "Roll or sheet"],
                }
            },
            "sort_order": 20,
            "is_featured": True,
        },
    )
    _ensure_catalog_item(
        session,
        supplier=supplier,
        supplier_company=trusted_supplier_company,
        public_title="Сложный RFQ по упаковке и производственной сборке",
        defaults={
            "internal_title": "Wave1 Complex Packaging RFQ",
            "public_description": "Отдельная точка входа для сложных запросов, где цена и конфигурация считаются только после ручного разбора.",
            "internal_description": "Demo showcase RFQ-only service.",
            "category_code": "custom-rfq",
            "category_label": "Сложный запрос / RFQ",
            "tags_json": ["rfq", "сложный проект", "custom"],
            "option_summaries_json": ["Бриф по продукту", "Тираж и сроки", "Материалы и образцы"],
            "list_price": None,
            "currency_code": "VND",
            "pricing_mode": "rfq",
            "pricing_summary": "Цена подтверждается только после ручного расчёта и проверки ограничений.",
            "pricing_note": "Используется как отдельный вход для нестандартных проектов wave1.",
            "catalog_mode": "rfq",
            "visibility": "public",
            "translations_json": {
                "en": {
                    "title": "Complex packaging and production RFQ",
                    "description": "A separate entry point for complex requests where pricing and configuration are confirmed only after manual review.",
                    "category_label": "Complex request / RFQ",
                    "pricing_summary": "Pricing is confirmed only after manual estimation and feasibility review.",
                    "option_summaries": ["Product brief", "Volume and deadlines", "Materials and samples"],
                }
            },
            "sort_order": 30,
            "is_featured": True,
        },
    )

    request_service = RequestIntakeService(session)
    sample_catalog = session.scalar(select(CatalogItem).where(CatalogItem.public_title == "Сложный RFQ по упаковке и производственной сборке"))
    sample_draft = session.scalar(select(Company).where(Company.public_name == "Wave1 Demo Draft Holder"))
    seeded_request = None
    if sample_draft is None:
        demo_company = Company(
            code=reserve_code(session, "companies", "CMP"),
            public_name="Wave1 Demo Draft Holder",
            legal_name="Wave1 Demo Draft Holder LLC",
            country_code="VN",
            public_status="hidden",
            internal_status="draft_context",
            public_note="Hidden demo company for draft/request operator workbench.",
            internal_note="Used by wave1 draft/request seed.",
        )
        session.add(demo_company)
        session.flush()
        draft = request_service.create_draft(
            customer_email="intake-demo@example.com",
            customer_name="Wave1 Intake Demo",
            customer_phone="+84901110001",
            guest_company_name="Demo Brand One",
            company_id=demo_company.id,
            catalog_item_id=sample_catalog.id if sample_catalog else None,
            title="Нужен расчёт по сложному RFQ",
            summary="Demo seed для operator review flow первой волны.",
            item_service_context="RFQ по упаковке, образцам и ручной проверке производственных ограничений.",
            city="Ho Chi Minh City",
            geo_json={"country_code": "VN", "city": "Ho Chi Minh City"},
            source_channel="rfq_public",
            intake_channel="rfq_public",
            locale_code="ru",
            requested_deadline_at=None,
            auth=admin_auth,
            reason_code="foundation_seed_draft",
            reason_note="Seed draft for wave1 request workbench.",
        )
        request_service.update_draft(
            draft,
            title=draft.title,
            summary=draft.summary,
            customer_name=draft.customer_name,
            customer_email=draft.customer_email,
            customer_phone=draft.customer_phone,
            guest_company_name=draft.guest_company_name,
            item_service_context=draft.item_service_context,
            city=draft.city,
            geo_json=draft.geo_json,
            requested_deadline_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            locale_code="ru",
            source_channel="rfq_public",
            auth=admin_auth,
            reason_code="foundation_seed_draft_ready",
            reason_note="Seed draft updated to ready_to_submit.",
        )
        request_record = request_service.submit_draft(
            draft,
            auth=admin_auth,
            reason_code="foundation_seed_request",
            reason_note="Seed draft promoted to request.",
        )
        request_service.transition_request(
            request_record,
            target_status="needs_review",
            reason_code="foundation_seed_request_needs_review",
            reason_note="Seed request enters operator review queue.",
            auth=admin_auth,
        )
        seeded_request = request_record
    else:
        seeded_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Нужен расчёт по сложному RFQ"))

    if seeded_request is not None:
        offer_service = OfferService(session)
        existing_offer = session.scalar(select(OfferRecord).where(OfferRecord.request_id == seeded_request.id))
        if existing_offer is None:
            if seeded_request.request_status != "supplier_search":
                request_service.transition_request(
                    seeded_request,
                    target_status="supplier_search",
                    reason_code="foundation_seed_supplier_search",
                    reason_note="Seed request moved into supplier search before demo offer creation.",
                    auth=admin_auth,
                )
            demo_bundle = offer_service.create_offer(
                request=seeded_request,
                amount=4200000,
                currency_code="VND",
                lead_time_days=9,
                terms_text="50% предоплата после подтверждения версии, остаток перед отгрузкой.",
                scenario_type="baseline",
                supplier_ref=trusted_supplier_company.code if trusted_supplier_company else None,
                public_summary="Базовый вариант по гофроупаковке с ручной проверкой материалов и сроков.",
                comparison_title="Базовый коммерческий вариант",
                comparison_rank=1,
                recommended=True,
                highlights=["Поставка из подтверждённой площадки", "Срок 9 дней", "Ручной review под wave1"],
                metadata={"seed": True},
                auth=admin_auth,
                reason_code="foundation_seed_offer",
                note="Seeded versioned offer for central commercial layer.",
            )
            offer_service.send_offer(
                offer=demo_bundle.offer,
                auth=admin_auth,
                reason_code="foundation_seed_offer_sent",
                note="Seeded offer sent for compare and customer view demos.",
            )

    order_seed_company = session.scalar(select(Company).where(Company.public_name == "Wave1 Demo Order Holder"))
    if order_seed_company is None:
        order_seed_company = Company(
            code=reserve_code(session, "companies", "CMP"),
            public_name="Wave1 Demo Order Holder",
            legal_name="Wave1 Demo Order Holder LLC",
            country_code="VN",
            public_status="hidden",
            internal_status="order_context",
            public_note="Hidden demo company for order workbench.",
            internal_note="Used by wave1 order seed.",
        )
        session.add(order_seed_company)
        session.flush()

    order_seed_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Wave1 Demo Order Seed"))
    if order_seed_request is None:
        order_draft = request_service.create_draft(
            customer_email="order-demo@example.com",
            customer_name="Wave1 Order Demo",
            customer_phone="+84901110002",
            guest_company_name="Demo Brand Two",
            company_id=order_seed_company.id,
            catalog_item_id=sample_catalog.id if sample_catalog else None,
            title="Wave1 Demo Order Seed",
            summary="Seed draft that flows into accepted offer and order.",
            item_service_context="Demo order path for operator payment and logistics workbench.",
            city="Ho Chi Minh City",
            geo_json={"country_code": "VN", "city": "Ho Chi Minh City"},
            source_channel="rfq_public",
            intake_channel="rfq_public",
            locale_code="ru",
            requested_deadline_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            auth=admin_auth,
            reason_code="foundation_seed_order_draft",
            reason_note="Seed draft for order contour.",
        )
        order_seed_request = request_service.submit_draft(
            order_draft,
            auth=admin_auth,
            reason_code="foundation_seed_order_request",
            reason_note="Seed order draft promoted to request.",
        )
        request_service.transition_request(
            order_seed_request,
            target_status="needs_review",
            reason_code="foundation_seed_order_needs_review",
            reason_note="Seed order request enters operator review queue.",
            auth=admin_auth,
        )
        request_service.transition_request(
            order_seed_request,
            target_status="supplier_search",
            reason_code="foundation_seed_order_supplier_search",
            reason_note="Seed order request moved into supplier search.",
            auth=admin_auth,
        )
        order_offer_service = OfferService(session)
        order_bundle = order_offer_service.create_offer(
            request=order_seed_request,
            amount=5600000,
            currency_code="VND",
            lead_time_days=14,
            terms_text="50% advance, 50% before dispatch.",
            scenario_type="baseline",
            supplier_ref=trusted_supplier_company.code if trusted_supplier_company else None,
            public_summary="Seed order commercial variant.",
            comparison_title="Seed order variant",
            comparison_rank=1,
            recommended=True,
            highlights=["Seed order", "Accepted variant"],
            metadata={"seed_order": True},
            auth=admin_auth,
            reason_code="foundation_seed_order_offer",
            note="Seed offer for order contour.",
        )
        order_offer_service.send_offer(
            offer=order_bundle.offer,
            auth=admin_auth,
            reason_code="foundation_seed_order_offer_sent",
            note="Seed order offer sent.",
        )
        order_offer_service.record_confirmation(
            offer=order_bundle.offer,
            action="accept",
            auth=admin_auth,
            reason_code="foundation_seed_order_offer_accepted",
            note="Seed order offer accepted internally for demo order contour.",
        )
        order_offer_service.convert_to_order(
            offer=order_bundle.offer,
            auth=admin_auth,
            reason_code="foundation_seed_order_created",
            note="Seed accepted offer converted to order.",
        )

    # RU: Seed тоже пишет аудит, чтобы пустой foundation не был "немой" и dashboard сразу показывал жизненный след.
    record_audit_event(
        session,
        module_name="seed",
        action="seed_applied",
        entity_type="company",
        entity_id=company.id,
        entity_code=company.code,
        auth=admin_auth,
        reason="foundation_seed",
        payload_json={"company_code": company.code, "supplier_code": supplier.code, "source_registry_code": source_registry.code},
    )
    return {
        "admin_email": settings.default_admin_email,
        "operator_email": settings.default_operator_email,
        "customer_email": settings.default_customer_email,
        "company_code": company.code,
        "supplier_code": supplier.code,
        "source_registry_code": source_registry.code,
    }
