// RU: Файл входит в проверенный контур первой волны.
"use client";

import Link from "next/link";
import {useEffect, useMemo, useState} from "react";
import {useLocale, useTranslations} from "next-intl";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {fetchFoundationJson} from "@/lib/foundation-client";

type CatalogDirection = {
  code: string;
  label: string;
  item_count: number;
  modes: string[];
};

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
  mode: string;
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

function localizedDirectionLabel(direction: CatalogDirection, directionItems: CatalogItem[], locale: string): string {
  if (directionItems.length > 0) {
    return localizedCatalogText(directionItems[0], locale, "category_label") ?? direction.label;
  }
  return direction.label;
}

export function CatalogShowcase() {
  const t = useTranslations("catalogShowcase");
  const locale = useLocale();
  const [directions, setDirections] = useState<CatalogDirection[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [directionPayload, itemPayload] = await Promise.all([
          fetchFoundationJson<{items: CatalogDirection[]}>("/api/v1/public/catalog/directions"),
          fetchFoundationJson<{items: CatalogItem[]}>("/api/v1/public/catalog/items"),
        ]);
        if (!active) {
          return;
        }
        setDirections(directionPayload.items);
        setItems(itemPayload.items);
      } catch (requestError) {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "catalog_load_failed");
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const grouped = useMemo(() => {
    return directions.map((direction) => ({
      ...direction,
      items: items.filter((item) => item.category_code === direction.code),
    }));
  }, [directions, items]);

  return (
    <div className="space-y-6">
      <Card className="glass-panel border-white/12 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t("eyebrow")}</div>
            <h1 className="text-4xl leading-tight">{t("title")}</h1>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground">{t("text")}</p>
          </div>
          <Link href="/rfq">
            <Button>{t("openRfq")}</Button>
          </Link>
        </div>
      </Card>

      {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}

      <div className="grid gap-4 md:grid-cols-3">
        {directions.map((direction) => (
          <Card key={direction.code} className="glass-panel border-white/12 p-5">
            <div className="text-sm uppercase tracking-[0.22em] text-muted-foreground">{direction.item_count} {t("itemsCount")}</div>
            <h2 className="mt-2 text-2xl leading-tight">{localizedDirectionLabel(direction, items.filter((item) => item.category_code === direction.code), locale)}</h2>
            <div className="mt-3 text-sm leading-6 text-muted-foreground">{direction.modes.map((entry) => t(`modes.${entry}`)).join(" · ")}</div>
          </Card>
        ))}
      </div>

      <div className="space-y-5">
        {grouped.map((direction) => (
          <section key={direction.code} className="space-y-4">
            <div className="space-y-1">
              <div className="text-sm uppercase tracking-[0.22em] text-muted-foreground">{t("directionLabel")}</div>
              <h3 className="text-3xl leading-tight">{localizedDirectionLabel(direction, direction.items, locale)}</h3>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
              {direction.items.map((item) => (
                <Card key={item.code} className="glass-panel border-white/12 p-5">
                  <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    <span>{t(`modes.${item.mode}`)}</span>
                    <span>·</span>
                    <span>{t(`pricingModes.${item.pricing_mode}`)}</span>
                  </div>
                  <h4 className="mt-3 text-2xl leading-tight">{localizedCatalogText(item, locale, "title")}</h4>
                  <p className="mt-3 text-sm leading-7 text-muted-foreground">{localizedCatalogText(item, locale, "description")}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <span key={tag} className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs uppercase tracking-[0.18em] text-foreground/78">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 space-y-2 rounded-3xl border border-white/10 bg-black/10 p-4">
                    {localizedOptions(item, locale).map((entry) => (
                      <div key={entry} className="text-sm leading-6 text-foreground/82">
                        {entry}
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 rounded-3xl border border-white/10 bg-black/10 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t("pricingLabel")}</div>
                    <div className="mt-2 text-sm leading-6 text-foreground/86">{localizedCatalogText(item, locale, "pricing_summary")}</div>
                    {item.list_price ? (
                      <div className="mt-2 text-sm font-semibold">
                        {t("priceFrom", {amount: new Intl.NumberFormat(locale).format(item.list_price), currency: item.currency_code})}
                      </div>
                    ) : null}
                  </div>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <Link href={`/catalog/${item.code}`}>
                      <Button variant="secondary">{t("viewDetail")}</Button>
                    </Link>
                    <Link href={item.mode === "rfq" ? `/rfq?item=${item.code}` : `/catalog/${item.code}`}>
                      <Button>{item.mode === "rfq" ? t("openRfq") : t("startDraft")}</Button>
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
