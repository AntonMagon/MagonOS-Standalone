import Link from 'next/link';
import {getTranslations} from 'next-intl/server';
import {ArrowRight, CircleAlert, DatabaseZap, Factory, ListChecks, MessageSquareQuote, Settings2} from 'lucide-react';

import {MetricCard} from '@/components/dashboard/metric-card';
import {SectionIntro} from '@/components/sections/section-intro';
import {MagicCard} from '@/components/ui/magic-card';
import {getPlatformStatus} from '@/lib/standalone-api';

// RU: Dashboard остаётся коротким runtime-входом в ключевые operator surfaces, а не отдельной бизнес-панелью со своей логикой.
const linkedSurfaces = [
  {
    key: 'suppliers',
    href: '/suppliers',
    icon: Factory
  },
  {
    key: 'requests',
    href: '/request-workbench',
    icon: ListChecks
  },
  {
    key: 'orders',
    href: '/orders',
    icon: MessageSquareQuote
  }
] as const;

export default async function DashboardPage() {
  // RU: Данные берём напрямую из API, чтобы главный экран не жил своей отдельной тестовой правдой.
  const t = await getTranslations('dashboard');
  const status = await getPlatformStatus();

  const counts = status?.storage_counts || {};
  // RU: На overview держим только следующие рабочие переходы, чтобы экран не имитировал аналитику без действия.
  const actionItems = [
    {
      title: t('actions.requests.title'),
      body: t('actions.requests.body'),
      href: '/request-workbench',
      icon: ListChecks,
    },
    {
      title: t('actions.suppliers.title'),
      body: t('actions.suppliers.body'),
      href: '/suppliers',
      icon: Factory,
    },
    {
      title: t('actions.config.title'),
      body: t('actions.config.body'),
      href: '/admin-config',
      icon: Settings2,
    },
  ] as const;

  return (
    <main className="container space-y-6 pt-8 md:space-y-8 md:pt-10">
      <section className="glass-panel reveal-section overflow-hidden rounded-[2.2rem] border-white/12 px-6 py-6 md:px-8 md:py-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
          <div className="space-y-6">
            <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} />
            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard title={t('metrics.companies.title')} value={String(counts.canonical_companies ?? 0)} detail={t('metrics.companies.detail')} />
              <MetricCard title={t('metrics.queue.title')} value={String(counts.review_queue ?? 0)} detail={t('metrics.queue.detail')} tone="accent" />
              <MetricCard title={t('metrics.feedback.title')} value={String(counts.feedback_events ?? 0)} detail={t('metrics.feedback.detail')} />
            </div>
          </div>

          <MagicCard className="rounded-[1.8rem] border-white/12" mode="gradient" gradientFrom="#ee4f27" gradientTo="#54d2b5">
            <div className="space-y-5 p-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">{t('runtimeLabel')}</p>
                  <h3 className="mt-2 text-2xl leading-tight">{status ? t('runtimeOnline') : t('runtimeOffline')}</h3>
                </div>
                <div className="rounded-full border border-white/12 bg-white/6 p-2 text-primary">
                  <DatabaseZap className="h-5 w-5" />
                </div>
              </div>
              <div className="break-words rounded-[1.2rem] border border-white/8 bg-black/12 p-4 text-sm leading-6 text-muted-foreground">
                {status ? t('runtimeDb', {label: status.db_label}) : t('runtimeUnavailable')}
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/ops-workbench">
                  <span className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-glow">
                    {t('openConsole')}
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
                <Link href="/orders">
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-foreground">
                    {t('openBoard')}
                  </span>
                </Link>
              </div>
            </div>
          </MagicCard>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.08fr_0.92fr]">
        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('workspaceLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('workspaceTitle')}</h2>
            <p className="text-sm leading-6 text-muted-foreground">{t('workspaceText')}</p>
          </div>
          <div className="grid gap-3 xl:grid-cols-3">
            {linkedSurfaces.map((surface) => {
              const Icon = surface.icon;
              return (
                <Link
                  key={surface.key}
                  href={surface.href}
                  className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4 transition-colors hover:bg-black/16"
                >
                  <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/12 bg-white/6 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="text-lg font-medium leading-tight">{t(`surfaces.${surface.key}.title`)}</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{t(`surfaces.${surface.key}.body`)}</p>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('recentLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('recentTitle')}</h2>
          </div>
          <div className="grid gap-3">
            {actionItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4 transition-colors hover:bg-black/16">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="text-lg font-medium leading-tight">{item.title}</div>
                      <div className="mt-2 text-sm leading-6 text-muted-foreground">{item.body}</div>
                    </div>
                    <div className="rounded-full border border-white/12 bg-white/8 p-2 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                </Link>
              );
            })}
            <div className="rounded-[1.2rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-muted-foreground">
              <div className="flex items-start gap-3">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span>{t('recentEmpty')}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
