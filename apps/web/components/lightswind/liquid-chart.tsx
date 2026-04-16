"use client";

import * as React from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { cn } from "@/lib/utils";

type Point = {
  label: string;
  value: number;
};

export function LiquidChart({
  data,
  className,
  label
}: {
  data: Point[];
  className?: string;
  label: string;
}) {
  const chartId = React.useId().replace(/:/g, "");
  const summary = data.map((item) => `${item.label}: ${item.value}`).join(", ");
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      className={cn("relative h-[220px] w-full rounded-[1.4rem] border border-white/10 bg-black/10 px-3 py-3", className)}
      role="img"
      aria-label={`${label}. ${summary}`}
      data-chart={chartId}
    >
      <style>{`
        [data-chart='${chartId}'] {
          --series-primary: hsl(var(--primary));
          --series-secondary: hsl(var(--accent));
        }
      `}</style>
      {mounted ? (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
            <defs>
              <linearGradient id={`${chartId}-fill`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--series-primary)" stopOpacity={0.44} />
                <stop offset="60%" stopColor="var(--series-secondary)" stopOpacity={0.12} />
                <stop offset="100%" stopColor="var(--series-secondary)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "currentColor", fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis hide />
            <Tooltip
              cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
              contentStyle={{
                borderRadius: "1rem",
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(15, 23, 42, 0.82)",
                backdropFilter: "blur(20px)",
                color: "white"
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--series-primary)"
              strokeWidth={2.4}
              fill={`url(#${chartId}-fill)`}
              dot={{ r: 0 }}
              activeDot={{ r: 4, fill: "var(--series-primary)", strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-full w-full animate-pulse rounded-[1rem] bg-white/6" aria-hidden="true" />
      )}
    </div>
  );
}
