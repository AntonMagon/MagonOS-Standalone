import Link from 'next/link';
import {getLocale} from 'next-intl/server';
import {
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Factory,
  FileCheck2,
  Package,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import type {PlatformStatus} from '@/lib/standalone-api';

type Copy = {
  eyebrow: string;
  title: string;
  text: string;
  primaryCta: string;
  secondaryCta: string;
  helper: string;
  statusOnline: string;
  statusOffline: string;
  metrics: {label: string; value: string}[];
  stepsTitle: string;
  stepsText: string;
  steps: {title: string; body: string}[];
  directionsTitle: string;
  directionsText: string;
  directions: {title: string; body: string; note: string}[];
  operatorTitle: string;
  operatorText: string;
  operatorPoints: string[];
  finalTitle: string;
  finalText: string;
  finalPrimary: string;
  finalSecondary: string;
};

const copyByLocale: Record<'ru' | 'en', Copy> = {
  ru: {
    eyebrow: 'Печать и упаковка без хаоса',
    title: 'Одна заявка. Понятный бриф. Быстрое предложение. Контроль файлов, сроков и исполнителя.',
    text:
      'MagonOS не пытается быть маркетплейсом на всё. Это рабочий сервис для типовых и сложных задач по печати и упаковке: собрать ввод, проверить материалы, выбрать путь расчёта и довести кейс до заказа без потери контекста.',
    primaryCta: 'Открыть каталог',
    secondaryCta: 'Оставить сложный запрос',
    helper: 'Если задача типовая, начни с каталога. Если проект нестандартный, сразу отправляй сложный запрос в ручной разбор.',
    statusOnline: 'Система отвечает',
    statusOffline: 'Веб уже собран, но backend сейчас недоступен',
    metrics: [
      {label: 'Типовой вход', value: 'каталог и короткая заявка'},
      {label: 'Сложный вход', value: 'ручной разбор без ложного калькулятора'},
      {label: 'Исполнение', value: 'предложение, файлы и заказ в одном следе'},
    ],
    stepsTitle: 'Как это работает',
    stepsText: 'Вместо хаотичной переписки у тебя один понятный маршрут от первого описания до подтверждённого заказа.',
    steps: [
      {
        title: '1. Выбираем понятный путь входа',
        body: 'Типовой кейс идёт через карточку каталога. Нестандартный проект сразу попадает в отдельный сложный запрос.',
      },
      {
        title: '2. Собираем нормальный бриф',
        body: 'Размер, материал, тираж, сроки, макеты и ограничения фиксируются в одном месте, а не теряются по сообщениям.',
      },
      {
        title: '3. Готовим предложение и ведём заказ',
        body: 'Оператор проверяет ввод, собирает вариант исполнения, согласует документы и переводит кейс в заказ.',
      },
    ],
    directionsTitle: 'Что можно сделать прямо сейчас',
    directionsText: 'Каталог остаётся компактным: только те направления, которые реально можно быстро проверить и довести до предложения.',
    directions: [
      {
        title: 'Упаковка из картона и гофры',
        body: 'Короба, обечайки, транспортная и презентационная упаковка.',
        note: 'Хорошо подходит для каталога и короткой заявки.',
      },
      {
        title: 'Этикетки и наклейки',
        body: 'Самоклейка, маркировка, промо-стикеры и сервисные наклейки.',
        note: 'Быстрый старт, если параметры уже понятны.',
      },
      {
        title: 'Нестандартный производственный кейс',
        body: 'Когда нужны необычные материалы, сложная конструкция, несколько сценариев или ручная проверка поставщика.',
        note: 'Лучше сразу отправлять в сложный запрос.',
      },
    ],
    operatorTitle: 'Что происходит после отправки',
    operatorText:
      'Система не обещает чудо-автоматизацию. Она собирает понятный рабочий след, чтобы оператор и клиент одинаково видели текущее состояние кейса.',
    operatorPoints: [
      'Заявка получает статус, ответственного и следующий шаг.',
      'Файлы и документы живут рядом с заявкой и заказом, а не отдельно.',
      'Поставщики проходят проверку, а не попадают в предложение вслепую.',
      'Заказ собирает оплату, готовность и движение без потери истории.',
    ],
    finalTitle: 'Нужен типовой заказ или сложный расчёт?',
    finalText: 'Обе точки входа уже есть. Выбирай каталог для быстрого старта или сложный запрос, если сначала нужен ручной разбор.',
    finalPrimary: 'Перейти в каталог',
    finalSecondary: 'Открыть сложный запрос',
  },
  en: {
    eyebrow: 'Print and packaging without chaos',
    title: 'One request. Clear brief. Fast offer. Controlled files, timing, and fulfillment.',
    text:
      'MagonOS is not trying to be a marketplace for everything. It is a working service for print and packaging intake: collect the brief, check materials, choose the right pricing path, and move the case into an order without losing context.',
    primaryCta: 'Open catalog',
    secondaryCta: 'Send a complex request',
    helper: 'Use the catalog for a straightforward job. If the project is unusual, send it directly into manual RFQ review.',
    statusOnline: 'System is online',
    statusOffline: 'The web shell is available, but the backend is currently offline',
    metrics: [
      {label: 'Simple intake', value: 'catalog and short request'},
      {label: 'Complex intake', value: 'manual review instead of a fake calculator'},
      {label: 'Execution', value: 'offer, files, and order in one trail'},
    ],
    stepsTitle: 'How it works',
    stepsText: 'Instead of chaotic chat threads, you get one clear route from the first description to a confirmed order.',
    steps: [
      {
        title: '1. Choose the right entry path',
        body: 'A straightforward case starts from a catalog card. A non-standard case goes straight into a dedicated RFQ route.',
      },
      {
        title: '2. Build a usable brief',
        body: 'Size, material, quantity, timing, artwork, and constraints are collected in one place instead of getting lost in messages.',
      },
      {
        title: '3. Prepare the offer and move into order',
        body: 'The operator reviews the input, builds a fulfillment variant, aligns documents, and turns the case into an order.',
      },
    ],
    directionsTitle: 'What you can start right now',
    directionsText: 'The storefront stays tight: only the directions that can actually be reviewed and moved into a real offer quickly.',
    directions: [
      {
        title: 'Carton and corrugated packaging',
        body: 'Boxes, sleeves, shipping packs, and presentation packaging.',
        note: 'Best fit for the catalog and short request path.',
      },
      {
        title: 'Labels and stickers',
        body: 'Self-adhesive labels, logistics marking, promo stickers, and service labels.',
        note: 'Fast start when the parameters are already clear.',
      },
      {
        title: 'Custom production case',
        body: 'When the job needs unusual materials, a complex structure, multiple scenarios, or manual supplier review.',
        note: 'Better handled through the dedicated RFQ path.',
      },
    ],
    operatorTitle: 'What happens after submit',
    operatorText:
      'The system does not pretend to be magic automation. It creates a readable working trail so the operator and the client can both understand the current state of the case.',
    operatorPoints: [
      'The request gets a status, an owner, and a next step.',
      'Files and documents stay attached to the request and order.',
      'Suppliers are reviewed before they appear in the offer.',
      'The order keeps payment, readiness, and movement in one record.',
    ],
    finalTitle: 'Need a straightforward order or a complex estimate?',
    finalText: 'Both entry points are already live. Use the catalog for a fast start or the complex request flow when manual review comes first.',
    finalPrimary: 'Go to catalog',
    finalSecondary: 'Open complex request',
  },
};

export async function RetroPrintLanding({platformStatus}: {platformStatus: PlatformStatus | null}) {
  const currentLocale = (await getLocale()) === 'ru' ? 'ru' : 'en';
  // RU: Главная использует отдельный product-first copyset, чтобы не тащить в public shell внутренний operator жаргон.
  const copy = copyByLocale[currentLocale];
  const counts = platformStatus?.storage_counts ?? {};
  const runtimeCount = String(counts.canonical_companies ?? 0);

  return (
    <main className="space-y-8 pb-16 pt-8 md:space-y-10 md:pt-10">
      <section className="container">
        <div className="hero-shell relative overflow-hidden rounded-[2.6rem] border border-border/80 px-6 py-8 md:px-10 md:py-10">
          <div className="absolute inset-y-0 right-0 hidden w-[42%] bg-[radial-gradient(circle_at_top,rgba(34,91,255,0.12),transparent_52%),linear-gradient(180deg,rgba(255,255,255,0.38),rgba(255,255,255,0))] lg:block" />
          <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(19rem,0.9fr)] lg:items-end">
            <div className="space-y-6">
              <div className="micro-label">{copy.eyebrow}</div>
              <div className="space-y-4">
                <h1 className="max-w-4xl text-4xl leading-[1.05] md:text-5xl">{copy.title}</h1>
                <p className="max-w-3xl text-base leading-8 text-foreground/76">{copy.text}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/catalog" className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-glow transition hover:translate-y-[-1px]">
                  {copy.primaryCta}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/rfq" className="inline-flex items-center gap-2 rounded-full border border-border bg-white/55 px-5 py-3 text-sm font-semibold text-foreground transition hover:bg-white/72">
                  {copy.secondaryCta}
                </Link>
              </div>
              <p className="max-w-3xl text-sm leading-7 text-muted-foreground">{copy.helper}</p>
            </div>

            <div className="paper-panel grid gap-4 p-5">
              <div className="flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
                    {platformStatus ? copy.statusOnline : copy.statusOffline}
                  </div>
                  <div className="text-2xl font-semibold text-foreground">
                    {platformStatus?.db_label ?? (currentLocale === 'ru' ? 'Backend недоступен' : 'Backend unavailable')}
                  </div>
                </div>
                <span className={`status-pill ${platformStatus ? 'status-pill-success' : 'status-pill-warn'}`}>
                  {platformStatus ? (currentLocale === 'ru' ? 'online' : 'online') : (currentLocale === 'ru' ? 'внимание' : 'attention')}
                </span>
              </div>

              <div className="grid gap-3">
                {copy.metrics.map((item, index) => (
                  <div key={item.label} className="rounded-[1.4rem] border border-border/75 bg-white/50 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</div>
                    <div className="mt-2 text-base font-medium text-foreground">{item.value}</div>
                    {index === 0 ? <div className="mt-2 text-sm text-muted-foreground">{runtimeCount} {currentLocale === 'ru' ? 'компаний уже в системе' : 'companies already in the system'}</div> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container grid gap-4 lg:grid-cols-3">
        <div className="paper-panel p-5">
          <div className="flex items-center gap-3">
            <Package className="h-5 w-5 text-primary" />
            <h2 className="text-xl">{copy.stepsTitle}</h2>
          </div>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">{copy.stepsText}</p>
        </div>
        {copy.steps.map((step, index) => {
          const icons = [ClipboardList, FileCheck2, ShieldCheck];
          const Icon = icons[index] ?? ClipboardList;
          return (
            <article key={step.title} className="paper-panel p-5">
              <div className="flex items-center gap-3">
                <span className="status-pill status-pill-primary">{index + 1}</span>
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 text-xl leading-tight">{step.title}</h3>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">{step.body}</p>
            </article>
          );
        })}
      </section>

      <section className="container grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="sheet-panel p-6">
          <div className="space-y-3">
            <div className="micro-label">{copy.directionsTitle}</div>
            <h2 className="text-3xl leading-tight">{copy.directionsText}</h2>
          </div>
          <div className="mt-5 grid gap-4">
            {copy.directions.map((direction) => (
              <article key={direction.title} className="rounded-[1.6rem] border border-border/75 bg-white/54 p-5">
                <h3 className="text-xl leading-tight">{direction.title}</h3>
                <p className="mt-3 text-sm leading-7 text-foreground/76">{direction.body}</p>
                <div className="mt-4 text-sm font-medium text-primary">{direction.note}</div>
              </article>
            ))}
          </div>
        </div>

        <div className="grid gap-4">
          <article className="paper-panel p-5">
            <div className="flex items-center gap-3">
              <Factory className="h-5 w-5 text-primary" />
              <h2 className="text-2xl leading-tight">{copy.operatorTitle}</h2>
            </div>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{copy.operatorText}</p>
            <div className="mt-5 grid gap-3">
              {copy.operatorPoints.map((point) => (
                <div key={point} className="flex gap-3 rounded-[1.3rem] border border-border/75 bg-white/50 px-4 py-3 text-sm leading-6 text-foreground/82">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span>{point}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="paper-panel p-5">
            <div className="flex items-center gap-3">
              <Sparkles className="h-5 w-5 text-primary" />
              <h2 className="text-2xl leading-tight">{copy.finalTitle}</h2>
            </div>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{copy.finalText}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href="/catalog" className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
                {copy.finalPrimary}
              </Link>
              <Link href="/rfq" className="inline-flex items-center gap-2 rounded-full border border-border bg-white/55 px-4 py-2.5 text-sm font-semibold text-foreground">
                {copy.finalSecondary}
              </Link>
            </div>
          </article>
        </div>
      </section>
    </main>
  );
}
