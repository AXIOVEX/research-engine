# AEE Assessment — Spec 003 (after_specify, before code)

**Date:** 2026-10-12 · **Tooling:** AEE engine 1.0.4 (glossa venv pin), threshold 0.70
**Claims assessed:** 12 (`aee-claims.json` v0.1.0) · **Machine record:** `aee-assessment.json`
**Outcome: GATHER_EVIDENCE** — 10 claims below threshold; all 12 are drafts, as they must be before the math layer exists.

## Per-claim state (before)

| Claim | Score | State |
|-------|-------|-------|
| CLM-003-01 theorem decomposition (parent + five sub-claims) | 0.675 | draft — schema specified, not built |
| CLM-003-02 composition never outruns weakest sub-claim; contested caps | 0.675 | draft |
| CLM-003-03 ingestion hashes bytes; sorry counts from bytes | 0.675 | draft |
| CLM-003-04 compile honesty states (run / not-runnable / claimed) | 0.958 | draft — key evidence (local Lean 4.33.1 toolchain) already observed |
| CLM-003-05 faithfulness pinning (formal vs original, verbatim + sourced) | 0.481 | draft |
| CLM-003-06 openness: primary status source + ledgered searches, evidence only | 0.675 | draft |
| CLM-003-07 dispute registration with both sides' evidence; state = replay | 0.675 | draft |
| CLM-003-08 digestion record or UNEXPLAINED + risk flag | 0.481 | draft |
| CLM-003-09 two lanes on every verdict record; lane 2 human-evidence only | 0.481 | draft |
| CLM-003-10 no aggregate solved-counts in outputs | 0.481 | draft |
| CLM-003-11 reliability seeding discipline (identified or nothing) | 0.675 | draft |
| CLM-003-12 study verdicts only via production path, multi-actor; INVALID ⇒ none | 0.958 | draft — the Phase 5 INVALID-run record is observed evidence for the discipline |

## Reading

This is the claims-first state the standing rule exists to produce: the
spec's commitments are on the record, scored as the unbuilt things they
are. CLM-003-04 and CLM-003-12 score higher because their decisive
evidence is not a promise — the toolchain is installed and the Phase 5
record exists. Everything else earns its score in Phases A–E or fails
honestly. The after_implement re-assessment (T315) is where the after
column gets written.

## Addendum — 2026-10-12 Tao realignment audit (DN-010)

Bundle reclassified v0.1.0 → v0.1.1: every claim now carries `lifecycle_stage` + `stage_basis`. Stages: CLM-003-01…05, 07…11 **checked** (built with seeded-defect tests, suite 82/82, CI read-back success); CLM-003-06 **created** — self-flagged nonconformance: `openness_check` was marked done (T308/T309) on build alone, with no test exercising it and no live run; correction is a fixture test plus live exercise during the worked study, after which it is re-staged; CLM-003-12 **created** (worked study not yet run). Full audit: docs/audits/2026-10-12-tao-realignment-audit.md.

Correction to the addendum (same day, 2026-10-12): the CLM-003-06 fixture test has landed (tests/test_mathclaims.py::test_openness_check_emits_evidence_not_a_verdict, suite 15/15 in that module) and CLM-003-06 is re-staged **checked** in bundle v0.1.1; its live exercise remains part of the worked study. The addendum above stands as the record of the nonconformance at audit time.

## Addendum 2 — after_implement re-assessment (2026-10-12)

The worked study (T310–T314) is complete: freeze root 5b497655dd6ae50d0ca39328b674bc528ad1f03d4a1febca70077ad514a49ad4 (run 2; run 1 superseded in-ledger after a disclosed driver defect), run VALID, verdicts: CLM-M-110 contested, CLM-M-210 contested, CLM-M-310 inconclusive, CLM-M-410 inconclusive, CLM-M-510 supported. Bundle hash abb856aa5b5d5f57725b088399f2276e6ac712c6896b3c3ed1fb47c91a353de4; Zenodo DOI 10.5281/zenodo.23317259; anchor verified against the independently fetched public record. CLM-003-12 re-staged created → checked; CLM-003-06's live exercise is done. Statuses/scores below are the assessor's read of the updated bundle at after_implement.
