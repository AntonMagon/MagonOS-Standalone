"use client";

import Link from "next/link";
import {FormEvent, useEffect, useMemo, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {downloadFoundationFile, fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";
import {
  FILE_REVIEW_OPTIONS,
  FILE_TYPE_OPTIONS,
  VISIBILITY_SCOPE_OPTIONS,
  displayDocumentState,
  displayDocumentType,
  displayFileCheckState,
  displayFileType,
  displayLogisticsState,
  displayMaybe,
  displayOfferStatus,
  displayOrderStatus,
  displayPaymentState,
  displayReasonCode,
  displayRequestStatus,
  displayVisibilityScope,
  formatFoundationDate,
} from "@/lib/foundation-display";

// RU: Деталь заявки — основной operator экран intake-цепочки, где blockers, offers, files и timeline собираются вокруг одного Request.
type ManagedFile = {
  code: string;
  owner_type: string;
  file_type: string;
  title?: string | null;
  check_state: string;
  visibility_scope: string;
  final_flag: boolean;
  latest_version?: {
    code: string;
    version_no: number;
    original_name: string;
    byte_size?: number | null;
  } | null;
  download_url?: string | null;
};

type ManagedDocument = {
  code: string;
  owner_type: string;
  document_type: string;
  template_key: string;
  title: string;
  visibility_scope: string;
  sent_state: string;
  confirmation_state: string;
  current_version?: {
    code: string;
    version_no: number;
    download_url?: string | null;
  } | null;
  download_url?: string | null;
};

type RequestDetail = {
  code: string;
  customer_ref?: string | null;
  title?: string | null;
  summary?: string | null;
  item_service_context?: string | null;
  city?: string | null;
  request_status: string;
  requested_deadline_at?: string | null;
  reasons: Array<{code: string; reason_kind: string; reason_code: string; note?: string | null}>;
  clarification_cycles: Array<{code: string; cycle_index: number; cycle_status: string; opened_reason_code: string; opened_note?: string | null}>;
  follow_up_items: Array<{code: string; title: string; detail?: string | null; follow_up_status: string; due_at?: string | null; customer_visible: boolean}>;
  managed_files: ManagedFile[];
  documents: ManagedDocument[];
  order?: {code: string; order_status: string; payment_state: string; logistics_state: string} | null;
  timeline: Array<{code: string; action: string; reason?: string | null; created_at?: string | null}>;
};

type OfferCompareItem = {
  offer: {
    code: string;
    request_ref: string;
    current_version_no: number;
    offer_status: string;
    confirmation_state: string;
    amount?: number | null;
    currency_code: string;
    lead_time_days?: number | null;
    terms_text?: string | null;
    scenario_type: string;
    supplier_ref?: string | null;
    public_summary?: string | null;
  };
  current_version: {
    code: string;
    version_no: number;
    version_status: string;
    confirmation_state: string;
  };
  comparison?: {
    comparison_title?: string | null;
    comparison_rank?: number | null;
    recommended: boolean;
    highlights: string[];
  } | null;
};

type DocumentTemplate = {
  template_key: string;
  document_type: string;
  title_prefix: string;
  visibility_scope: string;
};

type RequestPayload = {item: RequestDetail};
type ComparePayload = {request: RequestDetail; items: OfferCompareItem[]};
type TemplatesPayload = {items: DocumentTemplate[]};

const TRANSITION_OPTIONS = [
  "needs_review",
  "needs_clarification",
  "supplier_search",
  "offer_prep",
  "offer_sent",
  "cancelled",
] as const;

function ownerLabel(ownerType: string): string {
  if (ownerType === "offer") {
    return "Предложение";
  }
  if (ownerType === "order") {
    return "Заказ";
  }
  return "Заявка";
}

export function RequestWorkbenchDetail({requestCode}: {requestCode: string}) {
  const session = readFoundationSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [item, setItem] = useState<RequestDetail | null>(null);
  const [offers, setOffers] = useState<OfferCompareItem[]>([]);
  const [documentTemplates, setDocumentTemplates] = useState<DocumentTemplate[]>([]);
  const [targetStatus, setTargetStatus] = useState("needs_review");
  const [reasonCode, setReasonCode] = useState("operator_review_started");
  const [reasonNote, setReasonNote] = useState("");
  const [reasonKind, setReasonKind] = useState("reason");
  const [followUpTitle, setFollowUpTitle] = useState("");
  const [followUpDetail, setFollowUpDetail] = useState("");
  const [followUpDueAt, setFollowUpDueAt] = useState("");
  const [followUpCustomerVisible, setFollowUpCustomerVisible] = useState(false);
  const [offerForm, setOfferForm] = useState({
    amount: "4200000",
    lead_time_days: "9",
    scenario_type: "baseline",
    supplier_ref: "",
    public_summary: "Базовый вариант для ручного коммерческого review.",
    terms_text: "50% предоплата после подтверждения версии, остаток перед отгрузкой.",
    comparison_title: "Базовый вариант",
    comparison_rank: "1",
    highlights_text: "Ручной review,Подтверждённый supplier,Срок 9 дней",
    recommended: true,
  });
  const [selectedOfferCode, setSelectedOfferCode] = useState("");
  const [fileOwnerScope, setFileOwnerScope] = useState<"request" | "offer">("request");
  const [fileVisibilityScope, setFileVisibilityScope] = useState("customer");
  const [fileType, setFileType] = useState("attachment");
  const [fileReasonCode, setFileReasonCode] = useState("request_file_uploaded");
  const [fileNote, setFileNote] = useState("");
  const [fileUpload, setFileUpload] = useState<File | null>(null);
  const [selectedFileCode, setSelectedFileCode] = useState("");
  const [fileReviewState, setFileReviewState] = useState<"passed" | "failed">("passed");
  const [documentOwnerScope, setDocumentOwnerScope] = useState<"request" | "offer">("request");
  const [documentTemplateKey, setDocumentTemplateKey] = useState("offer_proposal");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentVisibilityScope, setDocumentVisibilityScope] = useState("customer");
  const [documentReasonCode, setDocumentReasonCode] = useState("document_generated_from_request");
  const [documentNote, setDocumentNote] = useState("");
  const [selectedDocumentCode, setSelectedDocumentCode] = useState("");

  const selectedOffer = useMemo(
    () => offers.find((offerItem) => offerItem.offer.code === selectedOfferCode) ?? null,
    [offers, selectedOfferCode]
  );

  function resolveOwnerCode(scope: "request" | "offer"): string | null {
    if (scope === "request") {
      return requestCode;
    }
    return selectedOfferCode || null;
  }

  async function load() {
    if (!session?.token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [requestPayload, comparePayload, templatesPayload] = await Promise.all([
        fetchFoundationJson<RequestPayload>(`/api/v1/operator/requests/${requestCode}`, {}, session.token),
        fetchFoundationJson<ComparePayload>(`/api/v1/operator/requests/${requestCode}/offers/compare`, {}, session.token),
        fetchFoundationJson<TemplatesPayload>("/api/v1/operator/document-templates", {}, session.token),
      ]);
      setItem(requestPayload.item);
      setOffers(comparePayload.items);
      setDocumentTemplates(templatesPayload.items);
      setTargetStatus(requestPayload.item.request_status === "new" ? "needs_review" : requestPayload.item.request_status);
      if (comparePayload.items.length && !selectedOfferCode) {
        setSelectedOfferCode(comparePayload.items[0].offer.code);
      }
      if (requestPayload.item.managed_files.length && !selectedFileCode) {
        setSelectedFileCode(requestPayload.item.managed_files[0].code);
      }
      if (requestPayload.item.documents.length && !selectedDocumentCode) {
        setSelectedDocumentCode(requestPayload.item.documents[0].code);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "request_detail_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestCode, session?.token]);

  useEffect(() => {
    const selectedTemplate = documentTemplates.find((item) => item.template_key === documentTemplateKey);
    if (selectedTemplate) {
      setDocumentVisibilityScope(selectedTemplate.visibility_scope);
    }
  }, [documentTemplateKey, documentTemplates]);

  async function submitTransition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/requests/${requestCode}/transition`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({target_status: targetStatus, reason_code: reasonCode, note: reasonNote || null}),
      }, session.token);
      await load();
    } catch (transitionError) {
      setError(transitionError instanceof Error ? transitionError.message : "request_transition_failed");
    }
  }

  async function addReason(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/requests/${requestCode}/reasons`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_kind: reasonKind, reason_code: reasonCode, note: reasonNote || null}),
      }, session.token);
      await load();
    } catch (reasonError) {
      setError(reasonError instanceof Error ? reasonError.message : "request_reason_failed");
    }
  }

  async function addFollowUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/requests/${requestCode}/follow-up-items`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          title: followUpTitle,
          detail: followUpDetail || null,
          due_at: followUpDueAt || null,
          customer_visible: followUpCustomerVisible,
          reason_code: reasonCode,
        }),
      }, session.token);
      setFollowUpTitle("");
      setFollowUpDetail("");
      setFollowUpDueAt("");
      setFollowUpCustomerVisible(false);
      await load();
    } catch (followUpError) {
      setError(followUpError instanceof Error ? followUpError.message : "follow_up_failed");
    }
  }

  async function createOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/requests/${requestCode}/offers`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          amount: offerForm.amount ? Number(offerForm.amount) : null,
          currency_code: "VND",
          lead_time_days: offerForm.lead_time_days ? Number(offerForm.lead_time_days) : null,
          terms_text: offerForm.terms_text || null,
          scenario_type: offerForm.scenario_type,
          supplier_ref: offerForm.supplier_ref || null,
          public_summary: offerForm.public_summary || null,
          comparison_title: offerForm.comparison_title || null,
          comparison_rank: offerForm.comparison_rank ? Number(offerForm.comparison_rank) : null,
          recommended: offerForm.recommended,
          highlights: offerForm.highlights_text.split(",").map((itemText) => itemText.trim()).filter(Boolean),
          reason_code: "offer_created_from_workbench",
          note: "Operator created commercial offer variant from request workbench.",
        }),
      }, session.token);
      await load();
    } catch (offerError) {
      setError(offerError instanceof Error ? offerError.message : "offer_create_failed");
    }
  }

  async function reviseSelectedOffer() {
    if (!session?.token || !selectedOfferCode) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/offers/${selectedOfferCode}/revise`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          amount: offerForm.amount ? Number(offerForm.amount) : null,
          currency_code: "VND",
          lead_time_days: offerForm.lead_time_days ? Number(offerForm.lead_time_days) : null,
          terms_text: offerForm.terms_text || null,
          scenario_type: offerForm.scenario_type,
          supplier_ref: offerForm.supplier_ref || null,
          public_summary: offerForm.public_summary || null,
          comparison_title: offerForm.comparison_title || null,
          comparison_rank: offerForm.comparison_rank ? Number(offerForm.comparison_rank) : null,
          recommended: offerForm.recommended,
          highlights: offerForm.highlights_text.split(",").map((itemText) => itemText.trim()).filter(Boolean),
          reason_code: "offer_critical_revision",
          note: "Critical revision created a new offer version and reset prior confirmation.",
        }),
      }, session.token);
      await load();
    } catch (offerError) {
      setError(offerError instanceof Error ? offerError.message : "offer_revision_failed");
    }
  }

  async function runOfferAction(offerCode: string, action: "send" | "accept" | "decline" | "expire" | "convert") {
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      const path = action === "convert" ? `/api/v1/operator/offers/${offerCode}/convert-to-order` : `/api/v1/operator/offers/${offerCode}/${action}`;
      const reasonMap = {
        send: "offer_sent_to_customer",
        accept: "customer_acceptance_recorded",
        decline: "customer_decline_recorded",
        expire: "offer_expired_timeout",
        convert: "confirmed_offer_converted_to_order",
      } as const;
      await fetchFoundationJson(path, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          reason_code: reasonMap[action],
          note: `Operator action ${action} for commercial offer.`,
        }),
      }, session.token);
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "offer_action_failed");
    }
  }

  async function uploadManagedFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token || !fileUpload) {
      return;
    }
    const ownerCode = resolveOwnerCode(fileOwnerScope);
    if (!ownerCode) {
      setError("owner_scope_not_ready");
      return;
    }
    setError(null);
    const body = new FormData();
    body.append("owner_type", fileOwnerScope);
    body.append("owner_code", ownerCode);
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
      setError(uploadError instanceof Error ? uploadError.message : "file_upload_failed");
    }
  }

  async function reviewSelectedFile() {
    if (!session?.token || !selectedFileCode) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/files/${selectedFileCode}/review`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({target_state: fileReviewState, reason_code: fileReasonCode, note: fileNote || null}),
      }, session.token);
      await load();
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "file_review_failed");
    }
  }

  async function finalizeSelectedFile() {
    if (!session?.token || !selectedFileCode) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/files/${selectedFileCode}/finalize`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_code: fileReasonCode, note: fileNote || null}),
      }, session.token);
      await load();
    } catch (finalizeError) {
      setError(finalizeError instanceof Error ? finalizeError.message : "file_finalize_failed");
    }
  }

  async function generateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.token) {
      return;
    }
    const ownerCode = resolveOwnerCode(documentOwnerScope);
    if (!ownerCode) {
      setError("owner_scope_not_ready");
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson("/api/v1/operator/documents/generate", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({
          owner_type: documentOwnerScope,
          owner_code: ownerCode,
          template_key: documentTemplateKey,
          title: documentTitle || null,
          visibility_scope: documentVisibilityScope || null,
          reason_code: documentReasonCode,
          note: documentNote || null,
        }),
      }, session.token);
      await load();
    } catch (documentError) {
      setError(documentError instanceof Error ? documentError.message : "document_generate_failed");
    }
  }

  async function runDocumentAction(documentCode: string, action: "send" | "confirm" | "replace") {
    if (!session?.token) {
      return;
    }
    setError(null);
    try {
      await fetchFoundationJson(`/api/v1/operator/documents/${documentCode}/${action}`, {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({reason_code: documentReasonCode, note: documentNote || null}),
      }, session.token);
      await load();
    } catch (documentError) {
      setError(documentError instanceof Error ? documentError.message : "document_action_failed");
    }
  }

  async function downloadOperatorAsset(path: string | null | undefined, filename: string) {
    if (!path || !session?.token) {
      return;
    }
    try {
      await downloadFoundationFile(path, filename, session.token);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "file_download_failed");
    }
  }

  if (!session?.token) {
    return (
      <main className="container py-10">
        <Card className="glass-panel border-white/12 p-6">
          <h1 className="text-3xl leading-tight">Карточка заявки</h1>
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

  if (loading) {
    return <main className="container py-10"><Card className="glass-panel border-white/12 p-6">Загрузка карточки заявки...</Card></main>;
  }

  if (!item) {
    return <main className="container py-10"><Card className="glass-panel border-red-400/30 bg-red-500/10 p-6 text-red-100">{error ?? "request_not_found"}</Card></main>;
  }

  return (
    <main className="container space-y-6 py-10">
      <Card className="glass-panel border-white/12 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Рабочая карточка заявки</div>
            <h1 className="mt-2 text-3xl leading-tight">{item.title ?? item.code}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
              Заявка остаётся центральной рабочей сущностью: вокруг неё живут предложения, документы, файлы и причины решений, но они не смешиваются в одну запись.
            </p>
          </div>
          <div className="space-y-1 text-right text-sm text-muted-foreground">
            <div>Код заявки: {item.code}</div>
            <div>Клиентская ссылка: {item.customer_ref ?? "Не указана"}</div>
            <div>Статус: {displayRequestStatus(item.request_status)}</div>
          </div>
        </div>
        {item.summary ? <p className="mt-4 text-sm leading-7 text-foreground/84">{item.summary}</p> : null}
        {item.order ? (
          <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            Заказ {item.order.code} · {displayOrderStatus(item.order.order_status)} · {displayPaymentState(item.order.payment_state)} · {displayLogisticsState(item.order.logistics_state)}
            <div className="mt-3">
              <Link href={`/orders/${item.order.code}`}>
                <Button variant="outline">Открыть заказ</Button>
              </Link>
            </div>
          </div>
        ) : null}
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.04fr)_minmax(0,0.96fr)]">
        <div className="space-y-4">
          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Переход статуса</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void submitTransition(event)}>
              <div className="space-y-2">
                <Label htmlFor="target-status">Целевой статус</Label>
                <select id="target-status" className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={targetStatus} onChange={(event) => setTargetStatus(event.target.value)}>
                  {TRANSITION_OPTIONS.map((status) => <option key={status} value={status}>{displayRequestStatus(status)}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="reason-code">Код причины</Label>
                <Input id="reason-code" placeholder="например: operator_review_started" value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reason-note">Комментарий</Label>
                <Textarea id="reason-note" rows={3} value={reasonNote} onChange={(event) => setReasonNote(event.target.value)} />
              </div>
              <Button type="submit">Применить переход</Button>
            </form>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Предложения и версии</h2>
            <div className="mt-4 space-y-3 text-sm">
              {offers.map((offerItem) => (
                <div key={offerItem.offer.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{offerItem.comparison?.comparison_title ?? offerItem.offer.public_summary ?? offerItem.offer.code}</div>
                      <div className="mt-1 text-muted-foreground">
                        {displayOfferStatus(offerItem.offer.offer_status)} · {displayOfferStatus(offerItem.offer.confirmation_state)} · v{offerItem.offer.current_version_no}
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <input type="radio" name="selected-offer" checked={selectedOfferCode === offerItem.offer.code} onChange={() => setSelectedOfferCode(offerItem.offer.code)} />
                      выбран
                    </label>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <div>Цена: {offerItem.offer.amount ?? "Не указана"} {offerItem.offer.currency_code}</div>
                    <div>Срок: {offerItem.offer.lead_time_days ?? "Не указан"} дней</div>
                    <div>Сценарий: {displayMaybe(offerItem.offer.scenario_type)}</div>
                    <div>Поставщик: {offerItem.offer.supplier_ref ?? "Не назначен"}</div>
                  </div>
                  {offerItem.offer.terms_text ? <div className="mt-3 text-muted-foreground">{offerItem.offer.terms_text}</div> : null}
                  {offerItem.comparison?.highlights?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {offerItem.comparison.highlights.map((highlight) => (
                        <span key={highlight} className="rounded-full border border-white/10 px-3 py-1 text-xs text-muted-foreground">{highlight}</span>
                      ))}
                    </div>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" type="button" variant="outline" onClick={() => void runOfferAction(offerItem.offer.code, "send")}>Отправить</Button>
                    <Button size="sm" type="button" variant="outline" onClick={() => void runOfferAction(offerItem.offer.code, "accept")}>Подтвердить</Button>
                    <Button size="sm" type="button" variant="outline" onClick={() => void runOfferAction(offerItem.offer.code, "decline")}>Отклонить</Button>
                    <Button size="sm" type="button" variant="outline" onClick={() => void runOfferAction(offerItem.offer.code, "expire")}>Закрыть по сроку</Button>
                    <Button size="sm" type="button" onClick={() => void runOfferAction(offerItem.offer.code, "convert")}>Создать заказ</Button>
                  </div>
                </div>
              ))}
              {!offers.length ? <div className="text-muted-foreground">Для этой заявки пока нет коммерческих вариантов.</div> : null}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Создать или пересмотреть предложение</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void createOffer(event)}>
              <div className="grid gap-3 md:grid-cols-2">
                <Input placeholder="Цена" value={offerForm.amount} onChange={(event) => setOfferForm((current) => ({...current, amount: event.target.value}))} />
                <Input placeholder="Срок (в днях)" value={offerForm.lead_time_days} onChange={(event) => setOfferForm((current) => ({...current, lead_time_days: event.target.value}))} />
                <Input placeholder="Сценарий" value={offerForm.scenario_type} onChange={(event) => setOfferForm((current) => ({...current, scenario_type: event.target.value}))} />
                <Input placeholder="Код поставщика" value={offerForm.supplier_ref} onChange={(event) => setOfferForm((current) => ({...current, supplier_ref: event.target.value}))} />
                <Input placeholder="Название для сравнения" value={offerForm.comparison_title} onChange={(event) => setOfferForm((current) => ({...current, comparison_title: event.target.value}))} />
                <Input placeholder="Позиция в сравнении" value={offerForm.comparison_rank} onChange={(event) => setOfferForm((current) => ({...current, comparison_rank: event.target.value}))} />
              </div>
              <Textarea placeholder="Публичное описание версии" rows={3} value={offerForm.public_summary} onChange={(event) => setOfferForm((current) => ({...current, public_summary: event.target.value}))} />
              <Textarea placeholder="Коммерческие условия" rows={3} value={offerForm.terms_text} onChange={(event) => setOfferForm((current) => ({...current, terms_text: event.target.value}))} />
              <Input placeholder="Акценты через запятую" value={offerForm.highlights_text} onChange={(event) => setOfferForm((current) => ({...current, highlights_text: event.target.value}))} />
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input type="checkbox" checked={offerForm.recommended} onChange={(event) => setOfferForm((current) => ({...current, recommended: event.target.checked}))} />
                рекомендованный вариант
              </label>
              <div className="flex flex-wrap gap-2">
                <Button type="submit">Создать вариант</Button>
                <Button type="button" variant="outline" disabled={!selectedOfferCode} onClick={() => void reviseSelectedOffer()}>
                  Критично пересмотреть выбранный вариант
                </Button>
              </div>
            </form>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Управляемые файлы</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void uploadManagedFile(event)}>
              <div className="grid gap-3 md:grid-cols-2">
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileOwnerScope} onChange={(event) => setFileOwnerScope(event.target.value as "request" | "offer")}>
                  <option value="request">Заявка</option>
                  <option value="offer" disabled={!selectedOffer}>Выбранное предложение</option>
                </select>
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileType} onChange={(event) => setFileType(event.target.value)}>
                  {FILE_TYPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileVisibilityScope} onChange={(event) => setFileVisibilityScope(event.target.value)}>
                  {VISIBILITY_SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <Input placeholder="например: request_file_uploaded" value={fileReasonCode} onChange={(event) => setFileReasonCode(event.target.value)} />
              </div>
              <Textarea placeholder="Комментарий к файлу" rows={2} value={fileNote} onChange={(event) => setFileNote(event.target.value)} />
              <Input type="file" onChange={(event) => setFileUpload(event.target.files?.[0] ?? null)} />
              <Button type="submit" disabled={!fileUpload}>Загрузить файл</Button>
            </form>
            <div className="mt-6 space-y-3 text-sm">
              {item.managed_files.map((file) => (
                <div key={file.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{file.title ?? file.latest_version?.original_name ?? file.code}</div>
                      <div className="mt-1 text-muted-foreground">
                        {ownerLabel(file.owner_type)} · {displayFileType(file.file_type)} · {displayFileCheckState(file.check_state)} · {displayVisibilityScope(file.visibility_scope)} · {file.final_flag ? "Финальная версия" : "Рабочая версия"}
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <input type="radio" name="selected-file" checked={selectedFileCode === file.code} onChange={() => setSelectedFileCode(file.code)} />
                      выбран
                    </label>
                  </div>
                  {file.latest_version ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button size="sm" type="button" variant="outline" onClick={() => void downloadOperatorAsset(file.download_url, file.latest_version?.original_name ?? `${file.code}.bin`)}>
                        Скачать v{file.latest_version.version_no}
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
              {!item.managed_files.length ? <div className="text-muted-foreground">Пока нет managed files для request/offer/order слоя.</div> : null}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto]">
              <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={fileReviewState} onChange={(event) => setFileReviewState(event.target.value as "passed" | "failed")}>
                {FILE_REVIEW_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
              <Input placeholder="например: file_manual_review_approved" value={fileReasonCode} onChange={(event) => setFileReasonCode(event.target.value)} />
              <Button type="button" variant="outline" disabled={!selectedFileCode} onClick={() => void reviewSelectedFile()}>Зафиксировать проверку</Button>
              <Button type="button" disabled={!selectedFileCode} onClick={() => void finalizeSelectedFile()}>Сделать финальной</Button>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Уточнения и follow-up</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void addFollowUp(event)}>
              <Input placeholder="Название шага" value={followUpTitle} onChange={(event) => setFollowUpTitle(event.target.value)} />
              <Textarea placeholder="Что именно нужно сделать" rows={3} value={followUpDetail} onChange={(event) => setFollowUpDetail(event.target.value)} />
              <Input type="datetime-local" value={followUpDueAt} onChange={(event) => setFollowUpDueAt(event.target.value)} />
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input type="checkbox" checked={followUpCustomerVisible} onChange={(event) => setFollowUpCustomerVisible(event.target.checked)} />
                Видно клиенту
              </label>
              <Button type="submit">Создать follow-up</Button>
            </form>
            <div className="mt-4 space-y-3 text-sm">
              {item.follow_up_items.map((followUp) => (
                <div key={followUp.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">{followUp.title}</div>
                  <div className="mt-1 text-muted-foreground">{displayMaybe(followUp.follow_up_status)} · {followUp.customer_visible ? "Клиент видит" : "Внутренний контур"}</div>
                  {followUp.detail ? <div className="mt-2 text-foreground/80">{followUp.detail}</div> : null}
                </div>
              ))}
            </div>
            <div className="mt-4 space-y-3 text-sm">
              {item.clarification_cycles.map((cycle) => (
                <div key={cycle.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">Цикл #{cycle.cycle_index}</div>
                  <div className="mt-1 text-muted-foreground">{displayMaybe(cycle.cycle_status)} · {displayReasonCode(cycle.opened_reason_code)}</div>
                  {cycle.opened_note ? <div className="mt-2 text-foreground/80">{cycle.opened_note}</div> : null}
                </div>
              ))}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Управляемые документы</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void generateDocument(event)}>
              <div className="grid gap-3 md:grid-cols-2">
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={documentOwnerScope} onChange={(event) => setDocumentOwnerScope(event.target.value as "request" | "offer")}>
                  <option value="request">Заявка</option>
                  <option value="offer" disabled={!selectedOffer}>Выбранное предложение</option>
                </select>
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={documentTemplateKey} onChange={(event) => setDocumentTemplateKey(event.target.value)}>
                  {documentTemplates.map((template) => <option key={template.template_key} value={template.template_key}>{displayDocumentType(template.document_type)}</option>)}
                </select>
                <Input placeholder="Переопределение заголовка документа" value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} />
                <select className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={documentVisibilityScope} onChange={(event) => setDocumentVisibilityScope(event.target.value)}>
                  {VISIBILITY_SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <Input placeholder="например: document_generated_from_request" value={documentReasonCode} onChange={(event) => setDocumentReasonCode(event.target.value)} />
              </div>
              <Textarea placeholder="Комментарий к документу" rows={2} value={documentNote} onChange={(event) => setDocumentNote(event.target.value)} />
              <Button type="submit">Сгенерировать документ</Button>
            </form>
            <div className="mt-6 space-y-3 text-sm">
              {item.documents.map((document) => (
                <div key={document.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{document.title}</div>
                      <div className="mt-1 text-muted-foreground">
                        {ownerLabel(document.owner_type)} · {displayDocumentType(document.document_type)} · {displayDocumentState(document.sent_state)} · {displayDocumentState(document.confirmation_state)}
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <input type="radio" name="selected-document" checked={selectedDocumentCode === document.code} onChange={() => setSelectedDocumentCode(document.code)} />
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
                    <Button size="sm" type="button" onClick={() => void runDocumentAction(document.code, "replace")}>Заменить версией</Button>
                  </div>
                </div>
              ))}
              {!item.documents.length ? <div className="text-muted-foreground">Пока нет документов для этого контура.</div> : null}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Причины и блокеры</h2>
            <form className="mt-4 grid gap-3" onSubmit={(event) => void addReason(event)}>
              <div className="space-y-2">
                <Label htmlFor="reason-kind">Тип записи</Label>
                <select id="reason-kind" className="w-full rounded-xl border border-white/12 bg-black/10 px-3 py-2 text-sm" value={reasonKind} onChange={(event) => setReasonKind(event.target.value)}>
                  <option value="reason">Причина</option>
                  <option value="blocker">Блокер</option>
                </select>
              </div>
              <Button type="submit">Добавить запись</Button>
            </form>
            <div className="mt-4 space-y-3 text-sm">
              {item.reasons.map((reason) => (
                <div key={reason.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">{displayMaybe(reason.reason_kind)} · {displayReasonCode(reason.reason_code)}</div>
                  {reason.note ? <div className="mt-1 text-muted-foreground">{reason.note}</div> : null}
                </div>
              ))}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Хронология</h2>
            <div className="mt-4 space-y-3 text-sm">
              {item.timeline.map((event) => (
                <div key={event.code} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="font-medium">{displayMaybe(event.action)}</div>
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
