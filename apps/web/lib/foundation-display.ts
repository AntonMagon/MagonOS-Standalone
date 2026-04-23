// RU: Общий display-layer держит wave1-термины в одном месте, чтобы страницы не светили raw status-code и служебные fallbacks.

const DRAFT_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  awaiting_data: "Ждёт данные",
  ready_to_submit: "Готов к отправке",
  blocked: "Заблокирован",
  abandoned: "Брошен",
  archived: "Архивирован",
};

const REQUEST_STATUS_LABELS: Record<string, string> = {
  new: "Новая",
  needs_review: "На проверке",
  needs_clarification: "Нужно уточнение",
  supplier_search: "Поиск поставщика",
  offer_prep: "Подготовка предложения",
  offer_sent: "Предложение отправлено",
  converted_to_order: "Переведена в заказ",
  cancelled: "Отменена",
};

const OFFER_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик предложения",
  sent: "Отправлена",
  awaiting_confirmation: "Ждёт подтверждения",
  pending: "Ожидает ответа",
  revised: "Пересмотрена",
  accepted: "Подтверждена",
  declined: "Отклонена",
  expired: "Истекла",
  superseded: "Заменена новой версией",
};

const ORDER_STATUS_LABELS: Record<string, string> = {
  awaiting_confirmation: "Ждёт внутреннего подтверждения",
  awaiting_payment: "Ждёт оплату",
  paid: "Оплачен",
  supplier_assigned: "Поставщик назначен",
  in_production: "В производстве",
  partially_ready: "Частично готов",
  ready: "Готов",
  in_delivery: "В доставке",
  completed: "Завершён",
  cancelled: "Отменён",
  disputed: "Спор",
};

const PAYMENT_STATE_LABELS: Record<string, string> = {
  created: "Платёж создан",
  pending: "Ожидает подтверждения",
  confirmed: "Подтверждён",
  failed: "Не прошёл",
  partially_refunded: "Частичный возврат",
  refunded: "Возврат выполнен",
};

const FILE_STATE_LABELS: Record<string, string> = {
  uploaded: "Загружен",
  checking: "Проверяется",
  passed: "Проверка пройдена",
  failed: "Проверка не пройдена",
  needs_manual_review: "Ждёт ручную проверку",
  approved_final: "Финальная версия",
};

const DOCUMENT_STATE_LABELS: Record<string, string> = {
  draft: "Черновик",
  published: "Опубликован",
  sent: "Отправлен",
  confirmed: "Подтверждён",
  replaced: "Заменён",
  archived: "Архивирован",
};

const VISIBILITY_SCOPE_LABELS: Record<string, string> = {
  internal: "Только команда",
  operator: "Только оператор",
  customer: "Клиенту",
  supplier: "Поставщику",
  public: "Публично",
  admin: "Только администратору",
};

const SUPPLIER_TRUST_LABELS: Record<string, string> = {
  discovered: "Обнаружен",
  normalized: "Нормализован",
  contact_confirmed: "Контакт подтверждён",
  capability_confirmed: "Компетенции подтверждены",
  trusted: "Доверенный",
  blocked: "Заблокирован",
  archived: "Архивирован",
};

const SUPPLIER_STATUS_LABELS: Record<string, string> = {
  discovered: "Обнаружен",
  normalized: "Нормализован",
  contact_confirmed: "Контакт подтверждён",
  capability_confirmed: "Компетенции подтверждены",
  trusted: "Готов к работе",
  active: "Активен",
  blocked: "Заблокирован",
  archived: "Архивирован",
};

const LOGISTICS_STATE_LABELS: Record<string, string> = {
  planning: "Планируется",
  ready: "Готов к отгрузке",
  ready_partial: "Частично готов к отгрузке",
  partial_delivery: "Частичная доставка",
  delivered: "Доставлен",
  cancelled: "Отменён",
  disputed: "Спор",
};

const READINESS_STATE_LABELS: Record<string, string> = {
  not_ready: "Не готов",
  partial_ready: "Частично готов",
  ready: "Готов",
};

const REFUND_STATE_LABELS: Record<string, string> = {
  none: "Без возврата",
  partial_refund: "Частичный возврат",
  refunded: "Возврат выполнен",
};

const DISPUTE_STATE_LABELS: Record<string, string> = {
  clear: "Без спора",
  open: "Спор открыт",
};

const FILE_TYPE_LABELS: Record<string, string> = {
  attachment: "Вложение",
  brief: "Бриф",
  artwork: "Макет",
  document_generated: "Системный документ",
  invoice_like: "Счёт/платёжный документ",
  internal_job: "Внутреннее задание",
};

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  offer_proposal: "Коммерческое предложение",
  offer_confirmation: "Подтверждение предложения",
  invoice_like: "Счёт",
  internal_job: "Внутреннее задание",
};

function humanizeCode(value?: string | null): string {
  if (!value) {
    return "Не указано";
  }
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}

function fromMap(map: Record<string, string>, value?: string | null, fallback = "Не указано"): string {
  if (!value) {
    return fallback;
  }
  return map[value] ?? humanizeCode(value);
}

export function formatFoundationDate(value?: string | null, fallback = "Не указано"): string {
  if (!value) {
    return fallback;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ru-RU");
}

export function displayMaybe(value?: string | null, fallback = "Не указано"): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  const trimmed = String(value).trim();
  return trimmed || fallback;
}

export function displayDraftStatus(value?: string | null): string {
  return fromMap(DRAFT_STATUS_LABELS, value);
}

export function displayRequestStatus(value?: string | null): string {
  return fromMap(REQUEST_STATUS_LABELS, value);
}

export function displayOfferStatus(value?: string | null): string {
  return fromMap(OFFER_STATUS_LABELS, value);
}

export function displayOfferVersionStatus(value?: string | null): string {
  return fromMap(OFFER_STATUS_LABELS, value);
}

export function displayOrderStatus(value?: string | null): string {
  return fromMap(ORDER_STATUS_LABELS, value);
}

export function displayPaymentState(value?: string | null): string {
  return fromMap(PAYMENT_STATE_LABELS, value);
}

export function displayFileCheckState(value?: string | null): string {
  return fromMap(FILE_STATE_LABELS, value);
}

export function displayDocumentState(value?: string | null): string {
  return fromMap(DOCUMENT_STATE_LABELS, value);
}

export function displayVisibilityScope(value?: string | null): string {
  return fromMap(VISIBILITY_SCOPE_LABELS, value);
}

export function displaySupplierTrustLevel(value?: string | null): string {
  // RU: Уровень доверия к поставщику всегда показываем человеческой фразой, а не raw backend code.
  return fromMap(SUPPLIER_TRUST_LABELS, value);
}

export function displaySupplierStatus(value?: string | null): string {
  return fromMap(SUPPLIER_STATUS_LABELS, value);
}

export function displayLogisticsState(value?: string | null): string {
  return fromMap(LOGISTICS_STATE_LABELS, value);
}

export function displayReadinessState(value?: string | null): string {
  return fromMap(READINESS_STATE_LABELS, value);
}

export function displayRefundState(value?: string | null): string {
  return fromMap(REFUND_STATE_LABELS, value);
}

export function displayDisputeState(value?: string | null): string {
  return fromMap(DISPUTE_STATE_LABELS, value);
}

export function displayReasonCode(value?: string | null, title?: string | null): string {
  return displayMaybe(title, humanizeCode(value));
}

export function displayFileType(value?: string | null): string {
  return fromMap(FILE_TYPE_LABELS, value);
}

export function displayDocumentType(value?: string | null): string {
  return fromMap(DOCUMENT_TYPE_LABELS, value);
}

export const VISIBILITY_SCOPE_OPTIONS = [
  {value: "internal", label: "Только команда"},
  {value: "customer", label: "Клиенту"},
  {value: "supplier", label: "Поставщику"},
  {value: "public", label: "Публично"},
  {value: "admin", label: "Только администратору"},
] as const;

export const FILE_REVIEW_OPTIONS = [
  {value: "passed", label: "Проверка пройдена"},
  {value: "failed", label: "Проверка не пройдена"},
] as const;

export const FILE_TYPE_OPTIONS = [
  {value: "attachment", label: "Вложение"},
  {value: "brief", label: "Бриф"},
  {value: "artwork", label: "Макет"},
  {value: "document_generated", label: "Системный документ"},
  {value: "invoice_like", label: "Счёт/платёжный документ"},
  {value: "internal_job", label: "Внутреннее задание"},
] as const;

export const ORDER_ACTION_LABELS: Record<string, string> = {
  assign_supplier: "Назначить поставщика",
  confirm_start: "Подтвердить старт",
  mark_production: "Перевести в производство",
  ready: "Отметить готовность",
  delivery: "Передать в доставку",
  complete: "Завершить заказ",
  cancel: "Отменить заказ",
  dispute: "Открыть спор",
};
