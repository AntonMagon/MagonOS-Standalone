import Link from 'next/link';
import {getLocale, getTranslations} from 'next-intl/server';
import {ArrowRight, Bot, FolderKanban, GitBranch, Radar, ShieldAlert, Workflow} from 'lucide-react';

import {SectionIntro} from '@/components/sections/section-intro';
import {MetricCard} from '@/components/dashboard/metric-card';
import {MagicCard} from '@/components/ui/magic-card';
import {getProjectVisualMap} from '@/lib/project-visual-map';

const flowIcons = [Workflow, FolderKanban, Radar, Bot, GitBranch, ArrowRight] as const;

export default async function ProjectMapPage() {
  const locale = await getLocale();
  const t = await getTranslations('projectMap');
  const payload = await getProjectVisualMap();

  // RU: Визуальная карта берёт уже сгенерированные locale-срезы, чтобы shell не пересобирал project state на каждый запрос.
  const contour = locale === 'en' ? payload?.validated_contour_en ?? [] : payload?.validated_contour_ru ?? [];
  const owned = locale === 'en' ? payload?.owned_capabilities_en ?? [] : payload?.owned_capabilities_ru ?? [];
  const overlap = locale === 'en' ? payload?.danger_overlap_en ?? [] : payload?.danger_overlap_ru ?? [];
  const scope = locale === 'en' ? payload?.out_of_scope_en ?? [] : payload?.out_of_scope_ru ?? [];

  return (
    <main className="container space-y-6 pt-8 md:space-y-8 md:pt-10">
      <section className="glass-panel reveal-section rounded-[2.2rem] border-white/12 px-6 py-6 md:px-8 md:py-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
          <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} />
          <MagicCard className="rounded-[1.8rem] border-white/12" mode="gradient" gradientFrom="#f97316" gradientTo="#22c55e">
            <div className="space-y-5 p-5">
              <div>
                <p className="text-sm text-muted-foreground">{t('statusLabel')}</p>
                <h3 className="mt-2 text-2xl leading-tight">{payload?.active_context.current_focus || t('fallbackFocus')}</h3>
              </div>
              <div className="rounded-[1.2rem] border border-white/8 bg-black/12 p-4 text-sm leading-6 text-muted-foreground">
                {payload?.active_context.biggest_operational_risk || t('fallbackRisk')}
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-glow">
                  {t('openRuntime')}
                </Link>
                <Link href="/ops-workbench" className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/8 px-4 py-2 text-sm font-semibold text-foreground">
                  {t('openOps')}
                </Link>
              </div>
            </div>
          </MagicCard>
        </div>
      </section>

      <section className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
        <div className="mb-4 space-y-2">
          <p className="text-sm text-muted-foreground">{t('flowLabel')}</p>
          <h2 className="text-2xl leading-tight">{t('flowTitle')}</h2>
        </div>
        <div className="grid gap-4 xl:grid-cols-6">
          {contour.map((item, index) => {
            const Icon = flowIcons[index] || Workflow;
            return (
              <div key={item} className="rounded-[1.4rem] border border-white/8 bg-black/10 p-4">
                <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/12 bg-white/6 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-sm font-semibold leading-6">{item}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('ownedLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('ownedTitle')}</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {owned.map((item) => (
              <div key={item} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4 text-sm leading-6 text-foreground/88">
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
            <div className="mb-4 flex items-start gap-3">
              <div className="rounded-full border border-white/12 bg-white/8 p-2 text-amber-400">
                <ShieldAlert className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('overlapLabel')}</p>
                <h2 className="text-2xl leading-tight">{t('overlapTitle')}</h2>
              </div>
            </div>
            <div className="space-y-3">
              {overlap.map((item) => (
                <div key={item} className="rounded-[1.2rem] border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-6 text-foreground/88">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
            <div className="mb-4 space-y-2">
              <p className="text-sm text-muted-foreground">{t('scopeLabel')}</p>
              <h2 className="text-2xl leading-tight">{t('scopeTitle')}</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {scope.map((item) => (
                <span key={item} className="inline-flex items-center rounded-full border border-white/10 bg-white/6 px-3 py-2 text-xs font-medium tracking-wide text-muted-foreground">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('automationLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('automationTitle')}</h2>
          </div>
          <div className="grid gap-3">
            {(payload?.automations || []).map((item) => (
              <div key={item} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-2xl border border-white/12 bg-white/6 text-primary">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="text-sm font-semibold leading-6">{item}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('recentLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('recentTitle')}</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title={t('metrics.skills')} value={String(payload?.skills.length || 0)} detail={t('metrics.skillsDetail')} />
            <MetricCard title={t('metrics.automations')} value={String(payload?.automations.length || 0)} detail={t('metrics.automationsDetail')} tone="accent" />
            <MetricCard title={t('metrics.worklog')} value={String(payload?.recent_worklog.length || 0)} detail={t('metrics.worklogDetail')} />
          </div>
          <div className="mt-4 grid gap-3">
            {(payload?.recent_worklog || []).map((entry) => (
              <div key={entry.heading} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{entry.heading}</div>
                <div className="mt-2 text-sm font-semibold leading-6">{entry.summary}</div>
                {entry.risk ? <div className="mt-2 text-sm leading-6 text-muted-foreground">{entry.risk}</div> : null}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
