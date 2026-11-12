"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

/** Set once the first page has hydrated in this browser tab. */
let hydratedOnce = false;

/**
 * A soft fade between shop pages: opacity only, 250 ms, no sliding.
 *
 * Never on the first page load: content that starts invisible delays the
 * largest paint and reads as a slow site. And never decided on the server:
 * module state there is shared by every visitor, so the server always
 * renders the page fully visible. Under reduced motion, no fade at all.
 *
 * Render only reads the flag; an effect sets it after the first page has
 * committed. React may render a component more than once while hydrating
 * (Strict Mode, an interrupted hydration), and a flag flipped during render
 * made the repeat render fade a page the server sent fully visible.
 */
export default function StoreTemplate({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const [fade] = useState(() => typeof window !== "undefined" && hydratedOnce);
  useEffect(() => {
    hydratedOnce = true;
  }, []);

  return (
    <motion.div
      initial={fade && !reduce ? { opacity: 0 } : false}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
