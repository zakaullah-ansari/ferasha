# Phase 10 — LangChain Agentic Workflows

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 3, 6, 9 |
| **Effort** | 26–32 hrs |
| **Priority** | 🟢 **Optional for launch** |

---

## 1. Objective

Add AI capabilities that solve real Ferasha problems — not AI for its own sake.

**This phase is deliberately last.** Agentic features built on an unstable domain model are work you throw away. Every feature here also needs a non-AI fallback, because these systems fail in ways that are hard to predict.

---

## 2. Prioritised use cases

Ordered by value per unit of risk.

### 2.1 Vendor description enrichment — highest value, lowest risk

The brief notes some products still need descriptions. This is an **internal, human-reviewed** tool: given attributes and images, draft copy in Ferasha's house voice.

Low risk because a human approves every output before publication. Saves the owner hours of writing. **Build this first.**

### 2.2 Measurement guidance assistant — highest customer value

Bespoke ordering fails when customers measure themselves incorrectly. A conversational assistant that walks a customer through taking measurements, sanity-checks values against the Phase 1 plausibility ranges, and **escalates to a human tailor when something looks wrong**.

Directly reduces the most expensive failure mode in the business: a ruined garment cut to bad measurements.

Hard constraint: the assistant **never silently accepts an implausible measurement**. Validation remains deterministic Python; the LLM handles conversation, not correctness.

### 2.3 Styling assistant — customer-facing, highest risk

Occasion + budget + modesty preference → curated selection.

Risks that must be controlled:
- **Must not recommend out-of-stock items** — grounded in live inventory
- **Must respect stated modesty preferences absolutely.** Recommending a sleeveless deep-neck piece to a customer who asked for full coverage is not a bad recommendation, it is offensive. Filtering is applied **deterministically in the retrieval query**, never left to the model
- Must not invent products, prices, or delivery dates

### 2.4 Support triage — internal

Classify and route incoming WhatsApp/email. Draft replies for human approval. **Never auto-sends.**

---

## 3. Architecture

RAG grounded in the actual catalogue. Retrieval uses `pgvector` in the existing PostgreSQL — consistent with D2 (Django owns the database) and avoids operating a separate vector store for a 50-SKU catalogue.

**Deterministic pre-filtering before retrieval.** Modesty preferences, stock status and price bounds are SQL `WHERE` clauses, not prompt instructions. A model can ignore a prompt; it cannot ignore a query filter.

Tool-calling is allow-listed and read-only for customer-facing agents. An agent must not be able to mutate an order, issue a refund, or change a price.

---

## 4. Guardrails

| Control | Implementation |
|---|---|
| Prompt injection | Vendor descriptions and reviews are untrusted input; never concatenated into system prompts |
| Grounding | Responses cite catalogue items by ID; unresolvable IDs are dropped |
| Hallucinated pricing | Prices rendered from the database, never from model output |
| Cost | Per-conversation token budget, aggressive caching, hard monthly cap with alerting |
| Latency | Timeouts with fallback to deterministic search |
| **Degradation** | With no `OPENAI_API_KEY`, every AI surface falls back cleanly to Phase 6 search and curated rules. **The site must be fully functional without AI** |
| PII | Measurements are sensitive personal data — never sent to a third-party LLM. This is a hard rule, enforced by a redaction layer |
| Logging | Prompts and responses logged for audit, with PII redacted |

### 4.1 The PII rule

Body measurements going to an external LLM provider is a DPDP Act problem and a trust problem. The measurement assistant therefore discusses *how to measure* — it never transmits actual values. Validation of real measurements stays entirely in deterministic backend Python.

---

## 5. Evaluation

AI features without evaluation are unmaintainable.

- Golden dataset of representative queries with expected behaviour
- **Regression tests on modesty filtering — zero tolerance for violations**
- Groundedness scoring; hallucination rate tracked
- Human review sample, weekly
- A/B against the non-AI baseline; if the agent does not beat curated rules on conversion, **ship the rules**

---

## 6. Exit criteria

- [ ] Every AI surface degrades cleanly with no API key configured
- [ ] Modesty filtering enforced in SQL, not prompts — **zero violations in the regression suite**
- [ ] No recommendation of out-of-stock items
- [ ] No measurement data leaves the platform (verified by log inspection)
- [ ] Prompt-injection attempts via vendor copy and reviews do not alter behaviour
- [ ] Cost cap enforced; alerting works
- [ ] Description tool used by the owner with human approval on every output
- [ ] Measurement assistant escalates implausible values to a human
- [ ] Agent beats the non-AI baseline on a measured metric, or is not shipped
