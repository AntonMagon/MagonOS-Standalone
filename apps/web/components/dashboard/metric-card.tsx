import {InteractiveGlassCard} from '@/components/lightswind/interactive-glass-card';
import {cn} from '@/lib/utils';

export function MetricCard({
  title,
  value,
  detail,
  tone = "primary"
}: {
  title: string;
  value: string;
  detail: string;
  tone?: "primary" | "accent";
}) {
  return (
    <InteractiveGlassCard className="min-h-[180px]">
      <div className="flex h-full flex-col justify-between gap-8">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="font-heading text-4xl leading-none">{value}</p>
        </div>
        <div className="flex items-center justify-between">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium",
              tone === "primary" ? "bg-primary/14 text-primary" : "bg-accent/16 text-accent-foreground"
            )}
          >
            {detail}
          </span>
          <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">scope</span>
        </div>
      </div>
    </InteractiveGlassCard>
  );
}
