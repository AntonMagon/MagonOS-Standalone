import Link from 'next/link';
import {getTranslations} from 'next-intl/server';
import {ArrowRight, CheckCircle2, GitBranch} from 'lucide-react';

import {InteractiveGlassCard} from '@/components/lightswind/interactive-glass-card';
import {MagneticButton} from '@/components/lightswind/magnetic-button';
import {SectionIntro} from '@/components/sections/section-intro';

const ruleKeys = ['one', 'two', 'three', 'four'] as const;

export default async function PersonalizePage() {
  const t = await getTranslations('appearance.page');

  return (
    <main className="container space-y-6 pt-8 md:space-y-8 md:pt-10">
      <section className="glass-panel reveal-section rounded-[2.2rem] border-white/12 px-6 py-6 md:px-8 md:py-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)] lg:items-start">
          <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} />
          <InteractiveGlassCard className="min-h-[320px]">
            <div className="flex h-full flex-col justify-between gap-8">
              <div className="space-y-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/12 bg-white/8 text-primary">
                  <GitBranch className="h-5 w-5" />
                </div>
                <h2 className="text-2xl leading-tight">{t('contractTitle')}</h2>
                <p className="text-sm leading-6 text-muted-foreground">{t('contractText')}</p>
              </div>
              <Link href="/dashboard">
                <MagneticButton className="group">
                  {t('openDialog')}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </MagneticButton>
              </Link>
            </div>
          </InteractiveGlassCard>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {ruleKeys.map((rule) => (
          <div key={rule} className="glass-panel reveal-section rounded-[1.8rem] border-white/10 p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-full border border-white/12 bg-white/8 p-2 text-primary">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <p className="text-sm leading-6 text-muted-foreground">{t(`rules.${rule}`)}</p>
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
