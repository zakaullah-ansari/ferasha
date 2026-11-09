import localFont from "next/font/local";

/**
 * The storefront's two typefaces, defined once for the app and for Storybook.
 *
 * Shipped with the site (app/fonts, from Fontsource 5.3.0, SIL Open Font
 * Licence 1.1 - licences alongside) rather than fetched from Google at
 * build time: building and the dev server no longer depend on reaching
 * fonts.googleapis.com, which had failed and taken pages down with it.
 * Still preloaded, swapped and size-adjusted by next/font: no layout shift.
 */
export const display = localFont({
  src: [
    { path: "../app/fonts/cormorant-garamond-latin-300-normal.woff2", weight: "300", style: "normal" },
    { path: "../app/fonts/cormorant-garamond-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../app/fonts/cormorant-garamond-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../app/fonts/cormorant-garamond-latin-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-display-serif",
  display: "swap",
  fallback: ["Georgia", "Times New Roman", "serif"],
});

export const ui = localFont({
  // Inter's variable font: every weight from one file.
  src: "../app/fonts/inter-latin-wght-normal.woff2",
  weight: "100 900",
  variable: "--font-ui-sans",
  display: "swap",
  fallback: ["system-ui", "Segoe UI", "Arial", "sans-serif"],
});

/** Class names that expose both fonts as the CSS variables globals.css reads. */
export const fontVariables = `${display.variable} ${ui.variable}`;
