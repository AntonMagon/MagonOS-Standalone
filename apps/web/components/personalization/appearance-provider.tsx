"use client";

import * as React from 'react';

type Palette = {
  id: string;
  values: Record<string, string>;
};

const palettes: Palette[] = [
  {
    id: 'ember-signal',
    values: {
      '--primary': '20 86% 54%',
      '--accent': '171 41% 34%',
      '--brand-glow': '20 86% 54%',
      '--brand-warm': '171 41% 34%'
    }
  },
  {
    id: 'tidal-mint',
    values: {
      '--primary': '188 72% 51%',
      '--accent': '168 55% 42%',
      '--brand-glow': '188 72% 51%',
      '--brand-warm': '168 55% 42%'
    }
  },
  {
    id: 'violet-ink',
    values: {
      '--primary': '255 82% 67%',
      '--accent': '221 83% 58%',
      '--brand-glow': '255 82% 67%',
      '--brand-warm': '221 83% 58%'
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
