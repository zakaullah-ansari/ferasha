# Ferasha — Implementation Roadmap

**Platform:** www.ferasha.com — luxury South Asian womenswear & bespoke tailoring
**Architecture:** Next.js 15 PWA + Django 5 REST core + FastAPI AI engine · PostgreSQL 16 · Redis 7
**Team:** solo, part-time developer
**Last updated:** 2026-09-07

---

## Phase index

Each phase has a detailed specification in [`docs/phases/`](./phases/).

| # | Phase | Status | Effort | Detail |
|---|---|---|---|---|
| 0 | Foundation, Environment & Tax Engine | ✅ **Complete** | ~35 h | [PHASE-00](./phases/PHASE-00-FOUNDATION.md) |
| 1 | Domain Models & Data Integrity | ✅ **Complete** | ~32 h | [PHASE-01](./phases/PHASE-01-DOMAIN-MODELS.md) |
| 2 | API Surface & Auth Hardening | ⬜ | 28–34 h | [PHASE-02](./phases/PHASE-02-API-AUTH.md) |
| 3 | AI Engine: Face-Blur Privacy Pipeline | ⬜ | 24–30 h | [PHASE-03](./phases/PHASE-03-AI-PRIVACY.md) |
| 4 | Frontend Foundation & Design System | ⬜ | 34–42 h | [PHASE-04](./phases/PHASE-04-FRONTEND.md) |
| 5 | Commerce: Cart, Checkout, Payments | ⬜ | 40–48 h | [PHASE-05](./phases/PHASE-05-COMMERCE.md) |
| 6 | Merchandising, Search & Discovery | ⬜ | 26–32 h | [PHASE-06](./phases/PHASE-06-MERCHANDISING.md) |
| 7 | Loyalty, Rewards & Retention | ⬜ | 20–26 h | [PHASE-07](./phases/PHASE-07-LOYALTY.md) |
| 8 | Integrations, Messaging & Notifications | ⬜ | 36–44 h | [PHASE-08](./phases/PHASE-08-INTEGRATIONS.md) |
| 9 | Admin, Operations & Atelier Workflow | ⬜ | 30–36 h | [PHASE-09](./phases/PHASE-09-ADMIN-OPS.md) |
| 10 | LangChain Agentic Workflows | ⬜ *optional* | 26–32 h | [PHASE-10](./phases/PHASE-10-AI-AGENTS.md) |
| 11 | Production Readiness & Compliance | ⬜ | 32–40 h | [PHASE-11](./phases/PHASE-11-PRODUCTION.md) |
| 12 | Migration, Launch & Post-Launch | ⬜ | 20–26 h | [PHASE-12](./phases/PHASE-12-LAUNCH.md) |

Supporting: [Tech stack decisions](./TECH-STACK.md)

---

## Critical path

```
0 ──> 1 ──> 2 ──┬──> 4 ──> 5 ──> 7 ──┐
                │         │           │
                ├──> 3 ───┤           ├──> 11 ──> 12
                │         │           │
                ├──> 6 ───┘           │
                │         8 ──────────┤
                └──> 9 ───────────────┘
                          10 (optional, off critical path)
```

Phases 3, 6 and 9 parallelise once Phase 2 fixes the API contract.

---

## Timeline

| Track | Hours | At 10 h/week | At 20 h/week |
|---|---|---|---|
| **Launch-critical** (0–9, 11, 12) | 300–360 | 30–36 weeks | 15–18 weeks |
| With Phase 10 | 326–392 | 33–39 weeks | 16–20 weeks |

Estimates assume single-developer focus and exclude content production (product photography, description writing), which runs as a parallel non-engineering workstream.

**Fastest path to revenue:** Phases 0–5 + 11 + 12 with Tier-1 integrations only ≈ 220–265 h. Phases 6, 7, 9 (beyond basic admin) and 10 follow post-launch.

---

## Recommendations that depart from the brief

These are considered judgements, not oversights. Each is argued in the linked phase.

| # | Brief said | Recommendation | Rationale |
|---|---|---|---|
| 1 | `models.JSONBField` | `models.JSONField` | The former does not exist in Django 5. The latter maps to native `jsonb`. |
| 2 | Modesty attributes as custom/JSON | **Typed columns** | Faceted-search inputs need indexes, constraints and aggregation. JSON gives none of these. [P1](./phases/PHASE-01-DOMAIN-MODELS.md) |
| 3 | All 12 integrations | **Tiered: 5 at launch** | 12 live dependencies before revenue is unsustainable for a solo developer. [P8](./phases/PHASE-08-INTEGRATIONS.md) |
| 4 | Loyalty/rewards programme | **Tiered status, not points** | Bridal purchase frequency is low; expiring points are worthless and discounting devalues a luxury brand. [P7](./phases/PHASE-07-LOYALTY.md) |
| 5 | Product recommendations | **Rules first, ML later** | With 50 SKUs and no interaction history, curated rules beat ML and are debuggable. [P6](./phases/PHASE-06-MERCHANDISING.md) |
| 6 | (unstated) | **Elasticsearch deferred** | Postgres FTS is sufficient at this catalogue size. Add a second datastore on evidence. [P6](./phases/PHASE-06-MERCHANDISING.md) |
| 7 | AI engine prominent | **Phase 10, optional** | Agentic features on an unstable domain model are wasted work. [P10](./phases/PHASE-10-AI-AGENTS.md) |
| 8 | Three colour tokens | **Full tonal ramps + contrast audit** | Gold on ivory is ~2.3:1 and fails WCAG AA for body text. [P4](./phases/PHASE-04-FRONTEND.md) |

---

## Locked architectural decisions

| # | Decision | Ruling |
|---|---|---|
| D1 | Identity | Django is the sole issuer. FastAPI verifies HS256 tokens with the shared key; it never mints them. |
| D2 | Database | Django owns all migrations. The AI engine touches only `ai_*` tables. |
| D3 | GST rates | Date-effective regimes + validated per-line override. |
| D4 | Image privacy | Fail-closed. Originals never publicly routable; approval only via signed callback. |
| D5 | Payments | Razorpay primary, behind a `PaymentGateway` port. |
| D6 | Money | `Decimal` only, 2dp, `ROUND_HALF_UP`. Floats banned in the money path. |
| D7 | Tax on invoices | Snapshotted at checkout, never recomputed on read. |

---

## Risk register

| Risk | Impact | Mitigation | Phase |
|---|---|---|---|
| Unblurred face published | 🔴 Severe — DPDP breach, vendor trust | Fail-closed pipeline; originals never public; human review on zero-detection | 3 |
| **GST rates go stale again** | 🔴 Severe — recoverable liability + penalty | Date-effective regimes; annual audit; admin-editable with audit trail | 0, 9 |
| SEO lost in migration | 🔴 Severe — immediate revenue loss | Complete 301 map; daily Search Console review for 2 weeks | 12 |
| Postgres-only behaviour unverified | 🟠 High | Full suite against `postgres:16` is the first task of Phase 11 | 11 |
| Measurement data corruption | 🟠 High — ruined garments, refunds | JSON Schema + plausibility ranges + append-only revisions | 1 |
| Payment double-charge | 🟠 High | Idempotency keys, webhook signature + replay protection | 5 |
| Integration scope creep | 🟠 High — delays launch | Explicit tiering; Tier 3 requires evidence of need | 8 |
| Solo-developer bus factor | 🟠 High | ADRs, tests as executable spec, runbooks, training manual | all |
| Float in money path | 🔴 Severe — audit failure | `Decimal` only; lint rule in CI | 0, 11 |
| Atelier capacity overrun | 🟡 Medium — missed promises | Capacity surfaced before delivery dates are quoted | 9 |

---

## Definition of Done — every phase

1. No `TODO`, no placeholder, no commented-out logic
2. Type-checked (`mypy` strict / TS strict) and lint-clean
3. Tests cover happy path, boundaries and failure modes
4. Constraints enforced at the database level, not only in application code
5. Secrets from environment/secret manager, never literals
6. Runs in `docker compose up` from a clean clone
7. Verified by **execution**, not assertion — exit criteria demonstrated, not claimed
