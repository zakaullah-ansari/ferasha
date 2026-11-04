import type { Metadata } from "next";

import { fontVariables } from "@/lib/fonts";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Ferasha — Modest Luxury Atelier",
    template: "%s · Ferasha",
  },
  description:
    "Pakistani and Punjabi suits, bridal lehengas, sharara and gharara, with bespoke tailoring. Every garment states its coverage honestly.",
  metadataBase: new URL("https://www.ferasha.com"),
  openGraph: { type: "website", locale: "en_IN", siteName: "Ferasha" },
};

export const viewport = {
  // The preset's --foreground, oklch(0.153 0.006 107.1), in sRGB.
  themeColor: "#0c0c09",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN" className={fontVariables}>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        {/* Skip link: the first tab stop on every page. */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to content
        </a>
        {/* Each route group brings its own chrome and its <main id="main">. */}
        {children}
      </body>
    </html>
  );
}
