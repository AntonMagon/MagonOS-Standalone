"use client";

import * as React from 'react';
import {MoonStar, SunMedium} from 'lucide-react';
import {useTheme} from 'next-themes';
import {useTranslations} from 'next-intl';

import {Button} from '@/components/ui/button';

export function ThemeToggle() {
  const {resolvedTheme, setTheme} = useTheme();
  const t = useTranslations('themeToggle');
  const isDark = resolvedTheme === 'dark';

  return (
    <Button
      type="button"
      size="icon"
      variant="outline"
      aria-label={isDark ? t('toLight') : t('toDark')}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
    >
      {isDark ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
    </Button>
  );
}
