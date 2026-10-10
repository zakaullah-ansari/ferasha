# Ferasha — Technology Stack Decisions

Rationale for every significant technology choice, including the ones rejected. Where a "best in the world" option exists but is wrong *for this project*, that is stated explicitly — the constraint that dominates every decision below is **one part-time developer**, which makes operational simplicity worth more than raw capability.

---

## 1. Build vs buy — the decision that precedes all others

Before choosing a stack, this deserves an honest answer.

| Option | Verdict |
|---|---|
| **Shopify Plus** | Fastest to revenue, excellent operationally. **Rejected:** the bespoke measurement workflow, atelier production pipeline and mandatory face-blur privacy pipeline are not expressible in Shopify's model without fighting it continuously. |
| **Medusa / Saleor** | Good open-source commerce cores. **Rejected:** still requires heavy customisation for the atelier workflow, and adds a framework's opinions to work around. |
| **Custom (chosen)** | Highest effort, but the differentiators — bespoke fit, modesty attributes, privacy pipeline — *are* the business. They cannot be bolted onto a generic platform. |

**If** the timeline pressure ever outweighs the differentiation, Shopify with a custom bespoke-ordering app is the honest fallback. That is not the current judgement, but it should be revisited if Phase 5 slips badly.

---

## 2. Backend — Django 5 + DRF

| Considered | Verdict |
|---|---|
| **Django + DRF** ✅ | Batteries included: admin, ORM, auth, migrations, security defaults. The **free admin alone** saves 30+ hours of Phase 9. Mature GST/Indian-market ecosystem. |
| FastAPI (whole backend) | Excellent for the AI service, but no ORM, no admin, no auth framework. Rebuilding those is weeks of work for no gain. |
| Node/NestJS | Single language across the stack is real, but Prisma migrations and the auth ecosystem are weaker than Django's for a data-heavy commerce domain. |
| Rails | Genuinely comparable. Django chosen because the AI/CV ecosystem is Python, keeping one language across `backend-core` and `ai-engine`. |

**Decision:** Django for the commerce core, FastAPI only for the async AI workload. Right tool per workload, one language overall.

---

## 3. AI engine — FastAPI + MediaPipe

Async ASGI suits CV work that is I/O- and CPU-bound in bursts. MediaPipe is production-grade, CPU-viable (no GPU cost), and ships both short-range and full-range face models — both needed for the mix of close-up and full-body editorial photography in Phase 3.

Rejected: running CV inside Django (blocks workers), and a GPU inference server (cost unjustified at this volume).

---

## 4. Frontend — Next.js 15 + TypeScript + Tailwind

| Considered | Verdict |
|---|---|
| **Next.js 15 App Router** ✅ | Server Components give SEO-critical pages fast first paint with minimal client JS. Mature image optimisation — decisive for an image-led catalogue. |
| Remix | Excellent data loading. Smaller ecosystem; weaker built-in image pipeline. |
| Astro | Best-in-class for content sites. Weaker for the heavily interactive checkout and FitDrawer. |
| SvelteKit | Smallest bundles, genuinely appealing. Smallest talent pool and ecosystem — a real risk for a solo maintainer. |

**Tailwind** for design tokens as a typed system and no dead CSS. **Framer Motion**, used with restraint — luxury reads as calm.

> The UI library layering (Radix / shadcn / motion / effects), the licence audit
> of Magic UI and React Bits, and the theming rules that stop shadcn/ui looking
> like shadcn/ui are specified in **[DESIGN-SYSTEM.md](./DESIGN-SYSTEM.md)**
> (decisions D8–D17). Note in particular that React Bits is **MIT + Commons
> Clause**, not MIT, and is quarantined accordingly.

---

## 5. Database — PostgreSQL 16

Not a close call. Native `jsonb` with GIN indexing for measurements, real check constraints, `pg_trgm` and full-text search (deferring Elasticsearch entirely in Phase 6), `pgvector` for Phase 10 RAG, and true transactional integrity for money.

MySQL: weaker JSON and no equivalent extension ecosystem. MongoDB: wrong for a domain that is overwhelmingly relational and financially consequential.

**One database serving OLTP, search and vectors** is a significant operational simplification for a solo developer.

---

## 6. Redis 7

Queue for the Phase 3 privacy pipeline, cache, session store, rate-limit counters.

RabbitMQ/Kafka rejected: correct at high volume, unjustified operational weight here. Redis Streams cover the requirement.

---

## 7. Payments — Razorpay primary

Chosen over Stripe **for this market specifically**. Razorpay covers UPI — the dominant Indian rail — plus cards, netbanking, wallets, EMI and BNPL in one integration, and settles in INR.

Stripe is the better global product but has weaker UPI support and INR settlement. Since the brief specifies INR-only pricing with a primarily Indian customer base, Razorpay wins on merit.

Both sit behind a `PaymentGateway` port (Phase 5), so this is reversible.

---

## 8. Search — PostgreSQL FTS, deferring Elasticsearch

At 50–500 SKUs, `tsvector` + `pg_trgm` with a domain synonym dictionary is genuinely sufficient and stays consistent with the primary database by construction.

Elasticsearch and Meilisearch are better search engines. They are also a second datastore to operate, secure, back up and keep in sync — for a catalogue that fits comfortably in memory. **Revisit on evidence** (>2,000 SKUs or measured latency degradation), not on principle.

---

## 9. Hosting — managed services, Mumbai region

Managed PostgreSQL with PITR, managed Redis, container platform with autoscaling, S3-compatible storage with **strictly separated private/public buckets** (Phase 3), Cloudflare for DNS/WAF/DDoS.

**Kubernetes explicitly rejected.** It is the right answer at scale and the wrong answer for one part-time developer — the operational burden would consume the time this project does not have.

**Region ap-south-1 (Mumbai):** lowest latency for the primary market, and keeping personal data in India materially simplifies DPDP Act compliance.

---

## 10. Methodology

Not Scrum — ceremony designed for teams is overhead for one person.

**Continuous flow with phase gates.** Small vertical slices, trunk-based development on short-lived branches, CI on every push, deploy when green. Each phase has explicit exit criteria that must be *demonstrated by execution*, not asserted.

**ADRs in `docs/adr/`.** Chief mitigation for solo-developer bus factor: in six months you will not remember why Razorpay beat Stripe, and neither will anyone who inherits this.

---

## 11. Testing

| Layer | Tool |
|---|---|
| Backend unit/integration | pytest + pytest-django, **against `postgres:16` in CI** |
| Fixtures | factory-boy |
| API contract | DRF `APIClient` + OpenAPI schema validation |
| Frontend unit | Vitest + Testing Library |
| E2E | Playwright |
| Accessibility | axe-core in CI |
| Load | k6 |

**Testing philosophy:** heavy on the money path (tax, payments, ledgers) and the privacy path, lighter on presentation. Coverage percentage is not the target — covering the paths where failure is expensive is.

The GST engine's 43 unit tests exist because a rounding error there is a tax liability, and because the engine was already found to be applying repealed law once.

---

## 12. Summary

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, Framer Motion |
| Commerce backend | Django 5, DRF, SimpleJWT |
| AI service | FastAPI, MediaPipe, OpenCV, LangChain (Phase 10) |
| Database | PostgreSQL 16 (+ `pg_trgm`, `pgvector`) |
| Cache/Queue | Redis 7 |
| Payments | Razorpay (ports & adapters) |
| Messaging | WhatsApp Cloud API + transactional email |
| Hosting | Managed containers + managed Postgres, ap-south-1 |
| CDN/WAF | Cloudflare |
| Observability | Sentry + structured JSON logs with correlation IDs |
| CI/CD | GitHub Actions |
