# Spec 012 — Assessment record, 2026-10-12

Build and assessment executed 2026-10-12 on branch `spec/012-core-connector`
(own worktree), under the owner directive of 2026-10-12: *"Add CORE, this
is still needed."* Assessor: pinned engine 1.0.4, threshold 0.70, run
against the bundle at both gates — never edited to fit.

## Gate scores (as computed)

| Phase | Outcome | Claims |
|---|---|---|
| after_specify (bundle v0.1.0, all draft, asserted evidence) | iterate | 0.680–0.756; 5 of 8 below threshold — expected pre-build |
| after_implement (bundle v0.2.0) | iterate | **8/8 supported, 0.984–1.000, none below threshold** |

Bundle outcome stays `iterate` as computed (8 declared failure modes —
the claims' own falsifiers — remain on the register). That is the
assessor's arithmetic, recorded, not a defect claim: every claim is
supported at the **checked** stage (DN-010) — machine verification and
fixture/live evidence; no human acceptance act exists for this spec.

| Claim | after_specify | after_implement | Disposition |
|---|---|---|---|
| CLM-012-01 interface parity | 0.680 draft | 0.999 | supported / checked |
| CLM-012-02 identity / folding | 0.680 draft | 0.984 | supported / checked |
| CLM-012-03 licence discipline | 0.756 draft | 0.999 | supported / checked |
| CLM-012-04 failure honesty | 0.680 draft | 1.000 | supported / checked |
| CLM-012-05 budget accounting | 0.756 draft | 0.999 | supported / checked |
| CLM-012-06 resolution order | 0.680 draft | 0.984 | supported / checked |
| CLM-012-07 RT-5 content recovery | 0.756 draft | 0.999 | supported / checked |
| CLM-012-08 assembly integration | 0.680 draft | 0.984 | supported / checked |

## What was built

- `CoreConnector` + `CoreApiError` (`src/tekmerion/connectors.py`):
  key-gated construction (Bearer; v3 withholds full text from keyless
  callers), budget reserve/settle on every call, works-search discovery,
  output-level licence + content construction, author-name normalization,
  journal-only venue, the licence-instrument gate (below).
- Content enrichment in `verification._resolve`: a contentless primary
  record triggers same-DOI resolution against the remaining connectors,
  in order; substitution only for agreement-judged, content-bearing
  candidates; provenance recorded in `detail`; failures never un-resolve.
  Primary order Crossref → OpenAlex → CORE is unchanged, and a
  content-bearing primary produces byte-identical outcomes with CORE
  absent (falsifier F-012-6, tested).
- MCP `_default_connectors` appends CORE iff `CORE_API_KEY` is present.

Tests: `tests/test_core_connector.py`, 28 tests, recorded fixtures in
the live-probed shapes, no network, no key. **Full suite: 341 passed,
2 skipped** (baseline on this branch's base: 313 passed, 2 skipped —
+28, zero regressions).

## Live evidence (probe + smoke; key loaded at runtime from the owner's
env file only; the value appears in no artifact)

Probe findings that corrected the design before code (2026-10-12,
7 calls): **there is no `/v3/works/doi:{doi}` route** (404 "No route
found" for real and fabricated DOIs — resolution by DOI is a
`q=doi:"…"` search); the **Work carries no licence** and usually no
full text; the **Output** (per-deposit) carries `license`, abstract,
and fullText; author names arrive inverted ("Schuch, Felipe Barreto");
output `yearPublished` is a string.

Smoke through the built connector (~35 further calls across runs,
including two runs invalidated by rate pacing and re-run; every run's
outcome recorded, none silently dropped):

| Target | Result | What CORE added |
|---|---|---|
| Einstein, `10.1002/andp.19053221004` (control) | Found (2 calls) | Metadata only: no deposit asserted a usable licence → content correctly withheld, basis `core-aggregated (no per-work licence asserted)` |
| Schuch, `10.1016/j.jpsychires.2016.02.023` (Phase 7's RT-5 record) | Found (4 calls) | **Content: a 1,792-char abstract** from the King's College London deposit, licence `http://creativecommons.org/licenses/by-nc-nd/4.0/`, `hosted_ok=False` |
| Goyal, `10.1001/jamainternmed.2013.13018` | Not in CORE (1 call → None) | Nothing — an honest negative: no repository deposit for this JAMA record |
| Title search | 3 items (1 call; 10 budget units at the search rate) | Metadata records, content dropped (no work-level licences) |

**End-to-end (the claim the spec exists for):** Phase 7's CIT-E-302,
cited exactly as Phase 7 cited it, through [Crossref, OpenAlex, CORE]:
Phase 7's outcome was `resolved / agree / metadata_only` (source
openalex). With CORE: `resolved / agree / `**content checked** —
`contextual` under keyword-stance/1 on the real deposit abstract —
`source=core`, detail *"resolved via crossref without
licence-permitted content; content via core (same DOI)"*. The lexical
reading is `contextual`, not `supports`: the real abstract hedges
(publication-bias adjustment), and the instrument reports that rather
than agreeing with the proposition. What changed is the epistemic
class: a zero-mass context record became a checked record with mass.
One honest wrinkle: the deposit's licence is CC BY-NC-ND, so
`hosted_ok=False` — a hosted-shape run still excludes this record at
the RT2-1 rights gate; a self-hosted run can use it. CORE widened
what is *checkable*; per-record rights still decide what is *usable
where*, which is the discipline working, not failing.

Failure honesty, observed live: repeated smoke runs exhausted the
personal key's per-minute pacing and CORE answered **HTTP 429**;
the connector raised `CoreApiError` (never a `not_found`), and one
pipeline run under the exhausted window degraded exactly as designed
(enrichment candidate contentless after a mid-consultation 429 → the
primary metadata record stood). Total calls for the day ≈ 42 — far
inside the key's published 1,000-token/day tier; the binding
constraint in practice is the per-minute rate (published: 25/min for
this tier), which the budget discipline surfaces rather than hides.

## Defects found by the smoke and fixed in-build (both with regression tests)

1. **Restriction markers are not licences.** A Schuch deposit asserts
   licence `intranet`; the first build treated any non-empty licence
   string as unlocking content — a licence-discipline breach caught by
   the live smoke, not by fixtures. Fix: `_licence_permits_content`
   (recognizable licence instruments only — licence/rights-statement
   URLs or known identifiers; markers and unrecognized values fail
   closed; basis still recorded verbatim).
2. **A publisher is not a venue.** CORE deposits often carry only a
   publisher ("Pergamon Press"); mapping it to `venue` manufactured a
   stage-2 venue disagreement and the enrichment guard passed over
   the very record the spec exists to recover. Fix: venue comes from
   `journals` only; absent → None (stage 2 does not judge absent
   fields).

## Budget basis (CLM-012-05)

CORE publishes no per-call price: the API is free with a registered
key and token-metered (published tiers: 100 tokens/day unauthenticated;
1,000/day registered personal — the owner's key tier — at ≤25/min;
a simple query costs 1 token). Per the Phase 7 §4.5 lesson, CORE usage
is accounted in calls and CreditBudget units only (search-kind = 10,
get-kind = 1, the budget's existing rates); no dollar figure is
attached anywhere.

## Remains not understood

- Deposit ordering: CORE's `outputs` order decided which licence
  governed Schuch (the KCL BY-NC-ND deposit was the first *usable*
  one). Whether CORE's order is stable, and whether a work's deposits
  can disagree on licence in ways that matter (a permissive deposit
  behind a restrictive one), is unmeasured — the connector takes the
  first qualifying deposit in listed order and records its basis;
  it does not licence-shop.
- Licence-field hygiene beyond `intranet`: the gate's allowlist is
  necessarily a judgment call on a messy field; other marker values
  surely exist. The gate fails closed (content dropped, basis
  visible), so an unrecognized *real* licence costs content, never
  rights — the safe direction, but a real cost.
- The stance checker on full text (abstract absent) inherits the
  lexical checker's recorded sentence-level brittleness at greater
  length; unmeasured on CORE full texts specifically.
- CORE coverage: Goyal's absence is one data point. What fraction of
  a typical pilot corpus is metadata-only at Crossref/OpenAlex *and*
  content-bearing at CORE is the number that decides how much RT-5
  dilution this connector actually removes; it needs a corpus-scale
  run (a future study's freeze), not a smoke test.
- The per-minute pacing interacts with enrichment breadth: under
  load, enrichment candidates will 429-degrade to metadata. Designed
  behavior, but its frequency in a real freeze is unmeasured.
