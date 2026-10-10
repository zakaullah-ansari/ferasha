# Phase 9 — Admin, Operations & Atelier Workflow

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 1, 5 |
| **Effort** | 30–36 hrs |

---

## 1. Objective

Give the owner and manager the tools to run the business daily, and give the atelier a workflow for bespoke production. The brief names Owner/Manager as day-to-day operators — **not developers**. Every workflow must be completable without touching a terminal or the Django admin's raw model views.

---

## 2. Operations dashboard

Priority-ordered by what actually needs attention:

- Orders requiring action (payment pending, measurements missing, ready to dispatch)
- **Atelier queue with due dates** — the bottleneck in a bespoke business
- Low stock alerts
- Media awaiting moderation (Phase 3 `NEEDS_REVIEW` queue)
- Returns pending inspection
- Today's revenue, this month vs last

---

## 3. Atelier workflow

The operational heart of Ferasha's differentiation. Bespoke orders are a production pipeline, not a shipping label.

```
Order placed (bespoke)
  → Measurement review        (tailor verifies plausibility; queries the customer if odd)
  → Fabric allocation         (deduct from stock)
  → Cutting                   (assigned, due-dated)
  → Stitching                 (assigned, due-dated)
  → Embellishment             (zardozi/gota — often outsourced)
  → Quality check             (against the frozen TailoringOrderSpec)
  → Finishing & packing
  → Dispatch
```

Each stage: assignee, due date, status, notes, photo evidence. Delays flagged before the customer notices — proactive communication is the single biggest driver of satisfaction in custom tailoring.

**Capacity planning:** the atelier has finite throughput. The system must surface when the queue exceeds capacity so delivery promises stay honest, rather than accepting orders it cannot fulfil.

---

## 4. Catalogue management

- Product CRUD with **modesty attributes as a required, prominent section** — not an afterthought at the bottom of a long form
- Bulk CSV import/export with validation and a dry-run preview
- Image upload routed through the Phase 3 pipeline; moderation queue with side-by-side original/blurred review for staff
- Variant matrix editor (size × colour) rather than one-at-a-time entry
- Draft → review → publish workflow

---

## 5. Inventory

Stock ledger with movement reasons (sale, return, damage, fabric allocation, adjustment). Every change attributable — "where did 3 metres of chiffon go" must be answerable.

Low-stock thresholds per variant. Fabric-level tracking for bespoke, which consumes raw material rather than finished goods.

---

## 6. Tax administration

Phase 0 hardcodes GST regimes in `constants.py`. That was correct for launch — but a rate change should not require a developer and a deploy.

Move regimes to **admin-editable records with an effective date and a full audit trail**, retaining the date-effective model. Changing a rate creates a new regime row; it never mutates history. A preview shows the impact on the current catalogue before the change is committed.

---

## 7. Reporting

Sales by period, category, fabric, occasion. GST summary for return filing. Bespoke vs ready-to-wear mix. Atelier throughput and delay analysis. Return rate by product (a high return rate on one product signals a sizing or description problem). Customer lifetime value by tier.

All exportable to CSV/Excel — the accountant will want the data in their own tools.

---

## 8. Access control & audit

Roles from Phase 0 mapped to real permissions. Staff see what they need, not everything — a stitching assignee has no reason to see customer payment details.

**Audit log** for every privileged action: price change, order state override, refund, stock adjustment, media approval. Immutable, with actor and timestamp. This is both a security control and a training aid.

---

## 9. Training manual (explicit brief requirement)

A **PDF training manual** for the owner and manager, versioned in the repository and regenerated when workflows change.

Contents:
1. Daily operations checklist
2. Adding a product (with modesty attributes explained — why each field matters commercially)
3. Processing a standard order
4. Processing a bespoke order through the atelier pipeline
5. Handling returns and issuing credit notes
6. Reviewing and approving media
7. Reading the reports
8. GST filing preparation
9. Troubleshooting: "what to do when X"
10. Escalation contacts

Written for a non-technical reader, screenshot-driven, in plain language. **Screenshots regenerated automatically from a seeded demo environment** so the manual cannot silently drift from the software.

---

## 10. Exit criteria

- [ ] Owner can complete every routine task without a developer
- [ ] Atelier pipeline tracks a bespoke order end to end with assignees and due dates
- [ ] Capacity overrun is surfaced before delivery promises are made
- [ ] Bulk import validates and previews before committing
- [ ] Stock ledger reconciles; every movement attributable
- [ ] GST regimes editable with audit trail; history immutable
- [ ] Audit log captures all privileged actions
- [ ] Training manual PDF generated, reviewed by the actual owner, and screenshots auto-regenerated
