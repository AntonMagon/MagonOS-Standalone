import Link from 'next/link';
import {getLocale, getTranslations} from 'next-intl/server';
import {ArrowRight, BookOpenText, Boxes, Database, Network, Route, ShieldCheck} from 'lucide-react';

import {SectionIntro} from '@/components/sections/section-intro';
import {MagicCard} from '@/components/ui/magic-card';
import {getPlatformReference} from '@/lib/platform-reference';

const sectionIcons = [Boxes, Route, Network, ShieldCheck] as const;

export default async function ReferencePage() {
  const locale = await getLocale();
  const t = await getTranslations('referencePage');
  const reference = getPlatformReference(locale);

  return (
    <main className="container space-y-6 pt-8 md:space-y-8 md:pt-10">
      <section className="glass-panel reveal-section rounded-[2.2rem] border-white/12 px-6 py-6 md:px-8 md:py-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
          <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} />
          <MagicCard className="rounded-[1.8rem] border-white/12" mode="gradient" gradientFrom="#f97316" gradientTo="#22c55e">
            <div className="space-y-5 p-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/14 bg-white/10 text-primary">
                <BookOpenText className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('quickLabel')}</p>
                <h3 className="mt-2 text-2xl leading-tight">{t('quickTitle')}</h3>
              </div>
              <div className="rounded-[1.2rem] border border-white/8 bg-black/12 p-4 text-sm leading-6 text-foreground/76">
                {t('quickText')}
              </div>
              <div className="grid gap-3">
                <Link href="/request-workbench" className="inline-flex items-center justify-between rounded-[1.1rem] border border-white/10 bg-white/[0.06] px-4 py-3 text-sm font-semibold text-foreground">
                  <span>{t('links.requestWorkbench')}</span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </Link>
                <Link href="/suppliers" className="inline-flex items-center justify-between rounded-[1.1rem] border border-white/10 bg-white/[0.06] px-4 py-3 text-sm font-semibold text-foreground">
                  <span>{t('links.suppliers')}</span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </Link>
                <Link href="/project-map" className="inline-flex items-center justify-between rounded-[1.1rem] border border-white/10 bg-white/[0.06] px-4 py-3 text-sm font-semibold text-foreground">
                  <span>{t('links.projectMap')}</span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
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
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{t('flowText')}</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {t.raw('flowSteps').map((step: string, index: number) => (
            <div key={step} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t('stepLabel', {index: index + 1})}</div>
              <div className="mt-2 text-base font-semibold leading-7 text-foreground">{step}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{t('entitiesLabel')}</p>
          <h2 className="text-2xl leading-tight">{t('entitiesTitle')}</h2>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {reference.entityGroups.map((group, index) => {
            const Icon = sectionIcons[index] || Database;
            return (
              <div key={group.id} className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
                <div className="mb-4 flex items-start gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/14 bg-white/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold leading-tight">{group.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{group.text}</p>
                  </div>
                </div>
                <div className="grid gap-3">
                  {group.items.map((item) => (
                    <div key={item.name} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
                      <div className="text-base font-semibold leading-7">{item.name}</div>
                      <p className="mt-2 text-sm leading-6 text-foreground/84">{item.summary}</p>
                      {/* RU: Блок "Как пользоваться" нужен прямо рядом с сущностью, чтобы справка не превращалась в абстрактный glossary без рабочего смысла. */}
                      <p className="mt-3 text-sm leading-6 text-muted-foreground">
                        <span className="font-semibold text-foreground/88">{t('usageLabel')}</span> {item.usage}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
          <div className="mb-4 space-y-2">
            <p className="text-sm text-muted-foreground">{t('depsLabel')}</p>
            <h2 className="text-2xl leading-tight">{t('depsTitle')}</h2>
          </div>
          <div className="grid gap-3">
            {reference.dependencyGroups.map((group) => (
              <div key={group.id} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
                <div className="text-base font-semibold leading-7">{group.title}</div>
                <p className="mt-2 text-sm leading-6 text-foreground/84">{group.text}</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                  {group.bullets.map((bullet) => (
                    <li key={bullet} className="rounded-[1rem] border border-white/6 bg-white/[0.04] px-3 py-2">
                      {bullet}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
            <div className="mb-4 space-y-2">
              <p className="text-sm text-muted-foreground">{t('rolesLabel')}</p>
              <h2 className="text-2xl leading-tight">{t('rolesTitle')}</h2>
            </div>
            <div className="grid gap-3">
              {reference.roleGuides.map((guide) => (
                <div key={guide.id} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
                  <div className="text-base font-semibold leading-7">{guide.role}</div>
                  <p className="mt-2 text-sm leading-6 text-foreground/84">{guide.text}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {guide.routes.map((route) => (
                      <code key={route} className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-muted-foreground">
                        {route}
                      </code>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel reveal-section rounded-[2rem] border-white/10 p-5">
            <div className="mb-4 space-y-2">
              <p className="text-sm text-muted-foreground">{t('limitsLabel')}</p>
              <h2 className="text-2xl leading-tight">{t('limitsTitle')}</h2>
            </div>
            <div className="grid gap-3">
              {reference.waveExclusions.map((item) => (
                <div key={item} className="rounded-[1.2rem] border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-6 text-foreground/88">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
