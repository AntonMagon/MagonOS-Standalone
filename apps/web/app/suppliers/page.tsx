// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";

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
  items: Array<{code: string; label: string; adapter_key: string}>;
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourcePayload["items"]>([]);
  const [suppliers, setSuppliers] = useState<SuppliersPayload["items"]>([]);
  const [ingests, setIngests] = useState<IngestPayload["items"]>([]);
  const [candidates, setCandidates] = useState<CandidatePayload["items"]>([]);
  const session = readFoundationSession();

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

  async function runDemoIngest() {
    if (!session?.token || !sources[0]) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await fetchFoundationJson("/api/v1/operator/supplier-ingests/run-inline", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          source_registry_code: sources[0].code,
          idempotency_key: `ui-demo-${Date.now()}`,
          reason_code: "ui_demo_supplier_ingest"
        })
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "supplier_ingest_failed");
      setLoading(false);
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
          <h1 className="text-3xl leading-tight">Supplier admin/workbench</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            Для operator/admin-экрана нужен foundation session token. Сначала зайди через экран login.
          </p>
          <div className="mt-6">
            <Link href="/login">
              <Button>Открыть login</Button>
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
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 suppliers</div>
          <h1 className="mt-2 text-3xl leading-tight">Supplier admin/workbench</h1>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
            Здесь живёт ручной контур первой волны: источники, raw ingest, dedup review, supplier registry и trust progression.
          </p>
        </div>
        <Button onClick={() => void runDemoIngest()} disabled={loading || !sources.length}>
          {loading ? "Обновление..." : "Запустить demo ingest"}
        </Button>
      </div>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Источники</h2>
          <div className="mt-4 space-y-3 text-sm">
            {sources.map((item) => (
              <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{item.label}</div>
                <div className="mt-1 text-muted-foreground">{item.code} · {item.adapter_key}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5 lg:col-span-2">
          <h2 className="text-xl">Последние ingest jobs</h2>
          <div className="mt-4 grid gap-3">
            {ingests.map((item) => (
              <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.code}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.source_registry_code} · raw {item.raw_count} · normalized {item.normalized_count} · merged {item.merged_count} · candidates {item.candidate_count}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-sm text-muted-foreground">{item.ingest_status}</div>
                    <Link href={`/supplier-ingests/${item.code}`}>
                      <Button variant="secondary">Raw layer</Button>
                    </Link>
                  </div>
                </div>
              </div>
            ))}
            {!ingests.length ? <div className="text-sm text-muted-foreground">Пока нет ingest jobs.</div> : null}
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
                      {item.code} · trust {item.trust_level} · status {item.supplier_status}
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
                  score {item.confidence_score} · {item.reason_code}
                </div>
                <div className="mt-1 text-sm text-foreground/80">
                  match: {item.matched_supplier?.display_name ?? "unknown"}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => void resolveCandidate(item.code, "merge")} disabled={loading}>
                    Merge
                  </Button>
                  <Button size="sm" onClick={() => void resolveCandidate(item.code, "reject")} disabled={loading}>
                    Separate
                  </Button>
                </div>
              </div>
            ))}
            {!candidates.length ? <div className="text-sm text-muted-foreground">Нет кандидатов на ручной dedup review.</div> : null}
          </div>
        </Card>
      </section>
    </main>
  );
}
