# Axiovex Research Engine — Project Constitution

**Version:** 1.0.0 · **Ratified:** 2026-10-11 · **Owner:** Tristen Pierson, Axiovex Systems, LLC

The constitution governs all work in this repository. Where a spec, plan, or implementation conflicts with an article here, the constitution wins and the conflict is recorded.

## Article I — Defensibility is the product

Every feature is judged by one question: does it make a result easier for an independent reviewer to verify, reproduce, or falsify? Speed, fluency, and convenience are subordinate. A feature that makes output faster but less inspectable is a regression.

## Article II — No claim without a falsifier

Every claim the system registers, and every claim this project makes about itself (in the README, specs, and reports), carries: a stable ID, a kind, the evidence it rests on, and the observation that would falsify it. A claim that cannot state its falsifier is not registered — it is rewritten until it can be, or dropped.

## Article III — Freeze before outcomes

Research designs — question, sources, inclusion criteria, verdict rules, controls, margins — are frozen and timestamped before evidence is gathered or outcomes are seen. Changes after freeze are amendments: new, dated, appended records that state what changed and why. The frozen original is never edited.

## Article IV — Append-only records

Records are never mutated or deleted. Corrections are new records that supersede old ones, with the supersession explicit. Any store, export, or cache in the system must preserve this: derived views may be rebuilt, the underlying record may not be rewritten.

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

## Amendment

This constitution is amended only by a dated design note recording the change, the reason, and the owner decision it rests on, plus a version increment here. The prior text remains in git history — Article IV applies to governance too.
