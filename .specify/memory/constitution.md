# Tekmerion — Project Constitution

**Version:** 1.1.0 · **Ratified:** 2026-10-11 · **Amended:** 2026-10-11 (Article IV strengthened + Article XIII added, per DN-005) · **Owner:** Tristen Pierson, Axiovex Systems, LLC
**Draft amendment pending:** v1.2.0 — Article XIV (below) is drafted per DN-009 and takes effect, with the version increment, on the owner's approval of the Phase 6 wireframe package. Until that approval it is a proposal recorded here, not a rule in force.

The constitution governs all work in this repository. Where a spec, plan, or implementation conflicts with an article here, the constitution wins and the conflict is recorded.

## Article I — Defensibility is the product

Every feature is judged by one question: does it make a result easier for an independent reviewer to verify, reproduce, or falsify? Speed, fluency, and convenience are subordinate. A feature that makes output faster but less inspectable is a regression.

## Article II — No claim without a falsifier

Every claim the system registers, and every claim this project makes about itself (in the README, specs, and reports), carries: a stable ID, a kind, the evidence it rests on, and the observation that would falsify it. A claim that cannot state its falsifier is not registered — it is rewritten until it can be, or dropped.

## Article III — Freeze before outcomes

Research designs — question, sources, inclusion criteria, verdict rules, controls, margins — are frozen and timestamped before evidence is gathered or outcomes are seen. Changes after freeze are amendments: new, dated, appended records that state what changed and why. The frozen original is never edited.

## Article IV — Append-only records: no deletions, ever

Records are never mutated or deleted, and **there is no delete operation** — not in any API, UI, or admin path. Change happens only by appending new snapshots of older records: each snapshot is content-addressed, names its parent, and the full lineage stays readable. Withdrawal is a new snapshot with `status: dead`, a mandatory reason, and `score: 0.0` (DN-005). Derived views may be rebuilt; the underlying record may not be rewritten, masked, or hidden. The sole exception is the break-glass erasure certificate of DN-005, exercised only under documented legal compulsion, owner-signed, on the record.

## Article V — Evidence is counted by origin

Evidence is grouped by origin. Derivatives — summaries, citations-of-citations, syndicated copies, model outputs trained or prompted on the same source — never increase the count. Every evidence item carries provenance sufficient for an independent party to retrieve and re-check the original.

## Article VI — Controls must be able to fail

Every gate, check, and control is designed with a discriminating positive and negative case. A control that cannot differentially fail is a defect: a run that passes it is marked **INVALID**, and the defect is recorded, not worked around. The project's own process obeys the same rule — reviews and tests that cannot fail do not count as verification.

## Article VII — Verdicts are claim-by-claim, from a fixed taxonomy

Verdicts are issued per claim, never as one blended score for a whole study. The taxonomy is fixed: **INVALID** (the run was defective), **INCONCLUSIVE** (evidence does not decide), **CONTRADICTED** (evidence decides against), **SUPPORTED** (evidence decides for, within the registered margin). Margins are reported with intervals.

## Article VIII — No fabricated references

A citation that cannot be resolved to a real, retrievable source is a run-failing defect. The system never generates a plausible-looking reference, never fills a gap with a representative example presented as real, and surfaces unverifiable items as defects — loudly, in the record.

## Article IX — Humans adjudicate

The engine prepares, weighs, and recommends. For institutional use, a named human adjudicator signs every verdict set that leaves the system. Points where judgment is required are designed as explicit adjudication points, not hidden inside automation.

## Article X — Honest status

Statuses are claims and follow Article II. Repository documents state only verified states ("repo created" only after read-back; "verified" only after the check that could have failed). Negatives, invalid runs, and limits are reported in the same register as successes. Exploratory and confirmation results are labeled and never blended.

## Article XI — Source rights are part of the design

Every external source enters through a connector that records its terms: what may be queried, stored, and redistributed. A source whose terms do not permit the intended use is not used for that use, however convenient.

## Article XII — Spec before code

Work runs constitution → spec → plan → tasks, with AEE claims on each spec. No implementation before the governing spec and architecture have been iterated, including a red-team pass. Amendments follow Article III.

## Article XIII — Signed, checkpointed, anchored

Every append is signed with its actor's Ed25519 key. Event ranges are periodically closed under signed Merkle checkpoints. Checkpoint roots are anchored externally (deposit or timestamp authority the operator does not control) before any institutional reliance — a chain whose only copy the operator holds proves consistency, not history; anchoring is what makes rewriting detectable by anyone. (DN-005, layers 1–5.)

## Article XIV — Wireframe-governed UI *(DRAFT — pending owner approval of the Phase 6 wireframe package; DN-009)*

The wireframes are the requirements for the UI's layout and appearance. No UI change ships without the wireframes (`docs/wireframes/`) being updated first and the **rendered** wireframes — screenshots at desktop and mobile widths — approved by the owner. A shipped UI that differs from the approved wireframes is a defect against the wireframes. The surface is where this product's discipline is either visible or faked — an INVALID run softened, a dead record omitted, a metadata-only basis hidden — so the surface is governed like the record: specified before built, reviewed as rendered, amended in the open.

## Amendment

This constitution is amended only by a dated design note recording the change, the reason, and the owner decision it rests on, plus a version increment here. The prior text remains in git history — Article IV applies to governance too.
