"use client";

import { useReducedMotion } from "motion/react";

import { Particles } from "@/components/ui/particles";
import { gold } from "@/lib/design/tokens";

/**
 * The account screens' backdrop, after Finvo's hero and Housiq's "Startup
 * Boost" band: deep forest with a green glow behind the card and a slow
 * drift of gold flecks, like zari catching the light. It runs straight into
 * the footer, whose giant wordmark closes the scene.
 *
 * Scoped with `dark`, so it paints in the footer's forest tokens while the
 * card above it stays in the light theme. Decorative only. The flecks are a
 * canvas (Magic UI particles); they are left out entirely for anyone who has
 * turned motion off.
 */
export function ForestBackdrop() {
  const reduceMotion = useReducedMotion();
  return (
    <div aria-hidden className="dark pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-background">
      <div className="absolute inset-0 bg-radial-[ellipse_70%_60%_at_50%_35%] from-primary/40 via-primary/10 via-50% to-transparent" />
      {!reduceMotion && (
        <Particles className="absolute inset-0" quantity={60} staticity={60} ease={70} vy={-0.05} color={gold[300]} />
      )}
    </div>
  );
}
