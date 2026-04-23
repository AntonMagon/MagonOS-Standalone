"use client";
// RU: Компонент собирает wave1 dashboards только из role-scoped API payloads и не склеивает customer/operator/admin данные.
// RU: Быстрый переход в admin-config делает настройку правил частью рабочего dashboard-контура.

import type {Route} from "next";
import Link from "next/link";
import {type ReactNode, useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, useFoundationSession} from "@/lib/foundation-client";
import {
  displayOfferStatus,
  displayOrderStatus,
  displayReasonCode,
  displayRequestStatus,
  displaySupplierStatus,
  displaySupplierTrustLevel,
  displayVisibilityScope,
  formatFoundationDate,
} from "@/lib/foundation-display";

// RU: Карточки dashboards должны вести дальше по клику и не оставаться purely informational summary без рабочего объекта.
type CountMap = Record<string, number>;

type ReasonDisplay = {
  code: string;
  title: string;
  category: string;
  severity: string;
};

type NotificationItem = {
  code: string;
  entry_kind: string;
  entity_type?: string | null;
  entity_code?: string | null;
  event_type?: string | null;
  title?: string | null;
  body?: string | null;
  reason_code?: string | null;
  reason_display?: ReasonDisplay | null;
  visibility_scope?: string | null;
  created_at?: string | null;
  payload?: Record<string, unknown> | null;
};

type BlockedItem = {
  kind: string;
  owner_code: string;
  status: string;
  reason_code: string;
  reason_display?: ReasonDisplay | null;
  note?: string | null;
  due_at?: string | null;
  created_at?: string | null;
  request_ref?: string | null;
};

function displayBlockedKind(kind: string): string {
  if (kind === "request_blocker") return "Блокер заявки";
  if (kind === "request_deadline") return "Просрочка по заявке";
  if (kind === "offer_confirmation") return "Задержка подтверждения оффера";
  if (kind === "supplier_blocked") return "Заблокированный поставщик";
  return kind;
}

function displayBlockedStatus(kind: string, status: string): string {
  if (kind.startsWith("request_")) return displayRequestStatus(status);
  if (kind.startsWith("offer_")) return displayOfferStatus(status);
  if (kind.startsWith("supplier_")) return displaySupplierStatus(status);
  if (kind.startsWith("order_")) return displayOrderStatus(status);
  return status;
}

function displayAdminMetricKey(key: string): string {
  if (key === "users") return "Пользователи";
  if (key === "rules") return "Правила";
  if (key === "rule_versions") return "Версии правил";
  if (key === "message_events") return "События хронологии";
  if (key === "notifications") return "Уведомления";
  return key;
}

type OfferPendingItem = {
  code: string;
  request_ref?: string | null;
  offer_status?: string | null;
  confirmation_state?: string | null;
  updated_at?: string | null;
};

type SupplierItem = {
  code: string;
  display_name: string;
  trust_level: string;
  supplier_status: string;
  blocked_reason?: string | null;
  capability_summary?: string | null;
};

type OperatorWorkbenchPayload = {
  requests_by_status: CountMap;
  offers_by_status: CountMap;
  orders_by_state: CountMap;
  suppliers_by_trust: CountMap;
  suppliers_by_status: CountMap;
  notifications: NotificationItem[];
  blocked_items: BlockedItem[];
  overdue_items: BlockedItem[];
  offers_pending_confirmation: OfferPendingItem[];
};

type ProcessingDashboardPayload = {
  requests_by_status: CountMap;
  orders_by_state: CountMap;
  offers_pending_confirmation: OfferPendingItem[];
  blocked_items: BlockedItem[];
  overdue_items: BlockedItem[];
};

type SupplyDashboardPayload = {
  suppliers_by_trust: CountMap;
  suppliers_by_status: CountMap;
  blocked_suppliers: SupplierItem[];
  top_suppliers: SupplierItem[];
};

type AdminDashboardPayload = {
  counts: {
    users: number;
    rules: number;
    rule_versions: number;
    message_events: number;
    notifications: number;
  };
  requests_by_status: CountMap;
  offers_by_status: CountMap;
  orders_by_state: CountMap;
  suppliers_by_trust: CountMap;
  suppliers_by_status: CountMap;
  notifications: NotificationItem[];
  blocked_items: BlockedItem[];
  overdue_items: BlockedItem[];
  telemetry: Record<string, unknown>;
};

function resolveOwnerHref(ownerType?: string | null, ownerCode?: string | null): string | null {
  if (!ownerType || !ownerCode) return null;
  if (ownerType === "request") return `/request-workbench/${ownerCode}`;
  if (ownerType === "order") return `/orders/${ownerCode}`;
  if (ownerType === "supplier" || ownerType === "supplier_company") return `/suppliers/${ownerCode}`;
  return null;
}

function resolveNotificationHref(item: NotificationItem): string | null {
  const payload = item.payload ?? {};
  const payloadRequestCode = typeof payload.request_code === "string" ? payload.request_code : null;
  const payloadRequestRef = typeof payload.request_ref === "string" ? payload.request_ref : null;
  const payloadOrderCode = typeof payload.order_code === "string" ? payload.order_code : null;
  const payloadSupplierCode = typeof payload.supplier_code === "string" ? payload.supplier_code : null;
  const payloadOwnerType = typeof payload.owner_type === "string" ? payload.owner_type : null;
  const payloadOwnerCode = typeof payload.owner_code === "string" ? payload.owner_code : null;

  if (item.entity_type === "order" || payloadOrderCode) {
    return `/orders/${payloadOrderCode ?? item.entity_code ?? ""}`;
  }
  if (item.entity_type === "request" || payloadRequestCode) {
    return `/request-workbench/${payloadRequestCode ?? item.entity_code ?? ""}`;
  }
  if (item.entity_type === "offer" || payloadRequestRef) {
    return payloadRequestRef ? `/request-workbench/${payloadRequestRef}` : null;
  }
  if (item.entity_type === "supplier" || item.entity_type === "supplier_company" || payloadSupplierCode) {
    return `/suppliers/${payloadSupplierCode ?? item.entity_code ?? ""}`;
  }
  return resolveOwnerHref(payloadOwnerType, payloadOwnerCode);
}

function resolveBlockedHref(item: BlockedItem): string | null {
  if (item.kind.startsWith("request_")) return `/request-workbench/${item.owner_code}`;
  if (item.kind.startsWith("supplier_")) return `/suppliers/${item.owner_code}`;
  if (item.kind.startsWith("offer_") && item.request_ref) return `/request-workbench/${item.request_ref}`;
  return null;
}

function resolveOfferPendingHref(item: OfferPendingItem): string | null {
  return item.request_ref ? `/request-workbench/${item.request_ref}` : null;
}

function CountSection({
  title,
  counts,
  formatKey,
  href,
  actionLabel,
}: {
  title: string;
  counts: CountMap;
  formatKey?: (key: string) => string;
  href?: string;
  actionLabel?: string;
}) {
  const entries = Object.entries(counts);
  return (
    <Card className="glass-panel border-white/12 p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl">{title}</h2>
        {href ? (
          <Link href={href as Route} className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground">
            {actionLabel ?? "Открыть"}
          </Link>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {entries.map(([key, value]) => {
          const content = (
            <div className="rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
              {/* RU: Summary-карточка тоже ведёт дальше по клику, чтобы dashboard не был тупиковой сводкой. */}
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{formatKey ? formatKey(key) : key}</div>
              <div className="mt-2 text-3xl leading-none">{value}</div>
            </div>
          );
          return href ? <Link key={key} href={href as Route} className="block">{content}</Link> : <div key={key}>{content}</div>;
        })}
        {!entries.length ? <div className="text-sm text-muted-foreground">Пока нет данных.</div> : null}
      </div>
    </Card>
  );
}

function NotificationSection({title, items}: {title: string; items: NotificationItem[]}) {
  return (
    <Card className="glass-panel border-white/12 p-5">
      <h2 className="text-xl">{title}</h2>
      <div className="mt-4 space-y-3 text-sm">
        {items.map((item) => {
          const href = resolveNotificationHref(item);
          const content = (
            <div className="rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
              <div className="flex items-start justify-between gap-3">
                <div className="font-medium">{item.title ?? displayReasonCode(item.reason_code, item.reason_display?.title) ?? item.code}</div>
                {href ? <div className="text-[11px] uppercase tracking-[0.18em] text-primary/80">Открыть</div> : null}
              </div>
              {item.body ? <div className="mt-2 text-foreground/80">{item.body}</div> : null}
              <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {displayVisibilityScope(item.visibility_scope)} · {formatFoundationDate(item.created_at)}
              </div>
            </div>
          );
          return href ? <Link key={item.code} href={href as Route} className="block">{content}</Link> : <div key={item.code}>{content}</div>;
        })}
        {!items.length ? <div className="text-sm text-muted-foreground">Нет активных уведомлений.</div> : null}
      </div>
    </Card>
  );
}

function BlockedSection({title, items}: {title: string; items: BlockedItem[]}) {
  return (
    <Card className="glass-panel border-white/12 p-5">
      <h2 className="text-xl">{title}</h2>
      <div className="mt-4 space-y-3 text-sm">
        {items.map((item, index) => {
          const href = resolveBlockedHref(item);
          const content = (
            <div className="rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{item.owner_code}</div>
                  <div className="mt-1 text-muted-foreground">
                    {displayReasonCode(item.reason_code, item.reason_display?.title)} · {displayBlockedStatus(item.kind, item.status)}
                  </div>
                </div>
                <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {displayBlockedKind(item.kind)}
                  {href ? <span className="ml-2 text-primary/80">· открыть</span> : null}
                </div>
              </div>
              {item.note ? <div className="mt-2 text-foreground/80">{item.note}</div> : null}
              <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {formatFoundationDate(item.due_at ?? item.created_at)}
              </div>
            </div>
          );
          return href ? (
            <Link key={`${item.owner_code}-${item.reason_code}-${index}`} href={href as Route} className="block">
              {content}
            </Link>
          ) : (
            <div key={`${item.owner_code}-${item.reason_code}-${index}`}>{content}</div>
          );
        })}
        {!items.length ? <div className="text-sm text-muted-foreground">Нет элементов.</div> : null}
      </div>
    </Card>
  );
}

function OffersPendingSection({items}: {items: OfferPendingItem[]}) {
  return (
    <Card className="glass-panel border-white/12 p-5">
      <h2 className="text-xl">Предложения, ожидающие подтверждения</h2>
      <div className="mt-4 space-y-3 text-sm">
        {items.map((item) => {
          const href = resolveOfferPendingHref(item);
          const content = (
            <div className="rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
              <div className="flex items-start justify-between gap-3">
                <div className="font-medium">{item.code}</div>
                {href ? <div className="text-[11px] uppercase tracking-[0.18em] text-primary/80">Открыть заявку</div> : null}
              </div>
              <div className="mt-1 text-muted-foreground">
                {item.request_ref ?? "без привязки к заявке"} · {displayOfferStatus(item.confirmation_state === "pending" ? item.offer_status : item.confirmation_state)}
              </div>
              <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">{formatFoundationDate(item.updated_at)}</div>
            </div>
          );
          return href ? <Link key={item.code} href={href as Route} className="block">{content}</Link> : <div key={item.code}>{content}</div>;
        })}
        {!items.length ? <div className="text-sm text-muted-foreground">Нет офферов, ожидающих подтверждения.</div> : null}
      </div>
    </Card>
  );
}

function SessionGate({title, description, children}: {title: string; description: string; children: ReactNode}) {
  // RU: Gate использует session hook, чтобы дашборды не гидратировались сначала как guest, а потом как operator/admin.
  const session = useFoundationSession();
  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">{title}</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">{description}</p>
          <div className="mt-6">
            <Link href="/login">
              <Button>Открыть вход</Button>
            </Link>
          </div>
        </Card>
      </main>
    );
  }
  return <>{children}</>;
}

function WorkbenchLinks() {
  return (
    <div className="flex flex-wrap gap-2">
      <Link href="/request-workbench"><Button variant="secondary">Заявки</Button></Link>
      <Link href="/orders"><Button variant="secondary">Заказы</Button></Link>
      <Link href="/suppliers"><Button variant="secondary">Поставщики</Button></Link>
      <Link href="/processing-dashboard"><Button variant="secondary">Производство</Button></Link>
      <Link href="/supply-dashboard"><Button variant="secondary">Снабжение</Button></Link>
      <Link href="/admin-dashboard"><Button variant="secondary">Обзор админа</Button></Link>
      <Link href="/admin-config"><Button variant="secondary">Настройка системы</Button></Link>
    </div>
  );
}

export function OperatorWorkbenchView() {
  const session = useFoundationSession();
  const [payload, setPayload] = useState<OperatorWorkbenchPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!session?.token) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFoundationJson<OperatorWorkbenchPayload>("/api/v1/operator/workbench", {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "operator_workbench_load_failed");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [session?.token]);

  return (
    <SessionGate title="Операторский рабочий стол" description="Для панели оператора нужен действующий токен с ролью оператора или администратора.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="micro-label">Рабочий стол оператора</div>
              <h1 className="mt-2 text-3xl leading-tight">Операторский рабочий стол</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Этот экран нужен не для отчёта, а для приоритизации. Здесь видно, какие заявки, предложения и поставщики требуют действия прямо сейчас.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка операторского рабочего стола...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Заявки по статусам" counts={payload.requests_by_status} formatKey={displayRequestStatus} href="/request-workbench" actionLabel="Открыть заявки" />
              <CountSection title="Заказы по состоянию" counts={payload.orders_by_state} formatKey={displayOrderStatus} href="/orders" actionLabel="Открыть заказы" />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <CountSection title="Предложения по статусам" counts={payload.offers_by_status} formatKey={displayOfferStatus} href="/request-workbench" actionLabel="Открыть предложения" />
              <CountSection title="Поставщики по доверию" counts={payload.suppliers_by_trust} formatKey={displaySupplierTrustLevel} href="/suppliers" actionLabel="Открыть поставщиков" />
              <CountSection title="Поставщики по статусам" counts={payload.suppliers_by_status} formatKey={displaySupplierStatus} href="/suppliers" actionLabel="Открыть поставщиков" />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <BlockedSection title="Заблокированные элементы" items={payload.blocked_items} />
              <BlockedSection title="Просроченные элементы" items={payload.overdue_items} />
              <OffersPendingSection items={payload.offers_pending_confirmation} />
            </section>

            <NotificationSection title="Уведомления" items={payload.notifications} />
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}

export function AdminDashboardView() {
  const session = useFoundationSession();
  const [payload, setPayload] = useState<AdminDashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!session?.token) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFoundationJson<AdminDashboardPayload>("/api/v1/admin/dashboard", {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "admin_dashboard_load_failed");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [session?.token]);

  return (
    <SessionGate title="Панель администратора" description="Для панели администратора нужен действующий токен с ролью администратора.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="micro-label">Обзор администратора</div>
              <h1 className="mt-2 text-3xl leading-tight">Панель администратора</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Здесь видно, что меняет поведение системы: правила, уведомления, блокеры и общая служебная телеметрия.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка панели администратора...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <CountSection title="Пользователи" counts={{users: payload.counts.users}} formatKey={displayAdminMetricKey} />
              <CountSection title="Правила" counts={{rules: payload.counts.rules}} formatKey={displayAdminMetricKey} />
              <CountSection title="Версии правил" counts={{rule_versions: payload.counts.rule_versions}} formatKey={displayAdminMetricKey} />
              <CountSection title="События хронологии" counts={{message_events: payload.counts.message_events}} formatKey={displayAdminMetricKey} />
              <CountSection title="Уведомления" counts={{notifications: payload.counts.notifications}} formatKey={displayAdminMetricKey} />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Заявки по статусам" counts={payload.requests_by_status} formatKey={displayRequestStatus} href="/request-workbench" actionLabel="Открыть заявки" />
              <CountSection title="Заказы по состоянию" counts={payload.orders_by_state} formatKey={displayOrderStatus} href="/orders" actionLabel="Открыть заказы" />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <BlockedSection title="Заблокированные элементы" items={payload.blocked_items} />
              <BlockedSection title="Просроченные элементы" items={payload.overdue_items} />
              <NotificationSection title="Административные уведомления" items={payload.notifications} />
            </section>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Снимок телеметрии</h2>
              <pre className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/20 p-4 text-xs text-foreground/80">
                {JSON.stringify(payload.telemetry, null, 2)}
              </pre>
            </Card>
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}

export function SupplyDashboardView() {
  const session = useFoundationSession();
  const [payload, setPayload] = useState<SupplyDashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!session?.token) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFoundationJson<SupplyDashboardPayload>("/api/v1/operator/dashboard/supply", {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "supply_dashboard_load_failed");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [session?.token]);

  return (
    <SessionGate title="Панель поставщиков" description="Для панели поставщиков нужен действующий токен с ролью оператора или администратора.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Контур поставщиков</div>
              <h1 className="mt-2 text-3xl leading-tight">Панель поставщиков</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Здесь собраны доверие, статусы, блокировки и рабочий срез по поставщикам без расширения в полноценный supplier portal.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка панели поставщиков...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Поставщики по доверию" counts={payload.suppliers_by_trust} formatKey={displaySupplierTrustLevel} href="/suppliers" actionLabel="Открыть реестр" />
              <CountSection title="Поставщики по статусам" counts={payload.suppliers_by_status} formatKey={displaySupplierStatus} href="/suppliers" actionLabel="Открыть реестр" />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <Card className="glass-panel border-white/12 p-5">
                <h2 className="text-xl">Заблокированные поставщики</h2>
                <div className="mt-4 space-y-3 text-sm">
                  {payload.blocked_suppliers.map((item) => (
                    <Link key={item.code} href={`/suppliers/${item.code}`} className="block rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
                      <div className="font-medium">{item.display_name}</div>
                      <div className="mt-1 text-muted-foreground">
                        {item.code} · {displaySupplierTrustLevel(item.trust_level)} · {displaySupplierStatus(item.supplier_status)}
                      </div>
                      {item.blocked_reason ? <div className="mt-2 text-foreground/80">{item.blocked_reason}</div> : null}
                    </Link>
                  ))}
                  {!payload.blocked_suppliers.length ? <div className="text-sm text-muted-foreground">Нет заблокированных поставщиков.</div> : null}
                </div>
              </Card>

              <Card className="glass-panel border-white/12 p-5">
                <h2 className="text-xl">Ключевые поставщики</h2>
                <div className="mt-4 space-y-3 text-sm">
                  {payload.top_suppliers.map((item) => (
                    <Link key={item.code} href={`/suppliers/${item.code}`} className="block rounded-2xl border border-white/10 bg-black/10 p-4 transition-colors hover:bg-black/16">
                      <div className="font-medium">{item.display_name}</div>
                      <div className="mt-1 text-muted-foreground">
                        {item.code} · {displaySupplierTrustLevel(item.trust_level)} · {displaySupplierStatus(item.supplier_status)}
                      </div>
                      {item.capability_summary ? <div className="mt-2 text-foreground/80">{item.capability_summary}</div> : null}
                    </Link>
                  ))}
                </div>
              </Card>
            </section>
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}

export function ProcessingDashboardView() {
  const session = useFoundationSession();
  const [payload, setPayload] = useState<ProcessingDashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!session?.token) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFoundationJson<ProcessingDashboardPayload>("/api/v1/operator/dashboard/processing", {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "processing_dashboard_load_failed");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [session?.token]);

  return (
    <SessionGate title="Производственный срез" description="Для производственного среза нужен действующий токен с ролью оператора или администратора.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Производственный обзор</div>
              <h1 className="mt-2 text-3xl leading-tight">Производственный срез</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Здесь собраны статусы заявок, ожидающие подтверждения офферы, состояния заказов и все блокировки с просрочками для ручного ведения исполнения.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка производственного среза...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Заявки по статусам" counts={payload.requests_by_status} formatKey={displayRequestStatus} href="/request-workbench" actionLabel="Открыть заявки" />
              <CountSection title="Заказы по состоянию" counts={payload.orders_by_state} formatKey={displayOrderStatus} href="/orders" actionLabel="Открыть заказы" />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <OffersPendingSection items={payload.offers_pending_confirmation} />
              <BlockedSection title="Заблокированные элементы" items={payload.blocked_items} />
              <BlockedSection title="Просроченные элементы" items={payload.overdue_items} />
            </section>
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}
