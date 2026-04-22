type Locale = 'ru' | 'en';

type LocalizedText = {
  ru: string;
  en: string;
};

type ReferenceItem = {
  name: string;
  summary: LocalizedText;
  usage: LocalizedText;
};

type ReferenceGroup = {
  id: string;
  title: LocalizedText;
  text: LocalizedText;
  items: ReferenceItem[];
};

type DependencyGroup = {
  id: string;
  title: LocalizedText;
  text: LocalizedText;
  bullets: LocalizedText[];
};

type RoleGuide = {
  id: string;
  role: LocalizedText;
  text: LocalizedText;
  routes: string[];
};

// RU: Эта карта нужна как быстрый shell-reference по сущностям и boundaries, а не как второй planning-doc вместо wave1-спецификации.
function pick(locale: Locale, value: LocalizedText) {
  return locale === 'ru' ? value.ru : value.en;
}

const entityGroups: ReferenceGroup[] = [
  {
    id: 'identity',
    title: {
      ru: 'Доступ и роли',
      en: 'Access and roles',
    },
    text: {
      ru: 'Эти сущности определяют, кто заходит в систему и какой контур ему можно видеть.',
      en: 'These entities define who enters the system and which contour they are allowed to see.',
    },
    items: [
      {
        name: 'UserAccount / UserRoleBinding / UserSession',
        summary: {
          ru: 'Пользователь, его роли и живая сессия standalone-shell.',
          en: 'The user, role bindings, and the active standalone-shell session.',
        },
        usage: {
          ru: 'Используй, когда нужно войти в систему, ограничить доступ или показать правильный рабочий экран по роли.',
          en: 'Use this when signing in, enforcing access, or deciding which working surface to show by role.',
        },
      },
      {
        name: 'RoleDefinition',
        summary: {
          ru: 'Нормализованный каталог ролей вроде admin, operator, customer.',
          en: 'The normalized role catalog such as admin, operator, customer.',
        },
        usage: {
          ru: 'Нужен для role-scoped visibility, dashboard access и запрета критичных действий не той роли.',
          en: 'Needed for role-scoped visibility, dashboard access, and blocking critical actions for the wrong role.',
        },
      },
      {
        name: 'Company',
        summary: {
          ru: 'Подтверждённая бизнес-сущность клиента или контрагента внутри автономного контура.',
          en: 'The confirmed business entity for a customer or counterparty inside the standalone contour.',
        },
        usage: {
          ru: 'Это каноническая карточка компании, вокруг которой строятся коммерческий контекст и рабочие переходы.',
          en: 'This is the canonical company record around which commercial context and operational transitions are built.',
        },
      },
    ],
  },
  {
    id: 'supplier',
    title: {
      ru: 'Поставщики и импорт',
      en: 'Suppliers and ingest',
    },
    text: {
      ru: 'Этот контур ведёт сырой входной поток поставщиков к нормализованной и пригодной для работы записи.',
      en: 'This contour moves raw supplier intake into a normalized record that operators can actually use.',
    },
    items: [
      {
        name: 'SupplierSourceRegistry',
        summary: {
          ru: 'Реестр источников импорта: fixture, live parsing и будущие адаптеры.',
          en: 'Registry of ingest sources: fixture, live parsing, and future adapters.',
        },
        usage: {
          ru: 'Используй, когда оператор выбирает, откуда запускать импорт и как читать состояние адаптера.',
          en: 'Use this when the operator chooses where to run ingest from and how to read adapter health.',
        },
      },
      {
        name: 'SupplierRawIngest',
        summary: {
          ru: 'Конкретный запуск импорта с raw-count, normalized-count, failure detail и retry history.',
          en: 'A concrete ingest run with raw-count, normalized-count, failure detail, and retry history.',
        },
        usage: {
          ru: 'Открывай эту сущность, если нужно понять async-state parsing job, причину сбоя или повторный запуск.',
          en: 'Open this entity when you need to understand the async parsing job state, failure reason, or retry path.',
        },
      },
      {
        name: 'SupplierCompany / SupplierSite / SupplierDedupCandidate',
        summary: {
          ru: 'Нормализованные поставщики, их площадки и спорные дубль-кандидаты.',
          en: 'Normalized suppliers, their sites, and contested duplicate candidates.',
        },
        usage: {
          ru: 'Используй это после ingest, когда надо подтвердить доверие, объединить дубли или открыть рабочую карточку площадки.',
          en: 'Use these after ingest when you need to confirm trust, merge duplicates, or open a working site card.',
        },
      },
    ],
  },
  {
    id: 'commercial',
    title: {
      ru: 'Коммерческая цепочка',
      en: 'Commercial chain',
    },
    text: {
      ru: 'Это ядро первой волны: lead capture, ручная квалификация, предложение и перевод в заказ.',
      en: 'This is the wave1 core: lead capture, manual qualification, offer, and conversion into order.',
    },
    items: [
      {
        name: 'DraftRequest',
        summary: {
          ru: 'Гостевой или customer-facing черновик с autosave и submit-guard.',
          en: 'A guest or customer-facing draft with autosave and submit guards.',
        },
        usage: {
          ru: 'Используй на публичном входе, когда ещё рано создавать полную заявку, но уже нужно собирать намерение клиента.',
          en: 'Use it at the public intake stage when it is too early for a full request but the customer intent must already be captured.',
        },
      },
      {
        name: 'RequestRecord',
        summary: {
          ru: 'Операторская заявка с review, clarification, blockers и supplier search.',
          en: 'The operator-owned request with review, clarification, blockers, and supplier search.',
        },
        usage: {
          ru: 'Это главный рабочий объект intake-команды. Отсюда идут timeline, offer prep, файлы и причины блокировки.',
          en: 'This is the main intake-team working object. It drives the timeline, offer prep, files, and blocking reasons.',
        },
      },
      {
        name: 'OfferRecord / OfferVersion',
        summary: {
          ru: 'Коммерческое предложение и его версии без смешивания с request или order.',
          en: 'The commercial offer and its revisions without mixing it with request or order.',
        },
        usage: {
          ru: 'Используй, когда надо вести сравнение ревизий, подтверждение клиентом и explainable переход в accepted/declined/expired.',
          en: 'Use these when handling revision comparison, customer confirmation, and the explainable transition into accepted/declined/expired.',
        },
      },
      {
        name: 'OrderRecord',
        summary: {
          ru: 'Тонкий оркестратор исполнения после принятого предложения.',
          en: 'The thin execution orchestrator after an accepted offer.',
        },
        usage: {
          ru: 'Открывай, когда предложение принято и нужно вести оплату-скелет, supplier assignment, production state и delivery state.',
          en: 'Open it once the offer is accepted and you need to track payment skeleton, supplier assignment, production state, and delivery state.',
        },
      },
    ],
  },
  {
    id: 'supporting',
    title: {
      ru: 'Файлы, документы, правила и аудит',
      en: 'Files, documents, rules, and audit',
    },
    text: {
      ru: 'Эти сущности не живут сами по себе: они поддерживают основную цепочку и делают автоматизацию объяснимой.',
      en: 'These entities do not live on their own: they support the main chain and keep automation explainable.',
    },
    items: [
      {
        name: 'ManagedFile / ManagedDocument',
        summary: {
          ru: 'Версионируемые файлы и документы, привязанные к request или order.',
          en: 'Versioned files and documents attached to a request or order.',
        },
        usage: {
          ru: 'Используй, когда нужен контролируемый download-flow, шаблоны, проверки и история версий по рабочему объекту.',
          en: 'Use these when you need controlled download flow, templates, checks, and version history for a working object.',
        },
      },
      {
        name: 'RuleDefinition / RuleVersion / ReasonCodeCatalog',
        summary: {
          ru: 'Правила переходов, их версии и каталог причин для explainability-first automation.',
          en: 'Transition rules, their versions, and the reason-code catalog for explainability-first automation.',
        },
        usage: {
          ru: 'Нужны там, где переход может быть запрещён, отложен или требовать объяснимую причину.',
          en: 'Needed anywhere a transition may be blocked, delayed, or require an explainable reason.',
        },
      },
      {
        name: 'NotificationRule / EscalationHint',
        summary: {
          ru: 'Базовый контур уведомлений без спама и лёгкие подсказки по SLA/escalation.',
          en: 'The baseline notification contour without spam and lightweight SLA/escalation hints.',
        },
        usage: {
          ru: 'Используй для role-scoped уведомлений, overdue-подсказок и операторских рабочих столов.',
          en: 'Use these for role-scoped notifications, overdue hints, and operator dashboards.',
        },
      },
      {
        name: 'AuditEvent / MessageEvent',
        summary: {
          ru: 'Канонический аудит и его timeline-проекция для интерфейса.',
          en: 'Canonical audit and its timeline projection for the interface.',
        },
        usage: {
          ru: 'Это главный ответ на вопрос «что произошло и почему». С него читаются timeline, reason display и уведомления.',
          en: 'This is the main answer to “what happened and why”. Timeline, reason display, and notifications read from it.',
        },
      },
    ],
  },
];

const dependencyGroups: DependencyGroup[] = [
  {
    id: 'product-shell',
    title: {
      ru: 'Web-shell -> foundation API',
      en: 'Web shell -> foundation API',
    },
    text: {
      ru: 'Пользовательский интерфейс в `apps/web` не должен держать бизнес-логику внутри себя: он работает как оболочка над foundation API.',
      en: 'The user interface in `apps/web` should not embed business logic: it acts as a shell over the foundation API.',
    },
    bullets: [
      {
        ru: 'Публичные страницы ведут в draft/request flow и не смешиваются с operator-admin представлением.',
        en: 'Public pages lead into the draft/request flow and do not mix with operator-admin representations.',
      },
      {
        ru: 'Operator screens читают request, offer, order, supplier и audit-контур через отдельные API-модули.',
        en: 'Operator screens read the request, offer, order, supplier, and audit contours through dedicated API modules.',
      },
    ],
  },
  {
    id: 'foundation-core',
    title: {
      ru: 'Foundation core -> БД и миграции',
      en: 'Foundation core -> DB and migrations',
    },
    text: {
      ru: 'Модульный монолит держит состояние через SQLAlchemy-модели и Alembic-миграции. Новая бизнес-сущность без миграции считается неполной.',
      en: 'The modular monolith stores state through SQLAlchemy models and Alembic migrations. A new business entity without a migration is incomplete.',
    },
    bullets: [
      {
        ru: 'Изменение статуса, причин или timeline почти всегда означает изменение модели, API и тестов вместе.',
        en: 'A change in statuses, reasons, or timeline almost always means model, API, and tests change together.',
      },
      {
        ru: 'Правила первой волны не живут в UI-константах: они идут через persistence и rules engine.',
        en: 'Wave1 rules do not live in UI constants: they go through persistence and the rules engine.',
      },
    ],
  },
  {
    id: 'async-adapters',
    title: {
      ru: 'Async и adapters boundary',
      en: 'Async and adapters boundary',
    },
    text: {
      ru: 'Асинхронность и внешние интеграции вынесены в явную границу, чтобы ядро не зависело от конкретного провайдера.',
      en: 'Async work and external integrations are kept behind an explicit boundary so the core does not depend on a specific provider.',
    },
    bullets: [
      {
        ru: 'Supplier parsing живёт через `integrations/foundation/*` и queue/retry state в `SupplierRawIngest`.',
        en: 'Supplier parsing lives through `integrations/foundation/*` and queue/retry state in `SupplierRawIngest`.',
      },
      {
        ru: 'Files/documents должны проходить через storage abstraction, а не напрямую шить путь к диску в workflow.',
        en: 'Files/documents should go through a storage abstraction rather than hard-coding filesystem paths into the workflow.',
      },
    ],
  },
  {
    id: 'truth-and-docs',
    title: {
      ru: 'Source-of-truth и docs boundary',
      en: 'Source-of-truth and docs boundary',
    },
    text: {
      ru: 'Плановая истина живёт в `gpt_doc`, а текущий runtime-контур должен читаться из кода, тестов и текущих docs в standalone-репозитории.',
      en: 'Planning truth lives in `gpt_doc`, while the current runtime contour must be read from code, tests, and current docs inside the standalone repo.',
    },
    bullets: [
      {
        ru: 'Если документация и код расходятся, сначала проверяй код и verification path, потом обновляй docs.',
        en: 'If docs and code drift apart, inspect code and the verification path first, then update docs.',
      },
      {
        ru: 'Эта справка нужна как быстрый вход, но не заменяет `docs/current-project-state.md` и wave1-спецификацию.',
        en: 'This reference is a fast entry point, but it does not replace `docs/current-project-state.md` or the wave1 spec.',
      },
    ],
  },
];

const roleGuides: RoleGuide[] = [
  {
    id: 'guest-customer',
    role: {
      ru: 'Гость / клиент',
      en: 'Guest / customer',
    },
    text: {
      ru: 'Используй публичный слой для маркетинга, витрины, RFQ и draft. Клиент не должен попадать во внутренние operator-экраны.',
      en: 'Use the public layer for marketing, showcase, RFQ, and draft. The customer must not land inside internal operator screens.',
    },
    routes: ['/', '/marketing', '/catalog', '/rfq', '/drafts/{draftCode}', '/requests/{customerRef}'],
  },
  {
    id: 'operator',
    role: {
      ru: 'Оператор',
      en: 'Operator',
    },
    text: {
      ru: 'Оператор ведёт intake, clarification, supplier search, offer prep, файлы, документы и supplier parsing.',
      en: 'The operator handles intake, clarification, supplier search, offer prep, files, documents, and supplier parsing.',
    },
    routes: ['/request-workbench', '/request-workbench/{requestCode}', '/orders', '/suppliers', '/supplier-ingests/{ingestCode}'],
  },
  {
    id: 'admin',
    role: {
      ru: 'Администратор',
      en: 'Administrator',
    },
    text: {
      ru: 'Админ видит dashboards, audit, rules, notifications и может проверять ширину контура, а не только один кейс.',
      en: 'The admin sees dashboards, audit, rules, notifications, and can inspect the contour at a system level rather than a single case.',
    },
    routes: ['/dashboard', '/admin-dashboard', '/ops-workbench', '/project-map', '/reference'],
  },
];

const waveExclusions: LocalizedText[] = [
  {
    ru: 'Полный supplier portal и самостоятельный supplier self-service.',
    en: 'A full supplier portal and standalone supplier self-service.',
  },
  {
    ru: 'Тяжёлый payment-core, бухгалтерия и полный ERP order management.',
    en: 'Heavy payment core, accounting, and full ERP order management.',
  },
  {
    ru: 'Склад, MES, production planning и широкая канал-страна матрица.',
    en: 'Warehouse, MES, production planning, and broad country/channel coverage.',
  },
  {
    ru: 'Обязательный heavy AI contour или vector DB как центральный runtime.',
    en: 'Mandatory heavy AI contour or a vector DB as a central runtime.',
  },
];

export function getPlatformReference(localeInput: string) {
  const locale: Locale = localeInput === 'ru' ? 'ru' : 'en';

  return {
    entityGroups: entityGroups.map((group) => ({
      id: group.id,
      title: pick(locale, group.title),
      text: pick(locale, group.text),
      items: group.items.map((item) => ({
        name: item.name,
        summary: pick(locale, item.summary),
        usage: pick(locale, item.usage),
      })),
    })),
    dependencyGroups: dependencyGroups.map((group) => ({
      id: group.id,
      title: pick(locale, group.title),
      text: pick(locale, group.text),
      bullets: group.bullets.map((item) => pick(locale, item)),
    })),
    roleGuides: roleGuides.map((guide) => ({
      id: guide.id,
      role: pick(locale, guide.role),
      text: pick(locale, guide.text),
      routes: guide.routes,
    })),
    waveExclusions: waveExclusions.map((item) => pick(locale, item)),
  };
}
