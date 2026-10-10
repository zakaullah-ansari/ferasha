# Phase 11 — Production Readiness, Security & Compliance

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 1–5 |
| **Blocks** | Phase 12 (launch) |
| **Effort** | 32–40 hrs |
| **Priority** | 🔴 **Non-negotiable before launch** |

---

## 1. Objective

Make Ferasha survivable in production: observable, recoverable, secure, and legally compliant.

---

## 2. The PostgreSQL debt — settle this first

Phase 0's suite ran against **SQLite** because the development sandbox had no PostgreSQL. This means the following are **currently unverified**:

- `jsonb` operators and containment queries (Phase 1 measurements)
- GIN index behaviour
- Several `CheckConstraint`s that SQLite silently tolerates
- `SELECT ... FOR UPDATE` row locking (Phase 1 stock, Phase 5 gift cards)
- Concurrent transaction semantics generally

**The very first task of this phase** is to run the entire suite against a real `postgres:16` service and fix what falls over. Do not treat the existing green suite as proof of Postgres correctness — it is not.

---

## 3. CI/CD

GitHub Actions, on every push:

```
lint (ruff, eslint, prettier)
  → typecheck (mypy strict, tsc --noEmit)
  → unit tests
  → integration tests  ← against postgres:16 + redis:7 services
  → coverage gate
  → OpenAPI schema drift check
  → frontend build + bundle-size gate
  → accessibility (axe-core)
  → container scan (Trivy)
  → dependency audit (pip-audit, npm audit)
  → secret scan (gitleaks)
```

Blue-green or rolling deploy with automated rollback. Migrations run separately from deploy, and are **backwards-compatible** — expand/contract, never a destructive migration in the same release as the code that depends on it.

---

## 4. Hosting

Recommendation for a solo part-time developer: **managed services over self-hosted infrastructure.** Time spent operating Kubernetes is time not spent on the product.

| Component | Approach |
|---|---|
| Database | Managed PostgreSQL 16 with PITR (AWS RDS / Neon / Supabase) |
| Redis | Managed (ElastiCache / Upstash) |
| Django + FastAPI | Container platform with autoscaling (ECS Fargate / Render / Fly.io) |
| Next.js | Vercel or the same container platform |
| Media | S3-compatible + CDN, with **strictly separated private and public buckets** (Phase 3) |
| DNS/WAF | Cloudflare — DDoS, WAF, bot protection |

**Region: Mumbai (ap-south-1)** — lowest latency for the primary market, and it keeps personal data in India, which simplifies DPDP compliance considerably.

---

## 5. Observability

- **Sentry** for both backend services and the frontend, with release tracking and source maps
- **Structured JSON logging** with a correlation ID propagated across Next.js → Django → FastAPI. Debugging a cross-service failure without this is guesswork
- Uptime monitoring on `/health` and `/ready` from multiple regions
- Business alerts, not just technical: checkout failure rate, payment decline spike, **AI-engine queue depth** (a backlog means merchandising is blocked), atelier overdue count
- Dashboards the owner can read, not only the developer

---

## 6. Backup & disaster recovery

| Target | Value |
|---|---|
| RPO | ≤ 15 minutes (PITR) |
| RTO | ≤ 4 hours |

Nightly logical `pg_dump` **plus** continuous PITR. Media bucket versioning and cross-region replication.

**A restore that has never been tested is not a backup.** Quarterly restore drill into a scratch environment, timed, with the runbook updated from what is learned.

Runbooks for: database restore, gateway outage, AI-engine failure, media loss, credential rotation, rollback.

---

## 7. Security

### 7.1 Baseline

OWASP Top 10 review. HSTS with preload, CSP (no `unsafe-inline`), `Referrer-Policy`, `Permissions-Policy`. Secrets in a manager with documented rotation. Dependency scanning with an SLA on criticals. Rate limiting at the edge as well as the application.

### 7.2 Ferasha-specific

| Asset | Threat | Control |
|---|---|---|
| **Unblurred originals** | Privacy breach | Private bucket, no public route, signed URLs for staff only, access logged |
| **Body measurements** | Sensitive personal data | Encryption at rest, access logged, never sent to third-party LLMs |
| **JWT signing key** | Total auth compromise | ≥32 bytes enforced (Phase 0), rotation procedure, separate key per environment |
| **Payment webhooks** | Forged payment confirmation | Signature verification, replay protection |
| **Invoice sequence** | Tax fraud exposure | Gap-free enforcement, audit log |

Penetration test before launch. For a platform handling payments and biometric-adjacent data, this is proportionate.

---

## 8. DPDP Act 2023 compliance

India's Digital Personal Data Protection Act applies directly to Ferasha.

- **Consent** — granular, recorded with timestamp and purpose, withdrawable as easily as given
- **Notice** — plain-language, in English and ideally Hindi
- **Data principal rights** — access, correction, erasure, grievance redressal. Implemented as real workflows, not an email address that nobody monitors
- **Erasure vs retention** — a customer can request deletion, but tax law requires invoice retention. Resolve this explicitly: anonymise personal data, retain the statutory financial record
- **Measurements are sensitive** — treat with the highest protection
- **Breach notification** — documented procedure with defined timelines
- **Grievance officer** — appointed and published, as the Act requires
- **Processor agreements** — with every vendor in Phase 8

Also: GST compliance (Phase 5), Legal Metrology packaging rules, Consumer Protection (E-Commerce) Rules 2020 — mandatory seller details, grievance officer, country of origin.

---

## 9. Performance

| Metric | Target |
|---|---|
| LCP | < 2.5 s on 4G, mid-range Android |
| INP | < 200 ms |
| CLS | < 0.1 |
| API p95 | < 300 ms |
| Search p95 | < 200 ms |

Load test to a realistic peak — a festive-season or collection-launch spike, not average traffic. Establish where it breaks *before* customers find out.

---

## 10. Exit criteria

- [ ] **Full suite green against PostgreSQL 16** (settles the Phase 0 debt)
- [ ] CI runs every gate; a failing gate blocks merge
- [ ] Backup restore drill completed and timed within RTO
- [ ] Penetration test complete; criticals and highs resolved
- [ ] DPDP: consent, rights workflows, grievance officer, breach procedure all live
- [ ] Correlation IDs traceable across all three services
- [ ] Load test passes at projected peak
- [ ] Core Web Vitals within target on throttled mobile
- [ ] Secrets rotated out of any development state; no secret in git history
- [ ] Runbooks written and rehearsed
