// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useEffect, useState} from "react";

import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
import {displayReasonCode, displaySupplierStatus, formatFoundationDate} from "@/lib/foundation-display";

// RU: Страница запуска импорта обязана показывать explainable async-state и не прятать retry/failure детали за API-only контуром.
type IngestDetailPayload = {
  ingest: {
    code: string;
    source_registry_code?: string | null;
    ingest_status: string;
    task_id?: string | null;
    trigger_mode?: string | null;
    raw_count: number;
    normalized_count: number;
    merged_count: number;
    candidate_count: number;
    started_at?: string | null;
    finished_at?: string | null;
    failed_at?: string | null;
    last_retry_at?: string | null;
    retry_count: number;
    failure_code?: string | null;
    failure_detail?: string | null;
    retry_allowed?: boolean;
    created_at?: string | null;
  };
  raw_records: Array<{
    code: string;
    company_name: string;
    source_url: string;
    raw_email?: string | null;
    raw_phone?: string | null;
    raw_address?: string | null;
    normalization?: {canonical_name: string; normalized_status: string; capability_summary?: string | null} | null;
  }>;
  dedup_candidates: Array<{
    code: string;
    candidate_status: string;
    confidence_score: number;
    matched_supplier?: {code: string; display_name: string} | null;
    normalization?: {canonical_name: string} | null;
  }>;
};

export default function SupplierIngestPage() {
  const params = useParams<{ingestCode: string}>();
  const ingestCode = String(params?.ingestCode || "");
  const session = readFoundationSession();
  const [payload, setPayload] = useState<IngestDetailPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const ingestStatus = payload?.ingest?.ingest_status;

  useEffect(() => {
    async function load() {
      if (!session?.token || !ingestCode) {
        return;
      }
      try {
        const data = await fetchFoundationJson<IngestDetailPayload>(`/api/v1/operator/supplier-ingests/${ingestCode}`, {}, session.token);
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "supplier_ingest_detail_failed");
      }
    }
    void load();
  }, [session?.token, ingestCode]);

  useEffect(() => {
    if (!session?.token || !ingestStatus) {
      return;
    }
    if (!["queued", "running"].includes(ingestStatus)) {
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const nextPayload = await fetchFoundationJson<IngestDetailPayload>(`/api/v1/operator/supplier-ingests/${ingestCode}`, {}, session.token);
        setPayload(nextPayload);
      } catch {
        // ignore transient polling failures; operator still sees last stable payload
      }
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [ingestStatus, ingestCode, session?.token]);

  async function retryIngest(mode: "job" | "inline") {
    if (!session?.token) {
      return;
    }
    setActionBusy(mode);
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/supplier-ingests/${ingestCode}/retry`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          reason_code: mode === "job" ? "ui_retry_failed_supplier_ingest" : "ui_retry_failed_supplier_ingest_inline",
          mode
        })
      }, session.token);
      const nextPayload = await fetchFoundationJson<IngestDetailPayload>(`/api/v1/operator/supplier-ingests/${ingestCode}`, {}, session.token);
      setPayload(nextPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "supplier_ingest_retry_failed");
    } finally {
      setActionBusy(null);
    }
  }

  async function forceRerunSource() {
    if (!session?.token || !payload?.ingest.source_registry_code) {
      return;
    }
    setActionBusy("force");
    setError(null);
    try {
      const response = await fetchFoundationJson<{ingest?: {code?: string}}>(
        "/api/v1/operator/supplier-ingests/enqueue",
        {
          method: "POST",
          headers: {"content-type": "application/json"},
          body: JSON.stringify({
            source_registry_code: payload.ingest.source_registry_code,
            idempotency_key: `${payload.ingest.source_registry_code.toLowerCase()}-${Date.now()}`,
            reason_code: "ui_force_rerun_supplier_ingest"
          })
        },
        session.token
      );
      if (response.ingest?.code) {
        window.location.href = `/supplier-ingests/${response.ingest.code}`;
        return;
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "supplier_ingest_force_rerun_failed");
    } finally {
      setActionBusy(null);
    }
  }

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Запуск импорта поставщиков</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Для этого экрана нужен вход в платформу.</p>
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
        <>
          <Card className="glass-panel border-white/12 p-5">
            <h1 className="text-3xl leading-tight">{payload.ingest.code}</h1>
            <div className="mt-4 space-y-2 text-sm text-muted-foreground">
              <div>
                {payload.ingest.source_registry_code} · {displayIngestStatus(payload.ingest.ingest_status)} · {displayTriggerMode(payload.ingest.trigger_mode)} · задача {payload.ingest.task_id || "не назначена"}
              </div>
              <div>
                сырых {payload.ingest.raw_count} · нормализовано {payload.ingest.normalized_count} · объединено {payload.ingest.merged_count} · спорных дублей {payload.ingest.candidate_count}
              </div>
              <div>
                создан: {formatFoundationDate(payload.ingest.created_at)} · старт: {formatFoundationDate(payload.ingest.started_at, "Не стартовал")} · финиш: {formatFoundationDate(payload.ingest.finished_at, "Ещё не завершён")}
              </div>
              <div>
                повторов {payload.ingest.retry_count} · последний повтор: {formatFoundationDate(payload.ingest.last_retry_at, "Не было")}
              </div>
            </div>
            {payload.ingest.failure_code ? (
              <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
                <div className="font-medium">{payload.ingest.failure_code}</div>
                <div className="mt-1">{payload.ingest.failure_detail || "Без detail"}</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => void retryIngest("job")} disabled={actionBusy !== null}>
                    {actionBusy === "job" ? "Ставлю повтор..." : "Повторить в очереди"}
                  </Button>
                  <Button size="sm" onClick={() => void retryIngest("inline")} disabled={actionBusy !== null}>
                    {actionBusy === "inline" ? "Повторяю..." : "Повторить синхронно"}
                  </Button>
                </div>
              </div>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => void forceRerunSource()} disabled={actionBusy !== null || !payload.ingest.source_registry_code}>
                {actionBusy === "force" ? "Ставлю повторный запуск..." : "Запустить источник заново"}
              </Button>
            </div>
          </Card>

          <section className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Первичный слой</h2>
              <div className="mt-4 space-y-3">
                {payload.raw_records.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div className="font-medium">{item.company_name}</div>
                    <div className="mt-1 break-all text-muted-foreground">{item.source_url}</div>
                    <div className="mt-2 text-foreground/80">{item.raw_email || "Email не найден"} · {item.raw_phone || "Телефон не найден"}</div>
                    <div className="mt-1 text-muted-foreground">{item.raw_address || "Адрес не найден"}</div>
                    {item.normalization ? (
                      <div className="mt-3 rounded-2xl border border-white/10 bg-white/6 px-3 py-3">
                        <div>{item.normalization.canonical_name}</div>
                        <div className="mt-1 text-muted-foreground">{displaySupplierStatus(item.normalization.normalized_status)}</div>
                        <div className="mt-1 text-muted-foreground">{item.normalization.capability_summary || "Сводка компетенций ещё не собрана"}</div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Разбор дублей</h2>
              <div className="mt-4 space-y-3">
                {payload.dedup_candidates.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{item.normalization?.canonical_name || item.code}</div>
                    <div className="mt-1 text-muted-foreground">{displayReasonCode(item.candidate_status)} · score {item.confidence_score}</div>
                    {item.matched_supplier ? (
                      <div className="mt-2">
                        <Link href={`/suppliers/${item.matched_supplier.code}`} className="text-primary underline-offset-4 hover:underline">
                          {item.matched_supplier.display_name}
                        </Link>
                      </div>
                    ) : null}
                  </div>
                ))}
                {!payload.dedup_candidates.length ? <div className="text-sm text-muted-foreground">В этом запуске нет спорных дублей.</div> : null}
              </div>
            </Card>
          </section>
        </>
      ) : (
        <Card className="glass-panel border-white/12 p-6 text-sm text-muted-foreground">Загрузка запуска импорта...</Card>
      )}
    </main>
  );
}

function displayIngestStatus(value?: string | null): string {
  if (value === "queued") return "В очереди";
  if (value === "running") return "В работе";
  if (value === "completed") return "Завершён";
  if (value === "failed") return "Сбой";
  return displayReasonCode(value);
}

function displayTriggerMode(value?: string | null): string {
  if (value === "job") return "Фоновая очередь";
  if (value === "job_retry") return "Фоновый повтор";
  if (value === "inline") return "Синхронный запуск";
  if (value === "inline_retry") return "Синхронный повтор";
  return displayReasonCode(value);
}
