# Phase 7 — Loyalty, Rewards & Retention

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phase 5 |
| **Effort** | 20–26 hrs |

---

## 1. Objective

Increase repeat purchase rate. For a boutique with a high average order value and a naturally low purchase frequency (bridal wear is not a weekly buy), retention economics differ sharply from fast fashion — the programme must reflect that.

---

## 2. Programme design

### 2.1 Why points-per-rupee is the wrong default

A generic 1-point-per-₹100 scheme suits high-frequency retail. Ferasha's customer might buy once for a wedding and return two years later for another. A points balance that expires in 12 months is worthless to them and actively irritating.

**Recommended model: tiered status + occasion-based rewards.**

| Tier | Qualification (rolling 24 months) | Benefits |
|---|---|---|
| **Guest** | — | Standard service |
| **Silver** | 1 order | Early access to new collections |
| **Gold** | ₹75k+ or 3 orders | Free shipping anywhere in India, priority stitching |
| **Platinum** | ₹2L+ or 6 orders | Complimentary alterations, dedicated stylist, first look at bridal |

Benefits are **service-led, not discount-led**. Discounting devalues a luxury brand; priority access and complimentary alterations reinforce it and cost less.

### 2.2 Occasion rewards

Wedding-anniversary and Eid reminders with a curated edit. Far higher conversion than generic point-balance emails, and it fits how this customer actually shops.

### 2.3 Referral

Bridal purchases are socially driven — the bride's circle is the highest-intent audience Ferasha will ever reach. Two-sided referral with fraud controls (self-referral detection, velocity limits, payout only on delivery-confirmed orders).

---

## 3. Points ledger (if implemented)

If a points component is included, it is **financial infrastructure**:

- **Append-only double-entry ledger.** Never a mutable balance column — a balance is a computed projection of the ledger
- Atomic redemption; concurrent redemption cannot overdraw (tested with parallel transactions)
- Expiry rules explicit and communicated
- Reconciliation job
- Accrual on **net paid value after refunds**, not gross — otherwise refund abuse mints points

Same rigour as gift cards in Phase 5.

---

## 4. Store credit & gift cards

Extends Phase 5. Store credit issued on returns where the customer prefers it over a refund. Both are **liabilities on the balance sheet** and must be reportable for accounting (Phase 8 integration).

---

## 5. Retention mechanics

| Mechanic | Trigger |
|---|---|
| Abandoned cart | 1h / 24h / 72h sequence, WhatsApp + email |
| Back in stock | Wishlist item restocked |
| Price drop | Wishlist item reduced |
| Post-delivery | Review request + fit feedback at +7 days |
| Replenishment | Occasion-based, not calendar-based |
| Win-back | 12 months dormant, new collection |

All respect consent and unsubscribe (Phase 8, DPDP Act).

---

## 6. Exit criteria

- [ ] Tier calculation correct across the rolling window, including refunds
- [ ] Points/credit ledger balances reconcile exactly
- [ ] Concurrent redemption cannot overdraw (tested)
- [ ] Refunds correctly reverse accrual
- [ ] Referral fraud controls block self-referral and velocity abuse
- [ ] Every automated message honours consent and unsubscribe
- [ ] Liability reporting available for accounting
