"use client";

import * as Dialog from '@radix-ui/react-dialog';
import {Check, Palette} from 'lucide-react';
import {useTranslations} from 'next-intl';

import {useAppearance} from '@/components/personalization/appearance-provider';
import {Button} from '@/components/ui/button';
import {cn} from '@/lib/utils';

export function AppearancePanel() {
  const {paletteId, palettes, setPalette} = useAppearance();
  const t = useTranslations('appearance');

  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button type="button" size="icon" variant="outline" aria-label={t('openButton')}>
          <Palette className="h-4 w-4" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/35 backdrop-blur-sm" />
        <Dialog.Content className="fixed right-4 top-4 z-50 w-[min(92vw,26rem)] rounded-[1.6rem] border border-white/15 bg-surface/88 p-5 shadow-panel backdrop-blur-2xl md:right-8 md:top-8">
          <div className="mb-5 space-y-2">
            <Dialog.Title className="font-heading text-xl font-semibold">{t('title')}</Dialog.Title>
            <Dialog.Description className="text-sm leading-6 text-muted-foreground">{t('description')}</Dialog.Description>
          </div>

          <div className="grid gap-3">
            {palettes.map((palette) => {
              const active = palette.id === paletteId;
              return (
                <button
                  key={palette.id}
                  type="button"
                  className={cn(
                    'group rounded-2xl border px-4 py-4 text-left transition-all',
                    active ? 'border-primary/50 bg-primary/10' : 'border-border/70 bg-background/50 hover:border-white/20 hover:bg-white/6'
                  )}
                  onClick={() => setPalette(palette.id)}
                  aria-pressed={active}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-foreground">{t(`palettes.${palette.id}.name`)}</div>
                      <div className="text-sm text-muted-foreground">{t(`palettes.${palette.id}.description`)}</div>
                    </div>
                    {active ? <Check className="h-4 w-4 text-primary" /> : null}
                  </div>
                  <div className="flex items-center gap-2">
                    {/* RU: Внутри одной палитры часть токенов намеренно делит один и тот же HSL, поэтому key должен опираться на имя токена, а не на само значение цвета. */}
                    {Object.entries(palette.values).map(([token, hsl]) => (
                      <span
                        key={`${palette.id}-${token}`}
                        className="h-8 w-8 rounded-full border border-white/15"
                        style={{backgroundColor: `hsl(${hsl})`}}
                        aria-hidden="true"
                      />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
