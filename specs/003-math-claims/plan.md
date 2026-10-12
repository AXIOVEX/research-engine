# Spec 003 — Plan

**Date:** 2026-10-12 · Companion to `spec.md`. Authority: DN-010 (adopted); owner directive 2026-10-12.

## Build order

```
Phase A  Math layer core (src/tekmerion/mathclaims.py) — theorem schema +
         composition, digestion + lane records, dispute registration,
         reliability projection. Seeded-defect tests first-class.
Phase B  Lean ingestion — fetch/hash/parse; compile runner over the local
         Lean 4.33.1 toolchain with the three honesty states; axioms probe.
Phase C  Checks — openness (primary status source + connector searches),
         attribution (literature search + dispute registration).
Phase D  The worked study — five cases (a)–(e) researched from retrieved
         public sources only; one study, multi-actor, frozen; verdicts
         through evaluate_run + composition; reliability seed from (e).
Phase E  Export + anchor — audit bundle, Zenodo deposit (owner directive
         as the recorded adjudicator approval), verify_anchor against the
         independently fetched public record. Re-assessment of this spec's
         claims at after_implement.
```

## Key decisions carried from the doctrine (DN-010)

- Parent composition precedence is fixed in Spec 003 §2 (contested cap
  first) — it is doctrine, not a tuning knob.
- Compile honesty states are part of the record's vocabulary; anything
  not run by us is labeled, and `not_runnable_here` never scores as a
  proof failure.
- Lane 2 moves only on human-evidence events. In the worked study the
  humans are the study's named adjudicator + any public explainers whose
  artifacts are retrieved; claimant self-explanation is labeled as such.
- No aggregate solved-count is produced by the report path (CLM-003-10);
  the study report enumerates per-case records.

## Risks carried visibly

- Claimant artifacts may be unreachable, moved, or too large to fetch;
  unreachable is recorded as a gap and scores INCONCLUSIVE, never filled
  in from narrative.
- Mathlib-dependent artifacts likely exceed the local environment
  (no Mathlib build present) — expect `not_runnable_here` /
  `claimed_by_source` states and record them as such.
- Public reporting on the five cases is contested terrain by design
  (case (a) above all): both sides' evidence is registered, and where
  retrieval fails, the failure is the record.

## Phase records

- 2026-10-12 — Spec drafted under DN-010; claims first: CLM-003-01…12
  assessed at `after_specify` (bundle v0.1.0) **before** any math-layer
  code: outcome **gather_evidence**, 10 of 12 below the 0.70 threshold
  (0.481–0.675); CLM-003-04 and CLM-003-12 at 0.958 on already-observed
  evidence (the local Lean toolchain; the Phase 5 INVALID-run record).
