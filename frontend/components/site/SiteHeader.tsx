import Link from "next/link";

import { HeaderActions } from "@/components/HeaderActions";
import { Marquee } from "@/components/ui/marquee";
import { ANNOUNCEMENTS, type NavLink, UTILITY_LINKS } from "@/lib/navigation";

import { MobileNav } from "./MobileNav";
import { PrimaryNavLinks } from "./PrimaryNavLinks";
import { ScrollAwareHeader } from "./ScrollAwareHeader";
import { SearchDialog } from "./SearchDialog";
import { ThemeToggle } from "./ThemeToggle";

/**
 * Announcement strip + a floating pill header after Housiq's (it steps aside
 * while reading down a page, see ScrollAwareHeader): categories left,
 * wordmark centred, account and bag right. The pill is frosted, so the page
 * shows faintly through it and around it. The strip scrolls slowly, pauses on hover (moving
 * text must be pausable) and stops under reduce-motion via the global rule.
 */
export function SiteHeader() {
  return (
    <>
      {/* Utility links either side of the strip from tablet up (after the
          reference stores); on phones the strip has the width to itself. */}
      <div className="border-b border-border/60 bg-muted/60">
        <div className="mx-auto flex max-w-6xl items-center gap-4 md:px-5">
          <UtilityLink link={UTILITY_LINKS[0]} />
          <Marquee pauseOnHover className="min-w-0 flex-1 py-1.5 [--duration:60s] [--gap:3rem]">
            {ANNOUNCEMENTS.map((line) => (
              <span key={line} className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">
                {line}
              </span>
            ))}
          </Marquee>
          <UtilityLink link={UTILITY_LINKS[1]} />
        </div>
      </div>
      <ScrollAwareHeader className="sticky top-0 z-30 h-header px-3 py-3 sm:px-4">
        <nav
          aria-label="Primary"
          className="mx-auto grid max-w-6xl grid-cols-[1fr_auto_1fr] h-full items-center rounded-full border border-primary/10 bg-background/90 pr-2 pl-3 shadow-lg shadow-primary/5 backdrop-blur-xl sm:pl-6"
        >
          <div className="flex items-center">
            <MobileNav />
            <PrimaryNavLinks />
          </div>
          <Link href="/" className="font-display text-3xl tracking-tight text-foreground">
            Ferasha
          </Link>
          <div className="flex items-center justify-end gap-1">
            <SearchDialog />
            <ThemeToggle />
            <HeaderActions />
          </div>
        </nav>
      </ScrollAwareHeader>
    </>
  );
}

function UtilityLink({ link }: { readonly link: NavLink }) {
  return (
    <Link
      href={link.href}
      className="hidden shrink-0 py-1.5 text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase underline-offset-4 transition-colors duration-300 hover:text-foreground hover:underline md:block"
    >
      {link.label}
    </Link>
  );
}
