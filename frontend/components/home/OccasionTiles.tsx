import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { BlurFade } from "@/components/ui/blur-fade";
import { cn } from "@/lib/cn";
import { type Occasion, OCCASIONS } from "@/lib/navigation";

/**
 * Shop by occasion. Until the brand shoot arrives each tile is a field of a
 * theme colour; with photography, the image sits beneath the same type.
 */
// Brand palette from globals.css @theme (contrast-tested in
// tests/contrast.test.ts): Kausar green, obsidian ink, champagne gold.
const TONES: Record<Occasion["tone"], string> = {
  primary: "bg-primary text-primary-foreground",
  // In dark mode an ink field would vanish into the page: a raised card instead.
  ink: "bg-ink-900 text-ivory dark:bg-card dark:text-card-foreground dark:ring-1 dark:ring-border",
  gold: "bg-gold-200 text-ink-900",
  muted: "bg-muted text-foreground",
};

export function OccasionTiles() {
  return (
    <section aria-labelledby="occasions-heading" className="mx-auto max-w-6xl px-5 py-16">
      <BlurFade inView>
        <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">Shop by occasion</p>
        <h2 id="occasions-heading" className="mt-3 font-display text-display-sm">
          Dressed for the moment
        </h2>
      </BlurFade>
      <ul className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
        {OCCASIONS.map((occasion, index) => (
          <li key={occasion.href}>
            <BlurFade inView delay={0.08 * index} duration={0.6} offset={12}>
              <Link
                href={occasion.href}
                className={cn(
                  "group flex aspect-[3/4] flex-col justify-between rounded-2xl p-5 transition-[translate,box-shadow] duration-500 ease-luxury hover:-translate-y-1 hover:shadow-2xl hover:shadow-primary/15",
                  TONES[occasion.tone],
                )}
              >
                <ArrowUpRight
                  aria-hidden="true"
                  className="size-5 self-end opacity-60 transition-transform duration-500 ease-luxury group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:opacity-100"
                />
                <span>
                  <span className="block font-display text-3xl">{occasion.label}</span>
                  <span className="mt-1 block text-xs leading-relaxed opacity-80">{occasion.note}</span>
                </span>
              </Link>
            </BlurFade>
          </li>
        ))}
      </ul>
    </section>
  );
}
