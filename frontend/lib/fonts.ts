import { Cormorant_Garamond, Inter } from "next/font/google";

/**
 * The storefront's two typefaces, defined once for the app and for Storybook.
 *
 * Self-hosted via next/font: no third-party font CDN, no render-blocking
 * request to fonts.googleapis.com, and no layout shift.
 */
export const display = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-display-serif",
  display: "swap",
});

export const ui = Inter({
  subsets: ["latin"],
  variable: "--font-ui-sans",
  display: "swap",
});

/** Class names that expose both fonts as the CSS variables globals.css reads. */
export const fontVariables = `${display.variable} ${ui.variable}`;
