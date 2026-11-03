import { Check, X } from "lucide-react";

import type {
  BackCoverage,
  NecklineModesty,
  ProductDetail,
  SleeveCoverage,
  SlitCoverage,
} from "@/lib/api/types";
import { cn } from "@/lib/cn";

/**
 * Coverage, dimension by dimension: where the garment covers, on a scale from
 * least to most covering, with the exact wording beside it. The scales and
 * labels mirror backend-core catalog/enums.py.
 *
 * The bars are decoration for sighted shoppers; the words carry the meaning,
 * so the bars are hidden from screen readers.
 */
interface Scale<T extends string> {
  readonly label: string;
  readonly order: readonly T[];
  readonly names: Record<T, string>;
}

const NECKLINE: Scale<NecklineModesty> = {
  label: "Neckline",
  order: ["deep", "moderate", "high", "closed"],
  names: { deep: "Deep", moderate: "Moderate", high: "High", closed: "Closed / collared" },
};
const SLEEVES: Scale<SleeveCoverage> = {
  label: "Sleeves",
  order: ["sleeveless", "cap", "short", "elbow", "three_quarter", "full", "extra_long"],
  names: {
    sleeveless: "Sleeveless", cap: "Cap sleeve", short: "Short", elbow: "Elbow length",
    three_quarter: "Three-quarter", full: "Full length", extra_long: "Extra long",
  },
};
const BACK: Scale<BackCoverage> = {
  label: "Back",
  order: ["open", "deep", "moderate", "full"],
  names: { open: "Open", deep: "Deep", moderate: "Moderate", full: "Fully covered" },
};
const SLIT: Scale<SlitCoverage> = {
  label: "Slit",
  order: ["thigh", "knee", "mid_calf", "ankle", "none"],
  names: { thigh: "Thigh-height", knee: "Knee-height", mid_calf: "Mid-calf", ankle: "Ankle-height", none: "No slit" },
};

function Row<T extends string>({ scale, value }: { scale: Scale<T>; value: T }) {
  const rank = scale.order.indexOf(value) + 1;
  return (
    <div className="grid grid-cols-[6rem_1fr] items-center gap-4 py-3">
      <dt className="text-sm text-muted-foreground">{scale.label}</dt>
      <dd className="flex items-center justify-between gap-4">
        <span className="text-sm whitespace-nowrap">{scale.names[value]}</span>
        <span aria-hidden="true" className="flex shrink-0 gap-0.5">
          {scale.order.map((step, index) => (
            <span
              key={step}
              className={cn("h-1.5 w-3 rounded-full", index < rank ? "bg-primary" : "bg-border")}
            />
          ))}
        </span>
      </dd>
    </div>
  );
}

function Fact({ yes, children }: { yes: boolean; children: React.ReactNode }) {
  const Icon = yes ? Check : X;
  return (
    <li className="flex items-center gap-2 text-sm">
      <Icon aria-hidden="true" className={cn("size-4", yes ? "text-primary" : "text-muted-foreground")} />
      <span className={yes ? undefined : "text-muted-foreground"}>{children}</span>
    </li>
  );
}

export function CoverageMap({ product }: { product: ProductDetail }) {
  return (
    <div>
      <dl className="divide-y">
        <Row scale={NECKLINE} value={product.neckline_modesty} />
        <Row scale={SLEEVES} value={product.sleeve_coverage} />
        <Row scale={BACK} value={product.back_coverage} />
        <Row scale={SLIT} value={product.slit_coverage} />
      </dl>
      <ul className="mt-4 grid grid-cols-2 gap-2">
        <Fact yes={product.is_opaque}>{product.is_opaque ? "Opaque fabric" : "Not opaque"}</Fact>
        <Fact yes={product.has_full_lining}>{product.has_full_lining ? "Fully lined" : "Not fully lined"}</Fact>
        <Fact yes={!product.requires_slip}>{product.requires_slip ? "Slip required" : "No slip needed"}</Fact>
        <Fact yes={!product.is_sheer_overlay_only}>
          {product.is_sheer_overlay_only ? "Sheer overlay" : "Not a sheer overlay"}
        </Fact>
      </ul>
    </div>
  );
}
