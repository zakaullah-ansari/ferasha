import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { ProductDetail } from "@/lib/api/types";
import { ATELIER } from "@/lib/brand";
import { DELIVERY } from "@/lib/delivery";
import { formatINR } from "@/lib/format";

import { CoverageMap } from "./CoverageMap";

const label = (value: string) => value.replace(/_/g, " ");

/**
 * Everything below the buy button, folded. Coverage opens by default: for
 * this audience it is the deciding detail, not small print.
 */
export function ProductDetails({ product }: { product: ProductDetail }) {
  return (
    <Accordion multiple defaultValue={["coverage"]} className="border-t">
      <AccordionItem value="coverage">
        <AccordionTrigger>Coverage, in detail</AccordionTrigger>
        <AccordionContent>
          <CoverageMap product={product} />
        </AccordionContent>
      </AccordionItem>

      {product.description && (
        <AccordionItem value="description">
          <AccordionTrigger>Description</AccordionTrigger>
          <AccordionContent className="leading-relaxed text-muted-foreground">
            {product.description}
          </AccordionContent>
        </AccordionItem>
      )}

      <AccordionItem value="fabric">
        <AccordionTrigger>Fabric &amp; care</AccordionTrigger>
        <AccordionContent>
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            {(
              [
                ["Fabric", product.fabric],
                ["Work", product.work_type],
                ["Occasion", product.occasion],
                ["Garment", product.garment_type],
              ] as const
            ).map(([term, value]) => (
              <div key={term}>
                <dt className="text-xs tracking-wide text-muted-foreground uppercase">{term}</dt>
                <dd className="mt-0.5 capitalize">{label(value)}</dd>
              </div>
            ))}
          </dl>
          {product.care_instructions && (
            <p className="mt-4 text-sm text-muted-foreground">{product.care_instructions}</p>
          )}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="delivery">
        <AccordionTrigger>Delivery</AccordionTrigger>
        <AccordionContent className="space-y-2 text-sm text-muted-foreground">
          <p>{DELIVERY.summary}.</p>
          <p>{DELIVERY.international}</p>
          <p>
            Questions? Call {ATELIER.name} on{" "}
            <a href={ATELIER.phoneHref} className="text-foreground underline underline-offset-4">
              {ATELIER.phoneDisplay}
            </a>
            .
          </p>
        </AccordionContent>
      </AccordionItem>

      {product.supports_bespoke && (
        <AccordionItem value="bespoke">
          <AccordionTrigger>Bespoke tailoring</AccordionTrigger>
          <AccordionContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Cut to your own measurements by {ATELIER.name}
              {Number(product.bespoke_surcharge) > 0 && <> for an additional {formatINR(product.bespoke_surcharge)}</>}.
              Stitching takes {product.stitching_days} days.
            </p>
            <p>Choose &ldquo;Bespoke&rdquo; in Select your fit to enter your measurements.</p>
          </AccordionContent>
        </AccordionItem>
      )}
    </Accordion>
  );
}
