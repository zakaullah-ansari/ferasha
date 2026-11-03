import Link from "next/link";

import { HeaderActions } from "@/components/HeaderActions";
import { Marquee } from "@/components/ui/marquee";
import { ANNOUNCEMENTS, PRIMARY_NAV } from "@/lib/navigation";

import { MobileNav } from "./MobileNav";

/**
 * Announcement strip + sticky header: categories left, wordmark centred,
 * account and bag right. The strip scrolls slowly, pauses on hover (moving
 * text must be pausable) and stops under reduce-motion via the global rule.
 */
export function SiteHeader() {
  return (
    <>
      <div className="border-b border-border/60 bg-muted/60">
        <Marquee pauseOnHover className="mx-auto max-w-6xl py-1.5 [--duration:60s] [--gap:3rem]">
          {ANNOUNCEMENTS.map((line) => (
            <span key={line} className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">
              {line}
            </span>
          ))}
        </Marquee>
      </div>
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-md">
        <nav
          aria-label="Primary"
          className="mx-auto grid max-w-6xl grid-cols-[1fr_auto_1fr] items-center px-5 py-3"
        >
          <div className="flex items-center">
            <MobileNav />
            <ul className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
              {PRIMARY_NAV.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="transition-colors duration-300 hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <Link href="/" className="font-display text-3xl tracking-tight text-foreground">
            Ferasha
          </Link>
          <div className="flex justify-end">
            <HeaderActions />
          </div>
        </nav>
      </header>
    </>
  );
}
