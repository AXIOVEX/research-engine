# Assessment addendum — build exit (2026-10-12, after_implement)

Claims bundle v0.2.0 (4 claims), assessed at after_implement with AEE engine 1.0.4, threshold 0.70. Outcome: iterate (the assessor's standard signal at this phase); per-claim propagated scores: CLM-008-01 1.00, CLM-008-02 1.00, CLM-008-03 1.00, CLM-008-04 1.00. All four claims moved draft → supported on shipped-test evidence only; lifecycle stage *checked* per the DN-010 audit convention. Full record in aee-assessment.json (this run replaced the after_specify record, which remains in git history).

## What the evidence is

- GRIM: the scrutiny manual's published examples reproduce exactly (5.19 inconsistent at n=28, consistent at n=32; the two-item example consistent). GRIMMER core: hand-verified cases (an SD of 0.10 at mean 2.00, n=10 is impossible — the sum of squares would have to fall in [40.081, 40.099]; an SD of 0.82 is achieved by a named dataset) and a brute-force enumeration of >1000 achieved integer datasets with zero false flags.
- Mapping (CLM-008-03): a GRIM impossibility emits contradiction 1.00 with falsifier_observation set; the recorded statcheck output (19 results whose classifications the statcheck project asserts in its own test suite; provenance in tests/fixtures/adapters/statcheck/PROVENANCE.json) maps 12 decision errors → partial contradiction 0.50 (falsifier_observation false), 6 inconsistencies → context, 1 consistent.
- Applicability (CLM-008-04): n=150 at 2 reported decimals is not_applicable (granularity finer than reporting precision), the same n at 3 decimals is informative, continuous data is inapplicable, and an all-not-applicable run emits no evidence.
- Coverage (CLM-008-01): extraction coverage is recorded on every statcheck run — 19 extracted / 19 present on the fixture manuscript, and 0 extracted / 1 present on prose whose only p-value is non-APA (the checker's silence is a number in the record, not a clean bill).

## Open items (not smoothed over)

- **Live statcheck verification (tasks T4)** has never been performed: no R runtime exists in this environment. The Rscript seam is implemented; the build's statcheck evidence comes from recorded outputs whose classifications are the statcheck project's own assertions.
- **GRIMMER parity/reconstruction test not applied** (deliberate; see plan.md) — GRIMMER findings here are core-test findings, and one documented published case diverges from full GRIMMER in the safe (miss) direction.
- **SPRITE not implemented** — it is a plausibility display; if a study ever needs reconstructions, they enter as context with the scope claim's warning attached, via a future spec revision.
