"use client";

import { useReducedMotion } from "motion/react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { buttonVariants } from "@/components/ui/button";

const subscribe = () => () => {};

/**
 * The header's light/dark switch (Magic UI's animated theme toggler, driven
 * by next-themes): the new theme spreads out in a circle from the button,
 * as on Aeron. It switches instantly for anyone who has turned motion off.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const reduceMotion = useReducedMotion();
  // The theme is only known in the browser; until then render as light so
  // the server and first client render agree.
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const theme = mounted && resolvedTheme === "dark" ? "dark" : "light";

  return (
    <AnimatedThemeToggler
      theme={theme}
      onThemeChange={setTheme}
      duration={reduceMotion ? 0 : 500}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className={buttonVariants({ variant: "ghost", size: "icon" })}
    />
  );
}
