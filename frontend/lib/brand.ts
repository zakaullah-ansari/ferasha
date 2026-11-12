/**
 * The atelier behind Ferasha, as the owner's own materials state it.
 * One definition so the footer, product pages and order pages never disagree.
 */
export const ATELIER = {
  name: "Kausar Dezine Studio",
  motto: "Fashion with Dignity",
  addressLines: [
    "Shop No. C/01, 187, Al-Shams Apt., near Karthika High School,",
    "New Hall Road, Kurla (W), Mumbai 400070",
  ],
  phoneDisplay: "+91 98199 95222",
  phoneHref: "tel:+919819995222",
} as const;

/** Directions to the atelier: a Maps search for its published address. */
export const ATELIER_MAPS_HREF = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  `${ATELIER.name}, ${ATELIER.addressLines.join(" ")}`,
)}`;

export const TAGLINE = "Discover your ethnic wardrobe";
