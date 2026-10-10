# Phase 12 — Migration, Launch & Post-Launch

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 5, 8, 9, 11 |
| **Effort** | 20–26 hrs + monitoring |

---

## 1. Objective

Replace the existing www.ferasha.com with the new platform **without losing search rankings, customer accounts, or order history** — and without a window where the business cannot take orders.

---

## 2. Migration from the existing store

The brief confirms an existing store at www.ferasha.com. Migration is where launches usually go wrong.

### 2.1 Audit first

Before writing any migration code, inventory the current site: every URL, product, customer, order, and inbound link. You cannot preserve what you have not catalogued.

### 2.2 Data migration

| Data | Approach |
|---|---|
| Products | Export → transform → import. **Modesty attributes will not exist in the old data** and must be set manually per product. Budget real time for this |
| Customers | Migrate accounts. **Passwords almost certainly cannot be migrated** (different hashing) — force a reset with a clear, pre-announced email |
| Orders | Historical orders imported read-only for customer service and warranty |
| Reviews | Migrate with original dates; ratings are hard-won social proof |
| Media | Re-import **through the Phase 3 privacy pipeline.** Existing images have never been face-blurred. This is a compliance requirement, not an optimisation |

Every migration script is idempotent, re-runnable, and produces a reconciliation report: counts in, counts out, discrepancies explained.

### 2.3 SEO preservation — the highest-risk item

Losing rankings costs revenue immediately and takes months to recover.

- **301 redirect map from every old URL to its new equivalent.** No exceptions, no lazy redirects to the homepage — those are treated as soft 404s
- Preserve URL structure where sensible; redirect where not
- Submit updated sitemaps; monitor Search Console for crawl errors daily for the first fortnight
- Retain title/meta patterns that already rank
- Verify structured data before go-live

---

## 3. Pre-launch

### 3.1 UAT with the actual owner

Not the developer clicking through happy paths. The owner and manager run **real workflows**: add a product, process a bespoke order, issue a refund, file a GST summary. Their confusion is the specification for the Phase 9 training manual.

### 3.2 Checklist

- [ ] All Phase 11 exit criteria met
- [ ] Real payment tested in live mode, then refunded
- [ ] WhatsApp templates approved and sending in production
- [ ] Invoice numbering starts correctly for the financial year
- [ ] Legal pages published: T&Cs, privacy (DPDP), returns, shipping, grievance officer
- [ ] Redirect map tested — **every** old URL resolves
- [ ] SSL, HSTS preload, DNS TTL lowered ahead of cutover
- [ ] Analytics and Sentry receiving production events
- [ ] Owner trained; manual delivered
- [ ] **Rollback plan written and rehearsed**

---

## 4. Launch

**Soft launch first.** Cutover DNS with a low TTL, then restrict traffic to a small cohort (staff, friendly customers) for several days. Real customers find issues no test suite will.

Full launch only when the soft-launch cohort transacts cleanly. Announce to the existing customer base via WhatsApp and email — password reset instructions must be prominent and pre-warned, or support will be overwhelmed.

**Elevated monitoring for the first 72 hours.** Watch checkout completion, payment declines, error rate, AI queue depth, and Search Console crawl errors.

---

## 5. Post-launch

### First 30 days
Daily error review. Weekly business metrics with the owner. Fix friction as observed — real behaviour will contradict at least some design assumptions. Monitor rankings closely; redirect issues surface within days.

### First 90 days
Tier 2 integrations (Phase 8). Conversion optimisation against measured funnel drop-off. **FitDrawer completion rate** is the leading indicator for the bespoke business. Content expansion. Reassess whether Phase 10 AI is warranted on evidence.

### Ongoing
Monthly dependency updates and security patches. Quarterly restore drill and access review. **Annual GST rate audit** — GST 2.0 in September 2025 proved this is not hypothetical; a rate change that goes unnoticed accrues liability silently.

---

## 6. Success metrics

Instrument these from day one, or the platform cannot be improved.

| Metric | Why it matters |
|---|---|
| Conversion rate | Overall health |
| **FitDrawer open → completion** | Whether bespoke ordering actually works |
| **Bespoke vs ready-to-wear mix** | Whether the differentiator is landing |
| Cart abandonment | Checkout friction |
| Average order value | Merchandising effectiveness |
| Return rate by product | Sizing and description accuracy |
| **Atelier on-time delivery** | Operational promise-keeping |
| Repeat purchase rate | Phase 7 effectiveness |
| Organic traffic vs pre-migration | **SEO preservation — watch weekly for 3 months** |
| Media moderation backlog | Whether Phase 3 is blocking merchandising |

---

## 7. Exit criteria

- [ ] Old site retired; all traffic on the new platform
- [ ] Zero unresolved 404s from the redirect map
- [ ] Organic traffic within 10% of pre-migration baseline at 90 days
- [ ] Orders processing end to end in production
- [ ] Owner operating independently without developer intervention
- [ ] No P1 incidents in the first 30 days
- [ ] All historical media re-processed through the privacy pipeline
