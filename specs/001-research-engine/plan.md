# Spec 001 — Plan (Design Phase)

**Date:** 2026-10-11 · Companion to `spec.md`. This plan sequences the *design* work; the implementation plan is a later artifact under a later spec.

## Approach

Six architecture workstreams, drafted in dependency order, then red-teamed as a set, then revised. The dependency order matters: the claim model constrains the verdict engine; the verdict engine constrains records/export; source rights constrain both retrieval and export.

```
WS1 Source layer ──────┐
WS2 Claim & evidence ──┼─► WS3 Verdict engine ─► WS4 Records & export
WS5 Trust & safety ────┘         │
                                 └──────────────► WS6 Product shape / MVP
```

## Workstreams

| WS | Document | Core questions it must answer |
|----|----------|-------------------------------|
| 1 | `docs/architecture/01-source-layer.md` | Connector contract; query logging; dedup keys; per-source rights (OD-4); failure behavior per source |
| 2 | `docs/architecture/02-claim-evidence-model.md` | Claim schema; falsifier representation; origin groups; dependency graph; ledger adopt/adapt/supersede map (OD-3) |
| 3 | `docs/architecture/03-verdict-engine.md` | Taxonomy mechanics; control design patterns that can fail; freeze workflow; exploratory vs confirmation; replay semantics |
| 4 | `docs/architecture/04-records-export.md` | Event store shape; hash chain; bundle format; OSF/Zenodo deposit; long-term readability |
| 5 | `docs/architecture/05-trust-safety.md` | Citation verification pipeline; uncertainty surfacing; adjudication points; licensing boundaries; abuse cases |
| 6 | `docs/architecture/06-product-shape.md` | Roles & workflows; API sketch; deployment shapes (OD-2); MVP slice definition (OD-1); competitor gap appendix |

## Method

- Draft each workstream as *decisions with reasons and rejected alternatives*, not feature lists.
- Every load-bearing design claim gets an AEE claim entry with a falsifier (e.g., "hash-chained replay detects tampering" — falsifier: a tampered bundle that replays clean).
- Red-team pass: adversarial review of the full set, specifically hunting (a) controls that cannot fail, (b) places where derivatives could inflate evidence, (c) places where a record could be silently rewritten, (d) citations that could enter unverified.
- Revision pass, then owner milestone report. Open decisions are surfaced to the owner one at a time.

## Verification (design phase)

- Cross-reference check: every FR in spec.md traces to a WS section and an AEE claim (SC-3).
- Consistency check across WS docs (terms, IDs, taxonomy used identically).
- Red-team findings log appended to this plan's record; criticals resolved or explicitly accepted (SC-1).
