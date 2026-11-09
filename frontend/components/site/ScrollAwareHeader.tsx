"use client";

import { motion, useMotionValueEvent, useReducedMotion, useScroll } from "motion/react";
import { useRef, useState } from "react";

/** Below this many pixels the header always shows: the top of a page is where it belongs. */
const REVEAL_ZONE = 120;
/** Ignore smaller movements, so trackpad jitter cannot make it flicker. */
const MIN_MOVE = 4;

/**
 * The sticky header steps aside while the shopper reads down a page, giving
 * the photography the screen, and returns the moment they scroll up. It
 * never hides while keyboard focus is inside it. Under reduced motion it
 * switches without sliding.
 */
export function ScrollAwareHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  const { scrollY } = useScroll();
  const reduce = useReducedMotion();
  const [hidden, setHidden] = useState(false);
  const [focused, setFocused] = useState(false);
  // The last position this header acted on (scrollY.getPrevious() is per
  // animation frame, so an instant jump compares against a stale value).
  const last = useRef(0);

  useMotionValueEvent(scrollY, "change", (current) => {
    const moved = current - last.current;
    if (Math.abs(moved) < MIN_MOVE) return;
    last.current = current;
    setHidden(current > REVEAL_ZONE && moved > 0);
  });

  return (
    <motion.header
      className={className}
      animate={{ y: hidden && !focused ? "-100%" : "0%" }}
      transition={reduce ? { duration: 0 } : { duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      onFocusCapture={() => setFocused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocused(false);
      }}
    >
      {children}
    </motion.header>
  );
}
