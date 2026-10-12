# AEE Assessment — Spec 002 (after_implement, Phases 0–3)

**Date:** 2026-10-12 · **Tooling:** spec-kit 1.0.10, AEE extension v1.2.0, AEE engine 1.0.4 (glossa venv pin), threshold 0.70
**Claims assessed:** 13 (`aee-claims.json` v0.3.0) · **Machine record:** `aee-assessment.json`
**Outcome: ITERATE** — 10 claims at 1.00 confidence; 3 below threshold, all of them Phase 4/5 commitments that are *supposed* to be below threshold today.

## Per-claim state

| Claim | Score | State |
|-------|-------|-------|
| CLM-002-01 append-only, chained, signed record layer | 1.00 | supported — Axiomere core + seeded-defect tests |
| CLM-002-02 per-record license_basis; unlicensed abstracts dropped | 1.00 | supported — connector tests + live Crossref run |
| CLM-002-03 OpenAlex budget discipline (reserve/settle, exhaustion = stop) | 1.00 | supported — tests + live key run |
| CLM-002-04 falsifier mandatory; statements immutable, supersede-only | 1.00 | supported — register tests |
| CLM-002-05 dependency cycles rejected as circular support | 1.00 | supported — graph tests |
| CLM-002-06 INVALID attaches to the run; zero claim verdicts | 1.00 | supported — verdict tests |
| CLM-002-07 SUPPORTED requires exposure + interval clearing the margin | 1.00 | supported — verdict tests |
| CLM-002-08 controls run through production paths (RT-1) | 1.00 | supported — incl. swap control vs. the real verifier |
| CLM-002-09 exploratory/confirmation wall + RT-3 disclosure | 1.00 | supported — wall + freeze-check tests |
| CLM-002-12 dead-snapshot withdrawal semantics | 1.00 | supported — Axiomere + StudyStore tests |
| CLM-002-10 citation pipeline drives fabrication to zero (K1) | 0.68 | **draft** — Phase 4 not built; the Phase 7 evaluation is its test |
| CLM-002-11 audit bundle verifies standalone | 0.48 | **draft** — Phase 5 not built |
| CLM-002-13 external anchoring before any pilot (AR-1/G2) | 0.48 | **draft** — Phase 5 not built; hard gate stands |

## Reading

The implemented surface (Phases 0–3) carries its claims at full confidence because each names a mechanism, a test that exercises it, and a falsifier. The three sub-threshold claims are not defects in this assessment — they are the remaining build, stated as predictions with kill criteria attached (CLM-002-10 *is* K1). ITERATE is the correct verdict for a spec mid-implementation: proceed to Phase 4, and these claims either gain evidence or fail honestly.

The engine's standing irreducibility challenge fired on all 13 claims. Two genuinely compound claims were split in response (002-01 → +002-12; 002-11 → +002-13); the remainder are single propositions and the challenge is recorded, not gamed.

*Process note:* this spec was implemented (Phases 0–3, 2026-10-11) before its AEE claims bundle existed — a deviation from the repo's own spec-kit + AEE flow, corrected by this assessment. Spec 001's claims were also normalized to the engine's claim format this date and re-assessed (`specs/001-research-engine/aee-assessment.json`: outcome **gather_evidence**, matching its original 2026-10-11 hand assessment). From Phase 4 onward, claims precede code.
