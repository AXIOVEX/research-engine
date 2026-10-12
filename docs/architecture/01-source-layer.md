# WS1 — Source Layer

**Status:** Draft v0.1, 2026-10-11 — registry facts marked † are being verified against provider documentation and will be amended with citations before this document leaves draft · Governs: FR-003, FR-012 · Constitution: Articles V, XI

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
| **BASE** (Bielefeld) | Broad academic index, strong non-English coverage | BASE ID | Discovery breadth, esp. repositories/theses |
| **Internet Archive Scholar** | Preservation copies; fatcat-linked records | IA Scholar ID | Fallback content channel; preservation anchor |
| **HathiTrust** | Book/scan corpus, bibliographic records | HathiTrust ID | Bibliographic + limited full text per rights |
| **DSAL** (Digital South Asia Library, UChicago) | Domain depth: South Asia reference corpora | DSAL record ID | First domain-depth connector; pattern for regional libraries |

### Data & deposit platforms

| Source | Role | Primary ID |
|--------|------|------------|
| **Zenodo** | Bundle deposit + anchoring (§WS4.2); dataset evidence | DOI |
| **OSF** | Registration + bundle deposit; study project structure | OSF ID / DOI |
| **tDAR** | Archaeology data evidence | tDAR ID |
| **Open Context** | Linked-open archaeological/contextual data | ARK / DOI |
| **ADS** (Archaeology Data Service) | Archived archaeology reports/datasets | ADS ID / DOI |
| **Pleiades** | Ancient-world gazetteer: place identity resolution | Pleiades ID |

Per-source API facts (auth model, rate limits, storage/redistribution terms) are recorded in the registry table in the appendix to this document as each is verified; unverified entries ship as `stub-only` by default (WS5 §4).

## 4. Query logging & reproducibility

A search is part of the scientific record (U2 teams must be able to re-run it). Every `search` call appends a `query.executed` event with the verbatim query, connector, filters, timestamp, and result count; the bundle includes the full query log (WS4). Re-running a logged query later legitimately returns different results (indexes grow) — the record distinguishes *the query* (reproducible) from *the result set* (hash-pinned at run time), and drift between them is reportable, not hidden.

## 5. Failure behavior

- Source unavailable at run time → run records the gap; if the source was load-bearing for a claim's sufficiency floor, affected claims cap at INCONCLUSIVE with reason code `source-unavailable`.
- Source changes terms → connector's `rights` entry is re-verified; stored content exceeding new terms is tombstone-redacted per WS4 §5.
- A source is found unreliable (systematic metadata errors) → it can be demoted to discovery-only (find candidates, verify elsewhere) by design note, with the demotion and its evidence in the record.

## 6. Open questions

- OQ-1.1 Screening assistance: Semantic Scholar-style ranking may order human screening but must never silently exclude. Where exactly is the line — rank-but-show-all, or threshold with disclosed counts? Leaning rank-but-show-all for confirmation runs.
- OQ-1.2 Which connector ships first? Proposed: Crossref (resolution backbone) + OpenAlex (discovery/graph) — the minimal pair that makes FR-005 and FR-003 real. Ratified with OD-1.
