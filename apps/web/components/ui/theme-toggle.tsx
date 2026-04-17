"use client";

import * as React from 'react';
import {MoonStar, SunMedium} from 'lucide-react';
import {useTheme} from 'next-themes';
import {useTranslations} from 'next-intl';

import {Button} from '@/components/ui/button';

export function ThemeToggle() {
  const {resolvedTheme, setTheme} = useTheme();
  const t = useTranslations('themeToggle');
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // RU: До mount next-themes ещё не знает итоговую client theme, поэтому SSR должен отдавать нейтральный toggle без смены aria-label и иконки.
  const isDark = resolvedTheme === 'dark';
  const ariaLabel = !mounted ? t('toDark') : isDark ? t('toLight') : t('toDark');

  return (
    <Button
      type="button"
      size="icon"
      variant="outline"
      aria-label={ariaLabel}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
    >
      {!mounted ? <MoonStar className="h-4 w-4" /> : isDark ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
    </Button>
  );
}
