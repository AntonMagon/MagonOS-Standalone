'use client';

import * as React from 'react';
import {Languages} from 'lucide-react';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

import {Button} from '@/components/ui/button';
import {localeCookieName, locales, type AppLocale} from '@/i18n/config';
import {cn} from '@/lib/utils';

type LanguageToggleProps = {
  className?: string;
  compact?: boolean;
};

export function LanguageToggle({className, compact = false}: LanguageToggleProps) {
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const [isPending, startTransition] = React.useTransition();
  const t = useTranslations('languageToggle');

  const applyLocale = React.useCallback(
    (nextLocale: AppLocale) => {
      if (nextLocale === locale) {
        return;
      }

      document.cookie = `${localeCookieName}=${nextLocale}; path=/; max-age=31536000; samesite=lax`;
      window.localStorage.setItem(localeCookieName, nextLocale);
      startTransition(() => {
        router.refresh();
      });
    },
    [locale, router]
  );

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/6 p-1 text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl',
        className
      )}
      role="group"
      aria-label={t('label')}
    >
      {!compact ? <Languages className="ml-2 h-4 w-4 text-muted-foreground" aria-hidden="true" /> : null}
      {locales.map((entry) => {
        const active = entry === locale;
        return (
          <Button
            key={entry}
            type="button"
            size="sm"
            variant={active ? 'primary' : 'ghost'}
            className={cn(
              'min-w-[3rem] rounded-full px-3',
              !active && 'text-muted-foreground hover:bg-white/10 hover:text-foreground',
              compact && 'h-8 min-w-[2.75rem] px-2.5 text-xs'
            )}
            aria-pressed={active}
            aria-label={entry === 'ru' ? t('switchToRu') : t('switchToEn')}
            disabled={isPending}
            onClick={() => applyLocale(entry)}
          >
            {t(entry)}
          </Button>
        );
      })}
    </div>
  );
}
