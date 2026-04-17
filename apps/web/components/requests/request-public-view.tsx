// RU: Файл входит в проверенный контур первой волны.
"use client";

import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson} from "@/lib/foundation-client";

type RequestDetail = {
  code: string;
  customer_ref: string;
  title?: string | null;
  summary?: string | null;
  item_service_context?: string | null;
  city?: string | null;
  request_status: string;
  requested_deadline_at?: string | null;
  reasons: Array<{code: string; reason_code: string; note?: string | null}>;
  follow_up_items: Array<{code: string; title: string; detail?: string | null; follow_up_status: string; due_at?: string | null}>;
  managed_files: Array<{
    code: string;
    title?: string | null;
    file_type: string;
    visibility_scope: string;
    final_flag: boolean;
    latest_version?: {code: string; original_name: string; version_no: number} | null;
    download_url?: string | null;
  }>;
  documents: Array<{
    code: string;
    title: string;
    document_type: string;
    template_key: string;
    sent_state: string;
    confirmation_state: string;
    current_version?: {code: string; version_no: number; download_url?: string | null} | null;
    download_url?: string | null;
  }>;
  order?: {code: string; order_status: string; payment_state: string; logistics_state: string; readiness_state: string} | null;
  timeline: Array<{code: string; action: string; reason?: string | null; created_at?: string | null}>;
};

type OfferCompareItem = {
  offer: {
    code: string;
    current_version_no: number;
    offer_status: string;
    confirmation_state: string;
    amount?: number | null;
    currency_code: string;
    lead_time_days?: number | null;
    terms_text?: string | null;
    scenario_type: string;
    supplier_ref?: string | null;
    public_summary?: string | null;
  };
  current_version: {
    code: string;
    version_no: number;
    confirmation_state: string;
  };
  comparison?: {
    comparison_title?: string | null;
    comparison_rank?: number | null;
    recommended: boolean;
    highlights: string[];
  } | null;
};

type RequestPayload = {item: RequestDetail};
type ComparePayload = {request: RequestDetail; items: OfferCompareItem[]};

export function RequestPublicView({customerRef}: {customerRef: string}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [item, setItem] = useState<RequestDetail | null>(null);
  const [offers, setOffers] = useState<OfferCompareItem[]>([]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [requestPayload, comparePayload] = await Promise.all([
        fetchFoundationJson<RequestPayload>(`/api/v1/public/requests/${customerRef}`),
        fetchFoundationJson<ComparePayload>(`/api/v1/public/requests/${customerRef}/offers/compare`),
      ]);
      setItem(requestPayload.item);
      setOffers(comparePayload.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "request_load_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [customerRef]);

  async function respondToOffer(offerCode: string, action: "accept" | "decline") {
    setError(null);
    try {
      const reasonCode = action === "accept" ? "customer_acceptance_recorded" : "customer_decline_recorded";
      await fetchFoundationJson(`/api/v1/public/requests/${customerRef}/offers/${offerCode}/${action}`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          reason_code: reasonCode,
          note: action === "accept" ? "Customer accepted this concrete offer version." : "Customer declined this concrete offer version.",
        }),
      });
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "offer_response_failed");
    }
  }

  if (loading) {
    return <Card className="glass-panel border-white/12 p-6">Загрузка Request...</Card>;
  }
  if (!item) {
    return <Card className="glass-panel border-red-400/30 bg-red-500/10 p-6 text-red-100">{error ?? "request_not_found"}</Card>;
  }

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-white/12 p-6">
        <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Customer Request</div>
        <h1 className="mt-2 text-3xl leading-tight">{item.title ?? item.code}</h1>
        <div className="mt-3 grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
          <div>Статус: {item.request_status}</div>
          <div>Customer ref: {item.customer_ref}</div>
          <div>Город: {item.city ?? "не указан"}</div>
          <div>Дедлайн: {item.requested_deadline_at ?? "не указан"}</div>
        </div>
        {item.summary ? <p className="mt-4 text-sm leading-7 text-foreground/84">{item.summary}</p> : null}
        {item.item_service_context ? (
          <div className="mt-4 rounded-2xl border border-white/10 bg-black/10 p-4 text-sm leading-7 text-foreground/80">
            {item.item_service_context}
          </div>
        ) : null}
        {item.order ? (
          <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            Заказ {item.order.code}: {item.order.order_status} · payment {item.order.payment_state} · logistics {item.order.logistics_state}
          </div>
        ) : null}
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <Card className="glass-panel border-white/12 p-5">
        <h2 className="text-xl">Сравнение предложений</h2>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          Здесь показываются только отправленные клиенту версии. Подтверждение относится к конкретной версии, а не ко всей заявке целиком.
        </p>
        <div className="mt-4 space-y-4 text-sm">
          {offers.map((offerItem) => (
            <div key={offerItem.offer.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{offerItem.comparison?.comparison_title ?? offerItem.offer.public_summary ?? offerItem.offer.code}</div>
                  <div className="mt-1 text-muted-foreground">
                    v{offerItem.offer.current_version_no} · {offerItem.offer.offer_status} · {offerItem.offer.confirmation_state}
                  </div>
                </div>
                {offerItem.comparison?.recommended ? <div className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">recommended</div> : null}
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <div>Цена: {offerItem.offer.amount ?? "n/a"} {offerItem.offer.currency_code}</div>
                <div>Lead time: {offerItem.offer.lead_time_days ?? "n/a"} дней</div>
                <div>Scenario: {offerItem.offer.scenario_type}</div>
                <div>Supplier ref: {offerItem.offer.supplier_ref ?? "n/a"}</div>
              </div>
              {offerItem.offer.public_summary ? <div className="mt-3 text-foreground/84">{offerItem.offer.public_summary}</div> : null}
              {offerItem.offer.terms_text ? <div className="mt-3 text-muted-foreground">{offerItem.offer.terms_text}</div> : null}
              {offerItem.comparison?.highlights?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {offerItem.comparison.highlights.map((highlight) => (
                    <span key={highlight} className="rounded-full border border-white/10 px-3 py-1 text-xs text-muted-foreground">{highlight}</span>
                  ))}
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Button type="button" onClick={() => void respondToOffer(offerItem.offer.code, "accept")} disabled={offerItem.offer.confirmation_state === "accepted"}>
                  Подтвердить эту версию
                </Button>
                <Button type="button" variant="outline" onClick={() => void respondToOffer(offerItem.offer.code, "decline")} disabled={offerItem.offer.confirmation_state === "declined"}>
                  Отклонить
                </Button>
              </div>
            </div>
          ))}
          {!offers.length ? <div className="text-muted-foreground">Пока нет отправленных предложений для сравнения.</div> : null}
        </div>
      </Card>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Причины и комментарии</h2>
          <div className="mt-4 space-y-3 text-sm">
            {item.reasons.map((reason) => (
              <div key={reason.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{reason.reason_code}</div>
                {reason.note ? <div className="mt-1 text-muted-foreground">{reason.note}</div> : null}
              </div>
            ))}
            {!item.reasons.length ? <div className="text-muted-foreground">Пока нет customer-visible причин.</div> : null}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Follow-up items</h2>
          <div className="mt-4 space-y-3 text-sm">
            {item.follow_up_items.map((followUp) => (
              <div key={followUp.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{followUp.title}</div>
                <div className="mt-1 text-muted-foreground">{followUp.follow_up_status}</div>
                {followUp.detail ? <div className="mt-2 text-foreground/80">{followUp.detail}</div> : null}
              </div>
            ))}
            {!item.follow_up_items.length ? <div className="text-muted-foreground">Пока нет открытых follow-up items.</div> : null}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Файлы</h2>
          <div className="mt-4 space-y-3 text-sm">
            {item.managed_files.map((file) => (
              <div key={file.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{file.title ?? file.latest_version?.original_name ?? file.code}</div>
                <div className="mt-1 text-muted-foreground">
                  {file.file_type} · {file.visibility_scope} · {file.final_flag ? "final" : "draft"}
                </div>
                {file.download_url && file.latest_version ? (
                  <div className="mt-3">
                    <a className="inline-flex rounded-xl border border-white/12 px-3 py-2 text-xs text-foreground transition hover:bg-white/5" href={file.download_url}>
                      Скачать {file.latest_version.original_name}
                    </a>
                  </div>
                ) : null}
              </div>
            ))}
            {!item.managed_files.length ? <div className="text-muted-foreground">Пока нет customer-visible файлов.</div> : null}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Документы</h2>
          <div className="mt-4 space-y-3 text-sm">
            {item.documents.map((document) => (
              <div key={document.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{document.title}</div>
                <div className="mt-1 text-muted-foreground">
                  {document.document_type} · {document.sent_state} · {document.confirmation_state}
                </div>
                {document.download_url && document.current_version ? (
                  <div className="mt-3">
                    <a className="inline-flex rounded-xl border border-white/12 px-3 py-2 text-xs text-foreground transition hover:bg-white/5" href={document.download_url}>
                      Скачать v{document.current_version.version_no}
                    </a>
                  </div>
                ) : null}
              </div>
            ))}
            {!item.documents.length ? <div className="text-muted-foreground">Пока нет customer-visible документов.</div> : null}
          </div>
        </Card>
      </section>

      <Card className="glass-panel border-white/12 p-5">
        <h2 className="text-xl">Timeline</h2>
        <div className="mt-4 space-y-3 text-sm">
          {item.timeline.map((event) => (
            <div key={event.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="font-medium">{event.action}</div>
              <div className="mt-1 text-muted-foreground">{event.reason ?? "no_reason_code"} · {event.created_at ?? "unknown_time"}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
