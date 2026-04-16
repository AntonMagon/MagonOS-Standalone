"use client";

import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

const cells = Array.from({ length: 24 }, (_, index) => index);

export function HeroGrid({ className }: { className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden rounded-[2rem]", className)} aria-hidden="true">
      <div className="absolute inset-0 bg-grid bg-[size:64px_64px] opacity-[0.08]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(236,116,40,0.22),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(31,163,132,0.2),transparent_34%)]" />
      <div className="absolute -left-16 top-10 h-56 w-56 rounded-full bg-brand-glow/25 blur-3xl" />
      <div className="absolute right-0 top-1/3 h-72 w-72 rounded-full bg-brand-warm/20 blur-3xl" />
      <div className="absolute inset-x-10 bottom-10 grid grid-cols-6 gap-3 opacity-60">
        {cells.map((cell) => (
          <motion.div
            key={cell}
            className="aspect-square rounded-2xl border border-white/10 bg-white/[0.04]"
            animate={{ opacity: [0.18, 0.52, 0.18], y: [0, -4, 0] }}
            transition={{
              duration: 4 + (cell % 5),
              repeat: Infinity,
              ease: "easeInOut",
              delay: cell * 0.08
            }}
          />
        ))}
      </div>
    </div>
  );
}
