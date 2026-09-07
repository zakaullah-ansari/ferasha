# Design System & UI Library Selection

**Status:** Decision record — binding for Phase 4 (Storefront).
**Date:** 2026-09-07
**Supersedes:** the one-line "Tailwind + Framer Motion" note in `TECH-STACK.md` §4.

---

## 0. The commercial constraint that drives everything

Ferasha is a **revenue-generating commercial storefront**. That single fact
eliminates a surprising number of otherwise-excellent options, and it is the
first filter applied below — before aesthetics, before DX, before star counts.

Three failure modes we are underwriting against:

1. **Licence contamination.** A component copied from a "free and open source"
   registry that turns out to carry a field-of-use restriction.
2. **Abandonment.** A library that stops receiving accessibility and React
   version fixes, leaving us to fork primitives we did not write.
3. **Aesthetic dating.** Effect-driven libraries encode a *moment*. Glassmorphism
   and neon-beam aesthetics read as "2024 SaaS landing page", which is precisely
   the wrong register for bridal couture.

---

## 1. Licence audit of the libraries you sent

I read the actual `LICENSE` files rather than the marketing pages, because two
of these are widely mis-reported in comparison blogs.

| Library | Reported licence | **Actual licence (verified)** | Verdict for Ferasha |
|---|---|---|---|
| **Magic UI** | MIT | **MIT** — verified clean, no additional conditions | ✅ Safe |
| **React Bits** | "MIT" in most blog tables | **MIT + Commons Clause v1.0** | ⚠️ **Usable, with a hard rule** |
| Aceternity UI | MIT (core) | MIT core, paid "all-access" templates | ✅ Safe for the free core |
| shadcn/ui | MIT | MIT | ✅ Safe |

### 1.1 React Bits — the finding that matters

The GitHub sidebar reports `NOASSERTION`, and the aggregator tables in
circulation flatten it to "MIT". The actual text, decoded from the repository:

> **MIT + Commons Clause License Condition v1.0** … permission to use, copy,
> modify, merge, publish, and distribute the Software **as part of an
> application, website, or product** …
>
> **Commons Clause Restriction** — You may use this Software, including for any
> commercial purpose, **so long as you do not sell, sublicense, or redistribute
> the components themselves — whether alone, in a bundle, or as a ported
> version.**

**What this means concretely for Ferasha:**

- ✅ Using React Bits components on `ferasha.com` is **explicitly permitted**,
  including commercially. The licence names this use case.
- ❌ We must never publish our `components/` directory as a public package,
  template, or starter kit if it contains derived React Bits code.
- ⚠️ **Commons Clause is not an OSI-approved open source licence.** Some
  corporate legal reviews and automated licence scanners (FOSSA, Snyk, `licensee`)
  will flag `NOASSERTION` or `Commons-Clause` and fail a CI gate.

**Rule adopted:** React Bits code is permitted, but must be **quarantined and
labelled** so it is auditable:

```
frontend/components/vendor/react-bits/     ← all React Bits-derived code
frontend/components/vendor/react-bits/LICENSE.md   ← verbatim upstream licence
```

Every file in that directory carries a provenance header. Phase 7 adds a CI
check asserting no React Bits-derived file leaks outside it. This costs us
nothing today and saves a painful excavation if Ferasha is ever acquired,
audited, or open-sources part of its frontend.

> **A note on how this was found:** three separate comparison articles list
> React Bits as plain "MIT". The licence is not MIT. This is exactly the class
> of detail that is cheap to verify now and expensive to discover during due
> diligence.

---

## 2. The architectural decision: layers, not a library

The most common and most expensive mistake here is treating this as a single
choice. It is four independent choices, and conflating them is what produces
storefronts that look like a template.

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 4  Bespoke Ferasha components                         │
│           FitDrawer, ModestyBadgeRow, FabricSwatch,          │
│           DupattaDrapePreview, GhararaFlareVisualiser        │
│           ── nobody else has these; they are the moat        │
├──────────────────────────────────────────────────────────────┤
│  LAYER 3  Motion — `motion` (Framer Motion 12)               │
│           behind LazyMotion + MotionConfig reducedMotion      │
├──────────────────────────────────────────────────────────────┤
│  LAYER 2  Styled components — shadcn/ui (copied, owned)      │
│           re-themed to Ferasha tokens, NOT default shadcn    │
├──────────────────────────────────────────────────────────────┤
│  LAYER 1  Headless primitives — Radix UI (via shadcn)        │
│           accessibility, focus management, ARIA              │
└──────────────────────────────────────────────────────────────┘
```

**Magic UI and React Bits belong to none of these layers.** They are a *garnish*
— a small number of specific effects on marketing surfaces. Treating them as a
foundation is how a luxury brand ends up looking like a developer-tools startup.

---

## 3. Layer-by-layer decisions

### Layer 1 — Headless primitives: **Radix UI**, migrating to Base UI when forced

| Option | Assessment |
|---|---|
| **Radix UI** ✅ | The incumbent. Powers shadcn/ui, Vercel, Linear, Supabase. ~30 primitives, WAI-ARIA gold standard, `asChild` composition avoids wrapper-div soup. **Maintenance has visibly slowed** — this is the one risk. |
| **Base UI** | From the creators of Radix, Floating UI *and* Material UI; stable v1.0 in 2026. The designated successor and more actively developed. shadcn/ui is adding support. |
| **React Aria** (Adobe) | The most rigorous accessibility and i18n in existence — locale-aware dates/numbers, exhaustive screen-reader testing. Steeper, hook-based. Apache 2.0. |
| Ark UI | Multi-framework (React/Vue/Solid). We are React-only; the abstraction is unpaid-for cost. |
| Headless UI | Only ~10 primitives. Too thin for commerce. |

**Decision: Radix UI**, consumed through shadcn/ui.

The reasoning is not that Radix is better than Base UI on the merits — Base UI
is arguably the more future-proof primitive set. It is that **shadcn/ui's
ecosystem is overwhelmingly Radix-based today**, and adopting Base UI now means
hand-porting every block we pull in. Radix's slowed maintenance is a real risk,
but it is a *stable* library, not a broken one, and shadcn/ui's Base UI support
gives us a migration path we do not have to take on day one.

**Revisit trigger (write this down):** if Radix ships no release addressing a
React version bump within 6 months of that React release, migrate to Base UI.

**Where React Aria wins anyway:** the **checkout and measurement forms**. These
are the two surfaces where an accessibility failure is a lost sale and a
regulatory exposure. React Aria's `useNumberField` and locale-aware formatting
are materially better than anything else for entering measurements in
inches-versus-centimetres, which is precisely the unit-confusion problem Phase 1
built a validator for. Using it selectively there is a deliberate, bounded
exception — not a second design system.

---

### Layer 2 — Styled components: **shadcn/ui, aggressively re-themed**

Non-negotiable, for one reason that outranks all the usual arguments: **you own
the code.** Ferasha needs modesty attributes (`is_opaque`, `has_full_lining`,
`slit_coverage`) rendered as first-class product metadata. That is not a prop on
anyone's `<Card>`. With shadcn the component is a file in our repo we simply
edit; with MUI or Mantine it is a fight with an abstraction layer.

**The critical discipline: shadcn/ui must not look like shadcn/ui.**

Default shadcn is instantly recognisable — `slate` palette, `Inter`, `0.5rem`
radius. Shipping that on a bridal couture site actively destroys the brand. The
default theme is a *starting point to be overwritten*, and Phase 4 replaces
every token:

| Token | shadcn default | **Ferasha** |
|---|---|---|
| Body typeface | Inter | A humanist serif for editorial copy |
| UI typeface | Inter | A restrained grotesque for controls only |
| Radius | `0.5rem` | `0.125rem` — near-square reads as couture |
| Palette | `slate` | Warm ivory/parchment base; ink-brown text; a single restrained accent |
| Shadows | Soft ambient | Near-none — flat, print-like surfaces |
| Motion default | `150ms ease` | `400–600ms` custom easing — luxury reads as *unhurried* |

> **Rejected: dark mode as the primary aesthetic.** Some 2026 trend pieces push
> dark-first for luxury. It is wrong here. These are heavily embellished
> garments — zardozi, gota, mirror work — photographed on light backgrounds by
> the manufacturers supplying our imagery. A dark UI fights the source material.
> Bottega Veneta, Aesop and COS — the actual quiet-luxury benchmarks — are all
> light. We ship light-first, with dark mode as a respected system preference,
> not the showcase.

---

### Layer 3 — Motion: **`motion` v12 (Framer Motion), constrained**

| Option | Assessment |
|---|---|
| **`motion` v12** ✅ | Best React integration; `AnimatePresence` for exits; automatic FLIP layout animation; first-class `prefers-reduced-motion`. |
| GSAP | More powerful timelines, ~60KB, imperative, awkward with RSC. Justified only for a bespoke bridal showcase — not the general system. |
| CSS-only | 0KB and correct for most of what we need. Genuinely the default. |

**Decision: `motion` v12, with three mandatory constraints.**

1. **`LazyMotion` + the `m` component.** Full `motion` is ~34KB gzipped;
   `LazyMotion` + `domAnimation` is ~4.6–15KB. On a catalogue where LCP is an
   image, 30KB of JS competing for bandwidth is a measurable conversion cost.
2. **`MotionConfig reducedMotion="user"` at the root.** Vestibular disorders are
   real and this is a WCAG obligation, not a nicety. Notably, **Magic UI and
   Aceternity do not ship reduced-motion handling by default** — anything
   adapted from them must have it added by hand.
3. **Transform and opacity only.** Never animate `width`/`height`/`top`/`left`.
   Layout changes use `layout`/`layoutId`.

---

### Layer 4 — Effects: **Magic UI, sparingly; React Bits, quarantined**

This is where your two links actually land, and the honest answer is: **at the
edges, not the core.**

| Library | Where it earns its place at Ferasha |
|---|---|
| **Magic UI** | MIT-clean, coexists with shadcn by design. Genuinely useful: `NumberTicker` (atelier order counts), `Marquee` (press logos), `BlurFade` (editorial reveals). **Avoid** its neon/beam/retro-grid catalogue entirely — wrong register. |
| **React Bits** | Two real technical advantages: **no forced Framer Motion dependency** (CSS-based, so RSC-compatible) and explicit reduced-motion controls. Best used for text-reveal effects on the bridal landing page. Subject to the quarantine rule in §1.1. |
| **Aceternity UI** | Dramatic, dark, glassmorphic, 3D. Superb at what it does; what it does is not couture. **Rejected** for the storefront. |

**The hard rule:** no Layer 4 component may appear on the product detail page,
the cart, or checkout. Those surfaces are conversion-critical and belong to
Layers 1–3 exclusively. Effects live on the homepage, the bridal lookbook, and
the brand-story pages.

---

## 4. Beyond your list — libraries worth knowing

Researched openly as you asked; these are the ones that survived scrutiny.

### Strongly recommended

| Library | Licence | Why it matters to Ferasha |
|---|---|---|
| **Embla Carousel** | MIT | The correct product-gallery carousel. Accessible, tiny, no dependencies. shadcn/ui wraps it already. |
| **Vaul** | MIT | Drawer/bottom-sheet primitive by shadcn's author. **This is the FitDrawer.** Mobile-first, exactly right for measurement entry in India, where traffic is overwhelmingly mobile. |
| **cmdk** | MIT | Command-menu primitive. Powers a fast catalogue search overlay. |
| **Sonner** | MIT | Toasts, by the same author. Restrained by default. |
| **next-intl** | MIT | i18n done properly. **You will need Urdu/Hindi eventually** — retrofitting i18n is brutal, designing for it is cheap. |
| **Lucide** | ISC | 1000+ consistent icons. |
| **Radix Colors** | MIT | Perceptually-uniform scales with guaranteed contrast pairs. The rigorous way to build the ivory/ink palette. |

### Worth evaluating

| Library | Note |
|---|---|
| **Origin UI** | ~400 free shadcn-compatible components. Largest free block collection — useful for account pages and forms. |
| **Motion Primitives** | Tasteful, restrained shadcn-compatible motion. Better aesthetic fit than Magic UI for a luxury brand. |
| **Tremor** | Only for the internal back-office dashboard. Never customer-facing. |
| **React Aria Components** | See §3 — the checkout/measurement exception. |

### Explicitly rejected

| Library | Why |
|---|---|
| MUI / Ant Design | 100–300KB, opinionated Material/enterprise styling to fight, and we would be paying to *remove* their design opinion. |
| Chakra / Mantine | Good libraries, wrong problem. Runtime styling and a design opinion we do not want. |
| Aceternity UI | Aesthetic mismatch (see §4 above). |
| "Uilora" | Appears heavily in 2026 listicles as "best overall". New, no meaningful track record, and the framing in those articles reads as placement rather than assessment. **Not staking a couture storefront on it.** |
| 8bitcn, Neobrutalism | Self-evidently wrong register. |

---

## 5. Design references — how to use the inspiration links

Your links split into two categories that deserve different treatment.

**Study these for e-commerce mechanics** (Mobbin is the strongest of your list —
real shipped flows, not concept work):

| Reference | The specific lesson for Ferasha |
|---|---|
| **Bottega Veneta** | The quiet-luxury blueprint: custom serif, full-bleed atelier video, **no social/UGC widgets** — a deliberate restraint decision. |
| **Aesop** | Editorial-first, text over image, warm cream ground, one sparing accent. "Shoppable navigation" — products surfaced in the menu itself. |
| **COS** | Negative space as a deliberate element; grid spacing as intentional as the photography. |
| **Nike** | Grid mechanics: light-grey product ground so cutouts pop, hover-reveal colourway swatches. |

**Treat these as mood, not blueprint:** Dribbble, Behance, Awwwards. Dribbble
and Behance reward screenshots that photograph well, not interfaces that convert
— many are non-functional. Awwwards rewards novelty and heavy motion, which is
usually the *opposite* of what sells couture. Mine them for typography pairings
and colour, never for interaction patterns or information architecture.

**Envato Elements: a licensing caution.** Standard Envato licences are
per-end-product and frequently prohibit redistribution. If you buy assets there,
record the licence per asset. More importantly — for a brand at this level,
stock imagery is a liability. Commission photography.

**bokaap.design** is a small curated gallery; pleasant, but not a decision input.

---

## 6. The uncomfortable recommendation

The libraries in this document will get Ferasha to a storefront that looks
**expensively generic** — clean, fast, accessible, and indistinguishable from
several hundred other well-built shadcn sites.

What will actually differentiate it is **Layer 4: the bespoke components** —
the fit drawer, the modesty badge system, the fabric swatch viewer, the
gharara flare visualiser. No library ships these, because nobody else has the
domain model we built in Phase 1.

The correct budget allocation is therefore roughly:

- **20%** wiring up shadcn/Radix (a solved problem — do not gold-plate it)
- **20%** the theme layer, tokens and typography (where "expensive" is decided)
- **60%** bespoke domain components and photography

And one thing worth more than every library listed here: **commission real
photography.** Bottega Veneta and Aesop are not winning on component libraries.
They are winning on art direction. A perfect shadcn implementation wrapped
around manufacturer stock photos will read as cheap; a plain implementation
wrapped around genuinely beautiful imagery will not.

---

## 7. Locked decisions

| # | Decision | Rationale |
|---|---|---|
| D8 | Radix UI (via shadcn/ui) as the primitive layer | Largest ecosystem; documented migration trigger to Base UI |
| D9 | React Aria for checkout + measurement forms only | Best-in-class numeric/locale input where errors are most costly |
| D10 | shadcn/ui, fully re-themed — never default tokens | Default shadcn is recognisable and brand-destructive |
| D11 | Light-first aesthetic; dark mode as preference only | Embellished garments are shot on light grounds |
| D12 | `motion` v12 behind `LazyMotion` + `reducedMotion="user"` | 34KB → ~5KB; WCAG compliance |
| D13 | Magic UI permitted on marketing surfaces only | MIT-clean; wrong register for conversion surfaces |
| D14 | React Bits quarantined to `components/vendor/react-bits/` | **Commons Clause is not OSI open source**; keep it auditable |
| D15 | No Layer 4 effects on PDP, cart, or checkout | Conversion surfaces stay boring and fast |
| D16 | Vaul for the FitDrawer; Embla for galleries | Mobile-first India traffic; accessible carousel |
| D17 | next-intl wired from day one, even English-only | Retrofitting i18n is brutal; designing for it is cheap |

---

## 8. Open questions for you

1. **Typography budget.** A licensed display serif (Canela, Tiempos, GT Sectra)
   costs roughly ₹40k–₹200k for web use and is the single highest-leverage
   branding decision available. The free fallback is Fraunces or Instrument
   Serif — genuinely good, but more common. Which way?
2. **Photography.** Are we committed to commissioning, or working from
   manufacturer imagery for launch? This changes the layout strategy
   substantially — stock imagery needs the grid to do more work.
3. **Urdu/Hindi at launch, or English-only?** Affects whether we need RTL
   support in the token system now rather than later.
