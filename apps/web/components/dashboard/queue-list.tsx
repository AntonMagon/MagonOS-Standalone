import {getTranslations} from 'next-intl/server';
import {CircleDashed, Layers2, ShieldCheck} from 'lucide-react';

import {defaultLocale} from '@/i18n/config';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';

const queueMap = [
  {key: 'standalone', icon: Layers2},
  {key: 'bridge', icon: ShieldCheck},
  {key: 'odoo', icon: CircleDashed}
] as const;

export async function QueueList() {
  const t = await getTranslations({locale: defaultLocale, namespace: 'dashboard.queues'});

  return (
    <Card className="glass-panel border-white/10 bg-white/[0.04]">
      <CardHeader>
        <CardTitle className="text-xl">{t('title')}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {queueMap.map((queue) => {
          const Icon = queue.icon;
          return (
            <div key={queue.key} className="flex items-center justify-between rounded-[1.2rem] border border-white/8 bg-black/10 px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full border border-white/12 bg-white/6 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-sm font-medium">{t(`items.${queue.key}.title`)}</div>
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{t('activeLayer')}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{t(`items.${queue.key}.detail`)}</div>
                </div>
              </div>
              <div className="font-heading text-sm uppercase tracking-[0.24em] text-foreground/80">{t(`items.${queue.key}.state`)}</div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
