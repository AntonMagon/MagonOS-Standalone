// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useEffect, useState} from "react";

import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
import {displaySupplierTrustLevel, formatFoundationDate} from "@/lib/foundation-display";

// RU: Карточка площадки нужна как operator view на конкретный supplier site, а не как универсальная supplier-страница.
type SitePayload = {
  site: {
    code: string;
    site_name: string;
    trust_level: string;
    site_status: string;
    current_load_percent?: number | null;
    lead_time_days?: number | null;
    capability_summary?: string | null;
  };
  supplier?: {code: string; display_name: string} | null;
  address?: {normalized_address?: string | null; city?: string | null; district?: string | null} | null;
  rating_history: Array<{code: string; overall_score: number; source_label?: string | null; captured_at?: string | null}>;
};

export default function SupplierSitePage() {
  const params = useParams<{siteCode: string}>();
  const siteCode = String(params?.siteCode || "");
  const session = readFoundationSession();
  const [payload, setPayload] = useState<SitePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!session?.token || !siteCode) {
        return;
      }
      try {
        const data = await fetchFoundationJson<SitePayload>(`/api/v1/operator/supplier-sites/${siteCode}`, {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "supplier_site_failed");
      }
    }
    void load();
  }, [session?.token, siteCode]);

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Площадка поставщика</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Для этого экрана нужен вход с ролью оператора или администратора.</p>
          <div className="mt-6">
            <Link href="/login">
              <Button>Открыть вход</Button>
            </Link>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className="container space-y-6 py-8">
      <Link href="/suppliers" className="text-sm text-muted-foreground hover:text-foreground">← К панели поставщиков</Link>
      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
      {payload ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <Card className="glass-panel border-white/12 p-5">
            <h1 className="text-3xl leading-tight">{payload.site.site_name}</h1>
            <div className="mt-4 space-y-2 text-sm">
              <div>Код: {payload.site.code}</div>
              <div>Доверие: {displaySupplierTrustLevel(payload.site.trust_level)} · статус: {displayMaybeCode(payload.site.site_status)}</div>
              <div>Загрузка: {payload.site.current_load_percent ?? 0}% · lead time: {payload.site.lead_time_days ?? "не указан"} дней</div>
              <div>{payload.site.capability_summary || "Сводка компетенций ещё не собрана"}</div>
              {payload.supplier ? (
                <div className="pt-2">
                  <Link href={`/suppliers/${payload.supplier.code}`} className="text-primary underline-offset-4 hover:underline">
                    {payload.supplier.display_name}
                  </Link>
                </div>
              ) : null}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Локация и рейтинг</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div>{payload.address?.normalized_address || "Адрес ещё не подтверждён"}</div>
                <div className="mt-1 text-muted-foreground">
                  {payload.address?.city || "Город не указан"} · {payload.address?.district || "Район не указан"}
                </div>
              </div>
              {payload.rating_history.map((item) => (
                <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div>Общий score: {item.overall_score}</div>
                  <div className="mt-1 text-muted-foreground">{item.source_label || "manual"} · {formatFoundationDate(item.captured_at)}</div>
                </div>
              ))}
            </div>
          </Card>
        </section>
      ) : (
        <Card className="glass-panel border-white/12 p-6 text-sm text-muted-foreground">Загрузка карточки площадки...</Card>
      )}
    </main>
  );
}

function displayMaybeCode(value?: string | null): string {
  if (!value) {
    return "Не указано";
  }
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}
