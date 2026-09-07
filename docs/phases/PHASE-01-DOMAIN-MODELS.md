# Phase 1 — Domain Models & Data Integrity

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phase 0 |
| **Blocks** | Phases 2, 3, 5, 6 |
| **Effort** | 30–36 hrs |

---

## 1. Objective

Model every business entity in PostgreSQL with **constraints enforced at the database level, not merely in Python**. Application validation is a usability feature; database constraints are the actual guarantee. A bug in a serializer must not be able to write a garment with negative stock or an invalid modesty enum.

---

## 2. Catalogue (`apps/catalog`)

### 2.1 Category

Self-referencing tree matching Ferasha's real merchandising taxonomy:

```
Karachi / Pakistani / Kashmiri Suits & Dress Materials
├── Lawn · Chiffon · Organza · Velvet · Cotton
Punjabi / Patiala / Lucknowi Suits & Dress Materials
├── Patiala Salwar · Chikankari · Anarkali
Bridal & Occasion Wear
├── Lehenga · Sharara · Gharara · Sharara Palazzo
├── Farshi Palazzo · Farshi Salwar · Gowns
Blouses · Jackets · Long Jackets · Tail Gowns
```

Materialised path or `django-treebeard` for O(1) subtree reads. Do **not** use naive recursive FK traversal — category pages are the hottest read path on the site.

### 2.2 Product

| Field | Type | Notes |
|---|---|---|
| `slug` | `SlugField unique` | Immutable after publish; changing it breaks SEO and inbound links |
| `vendor` | FK User | Role must be `vendor` — enforced by a check |
| `hsn_code` | `CharField` | Drives the Phase 0 tax engine |
| `gst_rate_override` | `Decimal null` | Per D3; validated against the regime's permitted rates |
| `base_price` | `Decimal(12,2)` | `CheckConstraint >= 0` |
| `fabric` | enum | Lawn, chiffon, organza, velvet, georgette, silk, cotton |
| `work_type` | enum | Zardozi, gota patti, mirror, chikankari, mukaish, resham |
| `occasion` | enum | Bridal, mehndi, nikah, walima, eid, casual, formal |
| `status` | enum | draft → pending_review → active → archived |

### 2.3 Modesty attributes — typed columns, **not** JSON

This is a deliberate departure from the original brief, which implied JSON storage.

**Rationale:** modesty attributes are faceted-search inputs and badge drivers. In a `jsonb` blob they cannot be cleanly indexed, cannot carry check constraints, and cannot be aggregated for facet counts. They are a fixed, well-known set — they belong in columns.

```python
is_opaque              = BooleanField(db_index=True)
has_full_lining        = BooleanField(db_index=True)
slit_coverage          = CharField(choices=SlitCoverage)   # none|knee|mid_calf|ankle|full
sleeve_coverage        = CharField(choices=SleeveCoverage) # sleeveless|cap|elbow|three_quarter|full|extra_long
neckline_modesty       = CharField(choices=NecklineModesty)# deep|moderate|high|closed
back_coverage          = CharField(choices=BackCoverage)
requires_slip          = BooleanField(default=False)
is_sheer_overlay_only  = BooleanField(default=False)
```

Every enum backed by a `CheckConstraint`. A composite index on `(is_opaque, has_full_lining, slit_coverage)` serves the primary modesty facet.

### 2.4 Modesty badge derivation

A **pure function** mapping attributes → displayable badge set, exported to the frontend via the Phase 2 OpenAPI schema so backend and frontend can never disagree:

```
FULLY_LINED        ← has_full_lining
OPAQUE_FABRIC      ← is_opaque
FULL_COVERAGE      ← slit_coverage in (ankle, full) ∧ sleeve_coverage in (full, extra_long)
MODEST_NECKLINE    ← neckline_modesty in (high, closed)
SLIP_REQUIRED      ← requires_slip            (advisory, not a badge)
```

Unit tested against a truth table. This must never be reimplemented in TypeScript.

### 2.5 ProductVariant

Size (XS–XXL + custom), colour, `stock_quantity`, per-variant SKU, price delta.

`CheckConstraint(stock_quantity >= 0)`. Stock decrements use `SELECT ... FOR UPDATE` or a conditional `UPDATE ... WHERE stock >= n` — never read-modify-write, which oversells under concurrency.

---

## 3. Bespoke tailoring (`apps/tailoring`)

### 3.1 BespokeFitProfile

`models.JSONField` — native `jsonb` on PostgreSQL. (`models.JSONBField` does not exist in Django 5.)

**`measurements` (jsonb):**
bust, underbust, waist, hip, shoulder, kameez_length, sleeve_length, armhole, bicep, wrist, neck_depth_front, neck_depth_back, trouser_length, thigh, knee, ankle_opening, farshi_flare, ghera

**`preferences` (jsonb):**
sleeve_type, lining_preference, neckline_style, closure_type, hem_finish, dupatta_length

Plus: `unit_system` (cm|inch), `measured_by` (self|tailor|stylist), `verified_at`, `verified_by`.

### 3.2 JSON Schema validation — non-negotiable

A raw `jsonb` column with no schema is a data-integrity hole. Wrong measurements mean a ruined ₹48,000 bridal lehenga, a refund, and a lost customer.

`apps/tailoring/validators.py` enforces:
- **Presence** — required keys per garment type
- **Type** — numeric, positive
- **Plausibility ranges** — e.g. bust 24–70 in / 61–178 cm; a bust of 400 is a unit-entry error, not a body
- **Cross-field coherence** — waist < bust + 20; kameez_length > 20 in
- **Unit consistency** — all measurements in the declared `unit_system`

Invoked from `Model.clean()` **and** the serializer, so admin edits and API writes are both covered.

GIN index on `measurements` for queryability.

### 3.3 FitProfileRevision — append-only

Measurements change between orders. Disputes ("you stitched it wrong") require knowing exactly what was specified *at the time*. Append-only history table, no updates, no deletes.

### 3.4 TailoringOrderSpec

A **snapshot** of the profile at order time — never a live FK. The profile mutates; the order must not.

---

## 4. Orders (`apps/orders`)

### 4.1 Order & OrderLine

Standard header/line split, plus:

- Place of supply **frozen** onto the order from the shipping address at placement
- `as_of` date frozen, so the Phase 0 tax engine reproduces rates exactly on any later credit note

### 4.2 OrderTaxSnapshot — the critical one

The full Phase 0 `TaxBreakdown` is **persisted at checkout and never recomputed on read.**

Rates change (as GST 2.0 proved). An invoice is a legal document; recomputing it on read means a customer's PDF silently changes after a Budget. Store: regime name, per-line rates and amounts, rate-wise summary, place of supply, totals.

### 4.3 State machine

```
draft → placed → payment_confirmed → in_atelier → measurement_review
      → stitching → quality_check → packed → shipped → delivered
                                                    ↘ return_requested → returned → refunded
      ↘ cancelled
```

Transitions validated in a service layer, not by assigning to a field. Every transition writes an `OrderEvent` audit row with actor, timestamp, and reason.

---

## 5. Reviews (`apps/reviews`)

Rating 1–5, title, body, **verified-purchase flag** (FK to a delivered OrderLine), photo uploads routed through the Phase 3 privacy pipeline, moderation status.

`UniqueConstraint(user, product)` — one review per customer per product.

**Fit feedback** is the high-value field for a tailoring business: `ran_small | true_to_size | ran_large`, aggregated onto the product to drive size guidance.

---

## 6. Deliverables

| File | Purpose |
|---|---|
| `apps/catalog/models.py` | Category, Product, ProductVariant, ProductImage |
| `apps/catalog/modesty.py` | Pure badge derivation function |
| `apps/tailoring/models.py` | BespokeFitProfile, FitProfileRevision, TailoringOrderSpec |
| `apps/tailoring/validators.py` | JSON Schema + plausibility ranges |
| `apps/orders/models.py` | Order, OrderLine, OrderTaxSnapshot, OrderEvent |
| `apps/orders/state_machine.py` | Validated transitions |
| `apps/reviews/models.py` | Review, ReviewPhoto |
| `tests/factories.py` | factory-boy factories for all of the above |

---

## 7. Exit criteria

- [ ] `makemigrations` / `migrate` clean against PostgreSQL 16
- [ ] Constraint tests prove Postgres **rejects**: negative stock, invalid modesty enum, out-of-range measurement, duplicate review, order in an impossible state
- [ ] Modesty badge truth table fully covered
- [ ] Measurement validator rejects unit-confusion (bust 400 cm) and implausible cross-field combinations
- [ ] Tax snapshot round-trips: an order placed under one regime reproduces its original rates after a regime change
- [ ] Concurrent stock decrement cannot oversell (tested with parallel transactions)

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| `jsonb` drifts schema-less | JSON Schema on save + append-only revisions |
| Oversell under concurrency | Conditional UPDATE / row locks, tested |
| Category tree slow on deep nests | Materialised path, not recursive traversal |
| Tax snapshot omitted, invoices recomputed | Snapshot written in the same transaction as order placement; test asserts immutability |
