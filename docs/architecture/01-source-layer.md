# WS1 — Source Layer

**Status:** Draft v0.2, 2026-10-11 — registry facts verified in Appendix A (2026-10-11 pass); items flagged UNVERIFIED there remain stub-only until re-checked at connector-build time · Governs: FR-003, FR-012 · Constitution: Articles V, XI

## 1. Why connectors, not scraping

The engine reads scholarly infrastructure through first-class connectors, never through general web scraping of the open web as a primary channel. Reasons: provenance (an API record is a re-checkable source of record; a scraped page is a snapshot of unknown authority), rights (API terms are knowable per source; scraping terms are a gray zone — Article XI), and reproducibility (a logged API query can be re-run; a search-engine result page cannot).

## 2. The connector contract

Every connector implements the same contract, so a source can be added, replaced, or distrusted without touching the engine:

- `identify` — resolve an identifier (DOI or native ID) to the source's canonical record.
- `search` — execute a query; the connector logs the *verbatim* query, parameters, timestamp, and result count before returning items (FR-003).
- `fetch` — retrieve one item's record (and content where terms permit), returning content + hash.
- `rights` — return the source's registry entry: what may be queried, stored, redistributed.
- `health` — report availability/rate-limit state; a connector in failure degrades the run explicitly (missing source is recorded in the bundle), never silently.

Cross-connector rules: deduplication is by DOI first, then source-native IDs crosswalked through Crossref/OpenAlex identity; an item retrieved from two connectors is **one item with two provenance paths**, and both paths are kept — agreement between independent connectors is itself weak evidence of record stability, disagreement is a quarantine trigger (WS5 §1.2).

## 3. Source registry (adoption set)

### Scholarly discovery & metadata

| Source | Role in the engine | Primary ID | Notes † |
|--------|--------------------|------------|---------|
| **Crossref** | Metadata/DOI backbone; citation resolution source of record | DOI | Metadata API; the resolution target for FR-005 |
| **OpenAlex** | Citation graph, concept/works discovery, crosswalks | OpenAlex ID + DOI | Free API; graph used for origin tracing and dependency discovery |
| **Semantic Scholar** | Discovery + TLDR/embedding-assisted screening support | S2 ID + DOI | API + bulk datasets; screening support only — never evidence by itself |
| **CORE** | Full-text aggregation where rights permit | CORE ID + DOI | Content channel for WS5 §1.3 content checks |
| **BASE** (Bielefeld) | Broad academic index, strong non-English coverage — **CONDITIONAL (RED-TEAM-02 RT2-1):** access is framed for non-commercial projects; excluded from the hosted (commercial) connector set until commercial terms are confirmed in writing. Registry rights entries are recorded *per deployment shape*, not per source alone | BASE ID | Discovery breadth, esp. repositories/theses |
| **Internet Archive Scholar** | Preservation copies; fatcat-linked records | IA Scholar ID | Fallback content channel; preservation anchor |
| **HathiTrust** | Book/scan corpus, bibliographic records | HathiTrust ID | Bibliographic + limited full text per rights |
| **DSAL** (Digital South Asia Library, UChicago) | Domain depth: South Asia reference corpora | DSAL record ID | First domain-depth connector; pattern for regional libraries |

### Data & deposit platforms

| Source | Role | Primary ID |
|--------|------|------------|
| **Zenodo** | Bundle deposit + anchoring (§WS4.2); dataset evidence | DOI |
| **OSF** | Registration + bundle deposit; study project structure | OSF ID / DOI |
| **tDAR** | Archaeology data evidence — **no public API found (verified 2026-10-11, Appendix A)**: access is platform/manual, not a connector, until tDAR confirms an API | tDAR ID |
| **Open Context** | Linked-open archaeological/contextual data — JSON query/read API, no auth | Item URI (UUID) |
| **ADS** (Archaeology Data Service) | Archived archaeology reports/datasets — **no public API documented**: machine path is DataCite metadata (ADS mints DOIs, prefix 10.5284) | DOI (10.5284…) |
| **Pleiades** | Ancient-world gazetteer: place identity resolution — JSON search API + daily dumps | Pleiades ID |

Per-source API facts are recorded in **Appendix A** (verified 2026-10-11 against provider documentation; items flagged UNVERIFIED ship as `stub-only` by default, WS5 §4).

## 4. Query logging & reproducibility

A search is part of the scientific record (U2 teams must be able to re-run it). Every `search` call appends a `query.executed` event with the verbatim query, connector, filters, timestamp, and result count; the bundle includes the full query log (WS4). Re-running a logged query later legitimately returns different results (indexes grow) — the record distinguishes *the query* (reproducible) from *the result set* (hash-pinned at run time), and drift between them is reportable, not hidden.

## 5. Failure behavior

- Source unavailable at run time → run records the gap; if the source was load-bearing for a claim's sufficiency floor, affected claims cap at INCONCLUSIVE with reason code `source-unavailable`.
- Source changes terms → connector's `rights` entry is re-verified; stored content exceeding new terms is tombstone-redacted per WS4 §5.
- A source is found unreliable (systematic metadata errors) → it can be demoted to discovery-only (find candidates, verify elsewhere) by design note, with the demotion and its evidence in the record.

## Appendix A — Verified registry facts (2026-10-11)

Verification pass against provider documentation. UNVERIFIED = not confirmable from a primary source in this pass; those limits are read from response headers at integration time and the registry entry is updated then.

| Source | Auth | Rate limits (documented) | Store / redistribute boundary |
|--------|------|--------------------------|-------------------------------|
| OpenAlex | **Free API key required** for production use (since 2026-02-13); the `mailto` polite pool is **retired** | Credit-metered, not request-metered: free key ≈ $1/day credit (list/filter ≈ $0.0001/call; search ≈ $0.001; single-work lookup free); burst cap 100 req/s | Metadata CC0 — store/redistribute freely. Full texts follow each work's own licence field |
| Crossref | No signup; Polite pool via `mailto`/User-Agent; Metadata Plus (paid) via token | Public 5 req/s · Polite 10 req/s · Plus 150 req/s | Metadata freely storable/redistributable; **abstracts are publisher-supplied — not assumed CC0**; per-work `license` element governs content |
| Semantic Scholar | Free key (`x-api-key`); unauthenticated shared pool is unreliable | Design ceiling **1 req/s** cumulative (introductory key); batch ≤500 IDs/request | **No blanket licence** — per-dataset/per-record licences (ODC-BY, CC BY-NC, …) captured at ingest; abstracts only where licensing allows |
| CORE | Free registered key (Bearer), API v3 | **UNVERIFIED for v3** (public docs still serve v2 quota tables) | Dumps ODC-BY (acknowledgement); aggregated content carries per-work licences — "in CORE" ≠ redistributable |
| BASE | Registered users; OAI-PMH is **IP-restricted**, non-commercial application with use case + IP range | No public numeric limits — UNVERIFIED | Non-commercial framing; store metadata/provenance, fetch full text from the provider |
| IA Scholar / Fatcat | Reads: no auth | None documented — UNVERIFIED | Catalogue + citation graph **CC0**; preserved full texts keep their own licences. *Availability: search surface reported degraded in 2026; legacy fatcat host defunct — bulk dumps are the primary route, API is convenience* |
| HathiTrust | Bib API: no auth (lookup only, not search). Data API: OAuth 1.0a institutional keyset | Bib: UNVERIFIED. Data API throttled, burst-oriented | Own metadata contributions CC0; contributor records may be restricted (OCLC policy); **in-copyright = non-consumptive or contract only — never stored/redistributed as text** |
| Zenodo | Reads: no token. Writes/deposits: personal access token | Guests 60 req/min · authenticated 100 req/min · search 30 req/min | Per-record licence chosen by depositor; published files effectively immutable (changes = new version). Keep **both** version DOI and concept DOI |
| OSF | Public reads: no auth. Writes: PAT / OAuth | **UNVERIFIED** officially; secondary sources consistently report ~100 req/min unauthenticated — design to that, confirm before production | Per-project/per-file licence set by owner; public ≠ openly licensed — default to metadata + links |
| Open Context | No auth observed | — | Per-item JSON; canonical item URI (UUID) is the dedup key |
| Pleiades | No key (custom User-Agent requested) | 100-hit cap per search query; daily dumps (JSON/CSV/GeoJSON) | Place records via canonical URI `pleiades.stoa.org/places/{id}` |

### Design flags carried into the design

1. **Connector economics are real:** OpenAlex is credit-metered — the connector prefers filter/list calls over search calls (≈10× cheaper) and budgets credits per run, recorded in the query log. Crossref pool selection (always send `mailto`) is a connector requirement, not a courtesy. **Budget reservation (RED-TEAM-02 RT2-2):** the freeze check (WS3 §3) reserves the estimated connector cost of the registered query plan; a run hitting a hard budget ceiling aborts to INVALID (`budget-exhausted`) instead of completing on silently partial evidence, unless the registration pre-declared a degraded-source contingency (affected claims then cap at INCONCLUSIVE per §5).
2. **Licence capture is a schema field** (see WS2 amendment): `license_basis` is populated per evidence item at ingest from the source record; there is no global default licence anywhere in the system.
3. **Not every registry entry is a connector:** tDAR and ADS have no public API — they enter as *discovery references* (ADS via DataCite metadata) with manual/partner access, and the registry records that honestly rather than pretending a connector exists.

## 6. Open questions

- OQ-1.1 Screening assistance: Semantic Scholar-style ranking may order human screening but must never silently exclude. Where exactly is the line — rank-but-show-all, or threshold with disclosed counts? Leaning rank-but-show-all for confirmation runs.
- OQ-1.2 Which connector ships first? Proposed: Crossref (resolution backbone) + OpenAlex (discovery/graph) — the minimal pair that makes FR-005 and FR-003 real. Ratified with OD-1.
