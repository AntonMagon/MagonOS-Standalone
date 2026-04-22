"use client";

import * as React from 'react';

type Palette = {
  id: string;
  values: Record<string, string>;
};

// RU: Provider держит только палитру shell и не должен втягивать бизнес-состояние страниц или пользователя.
const palettes: Palette[] = [
  {
    id: 'ember-signal',
    values: {
      '--primary': '223 100% 57%',
      '--accent': '190 86% 69%',
      '--brand-glow': '223 100% 57%',
      '--brand-warm': '8 65% 54%'
    }
  },
  {
    id: 'tidal-mint',
    values: {
      '--primary': '190 86% 69%',
      '--accent': '74 100% 65%',
      '--brand-glow': '190 86% 69%',
      '--brand-warm': '223 100% 57%'
    }
  },
  {
    id: 'violet-ink',
    values: {
      '--primary': '8 65% 54%',
      '--accent': '223 100% 57%',
      '--brand-glow': '8 65% 54%',
      '--brand-warm': '223 100% 57%'
    }
  }
];

type AppearanceContextValue = {
  paletteId: string;
  palettes: Palette[];
  setPalette: (paletteId: string) => void;
};

const AppearanceContext = React.createContext<AppearanceContextValue | null>(null);
const STORAGE_KEY = 'magonos-appearance-palette';

export function AppearanceProvider({children}: {children: React.ReactNode}) {
  const [paletteId, setPaletteId] = React.useState<string>(palettes[0].id);

  React.useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && palettes.some((palette) => palette.id === stored)) {
      setPaletteId(stored);
    }
  }, []);

  React.useEffect(() => {
    const palette = palettes.find((entry) => entry.id === paletteId);
    if (!palette) return;

    const root = document.documentElement;
    Object.entries(palette.values).forEach(([token, value]) => {
      root.style.setProperty(token, value);
    });
    window.localStorage.setItem(STORAGE_KEY, paletteId);
  }, [paletteId]);

  const value = React.useMemo(
    () => ({
      paletteId,
      palettes,
      setPalette: setPaletteId
    }),
    [paletteId]
  );

  return <AppearanceContext.Provider value={value}>{children}</AppearanceContext.Provider>;
}

export function useAppearance() {
  const context = React.useContext(AppearanceContext);
  if (!context) {
    throw new Error('useAppearance must be used within AppearanceProvider');
  }
  return context;
}
