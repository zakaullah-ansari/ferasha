import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";

import { ProductCard } from "@/components/ProductCard";
import { Badge } from "@/components/ui/badge";
import { BlurFade } from "@/components/ui/blur-fade";
import { Button } from "@/components/ui/button";
import { Lens } from "@/components/ui/lens";
import { Marquee } from "@/components/ui/marquee";
import { ProgressiveBlur } from "@/components/ui/progressive-blur";
import { Skeleton } from "@/components/ui/skeleton";
import { TextAnimate } from "@/components/ui/text-animate";
import type { ProductSummary } from "@/lib/api/types";

import { PRODUCT } from "../../tests/fixtures/commerce";
import suit from "../assets/kausar-lawn-suit.jpg";

/**
 * Motion lab: the shortlisted effects on real Ferasha content, to compare
 * before any of them reaches a live page.
 *
 * Principles: calm, decelerating (--ease-luxury), 0.3-0.7s, small distances,
 * one moment per screen; the garment is the hero. Every JS-driven effect here
 * settles instantly under "reduce motion" (try it in your OS settings).
 *
 * Photo: the owner's own Kausar Dezine Studio flyer, cropped to the garment.
 */
const meta = {
  title: "Motion",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const NAMES = [
  "Karachi Lawn Chikankari - Mint",
  "Organza Overlay Suit - Blush",
  "Velvet Gharara - Emerald",
  "Raw Silk Blouse - Gold",
  "Chanderi Punjabi Suit - Powder Blue",
  "Banarasi Bridal Lehenga - Crimson",
];

const PRODUCTS: ProductSummary[] = NAMES.map((name, index) => ({
  ...PRODUCT,
  id: `motion-${index}`,
  slug: `motion-${index}`,
  name,
  primary_image: suit.src,
}));

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-3">{children}</div>;
}

/**
 * **Product grid reveal** (`@magicui/blur-fade`). Cards fade up softly, one
 * after another, as they scroll into view - the classic editorial reveal.
 * Scroll down; each card animates once.
 */
export const GridReveal: Story = {
  render: () => (
    <div className="space-y-10">
      <BlurFade inView>
        <h2 className="font-display text-display-sm">New this season</h2>
      </BlurFade>
      <Grid>
        {PRODUCTS.map((product, index) => (
          <BlurFade key={product.id} inView delay={0.06 * (index % 3)} duration={0.6} offset={12}>
            <ProductCard product={product} />
          </BlurFade>
        ))}
      </Grid>
    </div>
  ),
};

/**
 * **Hero headline** (`@magicui/text-animate`). The homepage line arrives word
 * by word, once, like a printed title. Screen readers get the whole sentence.
 */
export const HeroHeadline: Story = {
  render: function Render() {
    const [run, setRun] = useState(0);
    return (
      <div className="space-y-8">
        <TextAnimate
          key={`blur-${run}`}
          as="h1"
          by="word"
          animation="blurInUp"
          duration={0.9}
          once
          className="font-display text-display-lg"
        >
          Modest luxury, cut to order.
        </TextAnimate>
        <TextAnimate
          key={`fade-${run}`}
          as="p"
          by="line"
          animation="fadeIn"
          delay={0.5}
          duration={0.8}
          once
          className="max-w-xl text-muted-foreground"
        >
          {"Pakistani and Punjabi suits, bridal lehengas, sharara and gharara.\nEvery garment publishes its coverage honestly."}
        </TextAnimate>
        <Button variant="outline" size="sm" onClick={() => setRun((n) => n + 1)}>
          Replay
        </Button>
      </div>
    );
  },
};

/**
 * **Fabric lens** (`@magicui/lens`) - the "texture-first zoom" from the
 * Sprint 4 plan. Move the pointer over the hem to see the work up close.
 * A desktop enhancement: on phones customers pinch-zoom natively.
 */
export const FabricLens: Story = {
  render: () => (
    <div className="w-80">
      <Lens zoomFactor={2.2} lensSize={180} ariaLabel="Zoom into the fabric">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={suit.src} alt="Mint lawn suit with printed dupatta" className="w-full" />
      </Lens>
    </div>
  ),
};

/** **Card hover**: a slow, slight zoom (already built into ProductCard). */
export const CardHover: Story = {
  render: () => (
    <div className="w-64">
      <ProductCard product={PRODUCTS[0]!} />
    </div>
  ),
};

/**
 * **Announcement strip** (`@magicui/marquee`). Slow and pauses on hover;
 * moving text must be pausable (WCAG 2.2.2), and it stops entirely under
 * reduce motion.
 */
export const AnnouncementStrip: Story = {
  parameters: { layout: "fullscreen" },
  render: () => (
    <div className="border-y bg-muted/50">
      <Marquee pauseOnHover className="py-2 [--duration:60s] [--gap:3rem]">
        {[
          "Free delivery within Maharashtra",
          "Tailored by Kausar Dezine Studio, Kurla",
          "Every garment states its coverage",
          "Bespoke stitching in 10 days",
        ].map((line) => (
          <span key={line} className="text-xs tracking-[0.2em] text-muted-foreground uppercase">
            {line}
          </span>
        ))}
      </Marquee>
    </div>
  ),
};

/**
 * **Progressive blur** (`@magicui/progressive-blur`). Content softens where it
 * scrolls away - premium depth from pure CSS, so very light on phones.
 */
export const EdgeBlur: Story = {
  render: () => (
    <div className="relative h-72 w-80 overflow-hidden rounded-xl border">
      <ul className="h-full space-y-3 overflow-y-auto p-4 pb-16 text-sm">
        {[...NAMES, ...NAMES].map((name, index) => (
          <li key={`${name}-${index}`} className="border-b pb-3">
            {name}
          </li>
        ))}
      </ul>
      <ProgressiveBlur position="bottom" height="30%" />
    </div>
  ),
};

/** **Loading**: calm placeholders (shadcn `skeleton`) instead of spinners. */
export const LoadingGrid: Story = {
  render: () => (
    <Grid>
      {PRODUCTS.map((product) => (
        <div key={product.id} className="space-y-3">
          <Skeleton className="aspect-[4/5] w-full rounded-lg" />
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      ))}
    </Grid>
  ),
};

/**
 * **Added to bag**: the count pops once (`tw-animate-css`, already in the
 * project), so the customer sees the bag change without a toast.
 */
export const BagCountPop: Story = {
  render: function Render() {
    const [count, setCount] = useState(1);
    return (
      <div className="flex items-center gap-6">
        <Button onClick={() => setCount((n) => n + 1)}>Add to bag</Button>
        <span className="relative text-sm">
          Bag
          <Badge
            key={count}
            className="ml-2 tabular-nums animate-in zoom-in-50 fade-in duration-300"
          >
            {count}
          </Badge>
        </span>
      </div>
    );
  },
};
