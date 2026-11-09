/**
 * The shop's policies, written once and rendered by app/(store)/policies.
 *
 * DRAFTS. Written from what the site actually does (delivery charges,
 * unpaid-order expiry, photo privacy, how GST is added) and from India's
 * Consumer Protection (E-Commerce) Rules 2020 and DPDP Act 2023. They are
 * not legal advice: the atelier must confirm every item in `toConfirm`, and
 * a lawyer should read them before launch. While `toConfirm` is non-empty
 * the page says so, so nothing unconfirmed passes as final.
 */

import { ATELIER } from "@/lib/brand";
import { DELIVERY } from "@/lib/delivery";

export interface PolicySection {
  readonly heading: string;
  readonly paragraphs?: readonly string[];
  readonly items?: readonly string[];
}

export interface Policy {
  readonly slug: string;
  readonly title: string;
  /** One line for the page header and the footer's link title. */
  readonly summary: string;
  readonly updated: string;
  readonly sections: readonly PolicySection[];
  /** Points the atelier has not confirmed yet. Empty means final. */
  readonly toConfirm: readonly string[];
}

const UPDATED = "9 November 2026";
const ADDRESS = ATELIER.addressLines.join(" ");
const CONTACT_LINE = `${ATELIER.name}, ${ADDRESS}. Phone ${ATELIER.phoneDisplay}.`;

export const POLICIES: readonly Policy[] = [
  {
    slug: "shipping",
    title: "Shipping & delivery",
    summary: "Where we deliver, what it costs and how long it takes.",
    updated: UPDATED,
    sections: [
      {
        heading: "Charges",
        items: [
          "Free delivery to any address in Maharashtra.",
          "₹150 to any other address in India, shown in your order total before you pay.",
          DELIVERY.international,
        ],
      },
      {
        heading: "When your order leaves the atelier",
        paragraphs: [
          "Ready-to-wear pieces are dispatched within 3 working days of payment.",
          "Bespoke and made-to-measure pieces are stitched for you after your measurements are confirmed. Each product page states its stitching time; dispatch follows once the garment passes our final quality check.",
        ],
      },
      {
        heading: "Following your order",
        paragraphs: [
          "Your account shows every order and where it is: in the atelier, being stitched, in quality check, packed, shipped and delivered. Once shipped, you will receive the courier's tracking details.",
        ],
      },
      {
        heading: "Unpaid orders",
        paragraphs: [
          "An order that is not paid within 30 minutes of being placed is cancelled automatically, and the pieces are released for other customers.",
        ],
      },
    ],
    toConfirm: [
      "Dispatch time for ready-to-wear pieces (drafted as 3 working days).",
      "Couriers used, and typical delivery times within and outside Maharashtra.",
    ],
  },
  {
    slug: "returns",
    title: "Returns & exchanges",
    summary: "What can be returned, how, and how refunds are paid.",
    updated: UPDATED,
    sections: [
      {
        heading: "Ready-to-wear pieces",
        paragraphs: [
          "You may return an unworn, unwashed piece with its tags attached within 7 days of delivery, for an exchange or a refund.",
        ],
      },
      {
        heading: "If the coverage is not as described",
        paragraphs: [
          "Every product page states its coverage: neckline, sleeves, back, slit, lining and opacity. If what arrives does not match what was stated, return it within 7 days of delivery for a full refund, including delivery charges.",
        ],
      },
      {
        heading: "Bespoke and made-to-measure pieces",
        paragraphs: [
          "Pieces stitched to your measurements cannot be returned for a change of mind. If the garment does not match the measurements you confirmed, or has a defect, we will alter or remake it at no cost.",
        ],
      },
      {
        heading: "How to return",
        items: [
          `Call or message the atelier on ${ATELIER.phoneDisplay} with your order number.`,
          "We arrange collection, or give you the address to send it to.",
          "Refunds are made to the original payment method within 7 working days of the piece reaching us.",
        ],
      },
      {
        heading: "Damaged or wrong item",
        paragraphs: [
          "If a piece arrives damaged or is not what you ordered, tell us within 48 hours of delivery with photographs, and we will replace it or refund you in full.",
        ],
      },
    ],
    toConfirm: [
      "Return window (drafted as 7 days from delivery).",
      "Whether ready-to-wear returns are refunded, exchanged, or either.",
      "The promise to refund in full when coverage differs from the product page.",
      "Who pays return shipping for change-of-mind returns.",
      "Refund timeline (drafted as 7 working days after the piece arrives).",
    ],
  },
  {
    slug: "privacy",
    title: "Privacy",
    summary: "What we collect, why, who sees it and your rights.",
    updated: UPDATED,
    sections: [
      {
        heading: "Who we are",
        paragraphs: [`Ferasha is run by ${CONTACT_LINE}`],
      },
      {
        heading: "What we collect",
        items: [
          "Your account: name, email address and, if you give it, your mobile number.",
          "Your orders: delivery address, what you bought and its status.",
          "For bespoke pieces: the measurements and fit preferences you save, used only to make your garments.",
          "Review photos you choose to upload. Faces are detected and blurred before any photo is published; a photo we cannot make safe is never shown.",
        ],
      },
      {
        heading: "What we do not collect",
        items: [
          "Card or bank details: payments are handled by our payment provider, and we never see or store them.",
          "Advertising or tracking cookies. We use only the cookies needed to keep you signed in.",
        ],
      },
      {
        heading: "Who we share it with",
        items: [
          "The courier delivering your order: name, address and phone number.",
          "Our payment provider, to take your payment.",
          "Tax authorities, as GST law requires for invoices.",
        ],
        paragraphs: ["We do not sell your information, and we do not share it for marketing."],
      },
      {
        heading: "How long we keep it",
        paragraphs: [
          "Order and invoice records are kept for as long as Indian tax law requires. Everything else is kept while your account is open, and deleted when you ask us to close it.",
        ],
      },
      {
        heading: "Your rights",
        paragraphs: [
          "Under the Digital Personal Data Protection Act, 2023 you may ask to see the information we hold about you, correct it, have it erased, or withdraw your consent. Contact our grievance officer (see the Contact page); we will respond within 30 days.",
        ],
      },
    ],
    toConfirm: [
      "The grievance officer's name and email, required by law and shown on the Contact page.",
      "Retention period for order records (GST law: at least 72 months from the annual return's due date).",
      "Review by a lawyer before launch.",
    ],
  },
  {
    slug: "terms",
    title: "Terms of use",
    summary: "The agreement between you and Ferasha when you shop with us.",
    updated: UPDATED,
    sections: [
      {
        heading: "Who you are buying from",
        paragraphs: [`Ferasha is run by ${CONTACT_LINE}`],
      },
      {
        heading: "Your account",
        paragraphs: [
          "Keep your password private. You are responsible for orders placed from your account; tell us at once if you think someone else has used it.",
        ],
      },
      {
        heading: "Products and coverage",
        paragraphs: [
          "We describe every garment's coverage as accurately as we can, including where it is sheer or needs a slip. Handwork and fabric dyes vary slightly between pieces; such variation is part of the craft and not a defect. Colours can look different on different screens.",
        ],
      },
      {
        heading: "Prices and GST",
        paragraphs: [
          "Prices are in Indian rupees. GST is calculated for your delivery address and added at checkout, with delivery, before you pay. The total you confirm is the total you pay.",
        ],
      },
      {
        heading: "Orders",
        paragraphs: [
          "Placing an order is an offer to buy. It is accepted when payment is confirmed. We may cancel an order and refund you in full if a piece turns out to be unavailable or was priced wrongly.",
        ],
      },
      {
        heading: "Bespoke orders",
        paragraphs: [
          "Made-to-measure garments are stitched to the measurements you confirm. Please check them carefully: we will alter or remake a garment that does not match them, but cannot accept returns for a change of mind (see Returns & exchanges).",
        ],
      },
      {
        heading: "Delivery, returns and privacy",
        paragraphs: [
          "Delivery, returns and your personal information are covered by our Shipping & delivery, Returns & exchanges and Privacy pages, which form part of these terms.",
        ],
      },
      {
        heading: "Our content",
        paragraphs: [
          "Designs, photographs and text on this site belong to the atelier and may not be copied for commercial use without permission.",
        ],
      },
      {
        heading: "Complaints and disputes",
        paragraphs: [
          "Please contact our grievance officer first (see the Contact page); we acknowledge complaints within 48 hours and aim to resolve them within one month. These terms are governed by the laws of India, and the courts of Mumbai have jurisdiction.",
        ],
      },
    ],
    toConfirm: [
      "The legal name of the business and its GSTIN, as invoices show them.",
      "Review by a lawyer before launch.",
    ],
  },
];

export function policy(slug: string): Policy | undefined {
  return POLICIES.find((candidate) => candidate.slug === slug);
}

/** The Contact page's own unconfirmed points (the grievance officer is a legal requirement). */
export const CONTACT_TO_CONFIRM: readonly string[] = [
  "The grievance officer's name, designation and email.",
  "An email address for customer care.",
  "Opening hours, and whether fittings are by appointment only.",
  "Whether WhatsApp should be offered alongside the phone number.",
];
