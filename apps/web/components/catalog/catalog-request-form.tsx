// RU: Файл входит в проверенный контур первой волны.
"use client";

import {FormEvent, startTransition, useMemo, useState} from "react";
import {useRouter} from "next/navigation";
import {useLocale, useTranslations} from "next-intl";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";

type CatalogRequestFormProps = {
  catalogItemCode?: string;
  catalogItemTitle?: string;
  intakeChannel: "catalog_ready" | "catalog_config" | "rfq_public";
  defaultSummary?: string;
  compact?: boolean;
};

type DraftResponse = {
  item: {
    code: string;
    title: string;
    intake_channel: string;
    draft_status: string;
  };
};

export function CatalogRequestForm({
  catalogItemCode,
  catalogItemTitle,
  intakeChannel,
  defaultSummary,
  compact = false,
}: CatalogRequestFormProps) {
  const t = useTranslations("catalogForms");
  const locale = useLocale();
  const router = useRouter();
  const [customerName, setCustomerName] = useState("");
  const [guestCompanyName, setGuestCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [requestedDeadlineAt, setRequestedDeadlineAt] = useState("");
  const [title, setTitle] = useState(
    catalogItemTitle ? t("titlePrefill", {title: catalogItemTitle}) : t("rfqTitlePrefill")
  );
  const [itemServiceContext, setItemServiceContext] = useState(
    catalogItemTitle ? t("contextPrefill", {title: catalogItemTitle}) : t("contextPlaceholder")
  );
  const [summary, setSummary] = useState(defaultSummary ?? t("summaryPlaceholder"));
  const [honeypot, setHoneypot] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<DraftResponse["item"] | null>(null);
  const startedAt = useMemo(() => Date.now(), []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/platform-api/api/v1/public/draft-requests", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({
          customer_email: email,
          customer_name: customerName || null,
          customer_phone: phone || null,
          guest_company_name: guestCompanyName || null,
          catalog_item_code: catalogItemCode || null,
          title,
          summary,
          item_service_context: itemServiceContext,
          city: city || null,
          requested_deadline_at: requestedDeadlineAt || null,
          intake_channel: intakeChannel,
          locale_code: locale,
          honeypot,
          elapsed_ms: Date.now() - startedAt,
        }),
      });
      const payload = (await response.json()) as DraftResponse | {detail?: string};
      if (!response.ok) {
        throw new Error(typeof payload === "object" && payload && "detail" in payload ? payload.detail || "draft_create_failed" : "draft_create_failed");
      }
      setSuccess((payload as DraftResponse).item);
      startTransition(() => {
        router.push(`/drafts/${(payload as DraftResponse).item.code}`);
      });
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "draft_create_failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="glass-panel border-white/12 p-6">
      <div className="space-y-2">
        <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t(`labels.${intakeChannel}`)}</div>
        <h2 className="text-2xl leading-tight">{compact ? t("compactTitle") : t("fullTitle")}</h2>
        <p className="text-sm leading-6 text-muted-foreground">
          {catalogItemTitle ? t("linkedItem", {title: catalogItemTitle}) : t("generalLead")}
        </p>
      </div>

      <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-name">{t("customerName")}</Label>
          <Input id="catalog-request-name" value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-company">{t("companyName")}</Label>
          <Input id="catalog-request-company" value={guestCompanyName} onChange={(event) => setGuestCompanyName(event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-email">{t("email")}</Label>
          <Input id="catalog-request-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-phone">{t("phone")}</Label>
          <Input id="catalog-request-phone" value={phone} onChange={(event) => setPhone(event.target.value)} />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="catalog-request-title">{t("title")}</Label>
          <Input id="catalog-request-title" required value={title} onChange={(event) => setTitle(event.target.value)} />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="catalog-request-summary">{t("summary")}</Label>
          <Textarea
            id="catalog-request-summary"
            required
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            rows={compact ? 4 : 6}
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="catalog-request-context">{t("context")}</Label>
          <Textarea
            id="catalog-request-context"
            required
            value={itemServiceContext}
            onChange={(event) => setItemServiceContext(event.target.value)}
            rows={compact ? 3 : 4}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-city">{t("city")}</Label>
          <Input id="catalog-request-city" required value={city} onChange={(event) => setCity(event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="catalog-request-deadline">{t("deadline")}</Label>
          <Input
            id="catalog-request-deadline"
            type="datetime-local"
            required
            value={requestedDeadlineAt}
            onChange={(event) => setRequestedDeadlineAt(event.target.value)}
          />
        </div>
        <div className="hidden" aria-hidden="true">
          <Label htmlFor="catalog-request-honeypot">{t("websiteTrap")}</Label>
          <Input id="catalog-request-honeypot" tabIndex={-1} autoComplete="off" value={honeypot} onChange={(event) => setHoneypot(event.target.value)} />
        </div>
        <div className="md:col-span-2 flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={loading}>
            {loading ? t("submitting") : t("submit")}
          </Button>
          <div className="text-sm leading-6 text-muted-foreground">{t("privacyHint")}</div>
        </div>
        {error ? (
          <div className="md:col-span-2 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
        ) : null}
        {success ? (
          <div className="md:col-span-2 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
            {t("success", {code: success.code})}
          </div>
        ) : null}
      </form>
    </Card>
  );
}
