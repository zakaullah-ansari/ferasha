import { cn } from "@/lib/cn";
import type { Modesty, ModestyFacet } from "@/lib/api/types";

/**
 * Modesty badges and advisories.
 *
 * The product decision this component encodes: **advisories are never
 * suppressed.** A sheer organza suit says it is sheer, on the listing card and
 * on the product page, before the customer pays. A modest-wear brand that
 * hides a coverage problem until the parcel arrives has sold one garment and
 * lost one customer.
 *
 * Accessibility: meaning is never carried by colour alone. Each item has a
 * text label and an additional screen-reader-only prefix ("Advisory:") so the
 * distinction between a badge and a warning survives in a screen reader and in
 * greyscale.
 */

type Tone = "badge" | "advisory";

const TONE_CLASSES: Record<Tone, string> = {
  // gold-700 on gold-50 — brand gold itself is 2.38:1 and cannot carry text.
  badge: "border-gold-300 bg-gold-50 text-gold-800",
  // The warning hue, which is contrast-tested for body text on ivory.
  advisory: "border-warning/40 bg-warning/8 text-warning",
};

function Pill({ facet, tone }: { facet: ModestyFacet; tone: Tone }) {
  return (
    <li
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
        "text-xs leading-none font-medium tracking-wide",
        TONE_CLASSES[tone],
      )}
      data-testid={`modesty-${tone}`}
      data-code={facet.code}
    >
      <span aria-hidden="true" className="text-[0.6rem]">
        {tone === "badge" ? "\u25C6" : "\u25B2"}
      </span>
      <span className="sr-only">
        {tone === "badge" ? "Modesty feature: " : "Advisory: "}
      </span>
      {facet.label}
    </li>
  );
}

export function ModestyBadgeList({
  modesty,
  className,
  /** Listing cards show a condensed set; the product page shows everything. */
  limit,
}: {
  modesty: Modesty;
  className?: string;
  limit?: number;
}) {
  const badges = limit ? modesty.badges.slice(0, limit) : modesty.badges;

  // Advisories are *never* truncated, even when badges are. Hiding a caveat
  // to fit a card layout is precisely the failure this component prevents.
  const advisories = modesty.advisories;

  const hidden = modesty.badges.length - badges.length;

  if (badges.length === 0 && advisories.length === 0) return null;

  return (
    <ul
      className={cn("flex flex-wrap items-center gap-1.5", className)}
      aria-label="Modesty and coverage information"
    >
      {advisories.map((facet) => (
        <Pill key={facet.code} facet={facet} tone="advisory" />
      ))}
      {badges.map((facet) => (
        <Pill key={facet.code} facet={facet} tone="badge" />
      ))}
      {hidden > 0 && (
        <li className="text-xs text-ink-600">+{hidden} more</li>
      )}
    </ul>
  );
}

/**
 * Coverage score, 0–100, as derived by the backend.
 *
 * Rendered as a number with an explicit label rather than a bare progress bar:
 * a bar implies "higher is better" universally, when in fact the right score
 * depends entirely on the occasion and the customer.
 */
export function CoverageScore({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const band = score >= 70 ? "high" : score >= 40 ? "moderate" : "low";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-xs tracking-wide text-ink-600 uppercase">Coverage</span>
      <span
        className="font-display text-base text-ink-900 tabular-nums"
        data-testid="coverage-score"
      >
        {score}
        <span className="text-ink-500 text-xs">/100</span>
      </span>
      {/* The band gives the number meaning without implying a value judgement. */}
      <span className="sr-only">{`${band} coverage`}</span>
      <span
        aria-hidden="true"
        className="h-1 w-16 overflow-hidden rounded-full bg-ink-200"
      >
        <span
          className="block h-full rounded-full bg-gold-600"
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </span>
    </div>
  );
}
