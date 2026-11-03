import Image from "next/image";
import Link from "next/link";

import { BlurFade } from "@/components/ui/blur-fade";
import { buttonVariants } from "@/components/ui/button";
import { ATELIER } from "@/lib/brand";
import kausarMark from "@/public/images/kausar-mark.png";

/**
 * The atelier behind Ferasha. Copy states only what the owner's own materials
 * say (tailoring, Kurla, "Fashion with Dignity"); have the owner review it.
 * The mark is an interim raster until the vector artwork arrives.
 */
export function AtelierStory() {
  return (
    <section aria-labelledby="atelier-heading" className="mx-auto max-w-6xl px-5 py-20">
      <div className="grid items-center gap-12 rounded-[2rem] border bg-card px-6 py-14 md:grid-cols-[auto_1fr] md:px-16">
        <BlurFade inView className="mx-auto">
          <Image src={kausarMark} alt="" className="h-48 w-auto md:h-64" sizes="120px" />
        </BlurFade>
        <BlurFade inView delay={0.15}>
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">The atelier</p>
          <h2 id="atelier-heading" className="mt-3 font-display text-display-sm">
            Tailored by {ATELIER.name}
          </h2>
          <p className="mt-2 font-display text-xl text-primary italic">{ATELIER.motto}</p>
          <p className="mt-6 max-w-xl leading-relaxed text-muted-foreground">
            Ferasha&apos;s garments are tailored at Kausar Dezine Studio in Kurla, Mumbai.
            Choose a standard size, or send your measurements and have a piece cut
            to you - and if you would rather be measured in person, visit the atelier.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href={ATELIER.phoneHref} className={buttonVariants({ size: "lg" })}>
              Call the atelier
            </a>
            <Link
              href="/products?supports_bespoke=true"
              className={buttonVariants({ size: "lg", variant: "outline" })}
            >
              Explore bespoke
            </Link>
          </div>
        </BlurFade>
      </div>
    </section>
  );
}
