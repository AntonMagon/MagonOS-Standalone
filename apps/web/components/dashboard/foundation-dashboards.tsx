"use client";
// RU: Компонент собирает wave1 dashboards только из role-scoped API payloads и не склеивает customer/operator/admin данные.

import Link from "next/link";
import {type ReactNode, useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";

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
  title?: string | null;
  body?: string | null;
  reason_code?: string | null;
  reason_display?: ReasonDisplay | null;
  visibility_scope?: string | null;
  created_at?: string | null;
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
};

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

function formatDate(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString("ru-RU");
}

function CountSection({title, counts}: {title: string; counts: CountMap}) {
  const entries = Object.entries(counts);
  return (
    <Card className="glass-panel border-white/12 p-5">
      <h2 className="text-xl">{title}</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{key}</div>
            <div className="mt-2 text-3xl leading-none">{value}</div>
          </div>
        ))}
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
        {items.map((item) => (
          <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="font-medium">{item.title ?? item.reason_display?.title ?? item.reason_code ?? item.code}</div>
            {item.body ? <div className="mt-2 text-foreground/80">{item.body}</div> : null}
            <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
              {item.visibility_scope ?? "n/a"} · {formatDate(item.created_at)}
            </div>
          </div>
        ))}
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
        {items.map((item, index) => (
          <div key={`${item.owner_code}-${item.reason_code}-${index}`} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-medium">{item.owner_code}</div>
                <div className="mt-1 text-muted-foreground">
                  {item.reason_display?.title ?? item.reason_code} · {item.status}
                </div>
              </div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.kind}</div>
            </div>
            {item.note ? <div className="mt-2 text-foreground/80">{item.note}</div> : null}
            <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
              {formatDate(item.due_at ?? item.created_at)}
            </div>
          </div>
        ))}
        {!items.length ? <div className="text-sm text-muted-foreground">Нет элементов.</div> : null}
      </div>
    </Card>
  );
}

function OffersPendingSection({items}: {items: OfferPendingItem[]}) {
  return (
    <Card className="glass-panel border-white/12 p-5">
      <h2 className="text-xl">Offers pending confirmation</h2>
      <div className="mt-4 space-y-3 text-sm">
        {items.map((item) => (
          <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="font-medium">{item.code}</div>
            <div className="mt-1 text-muted-foreground">
              {item.request_ref ?? "no_request_ref"} · {item.confirmation_state ?? item.offer_status ?? "n/a"}
            </div>
            <div className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">{formatDate(item.updated_at)}</div>
          </div>
        ))}
        {!items.length ? <div className="text-sm text-muted-foreground">Нет офферов, ожидающих подтверждения.</div> : null}
      </div>
    </Card>
  );
}

function SessionGate({title, description, children}: {title: string; description: string; children: ReactNode}) {
  const session = readFoundationSession();
  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">{title}</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">{description}</p>
          <div className="mt-6">
            <Link href="/login">
              <Button>Открыть login</Button>
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
      <Link href="/request-workbench"><Button variant="secondary">Requests</Button></Link>
      <Link href="/orders"><Button variant="secondary">Orders</Button></Link>
      <Link href="/suppliers"><Button variant="secondary">Suppliers</Button></Link>
      <Link href="/processing-dashboard"><Button variant="secondary">Processing</Button></Link>
      <Link href="/supply-dashboard"><Button variant="secondary">Supply</Button></Link>
      <Link href="/admin-dashboard"><Button variant="secondary">Admin</Button></Link>
    </div>
  );
}

export function OperatorWorkbenchView() {
  const session = readFoundationSession();
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
    <SessionGate title="Operator workbench" description="Для operator/admin панели нужен foundation session token.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 operator</div>
              <h1 className="mt-2 text-3xl leading-tight">Operator workbench</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Единая панель для intake, blocker reasons, overdue queues, role-scoped notifications и explainable transitions.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка operator workbench...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Requests by status" counts={payload.requests_by_status} />
              <CountSection title="Orders by state" counts={payload.orders_by_state} />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <CountSection title="Offers by status" counts={payload.offers_by_status} />
              <CountSection title="Suppliers by trust" counts={payload.suppliers_by_trust} />
              <CountSection title="Suppliers by status" counts={payload.suppliers_by_status} />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <BlockedSection title="Blocked items" items={payload.blocked_items} />
              <BlockedSection title="Overdue items" items={payload.overdue_items} />
              <OffersPendingSection items={payload.offers_pending_confirmation} />
            </section>

            <NotificationSection title="Notifications" items={payload.notifications} />
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}

export function AdminDashboardView() {
  const session = readFoundationSession();
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
    <SessionGate title="Admin dashboard" description="Для admin панели нужен foundation session token с ролью admin.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 admin</div>
              <h1 className="mt-2 text-3xl leading-tight">Admin dashboard</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Админ-слой показывает baseline rules, версии, объём message events и базовую telemetry без чёрного ящика.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка admin dashboard...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <CountSection title="Users" counts={{users: payload.counts.users}} />
              <CountSection title="Rules" counts={{rules: payload.counts.rules}} />
              <CountSection title="Rule versions" counts={{rule_versions: payload.counts.rule_versions}} />
              <CountSection title="Message events" counts={{message_events: payload.counts.message_events}} />
              <CountSection title="Notifications" counts={{notifications: payload.counts.notifications}} />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Requests by status" counts={payload.requests_by_status} />
              <CountSection title="Orders by state" counts={payload.orders_by_state} />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <BlockedSection title="Blocked items" items={payload.blocked_items} />
              <BlockedSection title="Overdue items" items={payload.overdue_items} />
              <NotificationSection title="Admin notifications" items={payload.notifications} />
            </section>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Telemetry snapshot</h2>
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
  const session = readFoundationSession();
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
    <SessionGate title="Supply dashboard" description="Для supply-side панели нужен foundation session token.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 supply</div>
              <h1 className="mt-2 text-3xl leading-tight">Supply dashboard</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Панель для supplier trust/status, blocked suppliers и текущего подтверждённого supply contour без полного supplier portal.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка supply dashboard...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Suppliers by trust" counts={payload.suppliers_by_trust} />
              <CountSection title="Suppliers by status" counts={payload.suppliers_by_status} />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <Card className="glass-panel border-white/12 p-5">
                <h2 className="text-xl">Blocked suppliers</h2>
                <div className="mt-4 space-y-3 text-sm">
                  {payload.blocked_suppliers.map((item) => (
                    <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                      <div className="font-medium">{item.display_name}</div>
                      <div className="mt-1 text-muted-foreground">
                        {item.code} · {item.trust_level} · {item.supplier_status}
                      </div>
                      {item.blocked_reason ? <div className="mt-2 text-foreground/80">{item.blocked_reason}</div> : null}
                    </div>
                  ))}
                  {!payload.blocked_suppliers.length ? <div className="text-sm text-muted-foreground">Нет заблокированных поставщиков.</div> : null}
                </div>
              </Card>

              <Card className="glass-panel border-white/12 p-5">
                <h2 className="text-xl">Top suppliers</h2>
                <div className="mt-4 space-y-3 text-sm">
                  {payload.top_suppliers.map((item) => (
                    <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                      <div className="font-medium">{item.display_name}</div>
                      <div className="mt-1 text-muted-foreground">
                        {item.code} · trust {item.trust_level} · status {item.supplier_status}
                      </div>
                      {item.capability_summary ? <div className="mt-2 text-foreground/80">{item.capability_summary}</div> : null}
                    </div>
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
  const session = readFoundationSession();
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
    <SessionGate title="Processing dashboard" description="Для processing панели нужен foundation session token.">
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 processing</div>
              <h1 className="mt-2 text-3xl leading-tight">Processing dashboard</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Здесь собраны requests by status, offers pending confirmation, order states и operational blockers/overdue для ручного processing contour.
              </p>
            </div>
            <WorkbenchLinks />
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка processing dashboard...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

        {payload ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <CountSection title="Requests by status" counts={payload.requests_by_status} />
              <CountSection title="Orders by state" counts={payload.orders_by_state} />
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              <OffersPendingSection items={payload.offers_pending_confirmation} />
              <BlockedSection title="Blocked items" items={payload.blocked_items} />
              <BlockedSection title="Overdue items" items={payload.overdue_items} />
            </section>
          </>
        ) : null}
      </main>
    </SessionGate>
  );
}
