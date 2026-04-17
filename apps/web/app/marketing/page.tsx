// RU: Маркетинговая страница остаётся лёгким public-layer и ведёт в showcase/draft/RFQ, а не создаёт отдельный бизнес-модуль.
import Link from "next/link";
import {getTranslations} from "next-intl/server";
import {ArrowRight, Megaphone, NotebookTabs, PackageSearch, Workflow} from "lucide-react";

import {Card} from "@/components/ui/card";
import {MagneticButton} from "@/components/lightswind/magnetic-button";
import {ShinyButton} from "@/components/ui/shiny-button";

export default async function MarketingPage() {
  const t = await getTranslations("marketingPage");

  const promiseKeys = ["one", "two", "three"] as const;
  const flowKeys = ["one", "two", "three"] as const;
  const surfaceKeys = ["catalog", "rfq", "request"] as const;
  const surfaceIcons = {
    catalog: PackageSearch,
    rfq: NotebookTabs,
    request: Workflow,
  } as const;

  return (
    <main className="container space-y-6 py-10">
      <Card className="glass-panel border-white/12 p-6 md:p-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-center">
          <div className="space-y-4">
            <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t("eyebrow")}</div>
            <h1 className="text-4xl leading-tight">{t("title")}</h1>
            <p className="max-w-4xl text-sm leading-7 text-muted-foreground">{t("text")}</p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/catalog">
                <MagneticButton>
                  {t("openCatalog")}
                  <ArrowRight className="ml-2 inline-block h-4 w-4" />
                </MagneticButton>
              </Link>
              <Link href="/rfq">
                <ShinyButton className="border-white/12 bg-white/8 text-foreground hover:bg-white/12">{t("openRfq")}</ShinyButton>
              </Link>
              <Link href="/catalog">
                <ShinyButton className="border-white/12 bg-white/8 text-foreground hover:bg-white/12">{t("openDraft")}</ShinyButton>
              </Link>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/12 bg-black/10 p-5 backdrop-blur-xl">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Megaphone className="h-4 w-4 text-primary" />
              {t("promiseLabel")}
            </div>
            <h2 className="text-2xl leading-tight">{t("promiseTitle")}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{t("promiseText")}</p>
            <div className="mt-4 space-y-3">
              {promiseKeys.map((key) => (
                <div key={key} className="rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm leading-6 text-foreground/84">
                  {t(`promises.${key}`)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <section className="grid gap-4 lg:grid-cols-3">
        {flowKeys.map((key, index) => (
          <Card key={key} className="glass-panel border-white/12 p-5">
            <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t("flowLabel")} · {index + 1}</div>
            <h2 className="mt-2 text-2xl leading-tight">{t(`flow.${key}.title`)}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{t(`flow.${key}.body`)}</p>
          </Card>
        ))}
      </section>

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
                <div className="h-full rounded-[1.8rem] border border-white/12 bg-black/10 p-5 transition hover:bg-black/16">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/12 bg-white/8 text-primary">
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
    </main>
  );
}
