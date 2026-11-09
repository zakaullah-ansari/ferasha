/**
 * What the shop can promise, stated once: the trust strip, the hero and the
 * announcement bar all read from here. Only what the site already does -
 * nothing about returns (the policy is still a draft) or payment security
 * (there is no payment step yet).
 */

import { ATELIER } from "@/lib/brand";
import { DELIVERY } from "@/lib/delivery";

export type TrustPointId = "coverage" | "tailored" | "bespoke" | "delivery";

export interface TrustPoint {
  readonly id: TrustPointId;
  readonly title: string;
  readonly detail: string;
}

export const TRUST_POINTS: readonly TrustPoint[] = [
  {
    id: "coverage",
    title: "Coverage stated on every piece",
    detail: "Neckline, sleeves, back, slit, lining and opacity, before you buy",
  },
  { id: "tailored", title: "Tailored in Kurla", detail: `Cut and stitched by ${ATELIER.name}` },
  { id: "bespoke", title: "Made to your measurements", detail: "Checked by the atelier before any cloth is cut" },
  { id: "delivery", title: DELIVERY.home, detail: DELIVERY.elsewhere },
];
