'use client';

import * as Dialog from '@radix-ui/react-dialog';
import * as React from 'react';
import type {Route} from 'next';
import Link from 'next/link';
import {usePathname, useRouter} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {ChevronRight, LogOut, Menu, X} from 'lucide-react';

import {LanguageToggle} from '@/components/navigation/language-toggle';
import {AppearancePanel} from '@/components/personalization/appearance-panel';
import {Button} from '@/components/ui/button';
import {ThemeToggle} from '@/components/ui/theme-toggle';
import {clearFoundationSession, useFoundationSession} from '@/lib/foundation-client';
import {siteNav} from '@/lib/site-nav';
import {cn} from '@/lib/utils';

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const session = useFoundationSession();
  const tNav = useTranslations('nav');
  const tHeader = useTranslations('header');
  const tCommon = useTranslations('common');
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const navItems = session?.token ? siteNav.filter((item) => item.href !== '/login') : siteNav;
  // RU: В primary nav оставляем только главные пользовательские пути и ежедневные рабочие экраны, всё вторичное уходит в drawer.
  const primaryHrefs = new Set(session?.token ? ['/', '/catalog', '/rfq', '/request-workbench', '/orders'] : ['/', '/catalog', '/rfq']);
  const primaryNavItems = navItems.filter((item) => primaryHrefs.has(item.href));
  const secondaryNavItems = navItems.filter((item) => !primaryHrefs.has(item.href));
  const roleLabel =
    session?.role_code === 'admin'
      ? 'Администратор'
      : session?.role_code === 'operator'
        ? 'Оператор'
        : session?.role_code === 'customer'
          ? 'Клиент'
          : session?.role_code === 'guest'
            ? 'Гость'
            : session?.role_code ?? tHeader('sessionUnknownRole');

  function handleLogout() {
    clearFoundationSession();
    setMobileOpen(false);
    router.push('/login');
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-50">
      <div className="container pt-4 md:pt-6">
        <div className="paper-strip flex items-center justify-between gap-3 rounded-[2rem] px-4 py-3 md:px-5">
          <Link href="/" className="flex min-w-0 flex-1 items-center gap-3 md:flex-none" aria-label={tHeader('homeAria')}>
            <span className="relative flex h-10 w-10 items-center justify-center rounded-full border border-foreground/12 bg-foreground/[0.04]">
              <span className="absolute inset-[0.35rem] rounded-full border border-primary/20" />
              <span className="signal-dot relative z-10 h-2.5 w-2.5 rounded-full bg-primary" />
            </span>
            <span className="min-w-0">
              <span className="block truncate font-heading text-sm font-semibold uppercase tracking-[0.28em] text-muted-foreground">
                {tCommon('brand')}
              </span>
              {/* RU: Подзаголовок должен сразу говорить про коммерческий сервис, а не про внутреннюю платформу. */}
              <span className="hidden truncate text-[13px] font-medium text-foreground/74 lg:block">{tHeader('shell')}</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1.5 lg:flex" aria-label={tHeader('mainNavAria')}>
            {primaryNavItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  // RU: Каст держим на границе Link, чтобы shared nav-конфиг не тащил жёсткую Next Route-типизацию на весь shell.
                  href={item.href as Route}
                  className={cn(
                    'rounded-full px-3.5 py-2 text-sm transition-colors',
                    // RU: Навигация в header должна читаться как рабочая, а не как полупрозрачный декоративный текст на фоне свечения.
                    active
                      ? 'border border-foreground/10 bg-foreground/[0.06] text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]'
                      : 'font-medium text-foreground/68 hover:bg-foreground/[0.04] hover:text-foreground'
                  )}
                  aria-current={active ? 'page' : undefined}
                >
                  {tNav(item.labelKey)}
                </Link>
              );
            })}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            {session?.token ? (
              <div className="hidden items-center gap-3 rounded-full border border-foreground/10 bg-foreground/[0.045] px-3 py-2 md:flex">
                  <div className="text-right">
                    <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{tHeader('sessionActive')}</div>
                    <div className="max-w-[11rem] truncate text-sm font-medium text-foreground/84">
                      {tHeader('sessionSignedInAs', {role: roleLabel, email: session.user?.email || tHeader('sessionUnknownEmail')})}
                  </div>
                </div>
              </div>
            ) : null}
            <Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}>
              <Dialog.Trigger asChild>
                <Button type="button" variant="outline" className="hidden md:inline-flex">
                  {tHeader('openPanel')}
                </Button>
              </Dialog.Trigger>
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
                <Dialog.Overlay className="fixed inset-0 z-50 bg-[rgba(43,46,52,0.22)] backdrop-blur-sm" />
                <Dialog.Content className="fixed inset-x-4 top-4 z-50 rounded-[1.6rem] border border-border bg-surface/96 p-5 shadow-panel backdrop-blur-2xl md:left-auto md:right-6 md:w-[min(30rem,calc(100vw-3rem))]">
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

                  <div className="space-y-4 border-b border-border/80 pb-4">
                    <div>
                      <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{tHeader('primaryLabel')}</div>
                      <div className="mt-3 grid gap-3">
                        {primaryNavItems.map((item) => {
                          const active = pathname === item.href;
                          return (
                            <Dialog.Close asChild key={item.href}>
                              <Link
                                href={item.href as Route}
                                className={cn(
                                  'flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-medium transition-colors',
                                  active ? 'border-primary/30 bg-primary/10 text-foreground' : 'border-border bg-background/78 text-foreground/88'
                                )}
                              >
                                <span>{tNav(item.labelKey)}</span>
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                              </Link>
                            </Dialog.Close>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{tHeader('navigationLabel')}</div>
                      <div className="mt-3 grid gap-3">
                        {secondaryNavItems.map((item) => {
                          const active = pathname === item.href;
                          return (
                            <Dialog.Close asChild key={item.href}>
                              <Link
                                href={item.href as Route}
                                className={cn(
                                  'flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-medium transition-colors',
                                  active ? 'border-primary/30 bg-primary/10 text-foreground' : 'border-border bg-background/78 text-foreground/88'
                                )}
                              >
                                <span>{tNav(item.labelKey)}</span>
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                              </Link>
                            </Dialog.Close>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {session?.token ? (
                    <div className="space-y-3 border-b border-border/80 pb-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{tHeader('sessionLabel')}</div>
                      <div className="rounded-2xl border border-border bg-background/70 px-4 py-3 text-sm leading-6 text-foreground/84">
                        {/* RU: В меню явно показываем роль и email, чтобы пользователь понимал, в каком контуре он сейчас работает. */}
                        <div className="font-medium">{roleLabel}</div>
                        <div className="text-muted-foreground">{session.user?.email || tHeader('sessionUnknownEmail')}</div>
                      </div>
                      <Button type="button" variant="outline" onClick={handleLogout}>
                        <LogOut className="mr-2 h-4 w-4" />
                        {tHeader('logout')}
                      </Button>
                    </div>
                  ) : null}

                  <div className="mt-5 space-y-3 border-t border-border/80 pt-4">
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
