import Image from "next/image";
import Link from "next/link";

import { BlurFade } from "@/components/ui/blur-fade";
import { buttonVariants } from "@/components/ui/button";
import { TextAnimate } from "@/components/ui/text-animate";
import { ATELIER } from "@/lib/brand";
import { cn } from "@/lib/cn";
import { GLASS } from "@/lib/glass";
import heroImage from "@/public/images/hero-interim.jpg";

/**
 * Homepage hero: headline left, garment right.
 *
 * Only the text animates. The photo is the page's LCP element, so it is never
 * faded in from transparent (that would delay LCP); next/image's blur-up
 * placeholder gives the soft reveal at no cost.
 *
 * Interim photo: the owner's own flyer, until the brand shoot arrives.
 */
export function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-10 md:grid-cols-[1.1fr_0.9fr] md:pt-16">
      <div>
        <BlurFade>
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">Modest luxury · Mumbai</p>
        </BlurFade>
        <TextAnimate
          as="h1"
          by="word"
          animation="blurInUp"
          duration={0.9}
          once
          startOnView={false}
          className="mt-5 font-display text-display-lg leading-[1.02]"
        >
          Modest luxury, cut to order.
        </TextAnimate>
        <BlurFade delay={0.5}>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-muted-foreground">
            Pakistani and Punjabi suits, bridal lehengas, sharara and gharara. Every
            garment publishes its coverage honestly, so you know exactly what arrives.
          </p>
        </BlurFade>
        <BlurFade delay={0.65}>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/products" className={buttonVariants({ size: "lg" })}>
              Shop the collection
            </Link>
            <a href={ATELIER.phoneHref} className={buttonVariants({ size: "lg", variant: "sweep" })}>
              Book a bespoke fitting
            </a>
          </div>
        </BlurFade>
        <BlurFade delay={0.8}>
          <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
            <li>Coverage stated on every piece</li>
            <li>Fully lined options</li>
            <li>Free delivery in Maharashtra</li>
          </ul>
        </BlurFade>
      </div>

      <div className="relative">
        <div className="relative aspect-[4/5] overflow-hidden rounded-[2rem] bg-muted">
          <Image
            src={heroImage}
            alt="Mint lawn suit with a printed dupatta"
            placeholder="blur"
            priority
            fill
            sizes="(min-width: 768px) 40vw, 100vw"
            className="object-cover"
          />
        </div>
        <BlurFade delay={1} className="absolute -bottom-6 left-6 right-6 md:-left-10 md:right-auto">
          <div className={cn("rounded-2xl px-5 py-4", GLASS.float)}>
            <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">Tailored by</p>
            <p className="mt-1 font-display text-lg">{ATELIER.name}</p>
          </div>
        </BlurFade>
      </div>
    </section>
  );
}
