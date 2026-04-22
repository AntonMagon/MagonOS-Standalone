// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson, useFoundationSession} from "@/lib/foundation-client";
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

function draftNextStep(status: string): string {
  if (status === "draft") return "Проверь описание, сроки и контактные данные.";
  if (status === "awaiting_data") return "Нужно добрать обязательные поля или файлы.";
  if (status === "ready_to_submit") return "Черновик готов: можно переводить в рабочую заявку.";
  if (status === "blocked") return "Есть блокер: сначала сними причину, потом двигай дальше.";
  return "Проверь, можно ли переводить кейс в следующий этап.";
}

function requestNextStep(status: string): string {
  if (status === "new") return "Открой заявку и зафиксируй первый разбор.";
  if (status === "needs_review") return "Проверь ввод, материалы и срок, затем задай следующий этап.";
  if (status === "needs_clarification") return "Нужно добрать уточнения от клиента или оператора.";
  if (status === "supplier_search") return "Подбери поставщика и собери рабочий коммерческий вариант.";
  if (status === "offer_prep") return "Подготовь предложение и проверь файлы с документами.";
  if (status === "offer_sent") return "Дождись ответа по предложению и следи за блокерами.";
  return "Открой заявку и проверь, что требуется сделать сейчас.";
}

export function RequestWorkbench() {
  // RU: Workbench — один из главных operator экранов, поэтому убираем прямое чтение localStorage из render path.
  const session = useFoundationSession();
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
        <Card className="paper-panel p-6">
          <h1 className="text-3xl leading-tight">Заявки и черновики</h1>
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
      <Card className="paper-panel p-6">
        <div className="micro-label">Рабочий стол приёма</div>
        <h1 className="mt-3 text-3xl leading-tight">Все входящие кейсы в одном месте</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
          Слева то, что ещё собирается как черновик. Справа то, что уже стало рабочей заявкой и требует следующего действия от оператора.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {/* RU: Явно разделяем draft и request прямо в шапке, чтобы оператор не угадывал границу сущностей по статусам. */}
          <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4 text-sm leading-6 text-foreground/82">
            <div className="font-medium">Черновик</div>
            <div className="mt-1 text-muted-foreground">Кейс ещё собирает обязательные поля и не должен уходить в работу раньше времени.</div>
          </div>
          <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4 text-sm leading-6 text-foreground/82">
            <div className="font-medium">Заявка</div>
            <div className="mt-1 text-muted-foreground">Кейс уже в работе: здесь появляются предложения, документы, причины и заказ.</div>
          </div>
        </div>
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
      {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка панели приёма...</Card> : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="paper-panel p-5">
          <h2 className="text-xl">Очередь черновиков</h2>
          <div className="mt-4 space-y-3">
            {drafts.map((item) => (
              <Link key={item.code} href={`/drafts/${item.code}`} className="block rounded-[1.5rem] border border-border/75 bg-white/54 p-4 transition hover:bg-white/70">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.title ?? item.code}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <span className="status-pill status-pill-muted">{item.code}</span>
                      <span className="status-pill status-pill-primary">{displayDraftStatus(item.draft_status)}</span>
                    </div>
                    <div className="mt-3 text-sm text-muted-foreground">{displayMaybe(item.customer_email)} · {displayMaybe(item.city)}</div>
                    <div className="mt-3 text-sm leading-6 text-foreground/82">{draftNextStep(item.draft_status)}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">{formatFoundationDate(item.requested_deadline_at)}</div>
                </div>
              </Link>
            ))}
            {!drafts.length ? <div className="text-sm text-muted-foreground">Очередь черновиков пока пуста.</div> : null}
          </div>
        </Card>

        <Card className="paper-panel p-5">
          <h2 className="text-xl">Очередь заявок</h2>
          <div className="mt-4 space-y-3">
            {requests.map((item) => (
              <Link key={item.code} href={`/request-workbench/${item.code}`} className="block rounded-[1.5rem] border border-border/75 bg-white/54 p-4 transition hover:bg-white/70">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.title ?? item.code}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <span className="status-pill status-pill-muted">{item.code}</span>
                      <span className={`status-pill ${item.request_status === "needs_clarification" ? "status-pill-warn" : item.request_status === "offer_sent" ? "status-pill-success" : "status-pill-primary"}`}>
                        {displayRequestStatus(item.request_status)}
                      </span>
                    </div>
                    <div className="mt-3 text-sm text-muted-foreground">{displayMaybe(item.customer_email)} · {displayMaybe(item.city)}</div>
                    <div className="mt-3 text-sm leading-6 text-foreground/82">{requestNextStep(item.request_status)}</div>
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
