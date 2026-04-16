"use client";

import * as React from "react";
import { motion, useSpring, useTransform } from "framer-motion";

import { cn } from "@/lib/utils";

type MagneticButtonProps = {
  children: React.ReactNode;
  className?: string;
  strength?: number;
  radius?: number;
} & Omit<
  React.ButtonHTMLAttributes<HTMLButtonElement>,
  "children" | "onDrag" | "onDragEnd" | "onDragStart" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration"
>;

export function MagneticButton({
  children,
  className,
  strength = 0.24,
  radius = 110,
  ...props
}: MagneticButtonProps) {
  const ref = React.useRef<HTMLButtonElement>(null);
  const x = useSpring(0, { stiffness: 180, damping: 18, mass: 0.55 });
  const y = useSpring(0, { stiffness: 180, damping: 18, mass: 0.55 });
  const innerX = useTransform(x, (value) => value * 0.4);
  const innerY = useTransform(y, (value) => value * 0.4);

  const onMove = (event: React.MouseEvent<HTMLButtonElement>) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    const dx = event.clientX - (rect.left + rect.width / 2);
    const dy = event.clientY - (rect.top + rect.height / 2);
    const distance = Math.hypot(dx, dy);

    if (distance <= radius) {
      x.set(dx * strength);
      y.set(dy * strength);
    } else {
      x.set(0);
      y.set(0);
    }
  };

  const reset = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.button
      ref={ref}
      type="button"
      onMouseMove={onMove}
      onMouseLeave={reset}
      whileTap={{ scale: 0.98 }}
      className={cn(
        "relative inline-flex min-h-12 items-center justify-center overflow-hidden rounded-full border border-white/15 bg-white/8 px-6 py-3 text-sm font-semibold text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] backdrop-blur-xl transition-colors hover:bg-white/12 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className
      )}
      style={{ x, y }}
      {...props}
    >
      <span className="absolute inset-0 bg-[linear-gradient(120deg,transparent,rgba(255,255,255,0.18),transparent)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <motion.span style={{ x: innerX, y: innerY }} className="relative z-10">
        {children}
      </motion.span>
    </motion.button>
  );
}
