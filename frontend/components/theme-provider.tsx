"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * Light and dark mode (next-themes, as the shadcn docs set it up): the `dark`
 * class on <html>, following the device's setting until the shopper picks
 * one, and set by an inline script before first paint so the page never
 * flashes the wrong theme.
 */
export function ThemeProvider(props: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange {...props} />;
}
