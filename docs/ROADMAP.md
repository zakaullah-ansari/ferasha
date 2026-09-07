# Ferasha — Phasewise Implementation Roadmap

**Version:** 1.0 · **Owner:** solo part-time developer · **Target:** www.ferasha.com
**Architecture:** Hybrid micro-monolith — Next.js 15 PWA + Django 5 REST core + FastAPI AI engine, on shared PostgreSQL 16 + Redis 7.

---

## 0. Locked architectural decisions

These were resolved before implementation and are treated as fixed. Reversing any of them mid-build is expensive.

| # | Decision | Ruling | Rationale |
|---|---|---|---|
| D1 | Identity ownership | Django is the sole issuer of credentials. SimpleJWT, HS256, custom `AbstractUser` keyed by UUID, email as `USERNAME_FIELD`. | One source of truth. FastAPI verifies Django-signed tokens with a shared `JWT_SIGNING_KEY`; it never mints them. |
| D2 | Database ownership | Django owns **all** migrations. The AI engine touches only its own `ai_*` tables via async SQLAlchemy, plus Redis for job state. | Two ORMs migrating the same tables is a production incident waiting to happen. |
| D3 | GST rate model | HSN/SAC slab resolution **plus** a validated per-line `rate_override`. | Correctness by default, escape hatch for genuine edge cases. Override is whitelisted against lawful rates. |
| D4 | Image privacy pipeline | Fail-closed. Upload → `PENDING_MODERATION` (never publicly served) → Redis job → MediaPipe blur → derivative written → callback marks `APPROVED`. | An unblurred face must never be reachable, even if the worker crashes. |
| D5 | Payments | Deferred. Domain layer (orders, tax, fit profiles) only in the foundation phases. | Avoids premature gateway lock-in; the order model is designed so a gateway drops in without refactor. |
| D6 | Money handling | `Decimal` only, 2dp, `ROUND_HALF_UP`. Floats are banned in the money path. | CGST Act s.170 rounding. Float drift is an audit failure. |
| D7 | Scope of pass 1 | Full runnable vertical slice, not just the four named files. | `docker compose up` must actually boot. |

---

## Phase status legend

`✅ DONE` · `🟡 IN PROGRESS` · `⬜ NOT STARTED`

---

## PHASE 0 — Foundation & Environment · ✅ DONE (79/79 tests green)

**Goal:** the monorepo boots, secrets are structured, money math is proven correct.

### 0.1 Repo & orchestration — ✅ DONE
- [x] Monorepo tree: `frontend/`, `backend-core/`, `ai-engine/`, `docs/`
- [x] `docker-compose.yml` — 6 services: Postgres 16 (5432), Redis 7 (6379), Django (8000), FastAPI (8001), AI worker, Next.js (3000). Healthchecks with `service_healthy` gating; named volumes `postgres-data`, `redis-data`, shared `media-data`.
- [x] `.env.example` — every secret enumerated, `JWT_SIGNING_KEY` shared Django↔FastAPI, `AI_ENGINE_SHARED_SECRET` for internal callbacks.
- [x] `.gitignore` — Python, Node, Django artefacts, env files, model caches.

### 0.2 Django settings — ✅ DONE
- [x] `config/settings.py` (230 lines): `DATABASE_URL` parser, Redis cache, DRF defaults (JWT auth, `IsAuthenticated` default-deny, throttling, pagination), SimpleJWT with rotation + blacklist, CORS, production security block (HSTS, SSL redirect, secure cookies) gated on `DEBUG`.

### 0.3 GST engine — ✅ DONE (31/31 tests green)
- [x] `apps/taxes/constants.py` — 38 state/UT → GST numeric codes, HSN 6204/6211/6214/6307, SAC 998821/999722, slab threshold ₹1000, whitelist of lawful rates.
- [x] `apps/taxes/services.py` (430 lines) — pure Python, zero Django imports. `PlaceOfSupply`, `TaxableLine`, `LineTax`, `TaxBreakdown` (frozen slotted dataclasses). Maharashtra → CGST+SGST; other Indian state → IGST; non-India → zero-rated export under LUT. Tax-inclusive back-out with slab convergence. Composite-supply shipping at the principal rate. Rounding residue absorbed into SGST so halves always sum exactly.
- [x] `tests/test_gst_engine.py` — 31 tests: slab boundaries (₹1000.00 vs ₹1000.01), post-discount per-piece valuation, dotted HSN (`6204.42.00`), override precedence, unlawful-override rejection, CGST+SGST ≡ IGST parity, JSON-safety, total consistency invariants.

### 0.4 Identity API & service boot — ✅ DONE
- [x] `apps/users/serializers.py` — `FerashaTokenObtainPairSerializer` (embeds `email`/`role`/`is_back_office`/`email_verified` claims consumed by the ai-engine), `RegistrationSerializer` (password confirmation, `validate_password`, terms gate, non-enumerable duplicate-email error), `AddressSerializer` (state validation against the GST code table, 6-digit PIN, **GSTIN state-prefix cross-check**), `UserSerializer` (preference key allow-list), `PasswordChangeSerializer`
- [x] `apps/users/permissions.py` — `IsOwnerOrBackOffice`, `IsBackOffice`, `IsVendorOrBackOffice`, `IsTailorOrBackOffice`, `ReadOnlyOrBackOffice`
- [x] `apps/users/views.py` — registration, token obtain/refresh/verify, logout with refresh blacklisting, `/auth/me`, password change, `AddressViewSet` scoped to the requesting user; `LoginRateThrottle` at 10/min
- [x] `apps/users/urls.py`, `admin.py`, all five `apps.py`
- [x] `apps/taxes/serializers.py` + `views.py` + `urls.py` — `POST /api/v1/tax/quote/`, `GET /api/v1/tax/reference/`
- [x] `config/urls.py`, `wsgi.py`, `asgi.py`, `health.py` (liveness + readiness probing Postgres and Redis), `manage.py`
- [x] `requirements.txt`, `requirements-dev.txt`, multi-stage `Dockerfile` (non-root uid 1001, healthcheck, Gunicorn)
- [x] `pytest.ini`, `.gitignore`, `config/settings_test.py` (SQLite fallback), `config/settings_demo.py`
- [x] `users/migrations/0001_initial.py` — both DB constraints emitted
- [x] `manage.py check` → 0 issues; `ruff` → clean

**Verified by execution, not assertion:**

| Check | Result |
|---|---|
| `pytest` (31 GST unit + 48 API integration) | **79 passed** |
| `GET /api/v1/health/` | `{"status":"ok"}` |
| `GET /api/v1/ready/` | `database: ok, cache: ok` |
| Tax quote — Maharashtra | CGST 600.00 + SGST 600.00, total 11200.00 |
| Tax quote — Delhi | IGST 1200.00, total 11200.00 |
| Tax quote — UAE | tax 0.00, LUT export note emitted |
| Register → login → JWT claims | `role=customer`, `aud=ferasha`, `iss=ferasha-backend-core` |
| `/auth/me` unauthenticated | 401 |
| Address with mismatched GSTIN prefix | 400 |
| Logout → reuse refresh token | 205 → 401 (blacklist works) |

**Sandbox note:** this environment has no PostgreSQL, Docker or root access, so the HTTP suite was executed against SQLite via `config.settings_test`. `jsonb` operators, GIN indexes and several `CheckConstraint`s are only meaningfully exercised on Postgres — the CI pipeline in Phase 7 must run the same suite against a real `postgres:16` service. The Postgres path is the default in `config/settings.py`; SQLite is test-only.

---

## PHASE 1 — Domain Models & Data Integrity · ⬜

**Goal:** every business entity exists in Postgres with constraints enforced at the DB level, not just in Python.

### 1.1 `apps/catalog`
- `Category` (MPTT-style self-FK: Karachi Suits → Lawn / Chiffon / Organza; Bridal → Lehenga / Gharara; Farshi Palazzo)
- `Product` — slug, vendor FK, HSN code, `base_price` (Decimal), `rate_override` (nullable, per D3), fabric, work type (zardozi / mirror / gota), occasion
- **Modesty attributes as first-class DB columns**, not JSON: `is_opaque` (bool), `has_full_lining` (bool), `slit_coverage` (enum: `none` / `knee` / `mid_calf` / `ankle` / `full`), `sleeve_coverage` (enum), `neckline_modesty` (enum), `requires_slip` (bool)
- `ModestyBadge` derivation service — pure function mapping attributes → displayable badge set, shared by API serializer and frontend types
- `ProductVariant` — size (XS–XXL), colour, `stock_quantity`, per-variant SKU
- DB `CheckConstraint`s: non-negative price, non-negative stock, valid enum values

### 1.2 `apps/tailoring`
- `BespokeFitProfile` — `models.JSONField` (native `jsonb` on Postgres; note `models.JSONBField` does not exist in Django 5 — `JSONField` is the correct API and maps to `jsonb`)
  - `measurements` jsonb: bust, underbust, waist, hip, shoulder, kameez_length, sleeve_length, armhole, neck_depth_front/back, trouser_length, farshi_flare, ghera
  - `preferences` jsonb: sleeve_type, lining_preference, neckline, closure, hem_finish
  - `unit_system` (cm/inch), `measured_by` (self / tailor / stylist), `verified_at`
- **JSON Schema validation** on save via a `validators.py` module — a raw jsonb field with no schema is a data-integrity hole
- GIN index on the jsonb columns for queryability
- `FitProfileRevision` — append-only history; measurements change between orders and disputes need an audit trail
- `TailoringOrderSpec` — snapshot of the profile at order time (never a live FK; the profile mutates)

### 1.3 `apps/orders`
- `Order`, `OrderLine`, `OrderTaxSnapshot` — the tax breakdown is **persisted at checkout**, never recomputed on read (rates change; invoices are immutable)
- Place-of-supply resolved from the shipping `Address` and frozen onto the order
- State machine: `draft → placed → in_atelier → stitching → qc → shipped → delivered`

**Exit criteria:** full `makemigrations`/`migrate` clean; factory-boy fixtures; constraint tests proving invalid modesty enums and negative stock are rejected by Postgres.

**Effort:** ≈ 20–25 hours.

---

## PHASE 2 — API Surface & Auth Hardening · ⬜

- DRF serializers + ViewSets for catalog (public read), tailoring (owner-only), orders
- **Object-level permissions**: a customer must never read another customer's fit profile. Custom `IsOwnerOrBackOffice`.
- Role-gated routes per `UserRole` (customer / vendor / tailor / stylist / staff / admin)
- Registration, email verification, password reset, token refresh + blacklist on logout
- `django-filter` facets: modesty attributes, price band, fabric, occasion
- OpenAPI 3.1 schema via `drf-spectacular` → **generated TypeScript client for the frontend** (single source of truth for types)
- Rate limiting per role; brute-force lockout on login
- `/api/v1/tax/quote/` endpoint wrapping the Phase 0 engine

**Exit criteria:** contract tests for every endpoint; authz test matrix (each role × each endpoint × own/other resource).

**Effort:** ≈ 25–30 hours.

---

## PHASE 3 — AI Engine: Privacy Pipeline · ⬜

**This is the compliance-critical phase. Fail-closed throughout.**

- `ai-engine/app/main.py` — FastAPI ASGI app, CORS, lifespan-managed MediaPipe model load (load **once** at startup, not per request), `/health`, `/ready`
- `app/core/security.py` — HS256 JWT verification against the shared key; internal-callback HMAC using `AI_ENGINE_SHARED_SECRET`
- `app/services/face_blur.py` — MediaPipe Face Detection (short + full-range models), bounding boxes expanded by a configurable margin, **elliptical** Gaussian mask (rectangles look cheap on editorial imagery), kernel size scaled to face size so small faces are as unrecoverable as large ones. Returns processed buffer + detection metadata.
- **Irreversibility check** — blur strength validated so the operation is not invertible; this is the actual privacy guarantee
- `app/worker.py` — Redis consumer, idempotent by job ID, exponential backoff, dead-letter queue
- `apps/media_assets` (Django side) — `MediaAsset` with `moderation_status`, original stored outside the public path, only the derivative is servable
- Zero-detection policy: an image where no face is found is still reviewed, not auto-approved
- Tests with synthetic faces asserting pixel variance collapse inside the mask region

**Exit criteria:** upload → blurred derivative end-to-end in compose; killing the worker mid-job leaves the asset `PENDING`, never `APPROVED`.

**Effort:** ≈ 20–25 hours.

---

## PHASE 4 — Frontend Foundation · ⬜

- Next.js 15 App Router, TypeScript strict, `tailwind.config.ts` with `ferasha-gold #C5A059`, `ferasha-obsidian #1A1A1A`, `ferasha-ivory #FDFBF7`, plus tonal ramps (a single hex per token is not enough for hover/border/disabled states)
- Typography: display serif for headings, clean sans for UI; fluid type scale
- `components/FitDrawer.tsx` — Framer Motion slide-out, tab toggle between **Standard (XS–XXL)** and **Bespoke**; bespoke inputs for bust, waist, farshi flare, sleeve length, full-lining toggle; cm/inch switch; **Zod validation with plausibility ranges**; focus trap, `Esc` to close, `aria-modal`, restore focus on close; persists to the Phase 1 `BespokeFitProfile` API
- Modesty badge components driven by the Phase 1 derivation service
- Server Components for catalog, Client Components only where interactive
- PWA: manifest, service worker, offline shell, installability

**Exit criteria:** Lighthouse ≥ 90 across the board; axe-core zero critical violations; keyboard-only journey through the FitDrawer.

**Effort:** ≈ 30–35 hours.

---

## PHASE 5 — Commerce Flows · ⬜

- Cart (guest + authenticated, merge on login), checkout, address book with GSTIN capture
- Live tax quote in checkout via the Phase 2 endpoint
- Payment gateway integration (D5 deferred decision — Razorpay for domestic, evaluate Stripe for export)
- GST-compliant invoice PDF: GSTIN, HSN-wise summary, place of supply, LUT declaration on exports
- Order tracking through the atelier state machine; email/WhatsApp notifications

**Effort:** ≈ 30–40 hours.

---

## PHASE 6 — LangChain Agentic Workflows · ⬜

Deliberately last. Agentic features on an unstable domain model are wasted work.

- Styling assistant (occasion + budget + modesty preference → curated set)
- Measurement guidance agent (conversational fit intake, escalates to human tailor)
- Vendor description enrichment with human-in-the-loop approval
- Strict cost controls: token budgets, caching, timeouts, graceful degradation when `OPENAI_API_KEY` is absent

**Effort:** ≈ 25–30 hours.

---

## PHASE 7 — Production Readiness · ⬜

- Gunicorn/Uvicorn workers, WhiteNoise → CDN, S3-compatible object storage for media
- CI: GitHub Actions — ruff, mypy, pytest with coverage gate, `npm run build`, Trivy image scan
- Sentry, structured JSON logging with correlation IDs across all three services
- Backups: nightly `pg_dump` + PITR, tested restore runbook
- Security pass: OWASP top 10, dependency audit, rate-limit tuning, secret rotation procedure
- DPDP Act 2023 compliance: consent records, data export, deletion (measurements are sensitive personal data)

**Effort:** ≈ 25–30 hours.

---

## Critical path & sequencing

```
Phase 0 ──> Phase 1 ──> Phase 2 ──┬──> Phase 4 ──> Phase 5 ──> Phase 7
                                  └──> Phase 3 ──────┘
                                            Phase 6 ──┘
```

Phase 3 (AI engine) runs parallel to Phase 4 once Phase 2 fixes the API contract. Phase 6 is strictly optional for launch.

**Total to launchable MVP (Phases 0–5, 7):** ≈ 190–230 hours. At 10 hrs/week part-time, ≈ 5–6 months. Dropping Phase 6 and deferring PWA offline saves ≈ 6 weeks.

---

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Unblurred face leaks publicly | Severe — privacy + vendor trust | D4 fail-closed: originals never in the public path; approval only on worker callback |
| MediaPipe misses a face (veil, profile, low light) | High | Full-range + short-range models, mandatory human review on zero-detection, never auto-approve |
| GST rates change in a Budget | Medium | Rates isolated in `constants.py`; tax snapshot persisted per order so historical invoices stay correct |
| jsonb measurements drift schema-less | High — bad garments, refunds | JSON Schema validation on save + append-only revision history |
| Solo-dev bus factor | High | ADRs in `docs/`, tests as executable spec, no undocumented cleverness |
| Float creeps into money math | Severe — audit failure | D6 `Decimal` only; lint rule to ban `float()` in `apps/taxes` and `apps/orders` |
| Scope creep into AI features pre-revenue | Medium | Phase 6 gated behind a working checkout |

---

## Definition of Done (every phase)

1. No `TODO`, no placeholder, no commented-out logic
2. Type-checked (`mypy` strict / TS strict) and lint-clean (`ruff` / `eslint`)
3. Tests covering the happy path, boundaries, and failure modes
4. DB-level constraints, not just application validation
5. Secrets from env, never literals
6. Runs in `docker compose up` from a clean clone
