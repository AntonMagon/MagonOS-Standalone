// RU: Файл входит в проверенный контур первой волны.
import Link from "next/link";
import {getTranslations} from "next-intl/server";

import {CatalogRequestForm} from "@/components/catalog/catalog-request-form";
import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";

export default async function RfqPage({
  searchParams,
}: {
  searchParams: Promise<{item?: string}>;
}) {
  const params = await searchParams;
  const t = await getTranslations("rfqPage");

  return (
    <main className="container py-10">
      <div className="space-y-6">
        <Card className="paper-panel p-6">
          <div className="space-y-2">
            <div className="micro-label">{t("eyebrow")}</div>
            <h1 className="text-4xl leading-tight">{t("title")}</h1>
            <p className="max-w-4xl text-base leading-8 text-muted-foreground">{t("text")}</p>
          </div>
          <div className="mt-5">
            <Link href="/catalog">
              <Button variant="secondary">{t("backToCatalog")}</Button>
            </Link>
          </div>
        </Card>

        <CatalogRequestForm
          // RU: RFQ всегда ведёт в ручной разбор и не должен маскироваться под мгновенный каталоговый заказ.
          catalogItemCode={params.item}
          intakeChannel="rfq_public"
          defaultSummary={t("defaultSummary")}
        />
      </div>
    </main>
  );
}
