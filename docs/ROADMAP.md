# Ferasha — Implementation Roadmap

**Platform:** www.ferasha.com — luxury South Asian womenswear & bespoke tailoring
**Architecture:** Next.js 15 PWA + Django 5 REST core + FastAPI AI engine · PostgreSQL 16 · Redis 7
**Team:** solo, part-time developer
**Last updated:** 2026-10-26

---

## Phase index

Each phase has a detailed specification in [`docs/phases/`](./phases/).

| # | Phase | Status | Effort | Detail |
|---|---|---|---|---|
| 0 | Foundation, Environment & Tax Engine | ✅ **Complete** | ~35 h | [PHASE-00](./phases/PHASE-00-FOUNDATION.md) |
| 1 | Domain Models & Data Integrity | ✅ **Complete** | ~32 h | [PHASE-01](./phases/PHASE-01-DOMAIN-MODELS.md) |
| 2 | API Surface & Auth Hardening | ✅ **Complete** | ~30 h | [PHASE-02](./phases/PHASE-02-API-AUTH.md) |
| 3 | AI Engine: Face-Blur Privacy Pipeline | 🟡 **6/9 verified** | ~28 h | [PHASE-03](./phases/PHASE-03-AI-PRIVACY.md) |
| 4 | Frontend Foundation & Design System | 🟡 **~70%** | 34–42 h | [PHASE-04](./phases/PHASE-04-FRONTEND.md) |
| 5 | Commerce: Cart, Checkout, Payments | ⬜ | 40–48 h | [PHASE-05](./phases/PHASE-05-COMMERCE.md) |
| 6 | Merchandising, Search & Discovery | ⬜ | 26–32 h | [PHASE-06](./phases/PHASE-06-MERCHANDISING.md) |
| 7 | Loyalty, Rewards & Retention | ⬜ | 20–26 h | [PHASE-07](./phases/PHASE-07-LOYALTY.md) |
| 8 | Integrations, Messaging & Notifications | ⬜ | 36–44 h | [PHASE-08](./phases/PHASE-08-INTEGRATIONS.md) |
| 9 | Admin, Operations & Atelier Workflow | ⬜ | 30–36 h | [PHASE-09](./phases/PHASE-09-ADMIN-OPS.md) |
| 10 | LangChain Agentic Workflows | ⬜ *optional* | 26–32 h | [PHASE-10](./phases/PHASE-10-AI-AGENTS.md) |
| 11 | Production Readiness & Compliance | ⬜ | 32–40 h | [PHASE-11](./phases/PHASE-11-PRODUCTION.md) |
| 12 | Migration, Launch & Post-Launch | ⬜ | 20–26 h | [PHASE-12](./phases/PHASE-12-LAUNCH.md) |

Supporting: [Tech stack decisions](./TECH-STACK.md) · [Design system & UI libraries](./DESIGN-SYSTEM.md)

---

## Progress — 2026-10-26

**Launch-critical burn-down:** roughly 130–140 h of 300–360 h **written** (≈ 40%). Written is not the same as verified — see [Verification debt](#verification-debt).

Test run of 2026-10-26, after clearing V1–V3 below. Executed, not asserted:

| Service | Code | Result |
|---|---|---|
| `backend-core` (Django 5) | 11,062 LOC across 7 apps | **384 passed, 1 skipped** |
| `ai-engine` (FastAPI) | face-blur service + worker | **58 passed, 19 skipped** |
| `frontend` (Next.js 15) | 3,293 LOC | **174 passed**, `tsc --noEmit` clean |

Every remaining skip is accounted for: one in `backend-core` for the
cross-service contract (V2), and all of `ai-engine`'s for missing photograph
fixtures (V4).

Reproduce:

```sh
docker compose run --rm backend-core pytest     # Django suite
docker compose run --rm ai-tests                # engine suite, `test` target
cd frontend && pnpm typecheck && pnpm test    # frontend
```

In CI, add `-e FERASHA_REQUIRE_CROSS_SERVICE=1` to the Django run so a missing
engine interpreter fails the build instead of skipping quietly.

### Phase 4 — what remains

- `components/ProductGallery.tsx` and `components/FacetFilter.tsx`
- PWA manifest + service worker — `frontend/public/` does not exist yet
- Playwright E2E for the FitDrawer journey
- Every exit criterion is still unverified: Lighthouse ≥ 90, axe-core, < 120 KB client JS, 320 px / 200% zoom

Shipped: token system with contrast + drift tests, `app/layout.tsx`, FitDrawer, ModestyBadge, ProductCard, ProductPurchasePanel, typed API client, tested `lib/units.ts`.

### Next on the critical path

**Phase 5 — Commerce (40–48 h).** Not started: there is no `Cart` model, no Razorpay integration, and `OrderViewSet` is read-only.

---

## Verification debt

Found on 2026-10-26 by running the suites rather than reading them. None of
these is a product defect; they are defects in the ability to *prove* the
product works, which DoD #7 treats as part of the work. V1–V3 are now fixed;
V4 was uncovered by fixing V3 and remains open.

| # | Problem | Evidence | Fix |
|---|---|---|---|
| ~~V1~~ **fixed** | `test_callbacks.py` hardcoded `SECRET = "insecure-shared-secret"`, the settings default. Any environment with a real `AI_ENGINE_SHARED_SECRET` — including `.env` as committed — left the server verifying with one key while the test signed with another. Every test asserting *rejection* still passed, so the suite looked half-healthy rather than misconfigured. | 10 failed, all `401 != 200` | **Done:** an autouse fixture pins `settings.AI_ENGINE_SHARED_SECRET` to the test's own key, making the signature a property of the test rather than of the environment. `apps/media_assets` went from 10 failed to 20 passed. |
| ~~V2~~ **fixed, with a caveat** | The cross-service HMAC test skipped when `ai-engine/.venv/bin/python` was missing. That virtualenv has never existed, so the one test guarding against canonicalisation drift between the two independent signers had never executed. | the single `SKIPPED` | **Done:** discovery now honours `AI_ENGINE_PYTHON` and the Windows `Scripts/python.exe` layout, the subprocess environment is portable, and `FERASHA_REQUIRE_CROSS_SERVICE=1` turns absence into a failure. **Caveat:** it still needs one interpreter holding *both* Django and the engine's dependencies, which neither image has by design, so it cannot run in Docker. It can no longer pass silently, which is the part that mattered. |
| ~~V3~~ **fixed** | `ai-engine/Dockerfile` installed only `requirements.txt`. `pytest` lives in `requirements-dev.txt`, so `docker compose run ai-engine pytest` exited with `executable file not found`. All 74 engine tests — blur irreversibility, EXIF stripping, decode guards, worker fail-closed semantics — had no runnable path in the containerised environment. | `AI_EXIT=1` | **Done:** a `test` build target plus a profile-gated `ai-tests` service. The runtime services are now pinned to `target: base`, because the new stage would otherwise have become the implicit default and shipped dev dependencies. Result: **58 passed, 19 skipped**. |
| **V4** | 19 of the 77 engine tests skip on `photograph fixtures unavailable`. They read real portraits from an `image-search/` directory at the repo root that is not committed and does not exist here. The casualties are the ones that matter most: blur irreversibility on real faces, every `test_api.py` auth and response test, and the worker happy path `test_verified_blur_uploads_then_approves`. Synthetic-face coverage still passes, so blur *mechanics* are proven while blur *efficacy on real photographs* is not. | 19 skipped, all one reason | Commit a small set of licensed portraits, or generate consented synthetic faces, as a checked-in fixture directory. Faces of real people should not go into the repo, so a licensed or synthetic set is the right answer, not a local folder. |

**Where this leaves the severe risk.** The risk register rates *unblurred face
published* 🔴 Severe, and Phase 3 is its entire mitigation. Clearing V1–V3
moved it from one of nine exit criteria verified to six: EXIF stripping, decode
guards, zero-detection routing, replay rejection, and worker crash recovery are
now demonstrated by passing tests rather than asserted.

What remains unproven is narrow and specific. Blur irreversibility is verified
on synthetic faces but not on real photographs, and the worker's happy path has
never executed — both for the same reason, V4. Closing V4 is therefore the
whole remaining distance between Phase 3 as written and Phase 3 as proven, and
is worth doing before Phase 5 adds a payment path with its own fail-closed
guarantees to verify.

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
| D8–D17 | Design system & UI libraries | Radix/shadcn layering, React Bits Commons Clause quarantine, light-first aesthetic. See [DESIGN-SYSTEM.md](./DESIGN-SYSTEM.md). |
| D18 | Tailwind config | v4 is configured in CSS via `@theme` in `app/globals.css`; `tailwind.config.ts` is legacy in v4 and is deliberately absent. `lib/design/tokens.ts` is the source of truth and `tests/tokens-sync.test.ts` fails on drift. |

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
