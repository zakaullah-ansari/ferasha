# Phase 6 — Merchandising, Search & Discovery

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phases 2, 4 |
| **Effort** | 26–32 hrs |

---

## 1. Objective

Make 50+ SKUs discoverable and desirable. At this catalogue size the constraint is not scale — it is *relevance* and merchandising quality.

---

## 2. Search

### 2.1 Start with PostgreSQL, not Elasticsearch

For 50–500 SKUs, PostgreSQL full-text search with `tsvector`, `pg_trgm` fuzzy matching and weighted ranking is genuinely sufficient — and it avoids operating a second datastore, keeping it consistent with the primary database by construction.

Elasticsearch/Meilisearch is a **Phase 11 decision, taken on evidence** (catalogue > ~2,000 SKUs, or measured query latency degradation), not upfront.

### 2.2 Domain-aware search

Generic search fails on this catalogue. Customers search "gharara", "farshi palazzo", "chikankari", "zardozi" — and misspell all of them.

- **Synonym dictionary**: gharara/ghararah, lehenga/lehnga/lengha, dupatta/dupata, salwar/shalwar, kameez/kurta
- **Transliteration tolerance** for Roman-script Urdu/Hindi
- Trigram fuzzy matching for typos
- Weighted ranking: name > category > fabric > work type > description

---

## 3. Faceted filtering

Facets over the Phase 1 **typed columns**:

- **Modesty** — fully lined, opaque, full sleeve, ankle-length slit *(the differentiating facet; lead with it)*
- Category, fabric, work type, occasion
- Price band, colour, size availability
- Bespoke-available

Facet counts in a single aggregate query. Filters reflected in the URL so a filtered view is shareable and indexable.

---

## 4. Recommendations

Deliberately **not** machine learning at this stage. With 50 SKUs and limited interaction history, ML underperforms good merchandising rules and is far harder to debug.

| Surface | Rule |
|---|---|
| Complete the look | Curated: lehenga → matching dupatta → blouse |
| Similar items | Same category + fabric + adjacent price band |
| Recently viewed | Session-based |
| Frequently bought together | Co-purchase counts, once volume exists |
| Editor's picks | Hand-curated by the owner — highest converting for a boutique |

Revisit ML in Phase 10 when there is real behavioural data.

---

## 5. Wishlist & comparison

**Wishlist** — persisted for authenticated users, session-based for guests, merged on login. Back-in-stock and price-drop notifications (Phase 8). Shareable — bridal shopping is a group activity, and this is a genuine acquisition channel.

**Comparison** — side-by-side on price, fabric, work, **modesty attributes**, sizes, delivery estimate. Up to 4 items. The modesty row is the differentiator.

---

## 6. Reviews

Display of the Phase 1 models: rating distribution, verified-purchase badges, **fit feedback aggregation** ("72% say true to size"), customer photos routed through the Phase 3 privacy pipeline, moderation queue.

Fit feedback is the highest-value review data for a tailoring business — surface it next to the size selector, not buried at the bottom.

---

## 7. Content & SEO

- Structured data: `Product`, `Offer`, `AggregateRating`, `BreadcrumbList`
- Canonical URLs; filtered views `noindex` unless curated
- Category landing pages with editorial copy (converts and ranks)
- Lookbooks and editorial photography
- Bridal buying guides, fabric care, measurement how-to — the measurement guide doubles as customer education that reduces bespoke errors
- XML sitemap, `robots.txt`, Open Graph and Twitter cards
- `hreflang` if UK/GCC content diverges

Brief notes some product descriptions still need writing — this is a content workstream to run in parallel, with a house style guide for consistency.

---

## 8. Exit criteria

- [ ] Search returns sensible results for misspelled domain terms ("ghrara", "lehnga")
- [ ] Facet counts accurate and computed in one query
- [ ] Filtered URLs shareable and correctly indexed/noindexed
- [ ] Wishlist merges on login
- [ ] Comparison renders modesty attributes side by side
- [ ] Fit feedback aggregates correctly and appears beside size selection
- [ ] Structured data validates in Google's Rich Results test
- [ ] Search p95 latency < 200 ms at catalogue size
