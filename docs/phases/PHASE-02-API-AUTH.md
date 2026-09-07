# Phase 2 — API Surface & Auth Hardening

| | |
|---|---|
| **Status** | ⬜ Not started |
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
- Email verification + password reset flows
- `drf-spectacular` schema at `/api/v1/schema/` + Swagger UI in non-production
- Generated `frontend/lib/api/types.ts`
- Contract tests per endpoint + the **full authz matrix**

---

## 8. Exit criteria

- [ ] Every endpoint has a contract test (shape, status codes, error cases)
- [ ] Authz matrix complete and green — no role can reach another user's measurements
- [ ] `assertNumQueries` guards the catalogue list and product detail
- [ ] OpenAPI schema validates against the 3.1 spec
- [ ] CI fails on a stale generated client
- [ ] Password reset does not reveal account existence (tested)
- [ ] Idempotency key prevents duplicate orders (tested)
