import { EyeOff, Layers, Ruler, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { BlurFade } from "@/components/ui/blur-fade";
import { buttonVariants } from "@/components/ui/button";
import { FULLY_COVERED } from "@/lib/navigation";

/**
 * Ferasha's differentiator, said plainly. Each promise is something the
 * platform actually enforces - keep it that way when editing the copy.
 */
const PROMISES = [
  {
    icon: ShieldCheck,
    title: "Coverage on every piece",
    body: "Sleeves, neckline, back and slit are stated for every garment, with advisories shown, never hidden.",
  },
  {
    icon: Layers,
    title: "Lining, stated not implied",
    body: "Fully lined means fully lined. Sheer overlays and slips are flagged before you buy.",
  },
  {
    icon: EyeOff,
    title: "Faces protected",
    body: "Every photo passes a face-blurring check before it can be published.",
  },
  {
    icon: Ruler,
    title: "Cut to your measurements",
    body: "Choose a standard size or send your own measurements for a bespoke fit.",
  },
] as const;

export function ModestyPromise() {
  return (
    <section aria-labelledby="promise-heading" className="bg-muted/50">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <BlurFade inView>
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">The modesty promise</p>
          <h2 id="promise-heading" className="mt-3 max-w-xl font-display text-display-sm">
            You know exactly what arrives.
          </h2>
        </BlurFade>
        <ul className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {PROMISES.map(({ icon: Icon, title, body }, index) => (
            <li key={title}>
              <BlurFade inView delay={0.08 * index}>
                <Icon aria-hidden="true" className="size-6 text-primary" strokeWidth={1.5} />
                <h3 className="mt-4 font-display text-xl">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </BlurFade>
            </li>
          ))}
        </ul>
        <BlurFade inView delay={0.3}>
          <Link href={FULLY_COVERED.href} className={buttonVariants({ variant: "outline", className: "mt-12" })}>
            {FULLY_COVERED.label}
          </Link>
        </BlurFade>
      </div>
    </section>
  );
}
