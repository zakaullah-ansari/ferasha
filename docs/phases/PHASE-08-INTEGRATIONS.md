# Phase 8 — Integrations, Messaging & Notifications

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phase 5 |
| **Effort** | 36–44 hrs |
| **Note** | Largest scope-creep risk in the project |

---

## 1. Objective

Connect Ferasha to the operational tools the business runs on. The brief answered "YES (All of the Above)" to twelve integration categories.

**A recommendation before anything is built:** twelve integrations is more surface area than the rest of the platform combined, and each one is a live dependency that can break in production. Building all twelve before launch would delay revenue by months and create a maintenance burden a part-time solo developer cannot sustain.

The plan below is therefore **explicitly tiered**. Tier 1 ships before launch; the rest are demand-driven.

---

## 2. Tiering

### Tier 1 — required for launch

| Integration | Why it cannot wait |
|---|---|
| **WhatsApp Business API** | Explicit brief requirement: order confirmations and invoices on WhatsApp. Primary customer channel in India |
| **Transactional email** | Invoices, password reset, order lifecycle |
| **Shipping carriers** | Blue Dart / DTDC / Professional — rates and tracking (Phase 5) |
| **Payment gateway** | Phase 5 |
| **Accounting export** | GST returns are a statutory obligation with deadlines |

### Tier 2 — first 90 days post-launch

Email marketing, Instagram Shopping, Meta catalogue, Google Merchant Centre, analytics.

### Tier 3 — on evidence of need

CRM, ERP, POS, dropshipping. **Do not build these speculatively.** A CRM with no sales team, or an ERP for a 50-SKU catalogue, is pure cost. Revisit when the business has the headcount and volume to use them.

---

## 3. WhatsApp Business API

The highest-value integration for this market.

- **Cloud API** (Meta-hosted) — avoids running BSP infrastructure
- **Pre-approved message templates** — WhatsApp requires template approval for business-initiated messages; template review takes days and is a schedule risk. **Start this early.**
- Opt-in captured and recorded at checkout; DPDP-compliant
- Order confirmation, dispatch with AWB, delivery, invoice PDF, abandoned cart, back-in-stock
- Two-way: customer replies route to a shared inbox
- **Fallback to SMS/email** when a WhatsApp send fails — never a silent drop

### 3.1 Cost control

Meta charges per conversation. Marketing conversations cost materially more than utility ones; misclassifying marketing as utility risks account restriction. Categorise correctly, budget per conversation type, and alert on spend.

---

## 4. Email

Transactional (invoices, lifecycle) kept **separate** from marketing — mixing them puts statutory invoice delivery at the mercy of spam-folder placement.

SPF, DKIM and DMARC configured and verified. Bounce and complaint handling. Deliverability monitoring.

---

## 5. Accounting

GST returns (GSTR-1, GSTR-3B) are statutory with hard deadlines and penalties.

Export of invoices, credit notes and HSN-wise summaries from the Phase 1 `OrderTaxSnapshot` — **the snapshot is the source of truth**, so returns filed today for a period before GST 2.0 use the rates that were actually charged.

Tally or Zoho Books integration, or a compliant CSV export as an interim. Reconciliation report: platform revenue vs gateway settlements vs accounting.

---

## 6. Social commerce

Meta catalogue feed and Instagram Shopping. Instagram is where this customer discovers bridal wear — for many boutiques it outperforms search.

**Critical constraint:** the product feed must contain **only Phase 3 `APPROVED` imagery**. Syndicating an unblurred original to Meta's CDN is a privacy breach that is effectively impossible to retract. The feed builder therefore reads exclusively from approved derivatives, enforced at the type level.

---

## 7. Analytics

- Server-side event tracking where possible — more accurate and privacy-preserving than client-only
- Consent management honouring DPDP; no tracking before consent
- GA4 plus a privacy-respecting alternative
- Funnel instrumentation: view → FitDrawer open → add to cart → checkout → paid
- **FitDrawer abandonment is the key custom metric** — it tells you whether bespoke ordering is too hard

---

## 8. Integration engineering standards

Every integration, without exception:

| Requirement | Rationale |
|---|---|
| **Adapter behind an interface** | Vendors get replaced; core logic must not know the vendor |
| **Circuit breaker** | A hung third party must not hang checkout |
| **Timeout + retry with jitter** | Thundering herds make outages worse |
| **Graceful degradation** | Defined behaviour when the dependency is down |
| **Webhook signature verification** | Unverified webhooks are an authentication bypass |
| **Webhook idempotency** | Providers retry; double-processing corrupts state |
| **Structured logging + correlation ID** | Cross-service debugging is otherwise guesswork |
| **Sandbox credentials in CI** | Never live keys in tests |
| **Secrets in a manager** | Never in env files in the repo |

**No integration is allowed to block checkout.** If WhatsApp is down, the order still completes and the message queues for retry.

---

## 9. Exit criteria

- [ ] Tier 1 integrations live and monitored
- [ ] WhatsApp templates approved and sending
- [ ] Invoice PDF delivered on WhatsApp and email
- [ ] Failed sends retry and fall back; nothing silently dropped
- [ ] SPF/DKIM/DMARC verified
- [ ] Accounting export reconciles against gateway settlements
- [ ] Meta feed contains only approved imagery (**tested**)
- [ ] Every adapter has a circuit breaker and defined degradation
- [ ] Third-party outage does not block checkout (chaos-tested)
- [ ] Consent recorded before any marketing message
