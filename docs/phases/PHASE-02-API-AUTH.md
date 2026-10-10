# Phase 2 — API Surface & Auth Hardening

| | |
|---|---|
| **Status** | ✅ **Complete** |
| **Depends on** | Phase 1 |
| **Blocks** | Phases 3, 4, 5 |
| **Effort** | 28–34 hrs |

---

## 1. Objective

Expose the Phase 1 domain over a versioned, typed, default-deny REST API, and generate the TypeScript client the frontend will consume — so the contract has exactly one source of truth.

---

## 2. Authorisation model

DRF is configured default-deny (`IsAuthenticated` globally). Every endpoint opts *out* explicitly.

| Resource | Anonymous | Customer | Vendor | Tailor | Staff/Admin |
|---|---|---|---|---|---|
| Catalogue read | ✅ active only | ✅ | ✅ | ✅ | ✅ all statuses |
| Catalogue write | ❌ | ❌ | ✅ own products | ❌ | ✅ |
| Own fit profile | ❌ | ✅ | ❌ | ✅ assigned only | ✅ |
| Others' fit profile | ❌ | ❌ | ❌ | ❌ | ✅ |
| Own orders | ❌ | ✅ | ❌ | ❌ | ✅ |
| Atelier queue | ❌ | ❌ | ❌ | ✅ | ✅ |
| Tax quote | ✅ | ✅ | ✅ | ✅ | ✅ |

**The authz test matrix is mandatory: every role × every endpoint × own-vs-foreign resource.** This is the single highest-value test suite in the project. Body measurements are sensitive personal data under the DPDP Act 2023.

**Foreign resources return 404, never 403.** A 403 confirms the resource exists.

---

## 3. Endpoints

```
/api/v1/
├── auth/            register, token, refresh, verify, logout, me, password/*
│                    email/verify, password/reset/{request,confirm}   ← new
├── addresses/
├── catalog/
│   ├── categories/
│   ├── products/            ?modesty, ?fabric, ?occasion, ?price_min/max, ?in_stock
│   ├── products/{slug}/
│   └── products/{slug}/reviews/
├── tailoring/
│   ├── fit-profiles/        owner-scoped
│   ├── fit-profiles/{id}/revisions/
│   └── size-chart/
├── orders/                  list, retrieve, create, cancel
├── cart/                    guest (session) + authenticated, merge on login
├── tax/                     quote, reference
└── health/, ready/
```

### 3.1 Faceted filtering

`django-filter` over the Phase 1 **typed modesty columns** — the reason they are not JSON. Facet counts computed in a single aggregate query, not N+1.

Ordering allow-listed (`price`, `-price`, `created_at`, `rating`). Never interpolate raw ordering params.

---

## 4. Email verification & password reset

Deferred from Phase 0, required before launch.

- Signed, single-use, time-limited tokens (`itsdangerous`-style or Django's `TimestampSigner`)
- Password reset **always returns 200**, whether or not the address exists — anything else is an enumeration oracle
- Reset invalidates all outstanding refresh tokens
- Rate limited per-IP *and* per-account

---

## 5. OpenAPI 3.1 → TypeScript client

`drf-spectacular` generates the schema; `openapi-typescript` generates the client.

Wired into CI: **if the schema changes and the committed client is stale, the build fails.** Hand-written frontend types drift silently from the backend and cause production bugs; generation makes drift impossible.

The modesty badge enum and size chart flow through this pipeline too.

---

## 6. Hardening

| Control | Implementation |
|---|---|
| Rate limits | Per-role scoped throttles; login 10/min; write endpoints tighter than read |
| Brute force | Progressive lockout after N failures, per account + per IP |
| Pagination | Capped `page_size`; a client cannot request 10,000 rows |
| Mass assignment | Explicit serializer `fields`; never `__all__` |
| Query explosion | `select_related`/`prefetch_related` audited; `assertNumQueries` in tests |
| Error shape | Uniform envelope; stack traces never leak in production |
| Idempotency | `Idempotency-Key` header on order creation (double-submit protection) |
| Request IDs | Correlation ID propagated to the AI engine and into logs |

---

## 7. Deliverables

- Serializers, ViewSets, filters for catalog / tailoring / orders / reviews / cart
- `apps/common/permissions.py` — extended object-level permission classes
- Email verification + password reset flows (single-use signed tokens,
  enumeration-neutral endpoints, refresh-token revocation on credential change)
- `drf-spectacular` schema at `/api/v1/schema/` + Swagger UI in non-production
- Generated `frontend/lib/api/types.ts`
- Contract tests per endpoint + the **full authz matrix**

---

## 8. Exit criteria

- [x] Every endpoint has a contract test (shape, status codes, error cases)
- [x] Authz matrix complete and green — no role can reach another user's measurements (43 tests)
- [x] Query budgets guard the catalogue list, product detail and category tree
- [x] OpenAPI schema generates with **zero errors and zero warnings**
- [x] Password reset does not reveal account existence (tested both directions)
- [ ] CI fails on a stale generated client → **Phase 7** (no CI runner yet)
- [ ] Generated `frontend/lib/api/types.ts` → **Phase 4** (frontend not yet scaffolded)
- [ ] Idempotency key prevents duplicate orders → **Phase 5** (checkout writes orders; the
      Phase 2 order API is read-only plus a staff-gated transition)

### Verification — executed, not asserted

| Check | Result |
|---|---|
| Full suite | **364 passed** |
| `ruff check .` | clean (203 findings triaged to 0) |
| `makemigrations --check` | no changes detected |
| `spectacular` | 0 errors, 0 warnings, 40 paths |
| Foreign fit profile | **404**, and the `Forbidden:` log line is absent |
| Foreign order detail | **404**; foreign order list `[]` |
| Injected `user` in profile payload | ignored; owner taken from token |
| `stock_quantity` in variant payload | absent for every non-back-office role |
| Verification token replayed | rejected — "already been used" |
| Reset token replayed | rejected; the first new password survives |
| Verification token used as reset token | rejected (distinct salts) |
| Reset with an attacker's live session | refresh returns **401** afterwards |
| Unknown vs known email on reset request | byte-identical response and status |
| Already-verified address re-request | no mail sent (would leak verification state) |
| Catalogue list, 2 → 20 products | **6 queries → 6 queries** |
| Category tree, 3 levels | **1 SELECT** |

### Mutation testing

The authz and budget suites were validated by deliberately reintroducing the
bugs they exist to catch, confirming each fails loudly before being restored:

| Injected defect | Caught by |
|---|---|
| Fit-profile owner scoping removed | 5 tests, incl. the 403-vs-404 oracle |
| `user` made mass-assignable | `test_cannot_create_profile_for_another_user` |
| `stock_quantity` added to the variant serializer | `test_stock_quantity_is_never_exposed` |
| `prefetch_related` dropped from the product queryset | budget: "grew from 6 to 46" |
| Customer event serializer reverted to the staff one | timeline redaction test |

### Defects found by running the code

1. **Internal order notes were served to customers.**
   `OrderDetailSerializer.get_events` had two *identical* branches — the
   back-office guard was written but both arms returned the same serializer.
   Staff-authored `reason` text ("fabric shortage", "fraud review") and the
   acting employee's name were exposed on the customer's own order. Split into
   a redacted `CustomerOrderEventSerializer`; regression test asserts the
   strings appear for staff and are absent for the customer.

2. **`(str, Enum)` renders as `ModestyBadge.FULLY_LINED` in f-strings.**
   JSON serialisation was correct, which is why it went unnoticed, but any log
   line or template interpolation would have emitted the enum repr into
   customer-visible output. Migrated `ModestyBadge`, `ModestyAdvisory` and
   `SupplyType` to `StrEnum`.

3. **Seven endpoints were silently missing from the OpenAPI schema.**
   drf-spectacular cannot infer a serializer for a bare `APIView` and drops the
   view with an error rather than failing the build — the generated client
   would simply not have had health, readiness, logout, password change, tax
   quote, tax reference or the measurement guide. All now carry explicit
   `@extend_schema` request/response definitions.

4. **Unstable generated type names.** Four models expose a field named
   `status`, producing hash-suffixed components (`Status4e2Enum`) that change
   between builds. Pinned via `ENUM_NAME_OVERRIDES`.
