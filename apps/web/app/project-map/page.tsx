import Link from 'next/link';
import {getLocale, getTranslations} from 'next-intl/server';
import {ArrowRight, Bot, FolderKanban, GitBranch, Radar, ShieldAlert, Workflow} from 'lucide-react';

import {SectionIntro} from '@/components/sections/section-intro';
import {MetricCard} from '@/components/dashboard/metric-card';
import {MagicCard} from '@/components/ui/magic-card';
import {getProjectVisualMap} from '@/lib/project-visual-map';

const flowIcons = [Workflow, FolderKanban, Radar, Bot, GitBranch, ArrowRight] as const;

function localizedProjectString(locale: string, value: string | undefined, fallback: string) {
  if (!value) {
    return fallback;
  }
  if (locale !== 'ru') {
    return value;
  }

  const normalized = value.trim();
  // RU: Project memory пока хранит verified summaries и risks на английском, поэтому для русской карты делаем явную локальную адаптацию самых частых operational phrases.
  if (normalized === 'Keep Russian shell text and docs from drifting while architecture work continues') {
    return 'Держать русский интерфейс, документацию и визуальную карту синхронными, пока продолжается архитектурная доработка.';
  }
  if (normalized === 'Keep runtime automation green while architecture work continues') {
    return 'Сохранять автоматические проверки и рабочий runtime в зелёной зоне, пока продолжается архитектурная работа.';
  }
  if (normalized.includes('Cold-start dev-shell latency can still be worse than steady-state performance')) {
    return 'После холодного старта dev-shell всё ещё может отвечать медленнее обычного. Это уже не ломает проверки, но пока не является доказательством production-производительности.';
  }
  if (normalized.includes('The guard now blocks known English domain leakage in Russian source/runtime layers')) {
    return 'Guard уже режет известные английские утечки в русском source-of-truth и на живом shell. Но более глубокое качество формулировок всё ещё требует отдельного продуктового review.';
  }
  return value;
}

function localizedAutomationName(locale: string, value: string) {
  if (locale !== 'ru') {
    return value;
  }

  const mapping: Record<string, string> = {
    'Hourly Repo Guard': 'Проверка репозитория каждые 3 часа',
    'Hourly Platform Smoke': 'Smoke-проверка платформы каждые 2 часа',
    'RU Locale Guard': 'Проверка русского слоя каждые 6 часов',
    'Hourly Visual Map': 'Пересборка визуальной карты каждые 6 часов',
    'Weekly Release Gate': 'Недельный релизный контроль',
    'Launchd Periodic Checks': 'Локальный launchd-контур периодических проверок',
  };

  return mapping[value] || value;
}

function localizedWorklogSummary(locale: string, value: string | undefined) {
  if (!value) {
    return '';
  }
  if (locale !== 'ru') {
    return value;
  }
  if (/[А-Яа-яЁё]/.test(value)) {
    return value;
  }

  if (value.includes('Added automatic Russian locale guard')) {
    return 'Добавлен автоматический guard для русского слоя в source-of-truth и на живых маршрутах shell.';
  }
  if (value.includes('Stabilized full-project audit runtime')) {
    return 'Стабилизированы общий аудит рантайма, perf smoke и периодические проверки.';
  }
  if (value.includes('Fixed smoke-runtime CI')) {
    return 'Починен smoke-runtime CI для запуска без локальной `.venv` в среде runner.';
  }
  return 'Техническое изменение зафиксировано в журнале проекта.';
}

function localizedWorklogRisk(locale: string, value: string | undefined) {
  if (!value) {
    return value;
  }
  if (locale !== 'ru') {
    return value;
  }
  if (value === 'See worklog entry') {
    return 'Подробности зафиксированы в project memory.';
  }
  return localizedProjectString(locale, value, value);
}

export default async function ProjectMapPage() {
  const locale = await getLocale();
  const t = await getTranslations('projectMap');
  const payload = await getProjectVisualMap();

  // RU: Визуальная карта берёт уже сгенерированные locale-срезы, чтобы shell не пересобирал project state на каждый запрос.
  const contour = locale === 'en' ? payload?.validated_contour_en ?? [] : payload?.validated_contour_ru ?? [];
  const owned = locale === 'en' ? payload?.owned_capabilities_en ?? [] : payload?.owned_capabilities_ru ?? [];
  const overlap = locale === 'en' ? payload?.danger_overlap_en ?? [] : payload?.danger_overlap_ru ?? [];
  const scope = locale === 'en' ? payload?.out_of_scope_en ?? [] : payload?.out_of_scope_ru ?? [];
  const focus = localizedProjectString(locale, payload?.active_context.current_focus, t('fallbackFocus'));
  const risk = localizedProjectString(locale, payload?.active_context.biggest_operational_risk, t('fallbackRisk'));
  const automations = (payload?.automations || []).map((item) => localizedAutomationName(locale, item));

  return (
    <main className="container space-y-6 pt-8 md:space-y-8 md:pt-10">
      <section className="glass-panel reveal-section rounded-[2.2rem] border-white/12 px-6 py-6 md:px-8 md:py-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
          <SectionIntro eyebrow={t('eyebrow')} title={t('title')} text={t('text')} />
          <MagicCard className="rounded-[1.8rem] border-white/12" mode="gradient" gradientFrom="#f97316" gradientTo="#22c55e">
            <div className="space-y-5 p-5">
              <div>
                <p className="text-sm text-muted-foreground">{t('statusLabel')}</p>
                <h3 className="mt-2 text-2xl leading-tight">{focus}</h3>
              </div>
              <div className="rounded-[1.2rem] border border-white/8 bg-black/12 p-4 text-sm leading-6 text-foreground/76">
                {risk}
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
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {contour.map((item, index) => {
            const Icon = flowIcons[index] || Workflow;
            return (
              <div key={item} className="rounded-[1.4rem] border border-white/10 bg-white/[0.085] p-4 shadow-[0_18px_40px_-24px_rgba(0,0,0,0.45)]">
                <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/14 bg-white/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t('flowStep', {index: index + 1})}</div>
                <div className="mt-2 text-base font-semibold leading-7 text-foreground">{item}</div>
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
            {automations.map((item) => (
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
                <div className="mt-2 text-sm font-semibold leading-6">{localizedWorklogSummary(locale, entry.summary)}</div>
                {entry.risk ? <div className="mt-2 text-sm leading-6 text-muted-foreground">{localizedWorklogRisk(locale, entry.risk)}</div> : null}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
