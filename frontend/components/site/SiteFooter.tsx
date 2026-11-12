import { MapPin, Phone } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { BlurFade } from "@/components/ui/blur-fade";
import { ATELIER, ATELIER_MAPS_HREF, TAGLINE } from "@/lib/brand";
import { FULLY_COVERED, LEGAL, OCCASIONS, PRIMARY_NAV, SUPPORT, type NavLink } from "@/lib/navigation";

/**
 * The site footer, after Housiq's: brand and ways to reach the atelier, link
 * columns under gold headings, a hairline, a quiet bottom bar with the legal
 * links, and the wordmark set huge in a gold fade, running off the bottom edge.
 *
 * `dark` scopes the theme's deep-forest palette to the footer, so the band uses
 * contrast-tested pairs rather than hand-picked ones.
 */
export function SiteFooter() {
  return (
    <footer className="dark relative mt-24 overflow-hidden bg-background text-foreground">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 pt-16 pb-12 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr_1.5fr]">
        <div>
          <p className="font-display text-3xl">Ferasha</p>
          <p className="mt-1 text-sm text-muted-foreground">{TAGLINE}</p>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Modest luxury, cut to order in Mumbai. Every garment publishes its
            coverage so you know what you are buying before it arrives.
          </p>
          <div className="mt-6 flex gap-3">
            <ReachOut href={ATELIER.phoneHref} label={`Call the atelier, ${ATELIER.phoneDisplay}`}>
              <Phone />
            </ReachOut>
            <ReachOut href={ATELIER_MAPS_HREF} label="Directions to the atelier (opens Google Maps)" external>
              <MapPin />
            </ReachOut>
          </div>
        </div>

        <FooterColumn title="Shop" links={[...PRIMARY_NAV, FULLY_COVERED]} />
        <FooterColumn title="Occasions" links={OCCASIONS} />
        <FooterColumn title="Help" links={SUPPORT} />

        <div className="text-sm">
          <FooterHeading>The atelier</FooterHeading>
          <p className="mt-4">
            <span className="font-display text-lg">{ATELIER.name}</span>
            <span className="block text-muted-foreground">{ATELIER.motto}</span>
          </p>
          <address className="mt-3 leading-relaxed not-italic text-muted-foreground">
            {ATELIER.addressLines.map((line) => (
              <span key={line} className="block">{line}</span>
            ))}
            <a href={ATELIER.phoneHref} className="text-foreground underline-offset-4 hover:underline">
              {ATELIER.phoneDisplay}
            </a>
          </address>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5">
        <div className="flex flex-col gap-4 border-t border-border py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} Ferasha · Tailored by {ATELIER.name}. Prices in INR; GST for your
            delivery address is added at checkout, before you pay.
          </p>
          <ul className="flex shrink-0 gap-5">
            {LEGAL.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="transition-colors duration-300 hover:text-foreground">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* The signature: the wordmark, huge, fading from gold into the forest
          and cut by the bottom edge. Decorative; the name is already above. */}
      <BlurFade inView offset={24} duration={0.8} aria-hidden className="pointer-events-none select-none">
        <p className="-mb-[0.22em] bg-linear-to-b from-gold-400/45 via-gold-400/15 to-transparent bg-clip-text text-center font-display text-[clamp(5.5rem,24vw,21rem)] leading-none text-transparent">
          Ferasha
        </p>
      </BlurFade>
    </footer>
  );
}

function FooterHeading({ children }: { children: string }) {
  return <p className="text-xs tracking-[0.2em] text-gold-400 uppercase">{children}</p>;
}

function FooterColumn({ title, links }: { title: string; links: readonly NavLink[] }) {
  return (
    <div>
      <FooterHeading>{title}</FooterHeading>
      <ul className="mt-4 space-y-2 text-sm">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="text-muted-foreground transition-colors duration-300 hover:text-foreground">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** A round icon link, Housiq's social buttons put to the atelier's real channels. */
function ReachOut({
  href,
  label,
  external = false,
  children,
}: {
  href: string;
  label: string;
  external?: boolean;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      aria-label={label}
      {...(external && { target: "_blank", rel: "noopener noreferrer" })}
      className="grid size-10 place-items-center rounded-full bg-muted text-gold-400 transition-colors duration-300 hover:bg-primary hover:text-primary-foreground [&_svg]:size-4"
    >
      {children}
    </a>
  );
}
