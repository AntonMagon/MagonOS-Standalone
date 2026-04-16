'use client';

import * as Dialog from '@radix-ui/react-dialog';
import * as React from 'react';
import type {Route} from 'next';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {Menu, Sparkles, X} from 'lucide-react';

import {LanguageToggle} from '@/components/navigation/language-toggle';
import {AppearancePanel} from '@/components/personalization/appearance-panel';
import {Button} from '@/components/ui/button';
import {ThemeToggle} from '@/components/ui/theme-toggle';
import {siteNav} from '@/lib/site-nav';
import {cn} from '@/lib/utils';

export function SiteHeader() {
  const pathname = usePathname();
  const tNav = useTranslations('nav');
  const tHeader = useTranslations('header');
  const tCommon = useTranslations('common');
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-50">
      <div className="container pt-4 md:pt-6">
        <div className="glass-panel flex items-center justify-between gap-3 rounded-full px-4 py-3 md:px-5">
          <Link href="/" className="flex min-w-0 items-center gap-3" aria-label={tHeader('homeAria')}>
            <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/10 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block truncate font-heading text-sm font-semibold uppercase tracking-[0.28em] text-muted-foreground">
                {tCommon('brand')}
              </span>
              <span className="hidden truncate text-sm text-foreground/80 sm:block">{tHeader('shell')}</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-2 md:flex" aria-label={tHeader('mainNavAria')}>
            {siteNav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  // RU: Каст держим на границе Link, чтобы shared nav-конфиг не тащил жёсткую Next Route-типизацию на весь shell.
                  href={item.href as Route}
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
            <LanguageToggle className="hidden md:inline-flex" />
            <AppearancePanel />
            <ThemeToggle />
            <Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}>
              <Dialog.Trigger asChild>
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  className="md:hidden"
                  aria-label={tHeader('mobileMenuOpen')}
                >
                  <Menu className="h-4 w-4" />
                </Button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm" />
                <Dialog.Content className="fixed inset-x-4 top-4 z-50 rounded-[1.6rem] border border-white/15 bg-surface/92 p-5 shadow-panel backdrop-blur-2xl md:hidden">
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <Dialog.Title className="font-heading text-xl font-semibold">{tHeader('mobileMenuTitle')}</Dialog.Title>
                      <Dialog.Description className="text-sm leading-6 text-muted-foreground">
                        {tHeader('mobileMenuText')}
                      </Dialog.Description>
                    </div>
                    <Dialog.Close asChild>
                      <Button type="button" size="icon" variant="outline" aria-label={tCommon('close')}>
                        <X className="h-4 w-4" />
                      </Button>
                    </Dialog.Close>
                  </div>

                  <div className="grid gap-3">
                    {siteNav.map((item) => {
                      const active = pathname === item.href;
                      return (
                        <Dialog.Close asChild key={item.href}>
                          <Link
                            // RU: В mobile nav используем тот же boundary-cast, иначе новый route ломает типизацию всего списка.
                            href={item.href as Route}
                            className={cn(
                              'rounded-2xl border px-4 py-3 text-sm font-medium transition-colors',
                              active ? 'border-primary/40 bg-primary/12 text-foreground' : 'border-white/10 bg-black/10 text-foreground/88'
                            )}
                          >
                            {tNav(item.labelKey)}
                          </Link>
                        </Dialog.Close>
                      );
                    })}
                  </div>

                  <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{tHeader('controlsLabel')}</div>
                    <div className="flex flex-wrap items-center gap-2">
                      <LanguageToggle compact />
                      <AppearancePanel />
                      <ThemeToggle />
                    </div>
                  </div>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>
      </div>
    </header>
  );
}
