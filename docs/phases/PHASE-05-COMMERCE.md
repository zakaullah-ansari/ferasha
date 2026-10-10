# Phase 5 — Commerce: Cart, Checkout, Payments, Invoicing

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 2, 4 |
| **Blocks** | Phase 7 (loyalty), Phase 12 (launch) |
| **Effort** | 40–48 hrs |
| **Risk** | 🔴 High — money moves here |

---

## 1. Objective

Take money correctly, exactly once, and produce a GST-compliant invoice. This is where correctness matters most and where "mostly works" is not acceptable.

---

## 2. Cart

- **Guest cart** — session/cookie keyed, no account required (explicit brief requirement)
- **Authenticated cart** — persisted, synced across devices
- **Merge on login** — guest cart merges into the account cart; quantities summed, conflicts resolved in the customer's favour
- Bespoke line items carry their `TailoringOrderSpec` snapshot
- **Prices revalidated server-side at checkout** — never trust a client-supplied price
- Stock revalidated at checkout; a race that oversells surfaces before payment, not after

---

## 3. Checkout

Guest checkout supported end to end.

Flow: cart review → address (with GSTIN capture for B2B) → shipping method → live tax quote → payment → confirmation.

The tax quote calls the Phase 0 engine with the **shipping address as place of supply**. The customer sees CGST+SGST, IGST, or a zero-rated export line before paying — no surprises.

### 3.1 Idempotency

Order creation requires an `Idempotency-Key`. A double-tapped pay button on a flaky 4G connection must not create two orders. Tested explicitly.

---

## 4. Payments

Brief requires: cards, UPI, wallets, netbanking, Apple/Google Pay, bank transfer, COD, BNPL. Currency **INR**.

### 4.1 Gateway strategy

**Razorpay as primary** — it covers UPI (the dominant Indian rail), cards, netbanking, wallets, EMI and BNPL in one integration, and settles in INR. A Stripe-first approach would be wrong for a primarily Indian customer base.

International orders (UK, UAE, Saudi, Qatar) are served through the same gateway's international card support initially; a second processor is evaluated only if export volume justifies it.

### 4.2 Architecture — ports and adapters

Payment logic sits behind a `PaymentGateway` interface. Razorpay is one adapter. This is why Phase 0 deliberately deferred payments: a gateway wired directly into order code cannot be swapped when commercial terms change.

### 4.3 Non-negotiables

| Control | Why |
|---|---|
| **Webhook signature verification** | An unverified webhook lets anyone mark an order paid |
| **Webhook idempotency** | Gateways retry; processing twice double-credits |
| **Server-side amount verification** | Confirm the captured amount matches the order total before fulfilling |
| **No card data touches Ferasha** | Gateway-hosted fields only; keeps PCI scope minimal |
| **Payment state machine** | `initiated → authorised → captured → settled`, with `failed` and `refunded` branches |
| **Reconciliation job** | Daily comparison of gateway settlements against orders; discrepancies alerted |

### 4.4 COD

COD is high-risk for premium goods. Controls: order-value cap, pincode allow-list, phone verification (OTP), and a repeat-refuser blocklist.

---

## 5. Shipping

### 5.1 Zones

| Zone | Rate |
|---|---|
| Mumbai | **Free** (brief requirement) |
| Rest of Maharashtra | Weight/dimension based |
| Rest of India | Weight/dimension + zone |
| International — UK, UAE, Saudi, Qatar | Weight + zone; duties/taxes flagged as recipient's liability |

### 5.2 Carriers

Blue Dart, DTDC, Professional Couriers. Real-time rates via carrier APIs where available, with a **cached rate-card fallback** — a carrier API outage must degrade to a sane quote, not block checkout.

Volumetric weight is computed and the greater of actual/volumetric used. Lehengas are light but bulky; ignoring this loses money on every order.

### 5.3 Tracking

AWB stored on the order, carrier webhooks update status, customer-facing timeline. Tracking updates pushed via WhatsApp and email (Phase 8).

---

## 6. Invoicing

A GST tax invoice is a legal document. Requirements:

- Sequential, gap-free invoice numbering per financial year (an audit will check this)
- Ferasha GSTIN, customer GSTIN where supplied
- **HSN-wise summary** with taxable value and tax per rate
- Place of supply and supply type
- CGST/SGST split or IGST, per the Phase 0 engine
- **Rendered from the persisted `OrderTaxSnapshot`, never recomputed** — this is why Phase 1 stores it
- LUT declaration on export invoices
- Credit notes for returns, referencing the original invoice and reproducing its regime

PDF delivered by WhatsApp and email (Phase 8).

---

## 7. Returns & refunds

State machine: `return_requested → approved → in_transit → received → inspected → refunded | rejected`.

**Bespoke items are non-returnable except for defect** — stated prominently at the point of sale, not buried in terms. A garment cut to one customer's measurements has no resale value.

Refunds issue a credit note and reverse the tax correctly under the original regime.

---

## 8. Promotions

Discount codes, gift cards, free-shipping thresholds.

- Discounts applied **before** tax — the Phase 0 engine already slabs on post-discount per-piece value, which can legitimately move a garment from 18% to 5%
- Gift cards are a **liability**, not revenue: separate ledger, balance tracking, expiry rules, atomic redemption that cannot double-spend
- Stacking rules defined explicitly and tested

---

## 9. Exit criteria

- [ ] Guest checkout completes without an account
- [ ] Cart merges correctly on login
- [ ] Tax shown at checkout matches the invoice exactly
- [ ] Webhook signature verification rejects forged callbacks (tested)
- [ ] Replayed webhook does not double-process (tested)
- [ ] Double-submitted checkout creates exactly one order (tested)
- [ ] Payment failure leaves no phantom order and releases stock
- [ ] Invoice numbering is sequential and gap-free under concurrency
- [ ] Export invoice carries the LUT declaration and zero tax
- [ ] Credit note reproduces the original order's tax regime
- [ ] Gift card cannot be double-spent under concurrent redemption
- [ ] Free shipping applies to Mumbai pincodes only
- [ ] Carrier API outage degrades to fallback rates, not a checkout failure
