# Spec 011 — Assessment record (2026-10-12)

## after_specify (bundle v0.1.0, before any implementation)

Assessed with the pinned assessor (`~/workspace/venvs/glossa-lab/bin/aee`,
AEE engine 1.0.4, threshold 0.70, phase `after_specify`); machine record:
`aee-assessment.json`.

**Outcome: iterate** — 9 claims assessed, 22 failure modes found, all 9
below the 0.70 threshold (0.481–0.680), all `draft` / lifecycle stage
`created`. This is the expected specify-time posture: the claims rest on
asserted evidence (the spec, and the Phase 7 evaluation report that is
their requirements source) and no implementation exists yet. The claims
precede the code; nothing in this spec was built before this assessment
ran.

Baseline recorded the same day, before changes: the full test suite
stands at **249 passed, 2 skipped**, and all eight frozen bundles named
in CLM-011-08 verify standalone (`verify_bundle` ok, no failures) with
their verdicts read and pinned in the claim's boundary.

## after_implement (bundle v0.2.0)

Built in this same package (branch `spec/011-machinery`): the three
fixes landed in `verdicts.py` (structured control outcomes, one
execution), `verification.py` (the falsifier naming rule),
`ui/state.py` (claim pass-through in `derive_evidence`; citations
sidecar into the exporter), and `export.py` (run-projection outcomes,
as-cited forms, exclusion markers, README mapping, and the three
verifier cross-checks). Re-assessed with the pinned assessor at
`after_implement` (machine record:
`aee-assessment-after-implement.json`).

**Result: all 9 claims `supported` at confidence 1.000, lifecycle
stage `checked`; 0 claims below the 0.70 threshold.** The bundle
outcome computes as `iterate` (22 failure modes stand across the
bundle, as at after_specify) — reported as computed, not rounded up.
Stage is checked throughout (the author's own tests — checking, not
acceptance; DN-010).

Evidence, per fix:

- **Control outcomes.** `tests/test_spec011.py` (25 tests) pins the
  pre-change failure strings literally (parity), reconstructs all
  three control outcomes from an exported bundle alone, and detects
  each tamper (flipped outcome, dropped control, misstated swap)
  after manifest rehash. Full suite: **274 passed, 2 skipped** — the
  249 baseline plus the 25 new, no regressions.
- **Falsifier wiring.** The battery fires on surname+year and on DOI,
  and stays silent on every boundary case (generic falsifier,
  title-only naming, wrong year/author, supports, metadata-only,
  quarantined, unresolved, no claim, no resolved record). The
  workspace rebuild path is exercised end-to-end: the flag is derived
  from ledger outcomes and CLM-A-001 verdicts CONTRADICTED with the
  falsifier reason — the mechanism attribution Phase 7's CLM-E-004
  registration asserted but the machinery could not produce.
- **Citation completeness + compatibility.** The bundle-alone audit
  reads the as-cited forms (fabricated DOI included), exactly one
  exclusion marker, and the README's conversion table from the
  artifact. All eight frozen bundles re-verify under the new code
  with their verdicts equal to the pre-change pinned values; a
  stripped-keys bundle verifies with absences noted in `checks`.

**Remains not understood / honest limits.** (1) Fixture controls'
observed verdicts are attested by the export-time production-path
execution and bound by manifest hashes — not recomputable from the
bundle alone, because fixtures are registration-external (identity
hashes are recorded so a reader holding the fixtures can bind them);
only the swap outcome is fully recomputed by the verifier. (2) The
falsifier naming rule reads identity from the resolved record as it
reaches the conversion: the live pipeline and the workspace flow
(sidecar-cached records) carry it; a bare-ledger replay with no
retrieved record cannot name-match and leaves the flag unset, by
design (doubt → unset) — issued verdicts in the ledger govern those
records regardless. (3) The naming rule's two forms (DOI,
first-author surname + year) cover the citation conventions the
program's registrations use; a falsifier naming its observation by
title alone will not fire it, and that is a recorded boundary, not
an oversight.
