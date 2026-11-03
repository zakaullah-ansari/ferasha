/**
 * Storefront navigation and merchandising entry points, defined once for the
 * header, the mobile menu, the homepage and the footer.
 *
 * Every link targets a filter the catalogue API supports (category slugs,
 * occasion, modesty facets), so none of them can lead to an empty page by
 * construction - only by an empty catalogue.
 */

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

/** Shortcut into the catalogue's strongest modesty filter. */
export const FULLY_COVERED: NavLink = { label: "Shop fully covered", href: "/products?fully_covered=true" };

export const ANNOUNCEMENTS: readonly string[] = [
  "Free delivery within Maharashtra",
  "Tailored by Kausar Dezine Studio, Kurla",
  "Every garment states its coverage",
  "Bespoke fittings by appointment",
];
