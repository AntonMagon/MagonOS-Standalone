"use client";

import dynamic from "next/dynamic";
import * as React from "react";

const OrbSceneCanvas = dynamic(() => import("@/components/3d/orb-scene-canvas").then((mod) => mod.OrbSceneCanvas), {
  ssr: false,
  loading: () => <div className="h-[320px] w-full animate-pulse rounded-[1.8rem] bg-white/6" aria-hidden="true" />
});

export function OrbScene() {
  const [isMobile, setIsMobile] = React.useState(false);
  const [reducedMotion, setReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      setIsMobile(media.matches);
      setReducedMotion(reduce.matches);
    };
    update();
    media.addEventListener("change", update);
    reduce.addEventListener("change", update);
    return () => {
      media.removeEventListener("change", update);
      reduce.removeEventListener("change", update);
    };
  }, []);

  if (isMobile || reducedMotion) {
    return (
      <div className="relative h-[260px] overflow-hidden rounded-[1.8rem] border border-white/12 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.26),transparent_24%),radial-gradient(circle_at_70%_70%,rgba(84,210,181,0.22),transparent_28%),linear-gradient(160deg,rgba(255,255,255,0.1),rgba(255,255,255,0.03))]">
        <div className="absolute inset-10 rounded-full border border-white/15 bg-white/8 blur-sm" />
        <div className="absolute inset-[22%] rounded-full border border-white/15 bg-[radial-gradient(circle_at_35%_30%,rgba(255,255,255,0.82),rgba(255,255,255,0.18)_38%,rgba(255,255,255,0.05)_70%)] shadow-[0_30px_80px_-32px_rgba(0,0,0,0.55)]" />
      </div>
    );
  }

  return <OrbSceneCanvas />;
}
