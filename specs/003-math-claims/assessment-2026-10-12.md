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
