"use client";

import * as React from "react";
import { motion, useMotionTemplate, useMotionValue } from "framer-motion";

import { cn } from "@/lib/utils";

export function InteractiveGlassCard({
  className,
  children
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const mouseX = useMotionValue(120);
  const mouseY = useMotionValue(120);

  return (
    <motion.div
      onPointerMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        mouseX.set(event.clientX - rect.left);
        mouseY.set(event.clientY - rect.top);
      }}
      className={cn(
        "group relative overflow-hidden rounded-[1.8rem] border border-white/14 bg-white/[0.05] p-5 shadow-panel backdrop-blur-2xl",
        className
      )}
      style={{
        backgroundImage: useMotionTemplate`radial-gradient(320px circle at ${mouseX}px ${mouseY}px, rgba(255,255,255,0.16), transparent 56%)`
      }}
    >
      <div className="absolute inset-0 bg-[linear-gradient(160deg,rgba(255,255,255,0.16),transparent_36%,transparent_64%,rgba(255,255,255,0.08))] opacity-70" />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
