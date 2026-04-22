import Link from 'next/link';
import {getLocale} from 'next-intl/server';
import {
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  Factory,
  FileStack,
  Files,
  GitBranch,
  ScanSearch,
  ShieldCheck,
  Waypoints,
  Workflow
} from 'lucide-react';

import type {PlatformStatus} from '@/lib/standalone-api';
import {cn} from '@/lib/utils';

type Copy = {
  stamp: string;
  heroEyebrow: string;
  title: string;
  text: string;
  statusOnline: string;
  statusOffline: string;
  metrics: {label: string; value: string}[];
  ctas: {primary: string; secondary: string; tertiary: string};
  heroPanel: {
    eyebrow: string;
    title: string;
    text: string;
    notes: string[];
  };
  process: {
    eyebrow: string;
    title: string;
    text: string;
    steps: {code: string; name: string; title: string; body: string; tone: 'neutral' | 'primary' | 'signal' | 'danger'}[];
  };
  network: {
    eyebrow: string;
    title: string;
    text: string;
    hub: {eyebrow: string; title: string; body: string; bullets: string[]};
    suppliers: {name: string; trust: string; body: string; route: string; tone: 'neutral' | 'primary' | 'signal' | 'danger'}[];
  };
  principles: {
    eyebrow: string;
    title: string;
    text: string;
    items: {eyebrow: string; title: string; body: string}[];
    strip: {title: string; body: string};
  };
  demo: {
    eyebrow: string;
    title: string;
    text: string;
    stamp: string;
    requestCode: string;
    version: string;
    status: string;
    summaryTitle: string;
    summaryItems: string[];
    routeTitle: string;
    routeItems: string[];
    suppliersTitle: string;
    suppliersItems: string[];
    explainTitle: string;
    explainItems: string[];
    actions: {primary: string; secondary: string};
  };
};

const copyByLocale: Record<'ru' | 'en', Copy> = {
  ru: {
    stamp: 'Публичный слой / редакция 01',
    heroEyebrow: 'Операционная платформа поиска, приёма и исполнения',
    title: 'MagonOS собирает путь от черновика к заказу в один управляемый контур.',
    text:
      'Платформа ведёт поиск поставщиков, приём заявки, маршрутизацию, предложения и исполнение как связанную цепочку. В центре не магия, а версии, сигналы, маршруты, ответственность и понятное объяснение каждого решения.',
    statusOnline: 'Контур доступен',
    statusOffline: 'Backend не ответил, но веб-слой и структура маршрута остаются доступны.',
    metrics: [
      {label: 'Канонический реестр', value: 'узлы и поставщики'},
      {label: 'Решения по маршруту', value: 'версии и статусы'},
      {label: 'Сигналы доверия', value: 'проверка и объяснимость'}
    ],
    ctas: {
      primary: 'Открыть рабочий контур',
      secondary: 'Смотреть поставщиков',
      tertiary: 'Открыть карту проекта'
    },
    heroPanel: {
      eyebrow: 'Живой маршрут процесса',
      title: 'Черновик -> заявка -> предложение -> заказ',
      text: 'Каждый этап несёт свой статус, документ и переход. Система показывает, что уже подтверждено, где нужен оператор и на каком основании маршрут двигается дальше.',
      notes: [
        'Решение не прячется за AI-магией: видно, какой сигнал его сдвинул.',
        'Версии и документы остаются рядом с маршрутом, а не теряются по слоям.',
        'Публичная витрина и операторский контур читаются как одна взрослая система.'
      ]
    },
    process: {
      eyebrow: 'Как работает система',
      title: 'Маршрут построен как техпроцесс, а не как набор разрозненных виджетов.',
      text: 'Каждый шаг меняет уровень ответственности: от свободного контура ввода к формальному запросу, затем к версии предложения и подтверждённому заказу.',
      steps: [
        {
          code: '01',
          name: 'Черновик',
          title: 'Собирает ввод, файлы и первые сигналы без ложной формальности.',
          body: 'Пользователь фиксирует задачу, прикладывает материал и оставляет контекст. Система ещё не обещает исполнение, но уже держит структуру данных.',
          tone: 'neutral'
        },
        {
          code: '02',
          name: 'Заявка',
          title: 'Переводит ввод в проверяемый приём со статусом и владельцем.',
          body: 'Появляются обязательные поля, рабочий ответственный, очередность и причины для маршрутизации. Это уже объект операционного контура.',
          tone: 'primary'
        },
        {
          code: '03',
          name: 'Предложение',
          title: 'Собирает версию решения, поставщиков и обоснование выбора.',
          body: 'Оператор видит не только цену, но и источник, доверие, ограничения производства и историю ревизий. Именно здесь включается explainability.',
          tone: 'signal'
        },
        {
          code: '04',
          name: 'Заказ',
          title: 'Фиксирует подтверждённый маршрут и передаёт работу в исполнение.',
          body: 'Заказ наследует документы, файлы, версию предложения и рабочий след. Исполнение стартует из подтверждённого контура, а не из устной договорённости.',
          tone: 'danger'
        }
      ]
    },
    network: {
      eyebrow: 'Сеть поставщиков',
      title: 'Платформа не витринно показывает поставщиков, а нормализует и связывает их с маршрутом решения.',
      text: 'Сначала собираются сигналы и подтверждения, затем узлы приводятся к общей модели, и только после этого маршрут решает, кто релевантен для конкретной заявки.',
      hub: {
        eyebrow: 'Маршрутизация / уровень доверия',
        title: 'Единый операционный слой связывает сигналы поставщика с решением по заявке.',
        body: 'В центре не каталог, а логика: происхождение сигнала, нормализация, уровень доверия, допуски по производству и роль в конкретном запросе.',
        bullets: [
          'Нормализация от сырого сигнала к подтверждённому узлу',
          'Уровень доверия и причина допуска',
          'Привязка к версии предложения'
        ]
      },
      suppliers: [
        {
          name: 'Северная упаковка',
          trust: 'Проверен',
          body: 'Гофрокартон, стабильный срок запуска, подтверждённые форматы.',
          route: 'Идёт в короткий список по коробам и транспортной таре.',
          tone: 'primary'
        },
        {
          name: 'Print Lab 24',
          trust: 'На верификации',
          body: 'Печать малых тиражей, быстрое изготовление контрольных образцов.',
          route: 'Включается, если заявке нужен короткий цикл утверждения.',
          tone: 'signal'
        },
        {
          name: 'Flex Unit',
          trust: 'Ограничен',
          body: 'Работает только в своём диапазоне материалов и ширин.',
          route: 'Подходит для части SKU, но режется правилами на сложных запросах.',
          tone: 'neutral'
        },
        {
          name: 'East Carton',
          trust: 'Нужен ручной контроль',
          body: 'Хорошая цена, но нестабильные сроки и неполный документный след.',
          route: 'Система не запрещает узел, а требует ручного подтверждения перед оффером.',
          tone: 'danger'
        }
      ]
    },
    principles: {
      eyebrow: 'Принципы платформы',
      title: 'Это не маркетплейс ради витрины. Это контролируемый процесс с документной памятью.',
      text: 'Интерфейс должен заранее объяснять, кто принял решение, на что он опирался и как состояние объекта менялось по пути.',
      items: [
        {
          eyebrow: 'Контроль',
          title: 'У каждого перехода есть владелец, статус и причина.',
          body: 'Платформа не скрывает ручную работу. Наоборот, она делает её видимой и проверяемой.'
        },
        {
          eyebrow: 'Прозрачность',
          title: 'Сигналы, версии и документы лежат рядом с маршрутом.',
          body: 'Оператор видит, почему поставщик попал в оффер и какая ревизия сейчас считается рабочей.'
        },
        {
          eyebrow: 'Роли',
          title: 'Публичный ввод, операторский слой и исполнение не смешиваются.',
          body: 'Каждый экран держит свою границу ответственности и не имитирует чужой контур.'
        },
        {
          eyebrow: 'Explainability',
          title: 'Решения читаются как техкарта, а не как чёрный ящик.',
          body: 'Даже когда сигналов много, система собирает их в понятный operational trail.'
        }
      ],
      strip: {
        title: 'Новая визуальная система опирается на бумажный лист, ревизии, линейки и сигнальные маршруты.',
        body: 'Так интерфейс выглядит как реальный рабочий инструмент для печати и упаковки, а не как очередной AI SaaS c декоративным свечением.'
      }
    },
    demo: {
      eyebrow: 'Демо-интерфейс',
      title: 'Один спокойный рабочий экран показывает, как новый стиль живёт в реальном продукте.',
      text: 'Это не фейковый дашборд. Это экран заявки, где виден контур, документы, короткий список поставщиков и логика следующего шага.',
      stamp: 'Операторский экран / заявка',
      requestCode: 'RQ-240118 / упаковка для запуска партии',
      version: 'Версия оффера v03',
      status: 'Приём подтверждён',
      summaryTitle: 'Сводка заявки',
      summaryItems: [
        'Гофрокороб для набора из трёх SKU, стартовый тираж и контрольный образец.',
        'Нужны печать, высечка, согласование файла и понятный срок запуска.',
        'Файлы и комментарии уже привязаны к заявке, черновик не потерян.'
      ],
      routeTitle: 'Маршрут решения',
      routeItems: [
        'Приём подтверждён и закрыт по обязательным полям.',
        'Маршрутизация отрезала поставщиков без нужной ширины и срока.',
        'Оффер собран по двум допустимым узлам и одной ручной проверке.'
      ],
      suppliersTitle: 'Короткий список поставщиков',
      suppliersItems: [
        'Северная упаковка — основной кандидат по стабильности.',
        'Print Lab 24 — резерв для образца и быстрых ревизий.',
        'East Carton — остаётся в контуре только после ручного допуска.'
      ],
      explainTitle: 'Почему система предлагает этот ход',
      explainItems: [
        'Lead time совпадает с окном запуска.',
        'Материал и формат подтверждены по предыдущим входам.',
        'Риск по срокам виден заранее и не маскируется красивой витриной.'
      ],
      actions: {
        primary: 'Открыть заявки',
        secondary: 'Открыть заказы'
      }
    }
  },
  en: {
    stamp: 'Public shell / revision 01',
    heroEyebrow: 'Operational platform for sourcing, intake, routing and execution',
    title: 'MagonOS turns the path from draft to order into one controlled operating contour.',
    text:
      'The platform runs sourcing, intake, routing, offers and execution as one connected chain. The center is not magic but versions, signals, routing, ownership and clear decision explainability.',
    statusOnline: 'Contour is available',
    statusOffline: 'The backend is not responding, but the web layer and route structure remain available.',
    metrics: [
      {label: 'Canonical registry', value: 'nodes and suppliers'},
      {label: 'Route decisions', value: 'versions and states'},
      {label: 'Trust signals', value: 'verification and explainability'}
    ],
    ctas: {
      primary: 'Open the working contour',
      secondary: 'View suppliers',
      tertiary: 'Open the project map'
    },
    heroPanel: {
      eyebrow: 'Live process route',
      title: 'Draft -> request -> offer -> order',
      text: 'Each stage carries its own status, document set and transition. The system shows what is confirmed, where an operator is needed and what evidence moves the route forward.',
      notes: [
        'No AI-magic fog: the signal that moved the decision stays visible.',
        'Versions and documents stay next to the route instead of being lost across layers.',
        'The public shell and the operator contour read as one adult system.'
      ]
    },
    process: {
      eyebrow: 'How the system works',
      title: 'The route behaves like a technical process, not a pile of disconnected widgets.',
      text: 'Each step changes the responsibility level: from open-ended input to formal intake, then to a versioned offer and finally to a confirmed order.',
      steps: [
        {
          code: '01',
          name: 'Draft',
          title: 'Captures input, files and early signals without fake formality.',
          body: 'The user records the task, attaches material and leaves context. The system does not promise execution yet, but it already holds structure.',
          tone: 'neutral'
        },
        {
          code: '02',
          name: 'Request',
          title: 'Turns loose input into verifiable intake with status and ownership.',
          body: 'Required fields, operator ownership, queue position and routing reasons appear. This is now part of the operating contour.',
          tone: 'primary'
        },
        {
          code: '03',
          name: 'Offer',
          title: 'Assembles the decision version, supplier options and choice rationale.',
          body: 'The operator sees not only price but source, trust, production constraints and revision history. This is where explainability becomes concrete.',
          tone: 'signal'
        },
        {
          code: '04',
          name: 'Order',
          title: 'Locks the confirmed route and hands the work into execution.',
          body: 'The order inherits documents, files, the offer version and the operating trail. Execution starts from a confirmed contour, not from a verbal handoff.',
          tone: 'danger'
        }
      ]
    },
    network: {
      eyebrow: 'Supplier intelligence',
      title: 'The platform does not merely display suppliers. It normalizes them and links them to the route logic.',
      text: 'Signals and confirmations come first, then nodes are normalized into a shared model, and only then does routing decide who fits a specific request.',
      hub: {
        eyebrow: 'Routing / trust layer',
        title: 'One operating layer connects supplier signals with the request decision.',
        body: 'The center is not a catalog but logic: signal origin, normalization, trust level, production tolerances and role within the active request.',
        bullets: [
          'Normalization from raw to confirmed',
          'Trust level and reason for eligibility',
          'Linkage to the active offer revision'
        ]
      },
      suppliers: [
        {
          name: 'Northern Packaging',
          trust: 'Verified',
          body: 'Corrugated formats, stable lead time, confirmed production sizes.',
          route: 'Moves into the shortlist for transport and carton packaging.',
          tone: 'primary'
        },
        {
          name: 'Print Lab 24',
          trust: 'Under review',
          body: 'Short-run print work and fast proof production.',
          route: 'Enters when the request needs a fast approval loop.',
          tone: 'signal'
        },
        {
          name: 'Flex Unit',
          trust: 'Constrained',
          body: 'Works only within a narrow material and width range.',
          route: 'Fits some SKU lines but gets trimmed by rules on complex work.',
          tone: 'neutral'
        },
        {
          name: 'East Carton',
          trust: 'Manual control',
          body: 'Strong price but unstable timing and incomplete document trail.',
          route: 'The system does not ban the node, but it demands manual approval before the offer moves forward.',
          tone: 'danger'
        }
      ]
    },
    principles: {
      eyebrow: 'Platform principles',
      title: 'This is not a storefront marketplace. It is a controlled process with document memory.',
      text: 'The interface should explain upfront who made the call, what it relied on and how the object changed while moving through the chain.',
      items: [
        {
          eyebrow: 'Control',
          title: 'Every transition has an owner, a state and a reason.',
          body: 'The platform does not hide manual work. It makes it visible and auditable.'
        },
        {
          eyebrow: 'Transparency',
          title: 'Signals, versions and documents stay next to the route.',
          body: 'The operator sees why a supplier entered the offer and which revision is currently active.'
        },
        {
          eyebrow: 'Roles',
          title: 'Public input, operator work and execution do not collapse into one blur.',
          body: 'Each screen keeps its own responsibility boundary instead of imitating someone else’s surface.'
        },
        {
          eyebrow: 'Explainability',
          title: 'Decisions read like a technical sheet, not a black box.',
          body: 'Even with many inputs, the system assembles them into a readable operational trail.'
        }
      ],
      strip: {
        title: 'The visual system is built from paper stock, revision marks, rulers and signal routes.',
        body: 'That makes the interface feel like a real tool for print and packaging operations rather than another glowing AI SaaS shell.'
      }
    },
    demo: {
      eyebrow: 'Demo interface',
      title: 'One calm working screen shows how the new language behaves inside the real product.',
      text: 'This is not a fake dashboard. It is a request screen showing the contour, documents, supplier shortlist and the reason behind the next step.',
      stamp: 'Operator screen / request view',
      requestCode: 'RQ-240118 / packaging for launch batch',
      version: 'Offer revision v03',
      status: 'Intake confirmed',
      summaryTitle: 'Request summary',
      summaryItems: [
        'Corrugated carton for a three-SKU set, launch run and control proof.',
        'Needs print, die cut, file approval and a clear launch window.',
        'Files and comments are already attached to the request, so the draft context is not lost.'
      ],
      routeTitle: 'Decision route',
      routeItems: [
        'Intake is confirmed and closed on required fields.',
        'Routing removed suppliers without the required width and timing.',
        'The offer is assembled from two eligible nodes plus one manual check.'
      ],
      suppliersTitle: 'Supplier shortlist',
      suppliersItems: [
        'Northern Packaging is the primary candidate for stability.',
        'Print Lab 24 remains the proof and fast-revision fallback.',
        'East Carton stays in scope only after a manual release.'
      ],
      explainTitle: 'Why the system suggests this route',
      explainItems: [
        'Lead time matches the launch window.',
        'Material and size are confirmed from previous inputs.',
        'Timing risk is visible upfront and not hidden behind a pretty storefront.'
      ],
      actions: {
        primary: 'Open requests',
        secondary: 'Open orders'
      }
    }
  }
};

const toneClasses = {
  neutral: 'border-foreground/12 bg-background/72',
  primary: 'border-primary/28 bg-primary/[0.08]',
  signal: 'border-accent/30 bg-accent/[0.08]',
  danger: 'border-danger/28 bg-danger/[0.08]'
} as const;

const toneDotClasses = {
  neutral: 'bg-foreground/70',
  primary: 'bg-primary',
  signal: 'bg-accent',
  danger: 'bg-danger'
} as const;

function TechnicalMarks() {
  return (
    <>
      <span className="absolute left-4 top-4 h-5 w-5 border-l border-t border-foreground/18" aria-hidden="true" />
      <span className="absolute right-4 top-4 h-5 w-5 border-r border-t border-foreground/18" aria-hidden="true" />
      <span className="absolute bottom-4 left-4 h-5 w-5 border-b border-l border-foreground/18" aria-hidden="true" />
      <span className="absolute bottom-4 right-4 h-5 w-5 border-b border-r border-foreground/18" aria-hidden="true" />
    </>
  );
}

function SectionLead({eyebrow, title, text}: {eyebrow: string; title: string; text: string}) {
  return (
    <div className="space-y-3">
      <div className="micro-label">{eyebrow}</div>
      <h2 className="max-w-4xl text-[clamp(2.4rem,5vw,4.4rem)] leading-[0.92] text-balance">{title}</h2>
      <p className="max-w-3xl text-base leading-7 text-muted-foreground md:text-lg">{text}</p>
    </div>
  );
}

function RouteGraphic() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 720 360"
      className="pointer-events-none absolute inset-x-4 top-10 hidden h-[320px] w-[calc(100%-2rem)] opacity-70 md:block"
    >
      <polyline
        points="96,104 256,104 256,180 420,180 420,256 602,256"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="text-foreground/15"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="8 10"
      />
      <polyline
        points="96,104 256,104 256,180 420,180 420,256 602,256"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        className="text-primary/25"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="3 20"
      />
      {[96, 256, 420, 602].map((x, index) => (
        <g key={x} transform={`translate(${x} ${index % 2 === 0 ? (index === 0 ? 104 : 256) : 180})`}>
          <circle r="13" className={cn('signal-dot', index === 3 ? 'fill-danger/90' : 'fill-primary/90')} />
          <circle r="25" className="fill-none stroke-current text-foreground/12" strokeWidth="1" />
        </g>
      ))}
    </svg>
  );
}

function SupplierMesh() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 860 420"
      className="pointer-events-none absolute inset-x-6 top-8 hidden h-[360px] w-[calc(100%-3rem)] opacity-70 lg:block"
    >
      <g fill="none" stroke="currentColor" strokeLinecap="round">
        <path d="M 164 90 C 250 120, 300 150, 430 205" className="text-primary/26" strokeWidth="2" strokeDasharray="7 11" />
        <path d="M 164 300 C 264 276, 312 250, 430 205" className="text-accent/28" strokeWidth="2" strokeDasharray="7 11" />
        <path d="M 698 92 C 610 130, 560 160, 430 205" className="text-accent/26" strokeWidth="2" strokeDasharray="7 11" />
        <path d="M 698 300 C 602 274, 550 244, 430 205" className="text-danger/24" strokeWidth="2" strokeDasharray="7 11" />
      </g>
      {[{x: 164, y: 90}, {x: 164, y: 300}, {x: 698, y: 92}, {x: 698, y: 300}, {x: 430, y: 205}].map((point) => (
        <g key={`${point.x}-${point.y}`} transform={`translate(${point.x} ${point.y})`}>
          <circle r="10" className="fill-current text-primary/85" />
          <circle r="22" className="fill-none stroke-current text-foreground/12" strokeWidth="1" />
        </g>
      ))}
    </svg>
  );
}

export async function RetroPrintLanding({platformStatus}: {platformStatus: PlatformStatus | null}) {
  const locale = await getLocale();
  const currentLocale = locale === 'ru' ? 'ru' : 'en';
  const copy = copyByLocale[currentLocale];
  const formatter = new Intl.NumberFormat(currentLocale === 'ru' ? 'ru-RU' : 'en-US');
  const companies = formatter.format(platformStatus?.storage_counts.canonical_companies ?? 0);
  const feedback = formatter.format(platformStatus?.storage_counts.feedback_events ?? 0);

  return (
    <main className="overflow-x-clip pb-12">
      <section className="container pt-6 md:pt-10">
        <div className="sheet-panel reveal-section relative overflow-hidden px-6 py-7 md:px-10 md:py-10 lg:px-12 lg:py-12">
          <TechnicalMarks />
          <div className="technical-mesh absolute inset-0 opacity-50" aria-hidden="true" />
          <div className="measure-rule absolute left-10 right-10 top-[4.4rem] hidden md:block" aria-hidden="true" />
          <div className="relative z-10 grid gap-10 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
            <div className="space-y-8">
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="micro-label">{copy.stamp}</span>
                <span className="signal-chip">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {platformStatus ? copy.statusOnline : copy.statusOffline}
                </span>
              </div>
              <div className="space-y-5">
                <p className="font-mono text-xs uppercase tracking-[0.32em] text-muted-foreground">{copy.heroEyebrow}</p>
                <h1 className="max-w-5xl text-[clamp(3.4rem,8vw,7.5rem)] leading-[0.88] text-balance">{copy.title}</h1>
                <p className="max-w-3xl text-base leading-7 text-muted-foreground md:text-xl md:leading-8">{copy.text}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/request-workbench" className="editorial-button editorial-button-primary">
                  {copy.ctas.primary}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/suppliers" className="editorial-button editorial-button-secondary">
                  {copy.ctas.secondary}
                </Link>
                <Link href="/project-map" className="editorial-button editorial-button-ghost">
                  {copy.ctas.tertiary}
                </Link>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="paper-panel min-h-[122px] px-4 py-4">
                  <div className="micro-label">{currentLocale === 'ru' ? 'Контур' : 'Runtime'}</div>
                  <div className="mt-4 text-3xl font-heading">{companies}</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.metrics[0].value}</p>
                </div>
                <div className="paper-panel min-h-[122px] px-4 py-4">
                  <div className="micro-label">{currentLocale === 'ru' ? 'Сигналы' : 'Signals'}</div>
                  <div className="mt-4 text-3xl font-heading">{feedback}</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.metrics[2].value}</p>
                </div>
                <div className="paper-panel min-h-[122px] px-4 py-4">
                  <div className="micro-label">{currentLocale === 'ru' ? 'Маршрут' : 'Flow'}</div>
                  <div className="mt-4 flex items-center gap-3 text-lg font-medium text-foreground">
                    <Waypoints className="h-5 w-5 text-primary" />
                    {copy.metrics[1].label}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.metrics[1].value}</p>
                </div>
              </div>
            </div>

            <aside className="paper-panel relative overflow-hidden p-5 md:p-6">
              <TechnicalMarks />
              <div className="relative z-10 space-y-5">
                <div className="space-y-3 pr-6">
                  <div className="micro-label">{copy.heroPanel.eyebrow}</div>
                  <h2 className="text-[clamp(2rem,4vw,3rem)] leading-[0.94]">{copy.heroPanel.title}</h2>
                  <p className="text-sm leading-7 text-muted-foreground md:text-base">{copy.heroPanel.text}</p>
                </div>
                <div className="space-y-4 border-t border-border/90 pt-5">
                  {copy.process.steps.map((step, index) => (
                    <article key={step.code} className="relative pl-12">
                      {index < copy.process.steps.length - 1 ? (
                        <span className="route-beam absolute left-[1.05rem] top-8 h-[calc(100%+0.9rem)] w-px" aria-hidden="true" />
                      ) : null}
                      <span
                        className={cn(
                          'absolute left-0 top-0 flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold',
                          toneClasses[step.tone]
                        )}
                      >
                        {step.code}
                      </span>
                      <div className="space-y-1.5 pb-3">
                        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-muted-foreground">{step.name}</p>
                        <h3 className="text-lg leading-snug">{step.title}</h3>
                        <p className="text-sm leading-6 text-muted-foreground">{step.body}</p>
                      </div>
                    </article>
                  ))}
                </div>
                <div className="grid gap-2 border-t border-border/90 pt-5">
                  {copy.heroPanel.notes.map((note) => (
                    <div key={note} className="rounded-[1.1rem] border border-border bg-background/68 px-4 py-3 text-sm leading-6 text-foreground/82">
                      {note}
                    </div>
                  ))}
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section className="container section-space">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)] lg:items-start">
          <SectionLead eyebrow={copy.process.eyebrow} title={copy.process.title} text={copy.process.text} />
          <div className="sheet-panel reveal-section relative overflow-hidden px-5 py-6 md:px-7 md:py-8">
            <TechnicalMarks />
            <RouteGraphic />
            <ol className="relative z-10 grid gap-4 md:grid-cols-2 md:gap-5">
              {copy.process.steps.map((step, index) => (
                <li
                  key={step.code}
                  className={cn(
                    'paper-panel min-h-[212px] px-5 py-5',
                    index === 1 ? 'md:translate-y-16' : '',
                    index === 2 ? 'md:-translate-y-4' : '',
                    index === 3 ? 'md:translate-y-10' : ''
                  )}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="micro-label">{step.name}</span>
                    <span className={cn('signal-chip gap-2', toneClasses[step.tone])}>
                      <span className={cn('h-2.5 w-2.5 rounded-full', toneDotClasses[step.tone])} />
                      {step.code}
                    </span>
                  </div>
                  <h3 className="mt-5 text-2xl leading-tight">{step.title}</h3>
                  <p className="mt-4 text-sm leading-7 text-muted-foreground">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="container section-space">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <SectionLead eyebrow={copy.network.eyebrow} title={copy.network.title} text={copy.network.text} />
          <div className="sheet-panel reveal-section relative overflow-hidden px-6 py-7">
            <TechnicalMarks />
            <SupplierMesh />
            {/* RU: Сеть поставщиков здесь показываем как сеть решений и сигналов доверия, а не как искусственный dashboard с фейковыми графиками. */}
            <div className="relative z-10 grid gap-4 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.06fr)_minmax(0,0.92fr)]">
              <div className="grid gap-4">
                {copy.network.suppliers.slice(0, 2).map((supplier) => (
                  <article key={supplier.name} className="paper-panel px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-lg leading-tight">{supplier.name}</h3>
                      <span className={cn('signal-chip', toneClasses[supplier.tone])}>{supplier.trust}</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">{supplier.body}</p>
                    <p className="mt-4 border-t border-border/80 pt-3 text-sm leading-6 text-foreground/84">{supplier.route}</p>
                  </article>
                ))}
              </div>

              <article className="paper-panel relative overflow-hidden px-5 py-5">
                <div className="measure-rule absolute left-4 right-4 top-4" aria-hidden="true" />
                <div className="relative z-10 space-y-5 pt-3">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-primary/24 bg-primary/[0.09] text-primary">
                    <Workflow className="h-5 w-5" />
                  </div>
                  <div className="space-y-2">
                    <div className="micro-label">{copy.network.hub.eyebrow}</div>
                    <h3 className="text-[clamp(2rem,3vw,2.6rem)] leading-[0.95]">{copy.network.hub.title}</h3>
                    <p className="text-sm leading-7 text-muted-foreground">{copy.network.hub.body}</p>
                  </div>
                  <ul className="grid gap-2">
                    {copy.network.hub.bullets.map((bullet) => (
                      <li key={bullet} className="signal-chip justify-start rounded-[1rem] px-3 py-2">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>

              <div className="grid gap-4">
                {copy.network.suppliers.slice(2).map((supplier) => (
                  <article key={supplier.name} className="paper-panel px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-lg leading-tight">{supplier.name}</h3>
                      <span className={cn('signal-chip', toneClasses[supplier.tone])}>{supplier.trust}</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">{supplier.body}</p>
                    <p className="mt-4 border-t border-border/80 pt-3 text-sm leading-6 text-foreground/84">{supplier.route}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container section-space">
        <SectionLead eyebrow={copy.principles.eyebrow} title={copy.principles.title} text={copy.principles.text} />
        <div className="reveal-section mt-8 grid gap-4 lg:grid-cols-12">
          {copy.principles.items.map((item, index) => (
            <article
              key={item.title}
              className={cn(
                'paper-panel px-5 py-5',
                index === 0 ? 'lg:col-span-5 lg:min-h-[280px]' : '',
                index === 1 ? 'lg:col-span-3 lg:min-h-[280px]' : '',
                index === 2 ? 'lg:col-span-4 lg:min-h-[280px]' : '',
                index === 3 ? 'lg:col-span-7 lg:min-h-[240px]' : ''
              )}
            >
              <div className="micro-label">{item.eyebrow}</div>
              <h3 className="mt-5 text-[clamp(1.8rem,3vw,2.5rem)] leading-[0.96]">{item.title}</h3>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-muted-foreground">{item.body}</p>
            </article>
          ))}
          <article className="sheet-panel relative overflow-hidden px-6 py-6 lg:col-span-5">
            <TechnicalMarks />
            <div className="relative z-10 space-y-4">
              <div className="micro-label">{currentLocale === 'ru' ? 'Редакционный контур' : 'Operational editorial'}</div>
              <h3 className="text-[clamp(2rem,3vw,3.1rem)] leading-[0.94]">{copy.principles.strip.title}</h3>
              <p className="max-w-2xl text-sm leading-7 text-muted-foreground">{copy.principles.strip.body}</p>
              <div className="signal-chip justify-start rounded-[1rem] px-3 py-2">
                <GitBranch className="h-4 w-4 text-primary" />
                {'draft -> request -> offer -> order'}
              </div>
            </div>
          </article>
        </div>
      </section>

      <section className="container section-space">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)]">
          <SectionLead eyebrow={copy.demo.eyebrow} title={copy.demo.title} text={copy.demo.text} />
          <div className="sheet-panel reveal-section relative overflow-hidden">
            <TechnicalMarks />
            <div className="measure-rule absolute left-6 right-6 top-5" aria-hidden="true" />
            <div className="relative z-10 px-6 pb-6 pt-9 md:px-7 md:pb-7">
              <div className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <div className="micro-label">{copy.demo.stamp}</div>
                  <h3 className="text-[clamp(2rem,3vw,2.8rem)] leading-[0.94]">{copy.demo.requestCode}</h3>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="signal-chip">
                    <CircleDashed className="h-4 w-4 text-accent" />
                    {copy.demo.status}
                  </span>
                  <span className="signal-chip">
                    <Files className="h-4 w-4 text-primary" />
                    {copy.demo.version}
                  </span>
                </div>
              </div>

              <div className="grid gap-5 pt-5 lg:grid-cols-[minmax(0,1.04fr)_minmax(0,0.96fr)]">
                <div className="grid gap-5">
                  <article className="paper-panel px-5 py-5">
                    <div className="flex items-center gap-2 text-foreground">
                      <FileStack className="h-4 w-4 text-primary" />
                      <h4 className="text-lg">{copy.demo.summaryTitle}</h4>
                    </div>
                    <ul className="mt-4 grid gap-3 text-sm leading-7 text-muted-foreground">
                      {copy.demo.summaryItems.map((item) => (
                        <li key={item} className="border-t border-border/80 pt-3 first:border-t-0 first:pt-0">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </article>

                  <article className="paper-panel px-5 py-5">
                    <div className="flex items-center gap-2 text-foreground">
                      <Waypoints className="h-4 w-4 text-accent" />
                      <h4 className="text-lg">{copy.demo.routeTitle}</h4>
                    </div>
                    <ul className="mt-4 grid gap-3 text-sm leading-7 text-muted-foreground">
                      {copy.demo.routeItems.map((item) => (
                        <li key={item} className="signal-chip justify-start rounded-[1rem] px-3 py-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </article>
                </div>

                <div className="grid gap-5">
                  <article className="paper-panel px-5 py-5">
                    <div className="flex items-center gap-2 text-foreground">
                      <Factory className="h-4 w-4 text-danger" />
                      <h4 className="text-lg">{copy.demo.suppliersTitle}</h4>
                    </div>
                    <ul className="mt-4 grid gap-3 text-sm leading-7 text-muted-foreground">
                      {copy.demo.suppliersItems.map((item) => (
                        <li key={item} className="border-t border-border/80 pt-3 first:border-t-0 first:pt-0">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </article>

                  <article className="paper-panel px-5 py-5">
                    <div className="flex items-center gap-2 text-foreground">
                      <ScanSearch className="h-4 w-4 text-primary" />
                      <h4 className="text-lg">{copy.demo.explainTitle}</h4>
                    </div>
                    <ul className="mt-4 grid gap-3 text-sm leading-7 text-muted-foreground">
                      {copy.demo.explainItems.map((item) => (
                        <li key={item} className="border-t border-border/80 pt-3 first:border-t-0 first:pt-0">
                          {item}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-5 flex flex-wrap gap-3">
                      <Link href="/request-workbench" className="editorial-button editorial-button-primary">
                        {copy.demo.actions.primary}
                      </Link>
                      <Link href="/orders" className="editorial-button editorial-button-secondary">
                        {copy.demo.actions.secondary}
                      </Link>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
