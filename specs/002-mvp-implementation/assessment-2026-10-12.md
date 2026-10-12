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

## Phase 5 addendum (2026-10-12, after_implement — claims first, honored; AR-1 demonstrated live)

Claims preceded code again. CLM-002-11 (bundle) and CLM-002-13 (anchor) were decomposed into ten atomic claims (CLM-002-21…30, bundle v0.5.0) and assessed at `after_specify` **before** any export code existed: 0.675–0.756, all drafts. After implementation, tests, and the live anchor demonstration, the bundle (v0.5.1) was re-assessed at `after_implement`; the machine record `aee-assessment.json` now reflects this run.

| Claim | Before (after_specify) | After (after_implement) | State |
|-------|-------|-------|-------|
| CLM-002-21 bundle completeness: ledger byte-faithful, full register | 0.68 | 1.00 | supported — standalone + determinism tests |
| CLM-002-22 manifest binds the file set (hashes + bundle hash) | 0.68 | 1.00 | supported — flipped-byte + unlisted-file defects |
| CLM-002-23 standalone verification (production verifier; root match) | 0.68 | 1.00 | supported — truncated ledger / tampered payload / altered root, all with attacker-rehashed manifests |
| CLM-002-24 registration bound to the ledger's frozen commitment | 0.67 | 1.00 | supported — tampered-registration defect + fail-closed export |
| CLM-002-25 WS5 §2 support-check coverage per claim | 0.68 | 1.00 | supported — metadata-only claim reports group_coverage 0.0 |
| CLM-002-26 WS5 §4 rights-gated content; substitutions listed | 0.68 | 1.00 | supported — CC-BY in; unlicensed stubbed + listed |
| CLM-002-27 deposit is adjudicator-approved; metadata states root + hash | 0.68 | 1.00 | supported — approval gate + metadata tests |
| CLM-002-28 anchor production via external party (Zenodo DOI) | 0.76 | 1.00 | supported — local loop + **live deposit** |
| CLM-002-29 receipt is part of the study record | 0.68 | 1.00 | supported — `anchor.recorded` event + manifest carriage |
| CLM-002-30 independent anchor verification (bundle + public record) | 0.68 | 1.00 | supported — foreign/tampered record defects + **live verification** |
| CLM-002-11 (roll-up) audit bundle verifies standalone | 0.48 | 1.00 | supported |
| CLM-002-13 (roll-up) external anchoring before any pilot (AR-1/G2) | 0.48 | 1.00 | supported — demonstration live; **G2 ratification is the owner's act** |

**The AR-1 demonstration, as it actually ran (2026-10-12):** a small demo study (one claim) was built through the production paths with live Crossref — the real 1905 Einstein DOI resolved and was adjudicated a translated-title *variant* (metadata-only evidence); a fabricated DOI returned not-found and was adjudicated *exclude*; one RT-4 second review was sampled and logged. The study froze at Merkle checkpoint root `7434209696ea39ba8e97a33b5caa0ae08928269ea81c7d6407f423191e86e317`. Its audit bundle (hash `92093186…`) was exported, verified standalone, and **deposited live to Zenodo: DOI [10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479), record created 2026-10-12T06:46:48Z**, the record's description stating the root and bundle hash. The receipt was appended to the study ledger (`anchor.recorded`), the ledger re-checkpointed, and the re-exported bundle was verified against the public record fetched independently: `verify_anchor` passes, including the deposited file's MD5 against the local package. Demo artifacts live outside the repo at `~/workspace/phase5-demo/` (study ledger, both bundles, package, public-record JSON, driver).

**A defect the demonstration surfaced (recorded, not worked around):** the demo study's evaluation run was **INVALID and issued no verdicts**. The swap control tampers by exchanging the actor fields of ledger lines 1 and 2; in this single-actor study both are `researcher`, so the tamper is a no-op, the production verifier (correctly) sees an intact chain, the control fails, and the run is INVALID per WS3 — the machinery refused to certify, which is its job (Article VI). The limitation is the control's fixed line selection: it assumes two early events with distinct actors (true of the Phase 3 fixtures, false of single-actor studies). Consequences, honestly: (1) the deposited bundle's `verdicts.json` is an empty list — the bundle records the INVALID outcome rather than a verdict; (2) the Zenodo description as first published anticipated an INCONCLUSIVE verdict and was **corrected in place** (metadata edit, same DOI, files unchanged) to state the INVALID outcome and why. Fixing the control's event selection is Phase 7 preparation work (the evaluation corpus will hit this), not Phase 5 scope; it is logged here and in tasks.md.

**Outcome remains ITERATE** (30 claims; exactly 1 below threshold): CLM-002-10 (K1) at 0.68, a draft by design until the Phase 7 frozen evaluation. Everything else in the bundle — Phases 0–5 — stands at 1.00.

## Phase 6 addendum (2026-10-12, after_specify — claims first, honored; then re-sequenced by owner ruling)

Ten atomic Phase 6 claims (CLM-002-31…40, bundle v0.6.0) were authored and assessed at `after_specify` **before** any UI code existed; the machine record `aee-assessment.json` now reflects this run. All ten are drafts below threshold — the correct pre-build state:

| Claim | After_specify | State |
|-------|-------|-------|
| CLM-002-31 register-first workspace (no landing/chat surface) | 0.68 | draft |
| CLM-002-32 registration rules enforced identically (falsifier refusal is the engine's; no ledger write) | 0.675 | draft |
| CLM-002-33 no edit/delete affordances; mutations are appends only | 0.68 | draft |
| CLM-002-34 dead renders dead (status + reason + score 0.0) | 0.675 | draft |
| CLM-002-35 INVALID run renders INVALID, reasons shown, zero claim verdicts | 0.675 | draft |
| CLM-002-36 metadata-only visibly flagged at every level | 0.68 | draft |
| CLM-002-37 adjudication via the engine's named appends; re-decision refused + surfaced | 0.675 | draft |
| CLM-002-38 role views bound affordances; identity via the SSO hook, recorded as actor | 0.68 | draft |
| CLM-002-39 export reachable; verifier result shown truthfully (failures surface with reasons) | 0.675 | draft |
| CLM-002-40 anchor receipt displayed from the record (mechanism, DOI, root) | 0.675 | draft |

**Re-sequencing (owner ruling, 2026-10-12):** before implementation began, the owner ruled *wireframes first, and the wireframes are constitutional* — no UI change without updated wireframes and his approval of the **rendered** wireframes (DN-009; constitution Article XIV drafted for v1.2.0, effective on that approval). The Phase 6 deliverable is therefore, first, the wireframe package in `docs/wireframes/` (screens (a)–(f) + component specimens, rendered at desktop + mobile and inspected; sample data is the Phase 5 demo study throughout — its INVALID run, metadata-only group, variant/excluded citations, and live DOI are the content). tasks.md gate T219-WF records the block; **no UI task is checked off, and these claims stay drafts**: their evidence is the approved-wireframe implementation, which does not exist yet. Two build notes from the wireframing itself: (1) the anchored bundle and the current bundle differ (v1 anchored, v2 carries the receipt) — screen (f) states both hashes rather than conflating them; (2) states absent from the demo study are specified as labeled specimens (`components.html`), not fabricated into study screens.

**Outcome remains ITERATE** (40 claims; 11 below threshold): CLM-002-10 (K1) at 0.68 by design, and CLM-002-31…40 as drafts awaiting gate T219-WF (owner approval of the rendered wireframes) and then implementation.

## Addendum — 2026-10-12 Tao realignment audit (DN-010)

Bundle reclassified v0.6.0 → v0.7.0: every claim now carries `lifecycle_stage` + `stage_basis`. No claim text, falsifier, or evidence was rewritten; git history is the append-only trail. Stages: all previously "supported at 1.00" claims are **checked** (their evidence is the author's own seeded-defect test suite, CI green by read-back — checking, not settlement), except CLM-002-13, which is **accepted** on the owner's G2 ratification act (DN-008) for the AR-1 gate demonstration. CLM-002-10 remains **created** (K1 held; its falsifier is the Phase 7 frozen evaluation). CLM-002-31…40 (UI) are **created** (UI unbuilt; wireframe gate T219-WF pending). No claim is explained or digested: no named-human explanation or digestion record exists for any of them. Full audit: docs/audits/2026-10-12-tao-realignment-audit.md.
