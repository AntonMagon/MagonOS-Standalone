import {getTranslations} from 'next-intl/server';
import {Clock3, FileSearch2, Users2} from 'lucide-react';

import {defaultLocale} from '@/i18n/config';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';

const itemMap = [
  {key: 'standalone', icon: FileSearch2},
  {key: 'commercial', icon: Users2},
  {key: 'rule', icon: Clock3}
] as const;

export async function ActivityList() {
  const t = await getTranslations({locale: defaultLocale, namespace: 'dashboard.activity'});

  return (
    <Card className="glass-panel h-full border-white/10 bg-white/[0.04]">
      <CardHeader>
        <CardTitle className="text-xl">{t('title')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {itemMap.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.key} className="rounded-[1.2rem] border border-white/8 bg-black/10 p-4">
              <div className="mb-2 flex items-start gap-3">
                <div className="mt-0.5 rounded-full border border-white/12 bg-white/6 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-medium text-foreground">{t(`items.${item.key}.title`)}</div>
                  <p className="text-sm leading-6 text-muted-foreground">{t(`items.${item.key}.detail`)}</p>
                </div>
              </div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{t(`items.${item.key}.tag`)}</div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
