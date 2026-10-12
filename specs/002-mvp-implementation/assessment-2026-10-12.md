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

## Phase 4 addendum (2026-10-12, after_implement — claims first, honored)

Claims preceded code this phase, per the standing rule. Seven atomic Phase 4 claims (CLM-002-14…20) were added to the bundle (v0.4.0) and assessed at `after_specify` **before** any pipeline code existed: scores 0.48–0.68, all drafts — the correct pre-build state. After implementation and tests, the bundle (v0.4.1) was re-assessed at `after_implement`; the machine record `aee-assessment.json` now reflects this run.

| Claim | Before (after_specify) | After (after_implement) | State |
|-------|-------|-------|-------|
| CLM-002-14 K1 accounting: one explicit outcome per citation, ledgered | 0.68 | 1.00 | supported — mixed-batch + transport-error tests |
| CLM-002-15 metadata disagreement quarantines the citation | 0.68 | 1.00 | supported — tampered-metadata seeded defect |
| CLM-002-16 content-verified only from licence-permitted retrieved content | 0.68 | 1.00 | supported — content stage tests incl. unsupported-content defect |
| CLM-002-17 origin grouping by WS2 keys; key 4 flagged, never auto-merged | 0.48 | 1.00 | supported — precedence-keys + suspect tests |
| CLM-002-18 adjudication queue is ledger-backed replay; named decisions | 0.68 | 1.00 | supported — replay + append-only decision tests |
| CLM-002-19 RT-4 seeded 10% second-review sampling; zero-disagreement anomaly | 0.68 | 1.00 | supported — determinism, anomaly, and disagreement-clears tests |
| CLM-002-20 RT-5 metadata-only cap mechanized in the verdict path | 0.48 | 1.00 | supported — cap binds / mixed-basis tests |

**Outcome remains ITERATE** (20 claims; 3 below threshold): CLM-002-10 (K1) at 0.68 — still a draft *by design*: its falsifier is the Phase 7 frozen evaluation, and Phase 4 building the pipeline does not discharge it. CLM-002-11 and CLM-002-13 (Phase 5 bundle/anchor) at 0.48. Two build notes worth the record: (1) grouping keys are applied as pairwise equivalence (union-find) — a per-item single-key reading would have made WS2 key 2 (same dataset) unreachable whenever both items carry DOIs, which is precisely the two-papers-one-dataset case key 2 exists for; a failing test caught the first implementation doing exactly that. (2) A live Crossref smoke (2026-10-12) resolved a real 1905 DOI, returned not-found for a fabricated one, and — correctly — routed the real paper to adjudication, because Crossref carries the German title and the citation used the English translation: translated titles are stage-2 *variant* judgments, and the queue is where they belong.
