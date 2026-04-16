import Link from 'next/link';
import {getTranslations} from 'next-intl/server';
import {ArrowRight, DatabaseZap, Factory, ListChecks, MessageSquareQuote} from 'lucide-react';

import {MetricCard} from '@/components/dashboard/metric-card';
import {SectionIntro} from '@/components/sections/section-intro';
import {MagicCard} from '@/components/ui/magic-card';
import {defaultLocale} from '@/i18n/config';
import {getOperatorUrl, getPlatformStatus, getRecentCompanies} from '@/lib/standalone-api';

const linkedSurfaces = [
  {
    key: 'companies',
    href: getOperatorUrl('companies'),
    icon: Factory
  },
  {
    key: 'review',
    href: getOperatorUrl('review-queue'),
    icon: ListChecks
  },
  {
    key: 'feedback',
    href: getOperatorUrl('feedback-status'),
    icon: MessageSquareQuote
  }
] as const;

export default async function DashboardPage() {
  const t = await getTranslations({locale: defaultLocale, namespace: 'dashboard'});
  const status = await getPlatformStatus();
  const recentCompanies = await getRecentCompanies(4);

  const counts = status?.storage_counts || {};

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
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{t('runtimeLabel')}</p>
                  <h3 className="mt-2 text-2xl">{status ? t('runtimeOnline') : t('runtimeOffline')}</h3>
                </div>
                <div className="rounded-full border border-white/12 bg-white/6 p-2 text-primary">
                  <DatabaseZap className="h-5 w-5" />
                </div>
              </div>
              <div className="rounded-[1.2rem] border border-white/8 bg-black/12 p-4 text-sm leading-6 text-muted-foreground">
                {status ? t('runtimeDb', {path: status.db_path}) : t('runtimeUnavailable')}
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href={getOperatorUrl()}>
                  <span className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-glow">
                    {t('openConsole')}
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
                <Link href={getOperatorUrl('production-board')}>
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
            <h2 className="text-2xl">{t('workspaceTitle')}</h2>
            <p className="text-sm leading-6 text-muted-foreground">{t('workspaceText')}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
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
                  <div className="text-lg font-medium">{t(`surfaces.${surface.key}.title`)}</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{t(`surfaces.${surface.key}.body`)}</p>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('recentLabel')}</p>
            <h2 className="text-2xl">{t('recentTitle')}</h2>
          </div>
          <div className="grid gap-3">
            {recentCompanies.length ? (
              recentCompanies.map((company) => (
                <Link
                  key={company.id}
                  href={getOperatorUrl(`companies/${company.id}`)}
                  className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4 transition-colors hover:bg-black/16"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-lg font-medium">{company.canonical_name}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.22em] text-muted-foreground">{company.canonical_key}</div>
                    </div>
                    <ArrowRight className="mt-1 h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm text-muted-foreground">
                    <span>{company.city || t('recentUnknownCity')}</span>
                    <span>{company.canonical_email || t('recentNoEmail')}</span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="rounded-[1.2rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-muted-foreground">
                {t('recentEmpty')}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
