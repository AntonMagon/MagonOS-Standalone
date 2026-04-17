// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
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
  customer_refs: {customer_name?: string | null; customer_ref?: string | null};
  created_at?: string | null;
};

type OrdersPayload = {items: OrderItem[]};

export function OrdersList() {
  const session = readFoundationSession();
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
        <Card className="glass-panel border-white/12 p-6">
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
      <Card className="glass-panel border-white/12 p-6">
        <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Заказный контур</div>
        <h1 className="mt-2 text-3xl leading-tight">Заказы после подтверждённого предложения</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
          Здесь виден лёгкий операционный слой заказа: поставщики, статусы оплаты и логистики, документы и готовность без тяжёлого производственного контура.
        </p>
      </Card>

      {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка заказов...</Card> : null}
      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <Card key={item.code} className="glass-panel border-white/12 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{item.code}</div>
                <h2 className="mt-2 text-xl">{item.customer_refs.customer_name ?? item.customer_refs.customer_ref ?? item.code}</h2>
                <div className="mt-2 text-sm text-muted-foreground">{formatFoundationDate(item.created_at)}</div>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <div>{displayOrderStatus(item.order_status)}</div>
                <div>{displayPaymentState(item.payment_state)}</div>
              </div>
            </div>
            <div className="mt-4 grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
              <div>Логистика: {displayLogisticsState(item.logistics_state)}</div>
              <div>Готовность: {displayReadinessState(item.readiness_state)}</div>
              <div>Спор: {displayDisputeState(item.dispute_state)}</div>
              <div>Поставщики: {item.supplier_refs.length ? item.supplier_refs.join(", ") : "Не назначены"}</div>
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
