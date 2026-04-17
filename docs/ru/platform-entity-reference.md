# Справка по сущностям и зависимостям standalone-контура

## Зачем это нужно

Эта справка нужна как быстрый рабочий вход в текущий wave1-контур.
Она отвечает на три вопроса:

- что это за сущность;
- в каком экране с ней реально работают;
- от каких слоёв и зависимостей она зависит.

Это не замена `gpt_doc/codex_wave1_spec_ru.docx`.
Это прикладная карта уже реализованного standalone-контура.

## Главная цепочка первой волны

Канонический поток:

`storefront / RFQ -> Draft -> Request -> Offer(versioned) -> accepted Offer -> Order`

Важно:

- `Draft`, `Request`, `Offer`, `Order` не смешиваются в одну универсальную запись.
- У каждого объекта свои статусы, причины, audit trail и transition guards.

## Ключевые сущности

### Доступ и роли

- `UserAccount`
  - канонический пользователь standalone-контура
  - нужен для входа, роли и доступа к рабочим поверхностям
- `UserRoleBinding`
  - связывает пользователя с ролью
  - нужен для role-scoped visibility и запрета действий не той роли
- `UserSession`
  - живая сессия shell
  - определяет, какой экран открывать после входа
- `RoleDefinition`
  - каталог ролей `admin / operator / customer / guest`

### Бизнес-сущности

- `Company`
  - подтверждённая компания внутри standalone
  - базовый business anchor для коммерческого контекста

### Поставщики и импорт

- `SupplierSourceRegistry`
  - источник импорта поставщиков
  - сейчас используется для fixture-ingest и live parsing
- `SupplierRawIngest`
  - один запуск импорта
  - хранит async-state, retry history, failure detail, counts
- `SupplierCompany`
  - нормализованная карточка поставщика
- `SupplierSite`
  - площадка / сайт поставщика
- `SupplierDedupCandidate`
  - спорный дубль, который нужно разобрать оператором

### Intake и коммерция

- `DraftRequest`
  - guest/customer-facing черновик
  - нужен до того, как оператор возьмёт кейс в полноценную заявку
- `RequestRecord`
  - операторская заявка
  - главный intake-объект для review, clarification, blockers и supplier search
- `OfferRecord`
  - коммерческое предложение как отдельная сущность
- `OfferVersion`
  - ревизии предложения
  - нужны для compare-flow и подтверждения без потери истории
- `OrderRecord`
  - тонкий execution-слой после принятого предложения

### Файлы, документы, правила, аудит

- `ManagedFile`
  - управляемый файл, привязанный к request/order
- `ManagedDocument`
  - управляемый документ, привязанный к request/order
- `RuleDefinition`
  - правило перехода или критичного действия
- `RuleVersion`
  - версия правила
- `ReasonCodeCatalog`
  - каталог explainable причин
- `NotificationRule`
  - baseline-правило уведомлений
- `EscalationHint`
  - лёгкий SLA/escalation слой первой волны
- `AuditEvent`
  - канонический журнал событий
- `MessageEvent`
  - timeline/notification-проекция для интерфейса

## Где с этим работать в интерфейсе

### Гость / клиент

Использует:

- `/`
- `/marketing`
- `/catalog`
- `/rfq`
- `/drafts/{draftCode}`
- `/requests/{customerRef}`

Что делает:

- оставляет lead;
- собирает draft;
- отправляет request-вход;
- читает customer-facing состояние и предложения.

### Оператор

Использует:

- `/request-workbench`
- `/request-workbench/{requestCode}`
- `/orders`
- `/orders/{orderCode}`
- `/suppliers`
- `/supplier-ingests/{ingestCode}`

Что делает:

- ведёт review и clarification;
- ищет поставщиков;
- собирает предложение;
- переводит accepted offer в order;
- работает с файлами, документами и parsing/retry.

### Администратор

Использует:

- `/dashboard`
- `/admin-dashboard`
- `/ops-workbench`
- `/project-map`
- `/reference`

Что делает:

- смотрит весь contour шире одного кейса;
- читает audit, timelines, rules, notifications;
- проверяет текущие границы и риски.

## Зависимости и boundaries

### `apps/web -> foundation API`

- UI не должен хранить главную бизнес-логику в себе.
- Shell показывает рабочие поверхности, а поведение идёт через foundation API.

### `foundation -> models + migrations`

- Бизнес-сущность без модели, миграции и теста считается неполной.
- Новый статус или новый reason-code почти всегда означает изменение persistence-слоя.

### `foundation -> integrations`

- Внешние источники и адаптеры живут в `src/magon_standalone/integrations/foundation/*`
- Нельзя вшивать parsing/storage-специфику прямо в ядро.

### `audit/rules/notifications`

- Автоматизация первой волны должна быть explainable.
- Критичный переход должен иметь:
  - guard;
  - reason code;
  - audit event;
  - role restriction;
  - понятный explainability payload.

## Как этим пользоваться при доработке

Если нужно менять продуктовый поток:

1. Найди, какая сущность реально владеет этапом.
2. Проверь, в каком экране она живёт.
3. Проверь, не нарушает ли изменение границу `Draft / Request / Offer / Order`.
4. Проверь, не утекает ли логика наружу из adapters boundary.
5. Добавь или обнови:
   - модель / миграцию;
   - API;
   - UI;
   - тест;
   - docs/ru.

Если неясно, куда ложится новая логика:

- если это public intake -> скорее `Draft` или public request view;
- если это operator review -> скорее `Request`;
- если это коммерческая ревизия -> `Offer` и `OfferVersion`;
- если это исполнение после согласования -> `Order`;
- если это parsing/ingest -> supplier source + `SupplierRawIngest`;
- если это "что произошло и почему" -> `AuditEvent` / `MessageEvent` / `ReasonCodeCatalog`.

## Что не входит в первую волну

Сознательно вне текущего контура:

- полный supplier portal;
- тяжёлый payment-core и бухгалтерия;
- склад и MES;
- broad country/channel coverage;
- heavy AI contour и обязательная vector DB.

## Связанные материалы

- planning truth: `gpt_doc/codex_wave1_spec_ru.docx`
- runtime truth: `docs/current-project-state.md`
- русская runtime-версия: `docs/ru/current-project-state.md`
- архитектурная карта: `docs/ru/foundation-architecture-as-built.md`
