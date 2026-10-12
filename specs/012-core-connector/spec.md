# Spec 012 — CORE Connector (WS1 content channel)

- **Date:** 2026-10-12 · **Status:** Specified 2026-10-12 (claims first; assessed at
  after_specify before any code). Build follows in this same spec package.
- **Authority:** Owner directive, 2026-10-12 (verbatim): *"Add CORE, this is
  still needed."* This spec records a scope change to OD-1 / DESIGN F4, which
  fixed the MVP connector set at Crossref + OpenAlex "by decision" — the
  decision is now revisited by the person who made it; the dated correction
  lands in `docs/pilot/DESIGN.md` F4 with this spec, it does not rewrite it.
- **Requirements source:** WS1 registry (`docs/architecture/01-source-layer.md`):
  CORE is the designed **full-text content channel** for WS5 §1.3 content
  checks — "Full-text aggregation where rights permit", CORE ID + DOI,
  free registered key (Bearer), API v3; aggregated content carries per-work
  licences ("in CORE" ≠ redistributable); v3 rate limits UNVERIFIED in the
  registry. Spec 002 Phase 7 EVALUATION-REPORT §2.1/§2.3/§2.5/§4.5 (resolution
  order reasoning; RT-5 ignorance-mass dilution measured on CIT-E-302;
  budget units ≠ dollars).

## Why CORE, and why now

Phase 7 measured the cost of the two-connector world: a citation that
resolves at Crossref and OpenAlex but carries **no licence-permitted content
at either** enters as `metadata_only` — context with zero mass (RT-5) — and
dilutes its claim's interval toward inconclusive (CLM-E-003: Cooney's checked
supporting group averaged against Schuch's metadata-only record at
10.1016/j.jpsychires.2016.02.023, a record with no abstract at either
connector). CORE aggregates full text from repositories worldwide; a work
that is metadata-only at both existing connectors can be content-checkable
through CORE. That is the gap this connector exists to close. It is not a
third metadata source — Crossref remains the resolution source of record and
OpenAlex the second — it is the content channel WS1 always designed.

## Design

### The connector (`src/tekmerion/connectors.py`)

`CoreConnector` implements the existing connector interface — `search(query,
limit)` and `resolve(doi)` returning `RetrievedItem` / `Optional[RetrievedItem]`
— against CORE API v3 (`https://api.core.ac.uk/v3`), authenticated with
`Authorization: Bearer <key>` (key from `CORE_API_KEY`, owner's registered
personal key; the connector refuses to construct without one, exactly as
`OpenAlexConnector` does, because v3 withholds `fullText` from keyless
callers — the channel's entire value is key-gated). No parallel semantics:
outcomes flow into the pipeline's existing vocabulary (resolution ∈
resolved / not_found / error; agreement; content ∈ supports / contradicts /
contextual / metadata_only) with `source="core"` on every item it produces.

Field mapping (v3 → RetrievedItem), **corrected by the 2026-10-12 live probe**
(plan step 2; the probe's evidence is in the dated assessment record):

- **There is no `/v3/works/doi:{doi}` route** (it answers 404 "No route
  found" for real and fabricated DOIs alike). Resolution by DOI is a
  search: `q=doi:"…"` on `/v3/search/works/`.
- **The Work object carries no licence and (usually) no full text.** It is
  the discovery vehicle: `doi` → `source_id` (the DOI is the identity; a
  record without a DOI carries its CORE id and cannot enrich or fold by
  DOI); `title`; `authors[].name` — served as "Surname, Given" and
  **normalized to natural order at the connector**, because stage 2
  matches on surnames and would misread the inverted form; `yearPublished`
  (int on works); venue from `journals[0].title` **only** — a deposit's
  publisher is not a venue, and claiming it as one manufactures a
  stage-2 venue disagreement against exactly the records CORE exists
  to enrich (observed live 2026-10-12: "Pergamon Press" vs the cited
  Journal of Psychiatric Research); absent journal → venue None, which
  stage 2 does not judge; a work-level `abstract` is present for some
  works.
- **The Output object (one per repository deposit, listed on the work as
  `/v3/outputs/{id}` URLs) is the licence + content unit**: it carries
  `license` (a licence URL string), its own `abstract`, and `fullText`
  (the v3 keyless placeholder string "Not available for public API
  users." is treated as absent content, because it is). `yearPublished`
  on outputs is a string and is parsed as such.
- So `resolve(doi)` = find the work by DOI search, then consult its
  outputs **in listed order, at most 3 fetches**, and build the item from
  the first output that asserts a licence *and* carries content
  (abstract preferred, full text otherwise). If no output qualifies, the
  item is built from the work with content dropped (see licence
  discipline). `search(query)` builds items from works only — no output
  fetches — so search items are metadata records unless a work itself
  asserts a licence; DOI resolution is where licensed content enters,
  which is precisely where the pipeline needs it (the enrichment path
  resolves by DOI).
- **An asserted licence unlocks content only if it is a recognizable
  licence instrument** — a licence or rights-statement URL, or a known
  licence identifier. The deposit licence field also carries
  restriction markers (a Schuch deposit asserted `intranet`, observed
  live 2026-10-12): a marker is not a licence, and unrecognized values
  fail closed — content dropped, the asserted basis still recorded
  verbatim so the degradation is visible.

### Licence discipline (per-record, mandatory)

`license_basis` is captured per record from the asserted licence of the
record the item is built from (the output's `license` field; a work that
itself asserted one would be honored the same way); when no consulted
record asserts a licence, the basis is
recorded as `core-aggregated (no per-work licence asserted)` and **the
content is dropped at the connector** — abstract and full text alike —
exactly as Crossref drops unlicensed abstracts (Crossref abstracts are not
CC0; CORE-aggregated content is not uniformly licensed either; WS1:
"in CORE" ≠ redistributable). A dropped-content CORE item therefore enters
the pipeline as a metadata record: it can resolve a citation, it cannot
carry stance mass. Non-commercial licences set `hosted_ok=False` by the
existing `_nc_flag` rule (RT2-1, rights per deployment shape).

### Failure honesty

CORE failure modes map onto the existing outcome shapes *distinctly*:
- A DOI with no matching work in the search results → `resolve` returns
  `None` (no record: the not_found shape, same as the other connectors).
  An individual output fetch answering 404 is skipped over, never fatal.
- HTTP 401/403 (auth), 429 (rate limit), 5xx, and transport failures →
  the connector raises `CoreApiError`. In the pipeline's resolution loop a
  raised connector is an explicit `error` outcome when no other route
  resolved — an outage never reads as "the work does not exist".
  One refinement, from the source's shape: a failure while consulting a
  *found* work's outputs degrades that resolve to the work's metadata
  record (the lookup itself succeeded); only the search step's failure
  raises.
- An empty search result is an empty list (the source answered; nothing
  matched) — never an exception, never a fabricated record.

### Budget accounting

Every CORE call reserves against a `CreditBudget` first (search = the
budget's `search` kind, resolve = `get`), exhaustion raises before any
HTTP happens (RT2-2). CORE publishes **no per-call dollar price**: the API
is free with a registered key, metered in *tokens* (CORE's published
tiers: unauthenticated 100 tokens/day; registered personal 1,000
tokens/day, ≤25/minute; a simple query costs 1 token, complex queries
3–5). Following the Phase 7 §4.5 lesson (connector budget units ≠ provider
dollars; price only from published rates), CORE spend is accounted in
**calls and budget units**, never converted to dollars. The key on file is
the registered-personal tier: 1,000 tokens/day is the operative external
ceiling, and the budget limit is configuration, as elsewhere.

### Resolution order and enrichment (the integration decision)

**Primary resolution order is unchanged: Crossref → OpenAlex → CORE.**
Crossref stays the source of record; no existing citation's resolution,
agreement, or verdict changes because CORE exists (CLM-012-06's falsifier
tests exactly this). CORE participates at position 3 in both the DOI route
and the no-DOI search, under the pipeline's existing first-agreeing-
candidate rule.

On top of that, one new path — **content enrichment**: when the primary
resolution returns a record with **no licence-permitted content** (the
RT-5 case), the pipeline asks the remaining connectors, in order, for the
same DOI. A candidate replaces the primary record only if *all* of these
hold: it is the same work (resolved by the same DOI), it carries
licence-permitted content, and stage 2 judges it in **agreement** with the
citation (an enrichment source never manufactures a disagreement the
primary record did not produce — a disagreeing candidate is passed over
and the primary stands). The result's `source` then names the enriching
connector and its `detail` records that enrichment happened and from
which source the metadata came. Enrichment failures (a raising connector)
never un-resolve a resolved citation: the primary record stands and the
failure is noted in `detail`.

Rationale, stated once: placing CORE third as a plain fallback would only
help citations that fail resolution entirely — rare, since Crossref
resolves nearly every DOI — and would leave the measured RT-5 dilution
untouched. Enrichment is the conservative shape that attacks the measured
problem: it fires only where the pipeline today produces metadata_only,
it can only *add* checked content for the same work, and every other
behavior is byte-identical to the pre-CORE pipeline.

### Assembly

`tekmerion.mcp.server._default_connectors` appends `CoreConnector` when
`CORE_API_KEY` is present in the environment — the OpenAlex pattern
(key-gated, absent key = absent connector, never a crash). The UI and
evaluation drivers receive connector lists from their callers as today;
the list order they pass is now documented as Crossref, OpenAlex, CORE.

## Non-goals

- No changes to verdict mathematics, stance checking, grouping keys, or
  thresholds. Grouping key 1 already folds by DOI; this spec proves the
  fold across sources (CLM-012-02), it does not alter it.
- No full-text *download* pipeline (no `downloadUrl` fetching, no PDF
  handling): content is what the v3 record itself carries.
- No CORE outputs/entities endpoints (data providers, journals, outputs):
  works only — the WS5 §1 pipeline's unit.
- No change to Crossref or OpenAlex behavior, costs, or ordering.
- CORE does not become a deposit/anchor subprocessor: queries and record
  lookups only (the gap-closure inventory update says exactly that).
