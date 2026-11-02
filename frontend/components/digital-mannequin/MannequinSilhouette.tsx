import { cn } from "@/lib/cn";

/** Where each measurement is taken, in the silhouette's 200x500 viewBox. */
const MEASUREMENT_POINTS = {
  shoulder: { cx: 100, cy: 92 },
  bust: { cx: 100, cy: 135 },
  waist: { cx: 100, cy: 200 },
  hip: { cx: 100, cy: 250 },
  sleeve: { cx: 72, cy: 160 },
  length: { cx: 100, cy: 470 },
} as const;

export type MeasurementPoint = keyof typeof MEASUREMENT_POINTS;

interface MannequinSilhouetteProps {
  readonly className?: string;
  readonly highlight?: MeasurementPoint;
  /** Shades the neckline-to-bust panel when the garment covers it fully. */
  readonly coveredNeckline?: boolean;
}

export function MannequinSilhouette({ className, highlight, coveredNeckline }: MannequinSilhouetteProps) {
  const point = highlight ? MEASUREMENT_POINTS[highlight] : undefined;
  return (
    <svg viewBox="0 0 200 500" className={cn("h-full w-full", className)} aria-hidden="true">
      <path
        className="fill-muted-foreground/20"
        d="M100,20 C110,20 120,30 120,50 C120,70 110,80 100,80 C90,80 80,70 80,50 C80,30 90,20 100,20 Z
           M80,85 L120,85 L130,150 L120,250 L100,260 L80,250 L70,150 Z
           M70,160 L130,160 L140,300 L120,480 L80,480 L60,300 Z"
      />
      {coveredNeckline && <path className="fill-primary/30" d="M80,85 L120,85 L125,120 L75,120 Z" />}
      {point && <circle {...point} r="5" className="fill-primary motion-safe:animate-pulse" />}
    </svg>
  );
}
