"use client";

import { motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/cn";

const DOTS = 6;
const LAP_SECONDS = 1.6;
/** Slow over the top, quick round the bottom: the dots bunch, then string out. */
const LAP_EASE = [0.62, 0.04, 0.38, 0.96] as const;

/**
 * Six dots chasing one another round a circle, in the current text colour.
 * Sized by font size (`text-base` is 1em across); under reduced motion it
 * holds still as a short arc. Announced to screen readers as `label`, unless
 * `decorative`: beside visible text that already says it, it is hidden.
 */
export function ChaseLoader({
  label = "Loading",
  decorative = false,
  className,
}: {
  label?: string;
  decorative?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <span
      {...(decorative ? { "aria-hidden": true } : { role: "status", "aria-label": label })}
      className={cn("relative inline-block size-[1em] align-middle", className)}>
      {Array.from({ length: DOTS }, (_, index) => {
        const size = `${(0.14 - index * 0.01).toFixed(3)}em`;
        return (
          <motion.span
            key={index}
            aria-hidden="true"
            className="absolute inset-0"
            initial={{ rotate: reduce ? index * -20 : 0 }}
            animate={reduce ? { rotate: index * -20 } : { rotate: 360 }}
            transition={
              reduce
                ? { duration: 0 }
                : { duration: LAP_SECONDS, ease: LAP_EASE, repeat: Infinity, delay: index * 0.075 }
            }
          >
            <span
              className="absolute top-[0.06em] left-1/2 rounded-full bg-current"
              style={{ width: size, height: size, marginLeft: `calc(${size} / -2)`, opacity: 1 - index * 0.13 }}
            />
          </motion.span>
        );
      })}
    </span>
  );
}
