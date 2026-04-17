// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
import {displayDraftStatus, displayMaybe, displayRequestStatus, formatFoundationDate} from "@/lib/foundation-display";

// RU: Workbench показывает очередь заявок как единый operator вход, а не как набор несвязанных статических карточек.
type DraftListItem = {
  code: string;
  title?: string | null;
  customer_email?: string | null;
  city?: string | null;
  draft_status: string;
  requested_deadline_at?: string | null;
};

type RequestListItem = {
  code: string;
  customer_ref?: string | null;
  title?: string | null;
  customer_email?: string | null;
  city?: string | null;
  request_status: string;
  requested_deadline_at?: string | null;
};

export function RequestWorkbench() {
  const session = readFoundationSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<DraftListItem[]>([]);
  const [requests, setRequests] = useState<RequestListItem[]>([]);

  useEffect(() => {
    const token = session?.token;
    if (!token) {
      setLoading(false);
      return;
    }
    let active = true;
    async function load() {
      setLoading(true);
        setError(null);
        try {
          const [draftPayload, requestPayload] = await Promise.all([
          fetchFoundationJson<{items: DraftListItem[]}>("/api/v1/operator/draft-requests", {}, token),
          fetchFoundationJson<{items: RequestListItem[]}>("/api/v1/operator/requests", {}, token),
        ]);
        if (active) {
          setDrafts(draftPayload.items);
          setRequests(requestPayload.items);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "request_workbench_failed");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [session?.token]);

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Интейк-панель заявок</h1>
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
    <main className="container space-y-6 py-10">
      <Card className="glass-panel border-white/12 p-6">
        <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Первая волна приёма</div>
        <h1 className="mt-2 text-3xl leading-tight">Черновики и заявки</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
          Центральный коммерческий вход первой волны: черновик собирает исходные данные, а заявка становится рабочей сущностью для проверки и движения дальше.
        </p>
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
      {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка панели приёма...</Card> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Очередь черновиков</h2>
          <div className="mt-4 space-y-3">
            {drafts.map((item) => (
              <Link key={item.code} href={`/drafts/${item.code}`} className="block rounded-2xl border border-white/10 bg-black/10 p-4 hover:bg-black/16">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.title ?? item.code}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{item.code} · {displayDraftStatus(item.draft_status)}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{displayMaybe(item.customer_email)} · {displayMaybe(item.city)}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">{formatFoundationDate(item.requested_deadline_at)}</div>
                </div>
              </Link>
            ))}
            {!drafts.length ? <div className="text-sm text-muted-foreground">Очередь черновиков пока пуста.</div> : null}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Очередь заявок</h2>
          <div className="mt-4 space-y-3">
            {requests.map((item) => (
              <Link key={item.code} href={`/request-workbench/${item.code}`} className="block rounded-2xl border border-white/10 bg-black/10 p-4 hover:bg-black/16">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.title ?? item.code}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{item.code} · {displayRequestStatus(item.request_status)}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{displayMaybe(item.customer_email)} · {displayMaybe(item.city)}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">{formatFoundationDate(item.requested_deadline_at)}</div>
                </div>
              </Link>
            ))}
            {!requests.length ? <div className="text-sm text-muted-foreground">Очередь заявок пока пуста.</div> : null}
          </div>
        </Card>
      </section>
    </main>
  );
}
