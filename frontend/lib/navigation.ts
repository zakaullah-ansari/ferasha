/**
 * Storefront navigation and merchandising entry points, defined once for the
 * header, the mobile menu, the homepage and the footer.
 *
 * Every link targets a filter the catalogue API supports (category slugs,
 * occasion, modesty facets), so none of them can lead to an empty page by
 * construction - only by an empty catalogue.
 */

import { ATELIER } from "@/lib/brand";
import { DELIVERY } from "@/lib/delivery";

export interface NavLink {
  readonly label: string;
  readonly href: string;
}

export const PRIMARY_NAV: readonly NavLink[] = [
  { label: "Suits", href: "/products?category=suits" },
  { label: "Bridal", href: "/products?category=bridal" },
  { label: "Sharara & Gharara", href: "/products?category=sharara-gharara" },
  { label: "Bespoke", href: "/products?supports_bespoke=true" },
];

/** The header's category links, with their catalogue slug: the homepage tabs. */
export const CATEGORY_NAV: readonly (NavLink & { readonly category: string })[] = PRIMARY_NAV.flatMap((link) => {
  const category = new URLSearchParams(link.href.split("?")[1]).get("category");
  return category ? [{ ...link, category }] : [];
});

export interface Occasion extends NavLink {
  readonly note: string;
  /** Tone of the tile until photography arrives; a theme token, not a colour. */
  readonly tone: "primary" | "ink" | "gold" | "muted";
}

export const OCCASIONS: readonly Occasion[] = [
  { label: "Bridal", href: "/products?occasion=bridal", note: "Lehengas and gharara for the day itself", tone: "primary" },
  { label: "Nikah", href: "/products?occasion=nikah", note: "Quiet grandeur for the ceremony", tone: "ink" },
  { label: "Eid", href: "/products?occasion=eid", note: "Festive suits, fully lined", tone: "gold" },
  { label: "Everyday", href: "/products?occasion=casual", note: "Lawn and cotton for every day", tone: "muted" },
];

/** Customer-care links, the footer's Help column. */
export const SUPPORT: readonly NavLink[] = [
  { label: "Contact", href: "/contact" },
  { label: "Shipping & delivery", href: "/policies/shipping" },
  { label: "Returns & exchanges", href: "/policies/returns" },
];

/** Legal pages, in the footer's bottom bar. */
export const LEGAL: readonly NavLink[] = [
  { label: "Privacy", href: "/policies/privacy" },
  { label: "Terms of use", href: "/policies/terms" },
];

/** Every help page; they live in lib/policies.ts and app/(store)/contact. */
export const HELP: readonly NavLink[] = [...SUPPORT, ...LEGAL];

/**
 * Either side of the announcement strip. "Track order" is the order history in
 * My account (sign-in first); there is no guest order lookup yet.
 */
export const UTILITY_LINKS: readonly [NavLink, NavLink] = [
  { label: "Track order", href: "/account" },
  { label: "Contact", href: "/contact" },
];

/** Shortcut into the catalogue's strongest modesty filter. */
export const FULLY_COVERED: NavLink = { label: "Shop fully covered", href: "/products?fully_covered=true" };

export const ANNOUNCEMENTS: readonly string[] = [
  DELIVERY.home,
  `Tailored by ${ATELIER.name}, Kurla`,
  "Every garment states its coverage",
  "Bespoke fittings by appointment",
];
