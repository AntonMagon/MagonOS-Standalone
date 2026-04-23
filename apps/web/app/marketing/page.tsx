// RU: Маркетинговая страница остаётся лёгким public-layer и ведёт в showcase/draft/RFQ, а не создаёт отдельный бизнес-модуль.
import Link from "next/link";
import {getTranslations} from "next-intl/server";
import {ArrowRight, ClipboardList, Megaphone, NotebookTabs, PackageSearch, Workflow} from "lucide-react";

import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";

export default async function MarketingPage() {
  const t = await getTranslations("marketingPage");

  const promiseKeys = ["one", "two", "three"] as const;
  const flowKeys = ["one", "two", "three"] as const;
  // RU: Маркетинговая страница рекламирует только реальные точки входа, а не абстрактные контуры и модули.
  const surfaceKeys = ["catalog", "rfq", "request"] as const;
  const surfaceIcons = {
    catalog: PackageSearch,
    rfq: NotebookTabs,
    request: Workflow,
  } as const;

  return (
    <main className="container space-y-6 py-10">
      <section className="sheet-panel overflow-hidden p-6 md:p-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-center">
          <div className="space-y-4">
            <div className="micro-label">{t("eyebrow")}</div>
            <h1 className="max-w-4xl text-4xl leading-tight md:text-5xl">{t("title")}</h1>
            <p className="max-w-4xl text-base leading-8 text-muted-foreground">{t("text")}</p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link href="/catalog">
                <Button size="lg">
                  {t("openCatalog")}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/rfq">
                <Button size="lg" variant="secondary">{t("openRfq")}</Button>
              </Link>
            </div>
          </div>

          <div className="paper-panel p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Megaphone className="h-4 w-4 text-primary" />
              {t("promiseLabel")}
            </div>
            <h2 className="text-2xl leading-tight">{t("promiseTitle")}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{t("promiseText")}</p>
            <div className="mt-4 space-y-3">
              {promiseKeys.map((key) => (
                <div key={key} className="rounded-[1.3rem] border border-border/75 bg-white/52 px-4 py-3 text-sm leading-6 text-foreground/84">
                  {t(`promises.${key}`)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {flowKeys.map((key, index) => (
          <article key={key} className="paper-panel p-5">
            <div className="status-pill status-pill-primary">{index + 1}</div>
            <h2 className="mt-4 text-2xl leading-tight">{t(`flow.${key}.title`)}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{t(`flow.${key}.body`)}</p>
          </article>
        ))}
      </section>

      <Card className="paper-panel p-6">
        <div className="space-y-2">
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t("flowLabel")}</div>
          <h2 className="text-3xl leading-tight">{t("flowTitle")}</h2>
        </div>
        <p className="mt-3 max-w-4xl text-sm leading-7 text-muted-foreground">{t("promiseText")}</p>
      </Card>

      <Card className="glass-panel border-white/12 p-6">
        <div className="space-y-2">
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t("surfacesLabel")}</div>
          <h2 className="text-3xl leading-tight">{t("surfacesTitle")}</h2>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {surfaceKeys.map((key) => {
            const Icon = surfaceIcons[key];
            const href = key === "catalog" ? "/catalog" : key === "rfq" ? "/rfq" : "/login";
            return (
              <Link key={key} href={href}>
                <div className="h-full rounded-[1.6rem] border border-border/75 bg-white/52 p-5 transition hover:bg-white/70">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border/75 bg-white/70 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="mt-4 text-xl leading-tight">{t(`surfaces.${key}.title`)}</div>
                  <p className="mt-3 text-sm leading-7 text-muted-foreground">{t(`surfaces.${key}.body`)}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </Card>

      <Card className="paper-panel p-6">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <ClipboardList className="h-4 w-4 text-primary" />
              {t("openDraft")}
            </div>
            <h2 className="mt-2 text-3xl leading-tight">{t("promiseTitle")}</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">{t("surfaces.request.body")}</p>
          </div>
          <Link href="/login">
            <Button size="lg" variant="secondary">
              {t("surfaces.request.title")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </Card>
    </main>
  );
}
