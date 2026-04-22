// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";

import {CatalogRequestForm} from "@/components/catalog/catalog-request-form";
import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson} from "@/lib/foundation-client";

type CatalogItem = {
  code: string;
  title: string;
  description: string | null;
  category_code: string;
  category_label: string;
  tags: string[];
  option_summaries: string[];
  list_price: number | null;
  currency_code: string;
  pricing_mode: string;
  pricing_summary: string | null;
  pricing_note: string | null;
  mode: "ready" | "config" | "rfq";
  translations: Record<string, Record<string, unknown>>;
};

function localizedCatalogText(
  item: CatalogItem,
  locale: string,
  field: "title" | "description" | "category_label" | "pricing_summary"
): string | null {
  const localized = item.translations?.[locale]?.[field];
  if (typeof localized === "string" && localized.trim()) {
    return localized;
  }
  return item[field];
}

function localizedOptions(item: CatalogItem, locale: string): string[] {
  const localized = item.translations?.[locale]?.option_summaries;
  if (Array.isArray(localized)) {
    return localized.filter((entry): entry is string => typeof entry === "string");
  }
  return item.option_summaries;
}

function intakeChannelForMode(mode: CatalogItem["mode"]): "catalog_ready" | "catalog_config" | "rfq_public" {
  if (mode === "ready") {
    return "catalog_ready";
  }
  if (mode === "config") {
    return "catalog_config";
  }
  return "rfq_public";
}

function detailExplain(mode: CatalogItem["mode"], locale: string) {
  if (mode === "ready") {
    return {
      fit: locale === "ru" ? "Подходит для понятного типового заказа, когда уже известны базовые параметры." : "Best for a straightforward job when the basic parameters are already clear.",
      prep: locale === "ru" ? "Подготовь размер, материал, тираж, дедлайн и ссылку на макет или пример." : "Prepare size, material, quantity, deadline, and a link to artwork or a reference.",
      flow: locale === "ru" ? "После отправки оператор проверит ввод, подтвердит расчёт и переведёт кейс в рабочую заявку." : "After submit, the operator reviews the input, confirms the estimate, and moves the case into a working request.",
    };
  }
  if (mode === "config") {
    return {
      fit: locale === "ru" ? "Подходит для типового продукта с уточнениями по материалу, формату или отделке." : "Best for a standard product that still needs decisions on material, format, or finish.",
      prep: locale === "ru" ? "Подготовь описание задачи, важные параметры, пример упаковки и дедлайн." : "Prepare the job description, key parameters, a packaging reference, and the deadline.",
      flow: locale === "ru" ? "Сначала собираем параметры, потом оператор проверяет ограничения и готовит коммерческий вариант." : "First we collect the parameters, then the operator checks constraints and prepares a commercial option.",
    };
  }
  return {
    fit: locale === "ru" ? "Подходит для нестандартного проекта, когда карточка не может честно обещать финальную цену." : "Best for a non-standard project where the card cannot honestly promise a final price.",
    prep: locale === "ru" ? "Подготовь задачу, желаемый результат, ограничения по производству, сроки и все исходные файлы." : "Prepare the brief, expected outcome, production constraints, timing, and all source files.",
    flow: locale === "ru" ? "Запрос уйдёт в ручной разбор. После проверки оператор соберёт предложение и маршрут исполнения." : "The request goes into manual review first. After validation, the operator prepares the offer and fulfillment route.",
  };
}

export function CatalogDetail({itemCode}: {itemCode: string}) {
  const t = useTranslations("catalogDetail");
  const locale = useLocale();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const payload = await fetchFoundationJson<{item: CatalogItem}>(`/api/v1/public/catalog/items/${itemCode}`);
        if (!active) {
          return;
        }
        setItem(payload.item);
      } catch (requestError) {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "catalog_item_not_found");
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [itemCode]);

  if (error) {
    return <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card>;
  }
  if (!item) {
    return <Card className="glass-panel border-white/12 p-6 text-sm text-muted-foreground">{t("loading")}</Card>;
  }

  const explain = detailExplain(item.mode, locale);

  return (
    <div className="space-y-6">
      <Card className="paper-panel p-6">
        <div className="flex flex-wrap gap-2">
          <span className="status-pill status-pill-muted">{localizedCatalogText(item, locale, "category_label")}</span>
          <span className={`status-pill ${item.mode === "rfq" ? "status-pill-warn" : item.mode === "config" ? "status-pill-primary" : "status-pill-success"}`}>{t(`modes.${item.mode}`)}</span>
          <span className="status-pill status-pill-muted">{t(`pricingModes.${item.pricing_mode}`)}</span>
        </div>
        <h1 className="mt-3 text-4xl leading-tight">{localizedCatalogText(item, locale, "title")}</h1>
        <p className="mt-4 max-w-4xl text-sm leading-7 text-muted-foreground">{localizedCatalogText(item, locale, "description")}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {item.tags.map((tag) => (
            <span key={tag} className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs uppercase tracking-[0.18em] text-foreground/78">
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/catalog">
            <Button variant="secondary">{t("backToCatalog")}</Button>
          </Link>
          {item.mode === "rfq" ? (
            <Link href={`/rfq?item=${item.code}`}>
              <Button>{t("openRfq")}</Button>
            </Link>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <Card className="paper-panel p-6">
          <div className="space-y-4">
            <div>
              <div className="text-sm uppercase tracking-[0.22em] text-muted-foreground">{t("optionsLabel")}</div>
              <h2 className="mt-2 text-2xl leading-tight">{t("optionsTitle")}</h2>
            </div>
            <div className="grid gap-3">
              {/* RU: Эти блоки объясняют карточку по-человечески: кому подходит, что подготовить и что произойдёт после отправки. */}
              <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{locale === "ru" ? "Кому подходит" : "Best for"}</div>
                <div className="mt-2 text-sm leading-6 text-foreground/84">{explain.fit}</div>
              </div>
              <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{locale === "ru" ? "Что подготовить" : "Prepare before submit"}</div>
                <div className="mt-2 text-sm leading-6 text-foreground/84">{explain.prep}</div>
              </div>
              <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{locale === "ru" ? "Что будет дальше" : "What happens next"}</div>
                <div className="mt-2 text-sm leading-6 text-foreground/84">{explain.flow}</div>
              </div>
            </div>
            <div className="space-y-3">
              {localizedOptions(item, locale).map((entry) => (
                <div key={entry} className="rounded-[1.4rem] border border-border/75 bg-white/54 px-4 py-3 text-sm leading-6 text-foreground/82">
                  {entry}
                </div>
              ))}
            </div>
            <div className="rounded-[1.4rem] border border-border/75 bg-white/54 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t("pricingLabel")}</div>
              <div className="mt-2 text-sm leading-6 text-foreground/86">{localizedCatalogText(item, locale, "pricing_summary")}</div>
              {item.pricing_note ? <div className="mt-2 text-sm leading-6 text-muted-foreground">{item.pricing_note}</div> : null}
              {item.list_price ? (
                <div className="mt-3 text-lg font-semibold">
                  {t("priceFrom", {amount: new Intl.NumberFormat(locale).format(item.list_price), currency: item.currency_code})}
                </div>
              ) : (
                <div className="mt-3 text-lg font-semibold">{t("priceOnRequest")}</div>
              )}
            </div>
          </div>
        </Card>

        <CatalogRequestForm
          catalogItemCode={item.code}
          catalogItemTitle={localizedCatalogText(item, locale, "title") ?? item.title}
          intakeChannel={intakeChannelForMode(item.mode)}
          defaultSummary={item.mode === "rfq" ? t("rfqSummary") : t("draftSummary")}
          compact={item.mode !== "rfq"}
        />
      </div>
    </div>
  );
}
