// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useEffect, useState} from "react";

import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";

type IngestDetailPayload = {
  ingest: {
    code: string;
    source_registry_code?: string | null;
    ingest_status: string;
    raw_count: number;
    normalized_count: number;
    merged_count: number;
    candidate_count: number;
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

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Raw ingest</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Нужен foundation login.</p>
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
      <Link href="/suppliers" className="text-sm text-muted-foreground hover:text-foreground">← К supplier workbench</Link>
      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
      {payload ? (
        <>
          <Card className="glass-panel border-white/12 p-5">
            <h1 className="text-3xl leading-tight">{payload.ingest.code}</h1>
            <div className="mt-4 text-sm text-muted-foreground">
              {payload.ingest.source_registry_code} · {payload.ingest.ingest_status} · raw {payload.ingest.raw_count} · normalized {payload.ingest.normalized_count} · merged {payload.ingest.merged_count} · candidates {payload.ingest.candidate_count}
            </div>
          </Card>

          <section className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Raw layer</h2>
              <div className="mt-4 space-y-3">
                {payload.raw_records.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div className="font-medium">{item.company_name}</div>
                    <div className="mt-1 break-all text-muted-foreground">{item.source_url}</div>
                    <div className="mt-2 text-foreground/80">{item.raw_email || "no email"} · {item.raw_phone || "no phone"}</div>
                    <div className="mt-1 text-muted-foreground">{item.raw_address || "no address"}</div>
                    {item.normalization ? (
                      <div className="mt-3 rounded-2xl border border-white/10 bg-white/6 px-3 py-3">
                        <div>{item.normalization.canonical_name}</div>
                        <div className="mt-1 text-muted-foreground">{item.normalization.normalized_status}</div>
                        <div className="mt-1 text-muted-foreground">{item.normalization.capability_summary || "No capability summary"}</div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="glass-panel border-white/12 p-5">
              <h2 className="text-xl">Dedup review</h2>
              <div className="mt-4 space-y-3">
                {payload.dedup_candidates.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm">
                    <div>{item.normalization?.canonical_name || item.code}</div>
                    <div className="mt-1 text-muted-foreground">{item.candidate_status} · score {item.confidence_score}</div>
                    {item.matched_supplier ? (
                      <div className="mt-2">
                        <Link href={`/suppliers/${item.matched_supplier.code}`} className="text-primary underline-offset-4 hover:underline">
                          {item.matched_supplier.display_name}
                        </Link>
                      </div>
                    ) : null}
                  </div>
                ))}
                {!payload.dedup_candidates.length ? <div className="text-sm text-muted-foreground">В этом ingest нет спорных дублей.</div> : null}
              </div>
            </Card>
          </section>
        </>
      ) : (
        <Card className="glass-panel border-white/12 p-6 text-sm text-muted-foreground">Загрузка raw ingest...</Card>
      )}
    </main>
  );
}
