import {InteractiveGlassCard} from '@/components/lightswind/interactive-glass-card';
import {cn} from '@/lib/utils';

export function MetricCard({
  title,
  value,
  detail,
  tone = 'primary'
}: {
  title: string;
  value: string;
  detail: string;
  tone?: 'primary' | 'accent';
}) {
  return (
    <InteractiveGlassCard className="min-h-[180px]">
      <div className="flex h-full flex-col justify-between gap-8">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="font-heading text-4xl leading-none">{value}</p>
        </div>
        <div>
          <span
            className={cn(
              'inline-flex max-w-full items-center rounded-full px-3 py-1 text-xs font-medium leading-5',
              tone === 'primary' ? 'bg-primary/14 text-primary' : 'bg-accent/16 text-accent-foreground'
            )}
          >
            {detail}
          </span>
        </div>
      </div>
    </InteractiveGlassCard>
  );
}
