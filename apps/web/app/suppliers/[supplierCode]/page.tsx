// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useCallback, useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, useFoundationSession} from "@/lib/foundation-client";
import {
  displayReasonCode,
  displaySupplierStatus,
  displaySupplierTrustLevel,
  formatFoundationDate,
} from "@/lib/foundation-display";

// RU: Карточка поставщика держит trust/status и историю проверок рядом, чтобы оператор не перескакивал между разрозненными экранами.
type SupplierDetailPayload = {
  supplier: {
    code: string;
    display_name: string;
    trust_level: string;
    supplier_status: string;
    capability_summary?: string | null;
    canonical_email?: string | null;
    canonical_phone?: string | null;
    website?: string | null;
  };
  company?: {code: string; name: string; legal_name?: string | null} | null;
  contacts: Array<{code: string; email?: string | null; phone?: string | null; verification_status: string}>;
  addresses: Array<{code: string; normalized_address?: string | null; city?: string | null; district?: string | null}>;
  sites: Array<{code: string; site_name: string; trust_level: string; current_load_percent?: number | null}>;
  verification_history: Array<{code: string; verification_type: string; reason_code: string; occurred_at?: string | null}>;
  rating_history: Array<{code: string; overall_score: number; source_label?: string | null; captured_at?: string | null}>;
  raw_records: Array<{code: string; company_name: string; source_url: string}>;
};

export default function SupplierDetailPage() {
  const params = useParams<{supplierCode: string}>();
  const supplierCode = String(params?.supplierCode || "");
  // RU: Карточка поставщика должна гидратироваться из того же session snapshot, что и остальные operator-экраны.
  const session = useFoundationSession();
  const [payload, setPayload] = useState<SupplierDetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session?.token || !supplierCode) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFoundationJson<SupplierDetailPayload>(`/api/v1/operator/suppliers/${supplierCode}`, {}, session.token);
      setPayload(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "supplier_detail_failed");
    } finally {
      setLoading(false);
    }
  }, [session?.token, supplierCode]);

  useEffect(() => {
    void load();
    // RU: Повторный load нужен и при смене supplierCode, и после появления session token на клиенте.
  }, [load]);

  async function verify(targetTrustLevel: "contact_confirmed" | "capability_confirmed" | "trusted") {
    if (!session?.token) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/suppliers/${supplierCode}/verify`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          target_trust_level: targetTrustLevel,
          reason_code: `ui_${targetTrustLevel}`
        })
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_verify_failed");
      setLoading(false);
    }
  }

  async function adminStatus(action: "block" | "archive") {
    if (!session?.token) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/admin/suppliers/${supplierCode}/${action}`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_code: `ui_${action}_supplier`})
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_status_failed");
      setLoading(false);
    }
  }

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Карточка поставщика</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Сначала нужен вход с ролью оператора или администратора.</p>
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/suppliers" className="text-sm text-muted-foreground hover:text-foreground">← К списку поставщиков</Link>
          <h1 className="mt-2 text-3xl leading-tight">{payload?.supplier.display_name ?? supplierCode}</h1>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">
            Здесь собраны исходные данные, подтверждённая компания, история проверок и текущий уровень доверия к поставщику.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void verify("contact_confirmed")} disabled={loading}>Подтвердить контакт</Button>
          <Button variant="secondary" onClick={() => void verify("capability_confirmed")} disabled={loading}>Подтвердить компетенции</Button>
          <Button onClick={() => void verify("trusted")} disabled={loading}>Сделать доверенным</Button>
        </div>
      </div>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
      {loading && !payload ? <Card className="glass-panel border-white/12 p-6 text-sm text-muted-foreground">Загрузка карточки поставщика...</Card> : null}

      {payload ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <Card className="glass-panel border-white/12 p-5 lg:col-span-2">
              <h2 className="text-xl">Подтверждённый поставщик</h2>
              <div className="mt-4 grid gap-3 text-sm">
                <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div>{payload.supplier.code}</div>
                  <div className="mt-1 text-muted-foreground">доверие: {displaySupplierTrustLevel(payload.supplier.trust_level)} · статус: {displaySupplierStatus(payload.supplier.supplier_status)}</div>
                  <div className="mt-2">{payload.supplier.capability_summary || "Компетенции ещё не подтверждены."}</div>
                  <div className="mt-2 text-muted-foreground">{payload.supplier.canonical_email || "Email не указан"} · {payload.supplier.canonical_phone || "Телефон не указан"}</div>
                  {payload.supplier.website ? <div className="mt-1 text-muted-foreground">{payload.supplier.website}</div> : null}
                </div>
                {payload.company ? (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="font-medium">Компания</div>
                    <div className="mt-1">{payload.company.name}</div>
                    <div className="mt-1 text-muted-foreground">{payload.company.code} · {payload.company.legal_name || "Юр. имя не указано"}</div>
                  </div>
                ) : null}
              </div>
            </Card>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Admin-действия</h2>
              <div className="mt-4 flex flex-col gap-3">
                <Button variant="secondary" onClick={() => void adminStatus("block")} disabled={loading}>Заблокировать поставщика</Button>
                <Button variant="secondary" onClick={() => void adminStatus("archive")} disabled={loading}>Архивировать поставщика</Button>
              </div>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Контакты и адреса</h2>
              <div className="mt-4 space-y-3">
                {payload.contacts.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{item.email || "Email не указан"} · {item.phone || "Телефон не указан"}</div>
                    <div className="mt-1 text-muted-foreground">{displayMaybeCode(item.verification_status)}</div>
                  </div>
                ))}
                {payload.addresses.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{item.normalized_address || "Адрес не указан"}</div>
                    <div className="mt-1 text-muted-foreground">{item.city || "Город не указан"} · {item.district || "Район не указан"}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Площадки</h2>
              <div className="mt-4 space-y-3">
                {payload.sites.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div>{item.site_name}</div>
                        <div className="mt-1 text-muted-foreground">доверие: {displaySupplierTrustLevel(item.trust_level)} · загрузка {item.current_load_percent ?? 0}%</div>
                      </div>
                      <Link href={`/supplier-sites/${item.code}`}>
                        <Button variant="secondary">Карточка площадки</Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">История проверок</h2>
              <div className="mt-4 space-y-3">
                {payload.verification_history.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{displayMaybeCode(item.verification_type)}</div>
                    <div className="mt-1 text-muted-foreground">{displayReasonCode(item.reason_code)} · {formatFoundationDate(item.occurred_at)}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Последние raw-доказательства</h2>
              <div className="mt-4 space-y-3">
                {payload.raw_records.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{item.company_name}</div>
                    <div className="mt-1 break-all text-muted-foreground">{item.source_url}</div>
                  </div>
                ))}
              </div>
            </Card>
          </section>
        </>
      ) : null}
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
