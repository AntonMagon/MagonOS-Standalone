// RU: Файл входит в проверенный контур первой волны.
import Link from 'next/link';
import {getTranslations} from 'next-intl/server';
import {ArrowRight, AudioWaveform, Boxes, Orbit, ShieldCheck, SlidersHorizontal, Workflow} from 'lucide-react';

import {MagneticButton} from '@/components/lightswind/magnetic-button';
import {InteractiveGlassCard} from '@/components/lightswind/interactive-glass-card';
import {SectionIntro} from '@/components/sections/section-intro';
import {AnimatedGridPattern} from '@/components/ui/animated-grid-pattern';
import {MagicCard} from '@/components/ui/magic-card';
import {ShinyButton} from '@/components/ui/shiny-button';
import {getOperatorUrl, getPlatformStatus} from '@/lib/standalone-api';
import {cn} from '@/lib/utils';

export default async function HomePage() {
  const t = await getTranslations('home');
  const platformStatus = await getPlatformStatus();

  const layers = [
    {
      key: 'standalone',
      icon: Orbit
    },
    {
      key: 'bridge',
      icon: SlidersHorizontal
    },
    {
      key: 'next',
      icon: AudioWaveform
    }
  ] as const;

  const highlights = ['one', 'two', 'three', 'four'] as const;

  return (
    <main>
      <section className="container pt-8 md:pt-10">
        <div className="hero-shell reveal-section relative overflow-hidden rounded-[2.4rem] border border-white/12 px-6 py-7 shadow-panel md:px-8 md:py-8 lg:px-10">
          <AnimatedGridPattern
            width={54}
            height={54}
            numSquares={22}
            className="absolute inset-0 text-white/20 [mask-image:radial-gradient(circle_at_center,white,transparent_78%)]"
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.18),transparent_28%),radial-gradient(circle_at_70%_30%,rgba(238,79,39,0.22),transparent_30%),linear-gradient(140deg,rgba(255,255,255,0.08),transparent_44%,rgba(84,210,181,0.12))]" />
          <div className="relative z-10 grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/14 bg-white/8 px-4 py-2 text-sm text-muted-foreground backdrop-blur-xl">
                <ShieldCheck className="h-4 w-4 text-primary" />
                {t('badge')}
              </div>
              <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} className="max-w-4xl" />
              <div className="flex flex-wrap items-center gap-3">
                <Link href="/catalog">
                  <ShinyButton className="border-white/12 bg-white/8 text-foreground hover:bg-white/12">
                    {t('openCatalog')}
                  </ShinyButton>
                </Link>
                <Link href="/dashboard">
                  <MagneticButton className="group min-w-[11rem]">
                    {t('openDashboard')}
                    <ArrowRight className="ml-2 inline-block h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </MagneticButton>
                </Link>
                <Link href="/ops-workbench">
                  <ShinyButton className="border-white/12 bg-white/8 text-foreground hover:bg-white/12">
                    {t('openOps')}
                  </ShinyButton>
                </Link>
              </div>
              <div className="grid gap-2 pt-2 md:grid-cols-2">
                {highlights.map((item) => (
                  <div key={item} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-sm leading-6 text-foreground/82 backdrop-blur-xl">
                    {t(`highlights.${item}`)}
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4">
              <MagicCard className="rounded-[2rem] border-white/15" mode="orb" glowFrom="#ee4f27" glowTo="#54d2b5">
                <div className="relative flex h-full flex-col justify-between p-6">
                  <div>
                    <p className="text-sm text-muted-foreground">{t('focusLabel')}</p>
                    <h3 className="mt-2 max-w-[14rem] text-2xl leading-tight">{t('focusTitle')}</h3>
                  </div>
                  <div className="rounded-[1.4rem] border border-white/10 bg-black/12 p-4 text-sm leading-6 text-muted-foreground backdrop-blur-xl">
                    {t('focusText')}
                  </div>
                  <div className="rounded-[1.4rem] border border-white/10 bg-black/12 p-4 text-sm leading-6 text-muted-foreground backdrop-blur-xl">
                    <div className="mb-2 text-xs uppercase tracking-[0.22em] text-muted-foreground">{t('runtimeLabel')}</div>
                    {platformStatus ? (
                      <div className="space-y-2">
                        <div className="text-foreground">{t('runtimeOnline')}</div>
                        <div>{t('runtimeCompanies', {count: platformStatus.storage_counts.canonical_companies ?? 0})}</div>
                        <div>{t('runtimeFeedback', {count: platformStatus.storage_counts.feedback_events ?? 0})}</div>
                      </div>
                    ) : (
                      <div>{t('runtimeOffline')}</div>
                    )}
                  </div>
                </div>
              </MagicCard>

              <div className="glass-panel relative overflow-hidden rounded-[2rem] border-white/15 p-5 md:p-6">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(84,210,181,0.16),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(238,79,39,0.16),transparent_26%)]" />
                <div className="relative z-10 flex h-full flex-col justify-between gap-6">
                  <div className="space-y-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/12 bg-white/10 text-primary">
                      <Boxes className="h-5 w-5" />
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t('surfacesLabel')}</p>
                      <h3 className="text-2xl leading-tight">{t('surfacesTitle')}</h3>
                      <p className="text-sm leading-6 text-foreground/80">{t('surfacesText')}</p>
                    </div>
                  </div>
                  <div className="grid gap-3">
                    {(['dashboard', 'ops', 'map'] as const).map((item) => (
                      <div key={item} className="rounded-[1.3rem] border border-white/12 bg-white/10 p-4 backdrop-blur-xl">
                        <div className="text-sm font-semibold leading-6">{t(`surfaces.${item}.title`)}</div>
                        <div className="mt-1 text-sm leading-6 text-foreground/72">{t(`surfaces.${item}.body`)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-[1.5rem] border border-white/12 bg-black/10 p-4">
                    {/* RU: На главной справа нужен не "красивый пустой блок", а короткий ориентир, куда пользователь идёт дальше по рабочему контуру. */}
                    <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Workflow className="h-4 w-4 text-primary" />
                      {t('flowPreviewTitle')}
                    </div>
                    <div className="grid gap-2">
                      {(['one', 'two', 'three'] as const).map((item) => (
                        <div key={item} className="rounded-2xl border border-white/10 bg-white/6 px-3 py-3 text-sm leading-6 text-foreground/76">
                          {t(`flowPreview.${item}`)}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container grid gap-4 py-8 md:grid-cols-3 md:py-10">
        {layers.map((layer, index) => {
          const Icon = layer.icon;
          return (
            <InteractiveGlassCard key={layer.key} className={cn('reveal-section min-h-[220px]', index === 1 && 'md:-translate-y-4')}>
              <div className="flex h-full flex-col justify-between gap-8">
                <div className="space-y-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/12 bg-white/8 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl leading-tight">{t(`layers.${layer.key}.title`)}</h3>
                    <p className="text-sm leading-6 text-muted-foreground">{t(`layers.${layer.key}.body`)}</p>
                  </div>
                </div>
              </div>
            </InteractiveGlassCard>
          );
        })}
      </section>

      <section className="container pb-10">
        <div className="glass-panel reveal-section rounded-[2rem] border-white/12 p-6 md:p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{t('operatorEyebrow')}</p>
              <h2 className="text-3xl leading-tight">{t('operatorTitle')}</h2>
              <p className="max-w-3xl text-sm leading-7 text-muted-foreground">{t('operatorText')}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href={getOperatorUrl()}>
                <MagneticButton>{t('openOperatorConsole')}</MagneticButton>
              </Link>
              <Link href={getOperatorUrl('companies')}>
                <ShinyButton className="border-white/12 bg-white/8 text-foreground hover:bg-white/12">
                  {t('openCompanyWorkbench')}
                </ShinyButton>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
