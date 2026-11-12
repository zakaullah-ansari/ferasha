import type { Metadata } from "next";

import { ThemeProvider } from "@/components/theme-provider";
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
  // The browser bar takes the page ground: mint in light, forest in dark.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafdfb" },
    { media: "(prefers-color-scheme: dark)", color: "#041b12" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: next-themes sets the class on <html> before
    // React hydrates (only this element's attributes are exempted).
    <html lang="en-IN" className={fontVariables} suppressHydrationWarning>
      {/* relative: the drawer positions correctly on iOS Safari (shadcn drawer docs). */}
      <body className="relative min-h-dvh bg-background text-foreground antialiased">
        {/* Skip link: the first tab stop on every page. */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to content
        </a>
        {/* Each route group brings its own chrome and its <main id="main">. */}
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
