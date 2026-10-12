# Spec 008 — statcheck + GRIM-family Adapter (P7: reporting-consistency) — plan

1. Claims + assessment (this spec). 2. Build gated on owner shortlist approval. 3. Seeded-defect tests through production paths before any study use.

## Build exit (2026-10-12)

Owner shortlist gate passed 2026-10-12; built the same day on branch adapters/build-006-008, on the shared seam defined by Spec 006.

GRIM family: the published method is arithmetic, so it is implemented natively (`grim_consistent`, `grimmer_core_consistent`) in exact rational arithmetic and validated three ways — the scrutiny manual's published examples (5.19 at n=28 inconsistent, n=32 consistent), hand-verified sum-of-squares cases, and a brute-force enumeration of achieved integer datasets in the test suite (any false flag on achieved data would be a manufactured falsifier; the enumeration tolerates none). GRIMMER is the core tests only: the parity/reconstruction test is deliberately not applied — the reference implementation's maintainer flags it as buggy in the current release — so this adapter's GRIMMER can miss an inconsistency (the documented (5.23, 2.55, 35) case) but cannot manufacture one. SPRITE is not implemented (plausibility display, not a check; the scope claim already bars presenting its output as data).

statcheck: no R runtime exists in this environment. The adapter ships the live R seam (`StatcheckRunner`) for environments that have one, and here consumes recorded statcheck outputs — the fixture's classifications are the statcheck project's own test-suite assertions (tests/fixtures/adapters/statcheck/PROVENANCE.json). The adapter never recomputes p-values under statcheck's name. Unavailable is a ledgered state with coverage still recorded. Live verification is open task T4.

Claims at exit: bundle v0.2.0, assessed at after_implement — CLM-008-01…04 all at 1.00 / supported, lifecycle stage *checked* (author's own tests; DN-010 convention).
