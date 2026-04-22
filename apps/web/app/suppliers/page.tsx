// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
import {
  displayReasonCode,
  displaySupplierStatus,
  displaySupplierTrustLevel,
  formatFoundationDate,
} from "@/lib/foundation-display";

type SuppliersPayload = {
  items: Array<{
    code: string;
    display_name: string;
    trust_level: string;
    supplier_status: string;
    capability_summary?: string | null;
  }>;
};

type SourcePayload = {
  items: Array<{
    code: string;
    label: string;
    adapter_key: string;
    config_json?: Record<string, unknown>;
    last_success_at?: string | null;
    health: {
      ok: boolean;
      detail: string;
      payload?: Record<string, unknown>;
    };
    schedule?: {
      enabled: boolean;
      interval_minutes: number;
      active: boolean;
      due_now: boolean;
      next_run_at?: string | null;
      last_event_at?: string | null;
      skip_reason?: string | null;
    };
    classification?: {
      mode?: string | null;
      llm_enabled?: boolean;
    };
    latest_ingest?: {
      code: string;
      ingest_status: string;
      task_id?: string | null;
      trigger_mode?: string | null;
      created_at?: string | null;
      started_at?: string | null;
      finished_at?: string | null;
      failed_at?: string | null;
      last_retry_at?: string | null;
      retry_count: number;
      failure_code?: string | null;
      failure_detail?: string | null;
      raw_count: number;
      normalized_count: number;
      merged_count: number;
      candidate_count: number;
    } | null;
  }>;
};

type IngestPayload = {
  items: Array<{
    code: string;
    source_registry_code?: string | null;
    ingest_status: string;
    raw_count: number;
    normalized_count: number;
    merged_count: number;
    candidate_count: number;
    created_at?: string | null;
  }>;
};

type CandidatePayload = {
  items: Array<{
    code: string;
    candidate_status: string;
    confidence_score: number;
    reason_code: string;
    matched_supplier?: {code: string; display_name: string} | null;
    normalization?: {canonical_name: string} | null;
  }>;
};

export default function SuppliersPage() {
  // RU: Экран поставщиков одновременно показывает список, статус адаптеров и ручки управления расписанием/ингестом.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourcePayload["items"]>([]);
  const [selectedSourceCode, setSelectedSourceCode] = useState<string>("");
  const [suppliers, setSuppliers] = useState<SuppliersPayload["items"]>([]);
  const [ingests, setIngests] = useState<IngestPayload["items"]>([]);
  const [candidates, setCandidates] = useState<CandidatePayload["items"]>([]);
  const session = readFoundationSession();
  const [actionCode, setActionCode] = useState<string | null>(null);

  async function load() {
    if (!session?.token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [sourceData, supplierData, ingestData, candidateData] = await Promise.all([
        fetchFoundationJson<SourcePayload>("/api/v1/operator/supplier-sources", {}, session.token),
        fetchFoundationJson<SuppliersPayload>("/api/v1/operator/suppliers", {}, session.token),
        fetchFoundationJson<IngestPayload>("/api/v1/operator/supplier-ingests", {}, session.token),
        fetchFoundationJson<CandidatePayload>("/api/v1/operator/supplier-dedup-candidates", {}, session.token)
      ]);
      setSources(sourceData.items);
      // RU: Operator UI держит явный выбранный источник, чтобы fixture/demo ingest и live parsing не смешивались неявно.
      setSelectedSourceCode((current) => {
        if (current && sourceData.items.some((item) => item.code === current)) {
          return current;
        }
        return sourceData.items[0]?.code ?? "";
      });
      setSuppliers(supplierData.items);
      setIngests(ingestData.items);
      setCandidates(candidateData.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "supplier_workbench_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!session?.token) {
      return;
    }
    const hasActiveJobs = ingests.some((item) => item.ingest_status === "queued" || item.ingest_status === "running");
    if (!hasActiveJobs) {
      return;
    }
    const timer = window.setTimeout(() => {
      void load();
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [ingests, session?.token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function enqueueSourceRun(sourceCode: string, reasonCode: string) {
    if (!session?.token || !sourceCode) {
      return;
    }
    setActionCode(sourceCode);
    setError(null);
    try {
      await fetchFoundationJson("/api/v1/operator/supplier-ingests/enqueue", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          source_registry_code: sourceCode,
          idempotency_key: `${sourceCode.toLowerCase()}-${Date.now()}`,
          reason_code: reasonCode
        })
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_ingest_failed");
    } finally {
      setActionCode(null);
    }
  }

  const selectedSource = sources.find((item) => item.code === selectedSourceCode) ?? sources[0] ?? null;

  function displaySourceLabel(item: SourcePayload["items"][number]) {
    if (item.adapter_key === "scenario_live") {
      return "Живой парсинг поставщиков";
    }
    if (item.adapter_key === "fixture_json") {
      return "Фикстурный импорт поставщиков";
    }
    return item.label;
  }

  function displayAdapterKey(adapterKey: string) {
    if (adapterKey === "scenario_live") {
      return "живой парсинг";
    }
    if (adapterKey === "fixture_json") {
      return "фикстурный JSON";
    }
    return adapterKey;
  }

  async function retryFailedIngest(ingestCode: string) {
    if (!session?.token) {
      return;
    }
    setActionCode(ingestCode);
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/supplier-ingests/${ingestCode}/retry`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          reason_code: "ui_retry_failed_supplier_ingest",
          mode: "job"
        })
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_ingest_retry_failed");
    } finally {
      setActionCode(null);
    }
  }

  async function resolveCandidate(candidateCode: string, decision: "merge" | "reject") {
    if (!session?.token) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/supplier-dedup-candidates/${candidateCode}/decision`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          decision,
          reason_code: decision === "merge" ? "ui_confirm_same_supplier" : "ui_confirm_separate_supplier"
        })
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_candidate_resolution_failed");
      setLoading(false);
    }
  }

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Панель поставщиков</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            Для этого экрана нужен вход с ролью оператора или администратора. Сначала авторизуйся в платформе.
          </p>
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
      <div className="paper-panel grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Поставщики · wave 1</div>
          <h1 className="mt-2 text-3xl leading-tight">Операторская панель поставщиков</h1>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
            Источники импорта, первичный слой, разбор дублей и движение по доверию собраны в один ручной контур без скрытой автоматизации.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-[minmax(18rem,22rem)_auto_auto] sm:items-end">
          <label className="flex min-w-0 flex-col gap-2 text-sm text-muted-foreground">
            <span>Источник импорта</span>
            <select
              value={selectedSourceCode}
              onChange={(event) => setSelectedSourceCode(event.target.value)}
              className="h-11 rounded-2xl border border-border bg-white/70 px-3 text-sm text-foreground outline-none transition focus:border-foreground/25"
            >
              {sources.map((item) => (
                <option key={item.code} value={item.code}>
                  {displaySourceLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <Button
            onClick={() => selectedSource && void enqueueSourceRun(selectedSource.code, "ui_supplier_ingest_enqueue")}
            disabled={loading || !selectedSource || actionCode === selectedSource?.code}
            className="h-11"
          >
            {actionCode === selectedSource?.code ? "Ставлю в очередь..." : "Поставить в очередь"}
          </Button>
          <Button variant="secondary" onClick={() => void load()} disabled={loading} className="h-11">Обновить</Button>
        </div>
      </div>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="paper-panel p-5">
          <h2 className="text-xl">Источники</h2>
          <div className="mt-4 space-y-3 text-sm">
            {sources.map((item) => (
              <div key={item.code} className="rounded-[1.4rem] border border-border/80 bg-white/55 p-4 shadow-[0_16px_38px_-32px_rgba(43,46,52,0.35)]">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{displaySourceLabel(item)}</div>
                    <div className="mt-1 text-muted-foreground">{item.code} · {displayAdapterKey(item.adapter_key)}</div>
                  </div>
                  <div className={`rounded-full border px-3 py-1 text-xs font-medium ${item.health.ok ? "border-emerald-300/60 bg-emerald-100/80 text-emerald-800" : "border-red-300/70 bg-red-100/90 text-red-800"}`}>
                    {item.health.ok ? "Адаптер готов" : "Адаптер недоступен"}
                  </div>
                </div>
                <div className="mt-2 text-muted-foreground">
                  {item.adapter_key === "scenario_live"
                    ? `Живой парсинг: ${String(item.config_json?.query || "printing packaging vietnam")} · ${String(item.config_json?.country || "VN")}`
                    : "Fixture-импорт для повторяемого demo и тестов"}
                </div>
                <div className="mt-3 rounded-[1.1rem] border border-border/70 bg-background/55 px-3 py-3 text-xs leading-6 text-muted-foreground">
                  <div>Состояние: {displaySourceHealth(item.health.detail, item.health.payload)}</div>
                  <div>Последний успешный запуск: {formatFoundationDate(item.last_success_at, "Ещё не было")}</div>
                  <div>
                    Постоянный режим: {item.schedule?.enabled ? `включён, каждые ${item.schedule.interval_minutes} мин.` : "выключен"}
                  </div>
                  <div>
                    Следующее окно: {formatFoundationDate(item.schedule?.next_run_at, item.schedule?.enabled ? "Запустится при первом свободном окне" : "Не планируется")}
                  </div>
                  <div>
                    Классификация: {displayClassificationMode(item.classification?.mode)}{item.classification?.llm_enabled ? " · LLM fallback активен" : " · LLM fallback выключен"}
                  </div>
                </div>
                {item.latest_ingest ? (
                  <div className="mt-3 rounded-[1.1rem] border border-border/70 bg-background/55 px-3 py-3 text-xs leading-6 text-muted-foreground">
                    <div className="font-medium text-foreground">{item.latest_ingest.code}</div>
                    <div className="mt-1">
                      {displayIngestStatus(item.latest_ingest.ingest_status)} · {displayTriggerMode(item.latest_ingest.trigger_mode)} · повторов {item.latest_ingest.retry_count}
                    </div>
                    <div className="mt-1">
                      сырых {item.latest_ingest.raw_count} · нормализовано {item.latest_ingest.normalized_count} · объединено {item.latest_ingest.merged_count} · дублей {item.latest_ingest.candidate_count}
                    </div>
                    <div className="mt-1">
                      создан: {formatFoundationDate(item.latest_ingest.created_at)} · финиш: {formatFoundationDate(item.latest_ingest.finished_at, "Ещё не завершён")}
                    </div>
                    {item.latest_ingest.failure_code ? (
                      <div className="mt-1 text-red-100">
                        {item.latest_ingest.failure_code}: {item.latest_ingest.failure_detail || "Без detail"}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="mt-3 text-xs text-muted-foreground">По этому источнику импорт ещё не запускался.</div>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => void enqueueSourceRun(item.code, "ui_supplier_ingest_enqueue")} disabled={loading || actionCode === item.code}>
                    В очередь
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => void enqueueSourceRun(item.code, "ui_force_rerun_supplier_ingest")} disabled={loading || actionCode === item.code}>
                    Перезапустить
                  </Button>
                  {item.latest_ingest?.ingest_status === "failed" ? (
                    <Button size="sm" variant="outline" onClick={() => void retryFailedIngest(item.latest_ingest!.code)} disabled={loading || actionCode === item.latest_ingest?.code}>
                      Повторить после сбоя
                    </Button>
                  ) : null}
                  {item.latest_ingest ? (
                    <Link href={`/supplier-ingests/${item.latest_ingest.code}`}>
                      <Button size="sm" variant="ghost">Открыть запуск</Button>
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="paper-panel p-5 lg:col-span-2">
          <h2 className="text-xl">Последние запуски импорта</h2>
          <div className="mt-4 grid gap-3">
            {ingests.map((item) => (
              <div key={item.code} className="rounded-[1.4rem] border border-border/80 bg-white/55 p-4 shadow-[0_16px_38px_-32px_rgba(43,46,52,0.35)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.code}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.source_registry_code} · сырых {item.raw_count} · нормализовано {item.normalized_count} · объединено {item.merged_count} · спорных дублей {item.candidate_count}
                    </div>
                    <div className="mt-1 text-sm text-muted-foreground">{formatFoundationDate(item.created_at)} · {displayIngestStatus(item.ingest_status)}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Link href={`/supplier-ingests/${item.code}`}>
                      <Button variant="secondary">Детали импорта</Button>
                    </Link>
                  </div>
                </div>
              </div>
            ))}
            {!ingests.length ? <div className="text-sm text-muted-foreground">Пока нет запусков импорта.</div> : null}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Поставщики</h2>
          <div className="mt-4 space-y-3">
            {suppliers.map((item) => (
              <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.display_name}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.code} · доверие: {displaySupplierTrustLevel(item.trust_level)} · статус: {displaySupplierStatus(item.supplier_status)}
                    </div>
                    {item.capability_summary ? (
                      <div className="mt-2 text-sm text-foreground/80">{item.capability_summary}</div>
                    ) : null}
                  </div>
                  <Link href={`/suppliers/${item.code}`}>
                    <Button variant="secondary">Карточка</Button>
                  </Link>
                </div>
              </div>
            ))}
            {!suppliers.length ? <div className="text-sm text-muted-foreground">Поставщики ещё не подтверждены.</div> : null}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Спорные дубли</h2>
          <div className="mt-4 space-y-3">
            {candidates.map((item) => (
              <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="font-medium">{item.normalization?.canonical_name ?? item.code}</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  score {item.confidence_score} · {displayReasonCode(item.reason_code)}
                </div>
                <div className="mt-1 text-sm text-foreground/80">
                  Совпадение: {item.matched_supplier?.display_name ?? "Не найдено"}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => void resolveCandidate(item.code, "merge")} disabled={loading}>
                    Объединить
                  </Button>
                  <Button size="sm" onClick={() => void resolveCandidate(item.code, "reject")} disabled={loading}>
                    Оставить отдельным
                  </Button>
                </div>
              </div>
            ))}
            {!candidates.length ? <div className="text-sm text-muted-foreground">Нет кандидатов на ручную проверку дублей.</div> : null}
          </div>
        </Card>
      </section>
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

function displaySourceHealth(detail?: string | null, payload?: Record<string, unknown>): string {
  if (detail === "fixture_ready") {
    return "Fixture JSON доступен";
  }
  if (detail === "live_parsing_ready") {
    const threshold = payload?.low_confidence_threshold;
    return threshold !== undefined ? `Живой парсинг готов, порог ${String(threshold)}` : "Живой парсинг готов";
  }
  if (detail === "live_parsing_unavailable") {
    return `Живой парсинг недоступен: ${String(payload?.error || "без detail")}`;
  }
  return displayReasonCode(detail);
}

function displayClassificationMode(value?: string | null): string {
  if (value === "ai_assisted_fallback") {
    return "парсинг + ai-assisted fallback";
  }
  if (value === "deterministic_only") {
    return "только детерминированный разбор";
  }
  return displayReasonCode(value);
}
