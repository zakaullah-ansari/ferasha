# Phase 4 — Frontend Foundation & Design System

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phase 2 (API + generated client) |
| **Runs parallel to** | Phase 3 |
| **Blocks** | Phase 5 |
| **Effort** | 34–42 hrs |

---

## 1. Objective

A Next.js 15 storefront that feels like a luxury atelier rather than a generic template, is fast on a mid-range Android phone over 4G in Mumbai, and is fully operable by keyboard and screen reader.

---

## 2. Design system

### 2.1 Colour

The brief specifies three tokens. **Three hexes are not a design system** — you need tonal ramps for hover, active, disabled, borders, and focus rings, and you need to verify contrast.

| Token | Hex | Role |
|---|---|---|
| `ferasha-gold` | `#C5A059` | Accent, CTAs, dividers, active states |
| `ferasha-obsidian` | `#1A1A1A` | Primary text, footer, overlays |
| `ferasha-ivory` | `#FDFBF7` | Page background, cards |

Each expands to a 50–900 ramp. Plus semantic tokens: success, warning, danger, info — a luxury palette still needs to render an error state legibly.

**Contrast is a hard constraint.** Gold `#C5A059` on ivory `#FDFBF7` is roughly **2.3:1** — it fails WCAG AA (4.5:1) for body text. Gold is therefore restricted to large display text, borders, and decorative use; body copy uses obsidian on ivory (~15:1). Verified in CI with an automated contrast check, not by eye.

### 2.2 Typography

- **Display** — a high-contrast serif for headings, which is where the luxury signal lives
- **Body/UI** — a clean sans with excellent Devanagari and Urdu-adjacent glyph coverage
- Fluid type scale via `clamp()`
- `next/font` with subsetting and `font-display: swap` — self-hosted, no third-party font CDN

### 2.3 Motion

Framer Motion, restrained. Luxury reads as *calm*. 200–300 ms, ease-out. **`prefers-reduced-motion` respected throughout** — non-negotiable, not an afterthought.

---

## 3. The FitDrawer component

The signature interaction of the site, and the one specified in the original brief.

### 3.1 Behaviour

Slide-out drawer with two modes:

- **Standard** — XS · S · M · L · XL · XXL, with a size chart and fit-feedback data from Phase 1 reviews
- **Bespoke** — bust, waist, hip, kameez length, sleeve length, **farshi flare**, plus a full-lining toggle and sleeve-type selector

### 3.2 Requirements

| Concern | Implementation |
|---|---|
| Validation | Zod schema mirroring the Phase 1 plausibility ranges — the *same* numbers, ideally generated from the OpenAPI schema |
| Units | cm ⇄ inch toggle, converting live without precision loss |
| Persistence | Draft to `localStorage`; saved profiles to the Phase 2 API |
| Focus | Trapped inside the drawer while open; restored to the trigger on close |
| Keyboard | `Esc` closes; full tab traversal; visible focus rings |
| ARIA | `role="dialog"`, `aria-modal="true"`, labelled by its heading |
| Scroll | Body scroll locked without layout shift |
| Mobile | Bottom sheet under 768 px, side drawer above |
| Errors | Inline, adjacent to the field, announced via `aria-live` |

### 3.3 Why validation ranges must be shared

If the frontend accepts a bust of 400 and the backend rejects it, the customer sees an opaque failure after filling a long form. If the frontend accepts it and the backend *doesn't* validate, a tailor cuts an unusable garment. Single source of truth, generated.

---

## 4. Rendering strategy

| Route | Strategy | Why |
|---|---|---|
| Home, category, product | **Server Components + ISR** | SEO-critical, cacheable, fast first paint |
| Search / faceted filter | Server Component + streaming | Facet counts server-side |
| FitDrawer, cart, checkout | Client Components | Genuinely interactive |
| Account, orders | Server Component, auth-gated | Never cache personal data |

Client JS budget: **< 120 KB gzipped** on the product page. Enforced in CI with a bundle-size gate.

---

## 5. Imagery

Ferasha is a visual business; images are the product. They are also the main performance threat.

- `next/image` with AVIF → WebP → JPEG fallback
- Responsive `srcset` sized to real breakpoints
- LQIP blur placeholders
- **Only Phase 3 `APPROVED` derivatives are ever rendered** — the component takes an approved-asset type, so an unapproved original is a *compile-time* error, not a runtime check
- Zoom/lightbox for fabric detail — essential for a fabric-led purchase
- Lazy loading below the fold; hero image preloaded

---

## 6. PWA

Manifest, installability, offline shell, and an offline-viewable saved fit profile — genuinely useful when a customer is standing in a tailor's shop with poor signal.

Service worker caches the app shell and catalogue reads. **Never** caches authenticated responses.

---

## 7. Accessibility

Target: **WCAG 2.2 AA**.

- axe-core in CI, zero critical violations
- Full keyboard journey: browse → filter → FitDrawer → add to cart → checkout
- Screen-reader labels on every control; modesty badges have text alternatives, never colour alone
- Minimum 44×44 px touch targets
- Tested at 200% zoom

---

## 8. Deliverables

Status as of 2026-10-26 — shipped in `82c2d78`.

| Deliverable | Status |
|---|---|
| Full token system with ramps | ✅ `lib/design/tokens.ts` + `@theme` in `app/globals.css`. **No `tailwind.config.ts`** — see note below. |
| `app/layout.tsx`, fonts, global styles | ✅ |
| `components/FitDrawer.tsx` + sub-components | ✅ built on `vaul`; 22 tests |
| `components/ModestyBadge.tsx` | ✅ |
| `components/ProductCard.tsx` | ✅ |
| `components/ProductGallery.tsx` | ⬜ not started |
| `components/FacetFilter.tsx` | ⬜ not started |
| `lib/api/` typed client + wrappers | ✅ `client.ts`, `types.ts`, `fit-schema.ts` |
| `lib/units.ts` — cm/inch, tested | ✅ 50 tests |
| PWA manifest + service worker | ⬜ not started — `frontend/public/` does not exist |
| Playwright E2E for the FitDrawer journey | ⬜ not started — only Vitest/jsdom coverage exists |

Also shipped, beyond the original list: `components/ProductPurchasePanel.tsx`, `app/products/page.tsx`, `app/products/[slug]/page.tsx`, and `tests/tokens-sync.test.ts`, which fails if `globals.css` drifts from the contrast-tested tokens.

**On the absent `tailwind.config.ts`:** Tailwind v4 is configured in CSS through `@theme`, and the config file is legacy. The deliverable was the token system, not the filename. Recorded as D18 in the [roadmap](../ROADMAP.md). `lib/design/tokens.ts` is the source of truth; `tests/tokens-sync.test.ts` enforces that the CSS variables agree with it, so a stale variable cannot silently reintroduce the gold-on-ivory contrast failure that motivated recommendation #8.

---

## 9. Exit criteria

None of these have been run yet. Verifying them is the remaining work on this phase, alongside the four unstarted deliverables above.

- [ ] Lighthouse ≥ 90 across Performance, Accessibility, Best Practices, SEO — throttled mobile
- [ ] axe-core zero critical violations
- [ ] Keyboard-only journey completes end to end
- [ ] `prefers-reduced-motion` honoured
- [ ] Contrast audit passes; gold never used for small body text
- [ ] Product page client JS < 120 KB gzipped
- [ ] FitDrawer round-trips a bespoke profile to the API and back
- [ ] Unapproved images cannot be rendered (type-level)
- [ ] Renders correctly at 320 px width and 200% zoom
