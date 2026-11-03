import Link from "next/link";

import { ATELIER, TAGLINE } from "@/lib/brand";
import { FULLY_COVERED, OCCASIONS, PRIMARY_NAV } from "@/lib/navigation";

export function SiteFooter() {
  return (
    // `dark` scopes the preset's dark palette to the footer, so the inverted
    // band uses the theme's own contrast-tested pairs rather than hand-picked ones.
    <footer className="dark mt-24 bg-background text-foreground">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 md:grid-cols-[1.4fr_1fr_1fr_1.4fr]">
        <div>
          <p className="font-display text-3xl">Ferasha</p>
          <p className="mt-1 text-sm text-muted-foreground">{TAGLINE}</p>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Modest luxury, cut to order in Mumbai. Every garment publishes its
            coverage so you know what you are buying before it arrives.
          </p>
        </div>

        <FooterColumn title="Shop" links={[...PRIMARY_NAV, FULLY_COVERED]} />
        <FooterColumn title="Occasions" links={OCCASIONS} />

        <div className="text-sm">
          <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">The atelier</p>
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
      <div className="border-t border-border">
        <p className="mx-auto max-w-6xl px-5 py-6 text-xs text-muted-foreground">
          Prices in INR, inclusive of GST where applicable.
        </p>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: readonly { label: string; href: string }[] }) {
  return (
    <div>
      <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">{title}</p>
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
