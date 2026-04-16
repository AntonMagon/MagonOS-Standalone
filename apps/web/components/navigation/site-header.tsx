"use client";

import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {PanelLeftOpen, Sparkles} from 'lucide-react';

import {siteNav} from '@/lib/site-nav';
import {cn} from '@/lib/utils';
import {AppearancePanel} from '@/components/personalization/appearance-panel';
import {ThemeToggle} from '@/components/ui/theme-toggle';

export function SiteHeader() {
  const pathname = usePathname();
  const tNav = useTranslations('nav');
  const tHeader = useTranslations('header');
  const tCommon = useTranslations('common');

  return (
    <header className="sticky top-0 z-50">
      <div className="container pt-4 md:pt-6">
        <div className="glass-panel flex items-center justify-between gap-4 rounded-full px-4 py-3 md:px-5">
          <Link href="/" className="flex min-w-0 items-center gap-3" aria-label={tHeader('homeAria')}>
            <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/10 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block truncate font-heading text-sm font-semibold uppercase tracking-[0.28em] text-muted-foreground">
                {tCommon('brand')}
              </span>
              <span className="block truncate text-sm text-foreground/80">{tHeader('shell')}</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-2 md:flex" aria-label={tCommon('brand')}>
            {siteNav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'rounded-full px-4 py-2 text-sm transition-colors',
                    active ? 'bg-white/14 text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.22)]' : 'text-muted-foreground hover:text-foreground'
                  )}
                  aria-current={active ? 'page' : undefined}
                >
                  {tNav(item.labelKey)}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <AppearancePanel />
            <ThemeToggle />
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-muted-foreground md:hidden"
              aria-label={tHeader('mobileNavHint')}
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
