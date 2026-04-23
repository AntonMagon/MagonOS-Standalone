from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit_event
from .codes import reserve_code
from .models import CatalogItem, Company, DraftRequest, OfferRecord, OrderLine, OrderRecord, RequestRecord, RoleDefinition, Supplier, SupplierCompany, SupplierSourceRegistry, UserAccount, UserRoleBinding
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
    # RU: Seed-карточки каталога обновляем идемпотентно, чтобы правки публичного copy доходили до уже поднятой demo-базы.
    if item is not None:
        item.supplier_id = supplier.id if supplier else None
        item.supplier_company_id = supplier_company.id if supplier_company else None
        item.public_title = public_title
        for field_name, value in defaults.items():
            setattr(item, field_name, value)
        session.flush()
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
    # RU: Seed обязан быть повторяемым, потому что launcher и smoke многократно поднимают один и тот же wave1 контур.
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

    supplier = session.scalar(select(Supplier).where(Supplier.display_name.in_(["Wave1 Supplier", "Базовый поставщик платформы"])))
    if supplier is None:
        supplier = Supplier(
            code=reserve_code(session, "suppliers", "SUP"),
            company_id=company.id,
            display_name="Базовый поставщик платформы",
            supplier_status="trusted",
            public_summary="Служебный поставщик для базового демо-контура платформы.",
            internal_note="Seed supplier.",
        )
        session.add(supplier)
        session.flush()
    else:
        supplier.display_name = "Базовый поставщик платформы"
        supplier.public_summary = "Служебный поставщик для базового демо-контура платформы."

    source_registry = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "fixture_json"))
    if source_registry is None:
        source_registry = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Демо-источник поставщиков",
            adapter_key="fixture_json",
            source_layer="raw",
            enabled=True,
            config_json={
                "source_label": "fixture_vn_suppliers",
                "schedule_enabled": False,
                "classification_mode": "deterministic_only",
            },
        )
        session.add(source_registry)
        session.flush()
    else:
        source_registry.label = "Демо-источник поставщиков"
        config = dict(source_registry.config_json or {})
        config.setdefault("schedule_enabled", False)
        config.setdefault("classification_mode", "deterministic_only")
        source_registry.config_json = config
    live_source_registry = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.adapter_key == "scenario_live"))
    if live_source_registry is None:
        live_source_registry = SupplierSourceRegistry(
            code=reserve_code(session, "supplier_source_registries", "SRC"),
            label="Поиск новых поставщиков",
            adapter_key="scenario_live",
            source_layer="raw",
            enabled=True,
            config_json={
                "query": "printing packaging vietnam",
                "country": "VN",
                "source_label": "live_parsing_vn_suppliers",
                "schedule_enabled": True,
                "schedule_interval_minutes": 60,
                "schedule_reason_code": "scheduled_supplier_ingest",
                "classification_mode": "ai_assisted_fallback",
            },
        )
        session.add(live_source_registry)
        session.flush()
    else:
        live_source_registry.label = "Поиск новых поставщиков"
        config = dict(live_source_registry.config_json or {})
        config.setdefault("query", "printing packaging vietnam")
        config.setdefault("country", "VN")
        config.setdefault("source_label", "live_parsing_vn_suppliers")
        config.setdefault("schedule_enabled", True)
        config.setdefault("schedule_interval_minutes", 60)
        config.setdefault("schedule_reason_code", "scheduled_supplier_ingest")
        config.setdefault("classification_mode", "ai_assisted_fallback")
        live_source_registry.config_json = config

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
    seeded_supplier = session.scalar(select(Company).where(Company.public_name.in_(["Wave1 Trusted Supplier", "Проверенный поставщик упаковки"])))
    if seeded_supplier is None:
        trusted_supplier = supplier_pipeline.create_manual_supplier(
            display_name="Проверенный поставщик упаковки",
            legal_name="Trusted Packaging Supplier Co., Ltd.",
            canonical_email="sourcing@wave1supplier.vn",
            canonical_phone="+842837540001",
            website="https://wave1supplier.vn",
            capability_summary="Офсетная печать и гофроупаковка",
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
    else:
        seeded_supplier.public_name = "Проверенный поставщик упаковки"
        seeded_supplier.legal_name = "Trusted Packaging Supplier Co., Ltd."

    trusted_supplier_company = session.scalar(select(SupplierCompany).where(SupplierCompany.display_name.in_(["Wave1 Trusted Supplier", "Проверенный поставщик упаковки"])))
    if trusted_supplier_company is not None:
        # RU: Демо-поставщик должен выглядеть как нормальная запись для оператора, а не как legacy wave1 slug.
        trusted_supplier_company.display_name = "Проверенный поставщик упаковки"
        trusted_supplier_company.legal_name = "Trusted Packaging Supplier Co., Ltd."
        trusted_supplier_company.capability_summary = "Офсетная печать и гофроупаковка"
    _ensure_catalog_item(
        session,
        supplier=supplier,
        supplier_company=trusted_supplier_company,
        public_title="Гофрокороб под маркетплейс и доставку",
        defaults={
            "internal_title": "Wave1 Corrugated Delivery Box",
            "public_description": "Типовой гофрокороб для доставки и маркетплейсов: можно быстро собрать параметры и получить расчёт.",
            "internal_description": "Demo showcase item for ready/config packaging entry point.",
            "category_code": "transport-packaging",
            "category_label": "Транспортная упаковка",
            "tags_json": ["короб", "доставка", "маркетплейс"],
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
                    "description": "A standard corrugated box for delivery and marketplace shipments with a clear path to pricing and parameter selection.",
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
            "public_description": "Этикетка с быстрым стартом: выбери материал и отделку, оставь короткий запрос и получи расчёт без долгой переписки.",
            "internal_description": "Demo showcase item for labels.",
            "category_code": "labels",
            "category_label": "Этикетки и стикеры",
            "tags_json": ["этикетка", "самоклейка", "банка"],
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
                    "description": "A label card with a fast start: choose the material and finish, then send a short request without a long back-and-forth.",
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
        public_title="Сложный запрос по упаковке и производственной сборке",
        defaults={
            "internal_title": "Wave1 Complex Packaging RFQ",
            "public_description": "Отдельная точка входа для сложных запросов, где цена и конфигурация считаются только после ручного разбора.",
            "internal_description": "Demo showcase RFQ-only service.",
            "category_code": "custom-rfq",
            "category_label": "Сложный запрос",
            "tags_json": ["сложный проект", "ручной разбор", "нестандартный кейс"],
            "option_summaries_json": ["Бриф по продукту", "Тираж и сроки", "Материалы и образцы"],
            "list_price": None,
            "currency_code": "VND",
            "pricing_mode": "rfq",
            "pricing_summary": "Цена подтверждается только после ручного расчёта и проверки ограничений.",
            "pricing_note": "Этот вход нужен для нестандартных проектов, где нельзя честно назвать цену без разбора.",
            "catalog_mode": "rfq",
            "visibility": "public",
            "translations_json": {
                "en": {
                    "title": "Complex packaging and production request",
                    "description": "A separate entry point for complex requests where pricing and configuration are confirmed only after manual review.",
                    "category_label": "Complex request",
                    "pricing_summary": "Pricing is confirmed only after manual estimation and feasibility review.",
                    "option_summaries": ["Product brief", "Volume and deadlines", "Materials and samples"],
                }
            },
            "sort_order": 30,
            "is_featured": True,
        },
    )
    complex_catalog_items = session.scalars(
        select(CatalogItem).where(
            CatalogItem.public_title.in_(
                ["Сложный RFQ по упаковке и производственной сборке", "Сложный запрос по упаковке и производственной сборке"]
            )
        )
    ).all()
    if complex_catalog_items:
        # RU: После переименования entry-point в сложный запрос схлопываем старый RFQ title и случайные дубли, чтобы в каталоге оставалась одна каноническая карточка.
        complex_catalog_items = sorted(complex_catalog_items, key=lambda item: item.code)
        canonical_catalog_item = complex_catalog_items[0]
        canonical_catalog_item.public_title = "Сложный запрос по упаковке и производственной сборке"
        for duplicate in complex_catalog_items[1:]:
            for draft_item in session.scalars(select(DraftRequest).where(DraftRequest.catalog_item_id == duplicate.id)).all():
                draft_item.catalog_item_id = canonical_catalog_item.id
            for request_item in session.scalars(select(RequestRecord).where(RequestRecord.catalog_item_id == duplicate.id)).all():
                request_item.catalog_item_id = canonical_catalog_item.id
            for order_line in session.scalars(select(OrderLine).where(OrderLine.catalog_item_id == duplicate.id)).all():
                order_line.catalog_item_id = canonical_catalog_item.id
            session.delete(duplicate)
        session.flush()

    request_service = RequestIntakeService(session)
    sample_catalog = session.scalar(select(CatalogItem).where(CatalogItem.public_title == "Сложный запрос по упаковке и производственной сборке"))
    if sample_catalog is None:
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
            title="Нужен расчёт по сложной упаковке с ручным разбором",
            summary="Клиенту нужен расчёт по сложной упаковке с образцами, ограничениями и проверкой сроков.",
            item_service_context="Упаковка с образцами, несколькими вариантами материалов и ручной проверкой производственных ограничений.",
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
        seeded_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Нужен расчёт по сложной упаковке с ручным разбором"))
        if seeded_request is None:
            seeded_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Нужен расчёт по сложному RFQ"))
        if seeded_request is not None:
            seeded_request.title = "Нужен расчёт по сложной упаковке с ручным разбором"
            seeded_request.summary = "Клиенту нужен расчёт по сложной упаковке с образцами, ограничениями и проверкой сроков."
            seeded_request.item_service_context = "Упаковка с образцами, несколькими вариантами материалов и ручной проверкой производственных ограничений."
            session.flush()

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
                comparison_title="Базовый вариант предложения",
                comparison_rank=1,
                recommended=True,
                highlights=["Подтверждённый поставщик", "Срок 9 дней", "Проверка материалов и сроков"],
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

    order_seed_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Тираж на доставку и маркетплейсы"))
    if order_seed_request is None:
        order_seed_request = session.scalar(select(RequestRecord).where(RequestRecord.title == "Wave1 Demo Order Seed"))
    if order_seed_request is None:
        order_draft = request_service.create_draft(
            customer_email="order-demo@example.com",
            customer_name="Wave1 Order Demo",
            customer_phone="+84901110002",
            guest_company_name="Demo Brand Two",
            company_id=order_seed_company.id,
            catalog_item_id=sample_catalog.id if sample_catalog else None,
            title="Тираж на доставку и маркетплейсы",
            summary="Кейс для оплаты, подтверждения поставщика и дальнейшей доставки.",
            item_service_context="Поставка транспортной упаковки с проверкой оплаты, назначения поставщика и логистики.",
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
            public_summary="Коммерческий вариант для транспортной упаковки с оплатой и доставкой.",
            comparison_title="Основной вариант для заказа",
            comparison_rank=1,
            recommended=True,
            highlights=["Транспортная упаковка", "Подтверждённый вариант"],
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
    else:
        order_seed_request.summary = "Кейс для оплаты, подтверждения поставщика и дальнейшей доставки."
        order_seed_request.item_service_context = "Поставка транспортной упаковки с проверкой оплаты, назначения поставщика и логистики."
        if order_seed_request.title == "Wave1 Demo Order Seed":
            order_seed_request.title = "Тираж на доставку и маркетплейсы"
        session.flush()

    intake_seed_draft = session.scalar(select(DraftRequest).where(DraftRequest.title == "Нужен расчёт по сложному RFQ"))
    if intake_seed_draft is not None:
        intake_seed_draft.title = "Нужен расчёт по сложной упаковке с ручным разбором"
        intake_seed_draft.summary = "Клиенту нужен расчёт по сложной упаковке с образцами, ограничениями и проверкой сроков."
        intake_seed_draft.item_service_context = "Упаковка с образцами, несколькими вариантами материалов и ручной проверкой производственных ограничений."

    order_seed_draft = session.scalar(select(DraftRequest).where(DraftRequest.title == "Wave1 Demo Order Seed"))
    if order_seed_draft is not None:
        order_seed_draft.title = "Тираж на доставку и маркетплейсы"
        order_seed_draft.summary = "Кейс для оплаты, подтверждения поставщика и дальнейшей доставки."
        order_seed_draft.item_service_context = "Поставка транспортной упаковки с проверкой оплаты, назначения поставщика и логистики."

    if order_seed_request is not None:
        seeded_order = session.scalar(select(OrderRecord).where(OrderRecord.request_id == order_seed_request.id))
        if seeded_order is not None:
            seeded_order.customer_refs_json = {
                "customer_ref": order_seed_request.customer_ref,
                "request_title": order_seed_request.title,
                "customer_email": order_seed_request.customer_email,
                "customer_name": order_seed_request.customer_name,
                "customer_phone": order_seed_request.customer_phone,
                "guest_company_name": order_seed_request.guest_company_name,
            }
    session.flush()

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
