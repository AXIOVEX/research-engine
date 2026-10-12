# Assessment addendum — build exit (2026-10-12, after_implement)

Claims bundle v0.2.0 (4 claims), assessed at after_implement with AEE engine 1.0.4, threshold 0.70. Outcome: iterate (the assessor's standard signal at this phase); per-claim propagated scores: CLM-006-01 1.00, CLM-006-02 1.00, CLM-006-03 1.00, CLM-006-04 1.00. All four claims moved draft → supported on shipped-test evidence only; lifecycle stage *checked* per the DN-010 audit convention (the author's own seeded-defect tests are checking, not settlement). Full record in aee-assessment.json (this addendum's run replaced the after_specify record, which remains in git history).

## What the evidence is

- Parser validated against recorded real outputs (provenance: tests/fixtures/adapters/checkcif/PROVENANCE.json): the IUCr service HTML report's line-parsed alert counts reproduce its own printed summary exactly (8 A / 0 B / 10 C / 11 G); two PLATON .chk fixtures parse to their alert listings with PLATON + check.def versions extracted.
- Falsifiers exercised: F-006-1 twice (recorded output without the artifact → context, no evidence; version-stripped output → no evidence), seam-level scope-claim refusal (CLM-006-02's mechanism), F-006-3 rows at parser/mapping/builder level (A → contradiction 1.00 + falsifier observation; B → 0.50; C/G → context; clean → context, never support).
- Unavailable-checker honesty: with no PLATON binary and no recorded output the run records `not_runnable_here` with the reason (PLATON's license position; the submission-service boundary) and emits no evidence.

## Open items (not smoothed over)

- **Live PLATON verification (tasks T4)** has never been performed: no PLATON binary exists in this environment and downloading one was not done (author-distributed, not OSI-licensed — installation under its terms is an operator decision). The `platon -u` invocation seam is implemented and exercised end-to-end with a test-double binary emitting the recorded real .chk bytes; that tests this adapter's machinery, not PLATON.
- The A-alert mapping row lacks a full run-path test for want of a public matched (CIF, A-bearing output) pair; see plan.md.
