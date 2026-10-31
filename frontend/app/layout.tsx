import type { Metadata } from "next";
import { Cormorant_Garamond, Inter } from "next/font/google";

import "./globals.css";

/**
 * Self-hosted via next/font: no third-party font CDN, no render-blocking
 * request to fonts.googleapis.com, and no layout shift.
 */
const display = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-display-serif",
  display: "swap",
});

const ui = Inter({
  subsets: ["latin"],
  variable: "--font-ui-sans",
  display: "swap",
});

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
    <html lang="en-IN" className={`${display.variable} ${ui.variable}`}>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        {/* Skip link: the first tab stop on every page. */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to content
        </a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/90 backdrop-blur">
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4"
      >
        <a href="/" className="font-display text-2xl tracking-tight text-foreground">
          Ferasha
        </a>
        <ul className="flex items-center gap-6 text-sm text-muted-foreground">
          <li><a href="/products" className="hover:text-foreground">Collection</a></li>
          <li><a href="/products?supports_bespoke=true" className="hover:text-foreground">Bespoke</a></li>
        </ul>
      </nav>
    </header>
  );
}

function SiteFooter() {
  return (
    // `dark` scopes the preset's dark palette to the footer, so the inverted
    // band uses the theme's own contrast-tested pairs rather than hand-picked ones.
    <footer className="dark mt-24 bg-background text-foreground">
      <div className="mx-auto max-w-6xl px-5 py-12">
        <p className="font-display text-xl">Ferasha</p>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
          Modest luxury, cut to order in Mumbai. Every garment publishes its
          coverage so you know what you are buying before it arrives.
        </p>
        <p className="mt-6 text-xs text-muted-foreground">
          Prices in INR, inclusive of GST where applicable.
        </p>
      </div>
    </footer>
  );
}
