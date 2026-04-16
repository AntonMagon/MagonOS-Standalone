import { cn } from "@/lib/utils";

export function SectionIntro({
  eyebrow,
  title,
  text,
  className
}: {
  eyebrow: string;
  title: string;
  text: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-4", className)}>
      <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
      <h2 className="max-w-3xl text-3xl leading-tight md:text-5xl">{title}</h2>
      <p className="max-w-2xl text-base leading-7 text-muted-foreground md:text-lg">{text}</p>
    </div>
  );
}
