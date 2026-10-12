# Phase 7 evaluation

The MVP engine's pre-registered evaluation (Spec 002, Phase 7): five
evidence questions from the systematic-review workflow, ten citations —
real records from Crossref/OpenAlex, among them a seeded fabricated
DOI, a seeded corrupted citation, a duplicate citation, and a
shared-dataset pair — plus positive, negative, and swap controls.
Predictions for every verdict were recorded in the corpus document
**before** the freeze.

**Registration:** Merkle root
`a4c798715c05ae151849ddf0e7c4a3dcb7b119620757b088686bd18d24e6c049`.
**Run:** VALID. **Anchor:** Zenodo
[DOI 10.5281/zenodo.23319126](https://doi.org/10.5281/zenodo.23319126).
Full report: `specs/002-mvp-implementation/evaluation/EVALUATION-REPORT.md`
in the repository.

## Verdicts — all five matched their pre-registered predictions

| Claim | Verdict | Mechanism, as it fired |
|---|---|---|
| CLM-E-001 (CBT-I) | **supported** | One origin group (duplicate folded in), support 0.8, interval clears the margin; fabricated citation excluded pre-evidence |
| CLM-E-002 (meditation) | **supported** | One agreeing group; corrupted citation excluded pre-evidence |
| CLM-E-003 (exercise) | **inconclusive** | Interval dilution: a content-checked supporting group averaged with a metadata-only group (ignorance mass) straddles the margin |
| CLM-E-004 (glucosamine) | **contradicted** | The cited record's conclusion negates the proposition; interval clears −margin |
| CLM-E-005 (Framingham) | **inconclusive** | Below sufficiency floor: the shared-dataset fold leaves 1 group against a registered floor of 2 |

## Kill criteria

| Criterion | Result |
|---|---|
| **K1** Citation resolution: fabrications driven to zero in the evidence basis | **Pass** — 10/10 citations accounted to exactly one outcome; the fabricated DOI was caught, quarantined, adjudicated *exclude*, and contributes zero evidence |
| **K2** Replay integrity: the bundle alone reproduces the verdicts; tampering is detected | **Pass** — *after* the evaluation caught a real verifier defect (below) |
| **K3** Adjudicator burden: a fresh reviewer retraces every verdict from the bundle alone within 2 h/question | **Pass** — 5/5 claims fully retraced in ~18 minutes total |
| **K4** Origin honesty: derivative sources counted once | **Pass** — duplicate and shared-dataset pairs each fold to one origin group; the fold is visible in CLM-E-005's verdict |
| **K5** Cost ≤ $25/question | **Pass** — $0.0012 per question at the providers' published rates |

## The defect the evaluation caught

K2's tamper case A — a verdict string flipped inside `verdicts.json`,
manifest rehashed — was **not detected on the first pass**: the
verifier's projection cross-check compared only the *count* of verdict
entries against the ledger, not their payloads. It was fixed in-phase
(payload-for-payload comparison, regression test), honest replay was
unchanged, and all four pre-existing demo bundles still verify under
the strengthened verifier. K2 is recorded as a pass *with that
sequence disclosed*.

## Stated limits

- **One operator played all four actors** (researcher, adjudicator,
  second reviewer, verdict service). Wherever independence matters,
  the report says so; the claims stand at *checked*, not *accepted*.
- The bundle carries no per-control outcomes and no retrieved content
  (the rights gate), so an offline auditor takes stage-3 stance labels
  on the pipeline's word — recorded as machinery findings, and since
  addressed in part by Spec 011 (per-control outcomes and falsifier
  observations now recorded in bundles).
- The lexical stance checker is brittle at sentence level; a subtler
  fabrication (a real DOI attached to the wrong proposition) stresses
  exactly that weakness.
