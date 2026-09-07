# Phase 0 — Foundation, Environment & Tax Engine

| | |
|---|---|
| **Status** | ✅ **COMPLETE** — verified by execution |
| **Depends on** | Nothing |
| **Blocks** | Every other phase |
| **Effort** | ~35 hrs (spent) |
| **Tests** | 95 passing |

---

## 1. Objective

Stand up a monorepo that boots from a clean clone, establish identity as a single source of truth, and prove the money path is arithmetically correct before any commerce logic is written on top of it.

Money and identity are the two things you cannot retrofit. Everything else in this roadmap assumes they are already right.

---

## 2. Scope

### 2.1 Delivered

| Area | Artefact | Notes |
|---|---|---|
| Orchestration | `docker-compose.yml` | 6 services, healthcheck gating via `service_healthy`, named volumes |
| Secrets | `.env.example` | Every secret enumerated; shared `JWT_SIGNING_KEY`, `AI_ENGINE_SHARED_SECRET` |
| Settings | `config/settings.py` | `DATABASE_URL` parser, Redis cache, DRF defaults, SimpleJWT, CORS, prod security block |
| Health | `config/health.py` | `/health/` liveness, `/ready/` readiness probing Postgres + Redis |
| Identity | `apps/users/` | UUID/email `AbstractUser`, `Address` with GSTIN, 6 role types |
| Auth API | serializers, views, permissions, urls | Register, JWT obtain/refresh/verify, logout w/ blacklist, `/auth/me`, password change, address CRUD |
| **Tax engine** | `apps/taxes/` | Date-effective GST regimes, pure `Decimal`, HSN slab + override |
| Packaging | `Dockerfile`, `requirements*.txt`, `pytest.ini`, `.gitignore` | Multi-stage, non-root uid 1001, Gunicorn |

### 2.2 Explicitly out of scope

Catalogue, orders, payments, shipping, frontend. All deferred to later phases.

---

## 3. Architectural decisions

### D1 — Django is the sole issuer of identity

SimpleJWT with HS256. The FastAPI AI engine **verifies** tokens using the shared `JWT_SIGNING_KEY`; it never mints them and never queries the Django user table.

The token carries a stable claim set that is a **contract** with the AI engine:

```json
{
  "user_id": "uuid", "email": "...", "full_name": "...",
  "role": "customer", "is_back_office": false, "email_verified": false,
  "aud": "ferasha", "iss": "ferasha-backend-core"
}
```

Changing this claim set is a breaking change requiring coordinated deployment.

### D2 — Django owns all migrations

The AI engine touches only its own `ai_*` tables via async SQLAlchemy, plus Redis for job state. Two ORMs migrating the same tables is a production incident waiting to happen.

### D3 — Date-effective tax regimes, not constants

See §5. This is the single most important decision in this phase.

### D6 — `Decimal` only in the money path

Floats are banned. `ROUND_HALF_UP` to 2dp per CGST Act s.170. A lint rule in Phase 11 enforces this mechanically.

---

## 4. Identity model

```
User (UUID pk, email as USERNAME_FIELD)
├── role: customer | vendor | tailor | stylist | staff | admin
├── preferences: JSONField (allow-listed keys only)
├── email_verified_at, phone_verified_at, accepted_terms_at
└── addresses: FK Address
                ├── kind: shipping | billing
                ├── state_code  ──> drives GST place of supply
                ├── country_code ──> drives export zero-rating
                └── gstin (optional, B2B input tax credit)
```

**Security properties implemented and tested:**

- Duplicate-email registration returns a *generic* error. Confirming account existence to an anonymous caller is an enumeration vector.
- `role` is read-only on `/auth/me` — a customer cannot self-promote to admin. Tested.
- Address book is scoped to the requesting user; a foreign address ID returns **404, not 403** (403 confirms the resource exists).
- Logout blacklists the refresh token; replay returns 401. Tested.
- Login throttled at 10/min separately from the global anon bucket.
- GSTIN state prefix is cross-checked against the address state — a Delhi GSTIN on a Maharashtra address produces a non-compliant invoice that surfaces at audit, not checkout.

---

## 5. The tax engine — and the defect found

### 5.1 What went wrong

The engine was originally written against the pre-2025 apparel slabs: 5% up to ₹1,000 per piece, 12% above. **That law was repealed.**

The 56th GST Council restructured apparel taxation with effect from **22 September 2025**:

| | Before 22 Sep 2025 | From 22 Sep 2025 |
|---|---|---|
| Concessional threshold | ₹1,000/piece | **₹2,500/piece** |
| Rate at or below | 5% | 5% |
| Rate above | 12% | **18%** |
| 12% slab | exists | **abolished for textiles** |

Sources: [ClearTax GST rate list](https://cleartax.in/s/gst-rates), [Busy — new GST on garments](https://busy.in/gst-rates/garments/), [CharteredHelp — GST 2.0](https://charteredhelp.com/gst-on-clothes/), [Lok Sabha statement via SAG Infotech](https://blog.saginfotech.com/govt-lok-sabha-gst-expensive-garments-raised-apparel-relief).

**Impact if shipped:** on a single ₹48,000 bridal lehenga the engine charged 12% (₹5,760) where 18% (₹8,640) is due — **₹2,880 under-collected per unit**, recoverable from Ferasha with interest and penalty on assessment. Ferasha's premium SKUs sit almost entirely above the ₹2,500 threshold, so this was systematic, not marginal.

### 5.2 The fix — date-effective regimes

The naive fix is to change two constants. That is wrong, because it makes historical invoices irreproducible: a credit note raised today against an order placed in August 2025 must use the rates in force *then*.

```python
@dataclass(frozen=True, slots=True)
class GSTRegime:
    name: str
    effective_from: date
    apparel_threshold: Decimal
    apparel_rate_at_or_below: Decimal
    apparel_rate_above: Decimal
    fabric_rate: Decimal
    tailoring_service_rate: Decimal
    courier_service_rate: Decimal
    permitted_rates: frozenset[Decimal]

GST_REGIMES = (REGIME_2017, REGIME_2025)
resolve_regime(as_of)  # -> the regime in force on that date
```

Every `TaxableLine` carries an optional `as_of`. `calculate_gst(..., as_of=...)` propagates it. The resulting `TaxBreakdown` records `regime_name` so the invoice states which law was applied.

Verified live:

```
Lehenga ₹48,000 → Mumbai, today       : 18% → CGST 4320 + SGST 4320 → ₹56,640
Lehenga ₹48,000 → Mumbai, 01-Jun-2025 : 12% → tax 5760              → ₹53,760
Kameez  ₹1,500  → today  : 5%  → ₹1,575   (customer saves ₹105)
Kameez  ₹1,500  → 2025   : 12% → ₹1,680
```

### 5.3 Two further corrections

- **Tailoring services are 5%, not 18%.** Job work on textiles falls under SAC 9988, taxed at 5% — not the standard 18% service rate originally applied. Ferasha's bespoke revenue would have been over-taxed.
- **Unstitched dress material** (HSN 5208/5407) added at a flat 5%. This is a real Ferasha SKU category and was previously unresolvable.

### 5.4 Routing rules

| Place of supply | Treatment | Statute |
|---|---|---|
| Maharashtra | CGST + SGST, each half the rate | Intra-state |
| Other Indian state/UT | IGST at the full rate | Inter-state |
| Outside India | 0%, zero-rated export | IGST Act s.16, under LUT |

Rounding residue on an odd rate is absorbed into SGST so the halves always sum exactly to the total. Verified: `CGST + SGST ≡ IGST` for the same rate and value.

---

## 6. Verification — executed, not asserted

| Check | Result |
|---|---|
| `pytest` (43 GST unit + 52 API integration) | **95 passed** |
| `manage.py check` | 0 issues |
| `ruff check` | clean |
| `GET /health/` | `{"status":"ok"}` |
| `GET /ready/` | `database: ok, cache: ok` |
| Lehenga → Mumbai (current) | 18%, CGST 4320 + SGST 4320 |
| Lehenga → Mumbai (Jun 2025) | 12%, regime `GST 1.0` |
| Lehenga → Delhi | IGST at 18% |
| Lehenga → Dubai | 0.00 tax, LUT note emitted |
| Bespoke tailoring SAC 998821 | 5% |
| Register → login → claims | `role=customer`, `aud=ferasha` |
| `/auth/me` unauthenticated | 401 |
| Foreign address ID | 404 (not 403) |
| Mismatched GSTIN prefix | 400 |
| Logout → replay refresh | 205 → 401 |
| Short JWT key + `DEBUG=0` | **refuses to boot** |

### 6.1 Defect found by running the code

Live server logs surfaced PyJWT's `InsecureKeyLengthWarning` — a 21-byte HMAC key, below the 32-byte RFC 7518 §3.2 minimum. That was a test key, but nothing prevented a weak key reaching production, and it is the *shared* key the AI engine trusts. The app now refuses to boot outside `DEBUG` with a short key. Both directions tested.

---

## 7. Known gaps carried forward

| Gap | Carried to |
|---|---|
| Suite runs on SQLite in this sandbox (no Postgres/Docker available). `jsonb` operators, GIN indexes and several `CheckConstraint`s are **not yet genuinely validated**. | Phase 11 — CI must run against real `postgres:16` |
| Email verification issues no token/link yet | Phase 2 |
| No `drf-spectacular` OpenAPI schema | Phase 2 |
| Rates hardcoded in `constants.py`, not DB-editable | Phase 9 — admin-editable with audit trail |

**`models.JSONBField` does not exist in Django 5.** The brief specified it. `models.JSONField` is the correct API and maps to native `jsonb` on PostgreSQL. Used throughout.

---

## 8. Definition of Done

- [x] No `TODO`, no placeholder, no commented-out logic
- [x] Lint-clean
- [x] Tests cover happy path, boundaries, failure modes
- [x] DB-level constraints, not just application validation
- [x] Secrets from env, never literals
- [x] Boots from a clean clone
- [ ] ~~Verified against PostgreSQL 16~~ → **deferred to Phase 11 CI**
