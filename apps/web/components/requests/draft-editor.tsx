"use client";

import Link from "next/link";
import {useRouter} from "next/navigation";
import {FormEvent, startTransition, useEffect, useMemo, useRef, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {fetchFoundationJson} from "@/lib/foundation-client";
import {displayDraftStatus, displayReasonCode, formatFoundationDate} from "@/lib/foundation-display";

// RU: Draft editor обслуживает только intake-слой до submit и не должен сам исполнять operator-only workflow.
type DraftDetail = {
  id: string;
  code: string;
  title?: string | null;
  summary?: string | null;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
  guest_company_name?: string | null;
  item_service_context?: string | null;
  city?: string | null;
  requested_deadline_at?: string | null;
  locale_code: string;
  draft_status: string;
  source_channel: string;
  submitted_request_id?: string | null;
  submitted_request_customer_ref?: string | null;
  required_fields_state: Array<{field_name: string; field_status: string; message?: string | null}>;
  file_links: Array<{code: string; label: string; file_url: string}>;
  timeline: Array<{code: string; action: string; reason?: string | null; created_at?: string | null}>;
};

type DraftPayload = {item: DraftDetail};
type SubmitPayload = {
  request: {
    code: string;
    customer_ref: string;
  };
};

type DraftEditorProps = {
  draftCode: string;
};

type DraftFormState = {
  title: string;
  summary: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  guest_company_name: string;
  item_service_context: string;
  city: string;
  requested_deadline_at: string;
};

const EMPTY_FORM: DraftFormState = {
  title: "",
  summary: "",
  customer_name: "",
  customer_email: "",
  customer_phone: "",
  guest_company_name: "",
  item_service_context: "",
  city: "",
  requested_deadline_at: "",
};

export function DraftEditor({draftCode}: DraftEditorProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [item, setItem] = useState<DraftDetail | null>(null);
  const [form, setForm] = useState<DraftFormState>(EMPTY_FORM);
  const [lastSynced, setLastSynced] = useState("");
  const [linkLabel, setLinkLabel] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const initializedRef = useRef(false);

  function toFormState(payload: DraftDetail): DraftFormState {
    return {
      title: payload.title ?? "",
      summary: payload.summary ?? "",
      customer_name: payload.customer_name ?? "",
      customer_email: payload.customer_email ?? "",
      customer_phone: payload.customer_phone ?? "",
      guest_company_name: payload.guest_company_name ?? "",
      item_service_context: payload.item_service_context ?? "",
      city: payload.city ?? "",
      requested_deadline_at: payload.requested_deadline_at ? payload.requested_deadline_at.slice(0, 16) : "",
    };
  }

  async function loadDraft() {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchFoundationJson<DraftPayload>(`/api/v1/public/draft-requests/${draftCode}`);
      setItem(payload.item);
      const nextForm = toFormState(payload.item);
      const serialized = JSON.stringify(nextForm);
      initializedRef.current = true;
      setForm(nextForm);
      setLastSynced(serialized);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "draft_load_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDraft();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftCode]);

  const serializedForm = useMemo(() => JSON.stringify(form), [form]);

  useEffect(() => {
    if (!initializedRef.current || !item || item.submitted_request_id) {
      return;
    }
    if (serializedForm === lastSynced) {
      return;
    }
    const timeout = window.setTimeout(async () => {
      setSaving(true);
      setError(null);
      try {
        const payload = await fetchFoundationJson<DraftPayload>(`/api/v1/public/draft-requests/${draftCode}`, {
          method: "PATCH",
          headers: {"content-type": "application/json"},
          body: JSON.stringify(form),
        });
        setItem(payload.item);
        setLastSynced(serializedForm);
      } catch (saveError) {
        setError(saveError instanceof Error ? saveError.message : "draft_autosave_failed");
      } finally {
        setSaving(false);
      }
    }, 900);
    return () => window.clearTimeout(timeout);
  }, [draftCode, form, item, lastSynced, serializedForm]);

  async function handleAddLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/public/draft-requests/${draftCode}/file-links`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          label: linkLabel,
          file_url: linkUrl,
          visibility: "role",
          reason_code: "customer_file_link_added",
        }),
      });
      setLinkLabel("");
      setLinkUrl("");
      await loadDraft();
    } catch (linkError) {
      setError(linkError instanceof Error ? linkError.message : "draft_file_link_failed");
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = await fetchFoundationJson<SubmitPayload>(`/api/v1/public/draft-requests/${draftCode}/submit`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          reason_code: "customer_submit_ready_draft",
          note: "Клиент отправил готовый черновик в центральный контур приёма.",
        }),
      });
      startTransition(() => {
        router.push(`/requests/${payload.request.customer_ref}`);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "draft_submit_failed");
      setSubmitting(false);
    }
  }

  async function handleAbandon() {
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/public/draft-requests/${draftCode}/abandon`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          target_status: "abandoned",
          reason_code: "customer_abandoned_draft",
          note: "Customer explicitly abandoned draft.",
        }),
      });
      await loadDraft();
    } catch (abandonError) {
      setError(abandonError instanceof Error ? abandonError.message : "draft_abandon_failed");
    }
  }

  if (loading) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">Загрузка черновика...</Card>
      </main>
    );
  }

  if (!item) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-red-400/30 bg-red-500/10 p-6 text-red-100">{error ?? "draft_not_found"}</Card>
      </main>
    );
  }

  return (
    <main className="container space-y-6 py-10">
      <Card className="paper-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="micro-label">Черновик клиента</div>
            <h1 className="mt-2 text-3xl leading-tight">Подготовка заявки {item.code}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
              Это ещё не рабочая заявка. Здесь нужно собрать обязательные поля, ссылки на файлы и понятное описание задачи, после чего кейс уйдёт в операторский приём.
            </p>
          </div>
          <div className="space-y-2 text-right text-sm text-muted-foreground">
            <div>Статус: {displayDraftStatus(item.draft_status)}</div>
            <div>{saving ? "Автосохранение..." : "Автосохранение активно"}</div>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {/* RU: Сначала объясняем цель черновика и следующий шаг, а уже потом показываем обязательные поля и историю. */}
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4 text-sm leading-6 text-foreground/82">
            <div className="font-medium">Что сделать</div>
            <div className="mt-1 text-muted-foreground">Опиши задачу, сроки, контакт и всё, что влияет на расчёт.</div>
          </div>
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4 text-sm leading-6 text-foreground/82">
            <div className="font-medium">Когда появится заявка</div>
            <div className="mt-1 text-muted-foreground">Только после того, как обязательные поля будут заполнены и черновик отправят в работу.</div>
          </div>
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4 text-sm leading-6 text-foreground/82">
            <div className="font-medium">Что дальше увидит оператор</div>
            <div className="mt-1 text-muted-foreground">Описание задачи, файлы, сроки и контекст товара или услуги без потери данных.</div>
          </div>
        </div>
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
        <Card className="glass-panel border-white/12 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="draft-title">Название</Label>
              <Input id="draft-title" value={form.title} onChange={(event) => setForm((prev) => ({...prev, title: event.target.value}))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="draft-summary">Описание</Label>
              <Textarea id="draft-summary" rows={5} value={form.summary} onChange={(event) => setForm((prev) => ({...prev, summary: event.target.value}))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="draft-context">Контекст товара / услуги</Label>
              <Textarea id="draft-context" rows={4} value={form.item_service_context} onChange={(event) => setForm((prev) => ({...prev, item_service_context: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-email">Email</Label>
              <Input id="draft-email" type="email" value={form.customer_email} onChange={(event) => setForm((prev) => ({...prev, customer_email: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-name">Контакт</Label>
              <Input id="draft-name" value={form.customer_name} onChange={(event) => setForm((prev) => ({...prev, customer_name: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-phone">Телефон</Label>
              <Input id="draft-phone" value={form.customer_phone} onChange={(event) => setForm((prev) => ({...prev, customer_phone: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-company">Компания</Label>
              <Input id="draft-company" value={form.guest_company_name} onChange={(event) => setForm((prev) => ({...prev, guest_company_name: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-city">Город</Label>
              <Input id="draft-city" value={form.city} onChange={(event) => setForm((prev) => ({...prev, city: event.target.value}))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="draft-deadline">Дедлайн</Label>
              <Input id="draft-deadline" type="datetime-local" value={form.requested_deadline_at} onChange={(event) => setForm((prev) => ({...prev, requested_deadline_at: event.target.value}))} />
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button onClick={() => void handleSubmit()} disabled={submitting || item.draft_status !== "ready_to_submit"}>
              {submitting ? "Отправка..." : "Перевести в заявку"}
            </Button>
            <Button variant="secondary" onClick={() => void handleAbandon()} disabled={item.draft_status === "archived"}>
              Пометить как брошенный
            </Button>
            {item.submitted_request_customer_ref ? (
              <Link href={`/requests/${item.submitted_request_customer_ref}`}>
                <Button variant="secondary">Открыть связанную заявку</Button>
              </Link>
            ) : null}
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Что ещё нужно заполнить</h2>
            <div className="mt-4 space-y-3">
              {item.required_fields_state.map((field) => (
                <div key={field.field_name} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">{field.field_name}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{field.field_status === "complete" ? "Заполнено" : "Нужно заполнить"}</div>
                  {field.message ? <div className="mt-1 text-sm text-foreground/80">{field.message}</div> : null}
                </div>
              ))}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Ссылки на файлы и материалы</h2>
            <form className="mt-4 space-y-3" onSubmit={(event) => void handleAddLink(event)}>
              <Input placeholder="Название ссылки" value={linkLabel} onChange={(event) => setLinkLabel(event.target.value)} />
              <Input placeholder="https://..." value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} />
              <Button type="submit">Добавить ссылку</Button>
            </form>
            <div className="mt-4 space-y-2 text-sm">
              {item.file_links.map((link) => (
                <a key={link.code} href={link.file_url} target="_blank" rel="noreferrer" className="block rounded-2xl border border-white/10 bg-black/10 px-3 py-3 hover:bg-black/16">
                  {link.label}
                </a>
              ))}
              {!item.file_links.length ? <div className="text-muted-foreground">Пока нет ссылок на файлы.</div> : null}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">История черновика</h2>
            <div className="mt-4 space-y-3 text-sm">
              {item.timeline.map((event) => (
                <div key={event.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">{displayReasonCode(event.action)}</div>
                  <div className="mt-1 text-muted-foreground">{displayReasonCode(event.reason)} · {formatFoundationDate(event.created_at)}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>
    </main>
  );
}
