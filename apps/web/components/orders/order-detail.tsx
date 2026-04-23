"use client";

import Link from "next/link";
import {FormEvent, useEffect, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {downloadFoundationFile, fetchFoundationJson, useFoundationSession} from "@/lib/foundation-client";
import {
  displayDocumentState,
  displayDocumentType,
  displayFileCheckState,
  displayFileType,
  displayLogisticsState,
  displayMaybe,
  displayOrderStatus,
  displayPaymentState,
  displayReadinessState,
  displayReasonCode,
  displayVisibilityScope,
  FILE_REVIEW_OPTIONS,
  FILE_TYPE_OPTIONS,
  formatFoundationDate,
  ORDER_ACTION_LABELS,
  VISIBILITY_SCOPE_OPTIONS,
} from "@/lib/foundation-display";

// RU: Деталь заказа остаётся execution-экраном после accepted offer и не смешивает order-state с offer/request DTO.
type OrderDetail = {
  code: string;
  order_status: string;
  payment_state: string;
  logistics_state: string;
  readiness_state: string;
  refund_state: string;
  dispute_state: string;
  supplier_refs: string[];
  customer_refs: {customer_name?: string | null; customer_ref?: string | null; customer_email?: string | null};
};

type OrderLine = {
  code: string;
  title: string;
  quantity: number;
  unit_label: string;
  line_status: string;
  planned_supplier_ref?: string | null;
  planned_stage_refs: string[];
  readiness_state: string;
  delivery_state: string;
  refund_state: string;
  dispute_state: string;
};

type PaymentRecord = {
  code: string;
  payment_state: string;
  amount?: number | null;
  currency_code: string;
  payment_ref?: string | null;
  provider_ref?: string | null;
};

type LedgerEntry = {
  code: string;
  entry_kind: string;
  direction: string;
  entry_state: string;
  amount?: number | null;
  currency_code: string;
  reason_code: string;
};

type ManagedFile = {
  code: string;
  owner_type: string;
  file_type: string;
  title?: string | null;
  check_state: string;
  visibility_scope: string;
  final_flag: boolean;
  latest_version?: {code: string; version_no: number; original_name: string} | null;
  download_url?: string | null;
};

type ManagedDocument = {
  code: string;
  document_type: string;
  template_key: string;
  title: string;
  sent_state: string;
  confirmation_state: string;
  current_version?: {code: string; version_no: number} | null;
  download_url?: string | null;
};

type TimelineEvent = {code: string; action: string; reason?: string | null; created_at?: string | null};
type Payload = {
  item: OrderDetail;
  lines: OrderLine[];
  payments: PaymentRecord[];
  ledger: LedgerEntry[];
  files: ManagedFile[];
  documents: ManagedDocument[];
  timeline: TimelineEvent[];
};

type DocumentTemplate = {
  template_key: string;
  document_type: string;
  title_prefix: string;
  visibility_scope: string;
};

type TemplatesPayload = {items: DocumentTemplate[]};

const ACTIONS = ["assign_supplier", "confirm_start", "mark_production", "ready", "delivery", "complete", "cancel", "dispute"] as const;
const PAYMENT_STATES = ["pending", "confirmed", "failed", "partially_refunded", "refunded"] as const;

function orderActionHint(item: OrderDetail): string {
  if (item.payment_state === "pending") return "Сначала нужно подтвердить оплату.";
  if (!item.supplier_refs.length) return "Нужно назначить поставщика.";
  if (item.readiness_state !== "ready") return "Нужно довести заказ до готовности.";
  if (item.logistics_state === "not_started") return "Нужно запланировать отгрузку.";
  if (item.order_status === "completed") return "Проверь итоговые документы и закрытие.";
  return "Открой действия по заказу и зафиксируй следующий переход.";
}

export function OrderDetailView({orderCode}: {orderCode: string}) {
  // RU: Деталь заказа тоже должна получать стабильный initial session snapshot, иначе layout скачет на гидратации.
  const session = useFoundationSession();
  const [payload, setPayload] = useState<Payload | null>(null);
  const [documentTemplates, setDocumentTemplates] = useState<DocumentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<typeof ACTIONS[number]>("assign_supplier");
  const [reasonCode, setReasonCode] = useState("order_supplier_assigned");
  const [note, setNote] = useState("");
  const [supplierRef, setSupplierRef] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentReason, setPaymentReason] = useState("manual_payment_record_created");
  const [paymentTargetState, setPaymentTargetState] = useState<typeof PAYMENT_STATES[number]>("pending");
  const [selectedPaymentCode, setSelectedPaymentCode] = useState("");
  const [fileVisibilityScope, setFileVisibilityScope] = useState("internal");
  const [fileType, setFileType] = useState("attachment");
  const [fileReasonCode, setFileReasonCode] = useState("order_file_uploaded");
  const [fileNote, setFileNote] = useState("");
  const [fileUpload, setFileUpload] = useState<File | null>(null);
  const [selectedFileCode, setSelectedFileCode] = useState("");
  const [fileReviewState, setFileReviewState] = useState<"passed" | "failed">("passed");
  const [documentTemplateKey, setDocumentTemplateKey] = useState("internal_job");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentVisibilityScope, setDocumentVisibilityScope] = useState("internal");
  const [documentReasonCode, setDocumentReasonCode] = useState("order_document_generated");
  const [documentNote, setDocumentNote] = useState("");
  const [selectedDocumentCode, setSelectedDocumentCode] = useState("");

  async function load() {
    if (!session?.token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [data, templatesPayload] = await Promise.all([
        fetchFoundationJson<Payload>(`/api/v1/operator/orders/${orderCode}`, {}, session.token),
        fetchFoundationJson<TemplatesPayload>("/api/v1/operator/document-templates", {}, session.token),
      ]);
      setPayload(data);
      setDocumentTemplates(templatesPayload.items);
      if (data.payments.length && !selectedPaymentCode) {
        setSelectedPaymentCode(data.payments[0].code);
      }
      if (data.files.length && !selectedFileCode) {
        setSelectedFileCode(data.files[0].code);
      }
      if (data.documents.length && !selectedDocumentCode) {
        setSelectedDocumentCode(data.documents[0].code);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "order_load_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderCode, session?.token]);

  useEffect(() => {
    const selectedTemplate = documentTemplates.find((item) => item.template_key === documentTemplateKey);
    if (selectedTemplate) {
      setDocumentVisibilityScope(selectedTemplate.visibility_scope);
    }
  }, [documentTemplateKey, documentTemplates]);

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    try {
      await fetchFoundationJson(`/api/v1/operator/orders/${orderCode}/action`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          action,
          reason_code: reasonCode,
          note: note || null,
          supplier_ref: supplierRef || null,
        }),
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "order_action_failed");
    }
  }

  async function createPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    try {
      const payment = await fetchFoundationJson<{item: PaymentRecord}>(`/api/v1/operator/orders/${orderCode}/payments`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          amount: paymentAmount ? Number(paymentAmount) : null,
          currency_code: "VND",
          reason_code: paymentReason,
          note: note || null,
        }),
      }, session.token);
      setSelectedPaymentCode(payment.item.code);
      await load();
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "payment_create_failed");
    }
  }

  async function transitionPayment() {
    if (!session?.token || !selectedPaymentCode) {
      return;
    }
    try {
      await fetchFoundationJson(`/api/v1/operator/payment-records/${selectedPaymentCode}/transition`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({target_state: paymentTargetState, reason_code: paymentReason, note: note || null}),
      }, session.token);
      await load();
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "payment_transition_failed");
    }
  }

  async function uploadManagedFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token || !fileUpload) {
      return;
    }
    const body = new FormData();
    body.append("owner_type", "order");
    body.append("owner_code", orderCode);
    body.append("file_type", fileType);
    body.append("visibility_scope", fileVisibilityScope);
    body.append("reason_code", fileReasonCode);
    body.append("note", fileNote);
    body.append("upload", fileUpload);
    try {
      await fetchFoundationJson("/api/v1/operator/files/upload", {method: "POST", body}, session.token);
      setFileUpload(null);
      await load();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "order_file_upload_failed");
    }
  }

  async function reviewSelectedFile() {
    if (!session?.token || !selectedFileCode) {
      return;
    }
    try {
      await fetchFoundationJson(`/api/v1/operator/files/${selectedFileCode}/review`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({target_state: fileReviewState, reason_code: fileReasonCode, note: fileNote || null}),
      }, session.token);
      await load();
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "order_file_review_failed");
    }
  }

  async function finalizeSelectedFile() {
    if (!session?.token || !selectedFileCode) {
      return;
    }
    try {
      await fetchFoundationJson(`/api/v1/operator/files/${selectedFileCode}/finalize`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_code: fileReasonCode, note: fileNote || null}),
      }, session.token);
      await load();
    } catch (finalizeError) {
      setError(finalizeError instanceof Error ? finalizeError.message : "order_file_finalize_failed");
    }
  }

  async function generateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    try {
      await fetchFoundationJson("/api/v1/operator/documents/generate", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          owner_type: "order",
          owner_code: orderCode,
          template_key: documentTemplateKey,
          title: documentTitle || null,
          visibility_scope: documentVisibilityScope || null,
          reason_code: documentReasonCode,
          note: documentNote || null,
        }),
      }, session.token);
      await load();
    } catch (documentError) {
      setError(documentError instanceof Error ? documentError.message : "order_document_generate_failed");
    }
  }

  async function runDocumentAction(documentCode: string, actionName: "send" | "confirm" | "replace") {
    if (!session?.token) {
      return;
    }
    try {
      await fetchFoundationJson(`/api/v1/operator/documents/${documentCode}/${actionName}`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_code: documentReasonCode, note: documentNote || null}),
      }, session.token);
      await load();
    } catch (documentError) {
      setError(documentError instanceof Error ? documentError.message : "order_document_action_failed");
    }
  }

  async function downloadOperatorAsset(path: string | null | undefined, filename: string) {
    if (!path || !session?.token) {
      return;
    }
    try {
      await downloadFoundationFile(path, filename, session.token);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "order_download_failed");
    }
  }

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Карточка заказа</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">Для этого экрана нужен вход с ролью оператора или администратора.</p>
          <div className="mt-6"><Link href="/login"><Button>Открыть вход</Button></Link></div>
        </Card>
      </main>
    );
  }

  if (loading) {
    return <main className="container py-10"><Card className="glass-panel border-white/12 p-6">Загрузка заказа...</Card></main>;
  }

  if (!payload) {
    return <main className="container py-10"><Card className="glass-panel border-red-400/30 bg-red-500/10 p-6 text-red-100">{error ?? "Заказ не найден"}</Card></main>;
  }

  return (
    <main className="container space-y-6 py-10">
      <Card className="paper-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="micro-label">Рабочий заказ</div>
            <h1 className="mt-2 text-3xl leading-tight">{payload.item.code}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
              Этот экран нужен, чтобы быстро понять: что с оплатой, кто исполняет заказ, на каком этапе готовность и какое действие нужно сделать сейчас.
            </p>
          </div>
          <div className="space-y-2 text-right text-sm text-muted-foreground">
            <div className="status-pill status-pill-primary">{displayOrderStatus(payload.item.order_status)}</div>
            <div>{displayPaymentState(payload.item.payment_state)}</div>
            <div>{displayLogisticsState(payload.item.logistics_state)}</div>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {/* RU: Верхняя сводка отвечает на четыре главных вопроса по заказу до погружения в формы и таблицы ниже. */}
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Оплата</div>
            <div className="mt-2 text-base font-medium">{displayPaymentState(payload.item.payment_state)}</div>
          </div>
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Готовность</div>
            <div className="mt-2 text-base font-medium">{displayReadinessState(payload.item.readiness_state)}</div>
          </div>
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Поставщик</div>
            <div className="mt-2 text-sm leading-6 text-foreground/84">{payload.item.supplier_refs.length ? payload.item.supplier_refs.join(', ') : 'Ещё не назначен'}</div>
          </div>
          <div className="rounded-[1.3rem] border border-border/75 bg-white/54 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Что сделать сейчас</div>
            <div className="mt-2 text-sm leading-6 text-foreground/84">{orderActionHint(payload.item)}</div>
          </div>
        </div>
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Что сделать сейчас</h2>
          <form className="mt-4 grid gap-3" onSubmit={(event) => void submitAction(event)}>
            <div className="space-y-2">
              <Label htmlFor="order-action">Операция</Label>
              <select id="order-action" className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={action} onChange={(event) => setAction(event.target.value as typeof ACTIONS[number])}>
                {ACTIONS.map((item) => <option key={item} value={item}>{ORDER_ACTION_LABELS[item]}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="order-reason-code">Код причины</Label>
              <Input id="order-reason-code" value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} placeholder="order_supplier_assigned" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="order-supplier-ref">Ref поставщика</Label>
              <Input id="order-supplier-ref" value={supplierRef} onChange={(event) => setSupplierRef(event.target.value)} placeholder="SUPC-..." />
            </div>
            <div className="space-y-2">
              <Label htmlFor="order-note">Комментарий</Label>
              <Textarea id="order-note" rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
            </div>
            <Button type="submit">Применить операцию</Button>
          </form>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Оплата и подтверждение</h2>
          <form className="mt-4 grid gap-3" onSubmit={(event) => void createPayment(event)}>
            <div className="space-y-2">
              <Label htmlFor="payment-amount">Сумма</Label>
              <Input id="payment-amount" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="payment-reason">Код причины</Label>
              <Input id="payment-reason" value={paymentReason} onChange={(event) => setPaymentReason(event.target.value)} placeholder="manual_payment_record_created" />
            </div>
            <Button type="submit" variant="outline">Создать запись оплаты</Button>
          </form>
          <div className="mt-6 space-y-2">
            <Label htmlFor="payment-record-select">Изменение статуса оплаты</Label>
            <select id="payment-record-select" className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={selectedPaymentCode} onChange={(event) => setSelectedPaymentCode(event.target.value)}>
              <option value="">Выбрать запись оплаты</option>
              {payload.payments.map((item) => <option key={item.code} value={item.code}>{item.code} · {displayPaymentState(item.payment_state)}</option>)}
            </select>
            <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={paymentTargetState} onChange={(event) => setPaymentTargetState(event.target.value as typeof PAYMENT_STATES[number])}>
              {PAYMENT_STATES.map((item) => <option key={item} value={item}>{displayPaymentState(item)}</option>)}
            </select>
            <Button type="button" onClick={() => void transitionPayment()}>Обновить статус оплаты</Button>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Позиции заказа</h2>
          <div className="mt-4 space-y-3 text-sm">
            {payload.lines.map((line) => (
              <div key={line.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="font-medium">{line.title}</div>
                <div className="mt-2 grid gap-2 text-muted-foreground md:grid-cols-2">
                  <div>{displayMaybe(line.line_status)}</div>
                  <div>{line.quantity} {line.unit_label}</div>
                  <div>Поставщик: {line.planned_supplier_ref ?? "Не назначен"}</div>
                  <div>Этапы: {line.planned_stage_refs.join(", ") || "Не заданы"}</div>
                  <div>Готовность: {displayReadinessState(line.readiness_state)}</div>
                  <div>Доставка: {displayLogisticsState(line.delivery_state)}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Платежи и движения</h2>
          <div className="mt-4 space-y-3 text-sm">
            {payload.payments.map((payment) => (
              <div key={payment.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{payment.code}</div>
                <div className="mt-1 text-muted-foreground">{displayPaymentState(payment.payment_state)} · {payment.amount ?? "Не указана"} {payment.currency_code}</div>
              </div>
            ))}
            {!payload.payments.length ? <div className="text-muted-foreground">Пока нет записей оплаты.</div> : null}
            <div className="pt-2 text-xs uppercase tracking-[0.22em] text-muted-foreground">Ledger</div>
            {payload.ledger.map((entry) => (
              <div key={entry.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                <div className="font-medium">{displayMaybe(entry.entry_kind)}</div>
                <div className="mt-1 text-muted-foreground">{displayMaybe(entry.direction)} · {displayMaybe(entry.entry_state)} · {entry.amount ?? "Не указана"} {entry.currency_code}</div>
                <div className="mt-1 text-muted-foreground">{displayReasonCode(entry.reason_code)}</div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Файлы по заказу</h2>
          <form className="mt-4 grid gap-3" onSubmit={(event) => void uploadManagedFile(event)}>
            <div className="grid gap-3 md:grid-cols-2">
              <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileType} onChange={(event) => setFileType(event.target.value)}>
                {FILE_TYPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
              <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileVisibilityScope} onChange={(event) => setFileVisibilityScope(event.target.value)}>
                {VISIBILITY_SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
              <Input placeholder="order_file_uploaded" value={fileReasonCode} onChange={(event) => setFileReasonCode(event.target.value)} />
            </div>
            <Textarea placeholder="Комментарий к файлу" rows={2} value={fileNote} onChange={(event) => setFileNote(event.target.value)} />
            <Input type="file" onChange={(event) => setFileUpload(event.target.files?.[0] ?? null)} />
            <Button type="submit" disabled={!fileUpload}>Загрузить файл в заказ</Button>
          </form>
          <div className="mt-6 space-y-3 text-sm">
            {payload.files.map((file) => (
              <div key={file.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{file.title ?? file.latest_version?.original_name ?? file.code}</div>
                    <div className="mt-1 text-muted-foreground">
                      {displayFileType(file.file_type)} · {displayFileCheckState(file.check_state)} · {displayVisibilityScope(file.visibility_scope)} · {file.final_flag ? "Финальная версия" : "Рабочая версия"}
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input type="radio" name="selected-order-file" checked={selectedFileCode === file.code} onChange={() => setSelectedFileCode(file.code)} />
                    выбран
                  </label>
                </div>
                {file.latest_version ? (
                  <div className="mt-3">
                    <Button size="sm" type="button" variant="outline" onClick={() => void downloadOperatorAsset(file.download_url, file.latest_version?.original_name ?? `${file.code}.bin`)}>
                      Скачать v{file.latest_version.version_no}
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
            {!payload.files.length ? <div className="text-muted-foreground">Пока нет файлов на уровне заказа.</div> : null}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto]">
            <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileReviewState} onChange={(event) => setFileReviewState(event.target.value as "passed" | "failed")}>
              {FILE_REVIEW_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <Input placeholder="file_manual_review_passed" value={fileReasonCode} onChange={(event) => setFileReasonCode(event.target.value)} />
            <Button type="button" variant="outline" disabled={!selectedFileCode} onClick={() => void reviewSelectedFile()}>Провести проверку</Button>
            <Button type="button" disabled={!selectedFileCode} onClick={() => void finalizeSelectedFile()}>Зафиксировать как финальный</Button>
          </div>
        </Card>

        <Card className="glass-panel border-white/12 p-5">
          <h2 className="text-xl">Документы по заказу</h2>
          <form className="mt-4 grid gap-3" onSubmit={(event) => void generateDocument(event)}>
            <div className="grid gap-3 md:grid-cols-2">
              <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={documentTemplateKey} onChange={(event) => setDocumentTemplateKey(event.target.value)}>
                {documentTemplates.map((template) => (
                  <option key={template.template_key} value={template.template_key}>{displayDocumentType(template.document_type)}</option>
                ))}
              </select>
              <Input placeholder="Переопределение названия документа" value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} />
              <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={documentVisibilityScope} onChange={(event) => setDocumentVisibilityScope(event.target.value)}>
                {VISIBILITY_SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
              <Input placeholder="order_document_generated" value={documentReasonCode} onChange={(event) => setDocumentReasonCode(event.target.value)} />
            </div>
            <Textarea placeholder="Комментарий к документу" rows={2} value={documentNote} onChange={(event) => setDocumentNote(event.target.value)} />
            <Button type="submit">Сгенерировать документ</Button>
          </form>
          <div className="mt-6 space-y-3 text-sm">
            {payload.documents.map((document) => (
              <div key={document.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{document.title}</div>
                    <div className="mt-1 text-muted-foreground">
                      {displayDocumentType(document.document_type)} · {displayDocumentState(document.sent_state)} · {displayDocumentState(document.confirmation_state)}
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input type="radio" name="selected-order-document" checked={selectedDocumentCode === document.code} onChange={() => setSelectedDocumentCode(document.code)} />
                    выбран
                  </label>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {document.download_url && document.current_version ? (
                    <Button size="sm" type="button" variant="outline" onClick={() => void downloadOperatorAsset(document.download_url, `${document.title}.md`)}>
                      Скачать v{document.current_version.version_no}
                    </Button>
                  ) : null}
                  <Button size="sm" type="button" variant="outline" onClick={() => void runDocumentAction(document.code, "send")}>Отправить</Button>
                  <Button size="sm" type="button" variant="outline" onClick={() => void runDocumentAction(document.code, "confirm")}>Подтвердить</Button>
                  <Button size="sm" type="button" onClick={() => void runDocumentAction(document.code, "replace")}>Заменить</Button>
                </div>
              </div>
            ))}
            {!payload.documents.length ? <div className="text-muted-foreground">Пока нет документов на уровне заказа.</div> : null}
          </div>
        </Card>
      </section>

      <Card className="glass-panel border-white/12 p-5">
        <h2 className="text-xl">История исполнения</h2>
        <div className="mt-4 space-y-3 text-sm">
          {payload.timeline.map((event) => (
            <div key={event.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="font-medium">{displayMaybe(event.action)}</div>
              <div className="mt-1 text-muted-foreground">{displayReasonCode(event.reason)} · {formatFoundationDate(event.created_at)}</div>
            </div>
          ))}
        </div>
      </Card>
    </main>
  );
}
