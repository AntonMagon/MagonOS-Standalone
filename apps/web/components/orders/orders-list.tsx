// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, useFoundationSession} from "@/lib/foundation-client";
import {
  displayDisputeState,
  displayLogisticsState,
  displayOrderStatus,
  displayPaymentState,
  displayReadinessState,
  formatFoundationDate,
} from "@/lib/foundation-display";

// RU: Список заказов нужен как короткий operational entrypoint без лишней вторичной аналитики на карточках.
type OrderItem = {
  code: string;
  order_status: string;
  payment_state: string;
  logistics_state: string;
  readiness_state: string;
  dispute_state: string;
  supplier_refs: string[];
  customer_refs: {request_title?: string | null; customer_name?: string | null; guest_company_name?: string | null; customer_ref?: string | null};
  created_at?: string | null;
};

type OrdersPayload = {items: OrderItem[]};

function orderNextAction(item: OrderItem): string {
  if (item.payment_state === "pending") return "Нужно проверить оплату и подтвердить старт заказа.";
  if (item.supplier_refs.length === 0) return "Нужно назначить поставщика перед запуском.";
  if (item.readiness_state === "not_ready") return "Нужно довести производство или комплектацию до готовности.";
  if (item.logistics_state === "not_started") return "Нужно планировать отгрузку и доставку.";
  if (item.order_status === "completed") return "Заказ закрыт. Проверь документы и итоговый след.";
  return "Открой заказ и проверь текущий следующий шаг.";
}

function orderCardTitle(item: OrderItem): string {
  return item.customer_refs.request_title ?? item.customer_refs.guest_company_name ?? item.customer_refs.customer_name ?? item.customer_refs.customer_ref ?? item.code;
}

export function OrdersList() {
  // RU: Session hook устраняет hydration mismatch между logged-out shell на сервере и operator view после client boot.
  const session = useFoundationSession();
  const [items, setItems] = useState<OrderItem[]>([]);
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
        const payload = await fetchFoundationJson<OrdersPayload>("/api/v1/operator/orders", {}, session.token);
        setItems(payload.items);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "orders_load_failed");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [session?.token]);

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="paper-panel p-6">
          <h1 className="text-3xl leading-tight">Заказы</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Для этого экрана нужен вход с ролью оператора или администратора.</p>
          <div className="mt-6">
            <Link href="/login"><Button>Открыть вход</Button></Link>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className="container space-y-6 py-10">
      <Card className="paper-panel p-6">
        <div className="micro-label">Рабочий стол заказов</div>
        <h1 className="mt-3 text-3xl leading-tight">Исполнение после подтверждённого предложения</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
          Здесь видно, что происходит с заказом прямо сейчас: оплата, поставщик, готовность, доставка и следующий шаг для оператора.
        </p>
      </Card>

      {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка заказов...</Card> : null}
      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <Card key={item.code} className="paper-panel p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap gap-2">
                  <span className="status-pill status-pill-muted">{item.code}</span>
                  <span className="status-pill status-pill-primary">{displayOrderStatus(item.order_status)}</span>
                </div>
                <h2 className="mt-2 text-xl">{orderCardTitle(item)}</h2>
                <div className="mt-2 text-sm text-muted-foreground">{formatFoundationDate(item.created_at)}</div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className={`status-pill ${item.payment_state === "confirmed" ? "status-pill-success" : item.payment_state === "failed" ? "status-pill-danger" : "status-pill-warn"}`}>
                {displayPaymentState(item.payment_state)}
              </span>
              <span className={`status-pill ${item.readiness_state === "ready" ? "status-pill-success" : "status-pill-warn"}`}>
                {displayReadinessState(item.readiness_state)}
              </span>
              <span className="status-pill status-pill-muted">{displayLogisticsState(item.logistics_state)}</span>
              <span className={`status-pill ${item.dispute_state === "open" ? "status-pill-danger" : "status-pill-muted"}`}>
                {displayDisputeState(item.dispute_state)}
              </span>
            </div>
            <div className="mt-4 grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
              {/* RU: На карточке списка держим только supplier и next step, чтобы экран не превращался в псевдо-ERP отчёт. */}
              <div>Поставщики: {item.supplier_refs.length ? item.supplier_refs.join(", ") : "Не назначены"}</div>
              <div>Следующий шаг: {orderNextAction(item)}</div>
            </div>
            <div className="mt-4">
              <Link href={`/orders/${item.code}`}>
                <Button>Открыть заказ</Button>
              </Link>
            </div>
          </Card>
        ))}
        {!loading && !items.length ? <Card className="glass-panel border-white/12 p-5 text-sm text-muted-foreground">Пока нет заказов.</Card> : null}
      </div>
    </main>
  );
}
