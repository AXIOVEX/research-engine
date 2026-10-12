# Spec 011 — Evaluation-Machinery Completion — tasks

Requirements source: Spec 002 Phase 7 EVALUATION-REPORT §4.7, §4.8,
§2.3 friction (1) (2) (5) (6) — machinery findings (7) (8) and the
bundle-completeness items. Out-of-scope §2.3 items and their reasons
are recorded in spec.md's non-goals.

- [x] T0 Spec + claims bundle v0.1.0 + assessor run at after_specify
      (outcome iterate; 9 drafts at 0.481–0.680 — asserted evidence only,
      as expected before implementation; `assessment-2026-10-12.md`).
- [x] T1 Structured control outcomes (`verdicts.py`):
      `run_controls_report` as the one execution; `run_controls`
      reimplemented as its failure-projection (parity-tested against
      the pre-change strings); `RunResult.control_outcomes`;
      `evaluate_run` populates both return paths (CLM-011-01, -02).
- [x] T2 Run projection records outcomes (`export.py`):
      `run_outcome_projection` gains `controls` in all three branches —
      replay outcomes (invalid / not-run), export-time re-execution
      (issued), attested `passed: null` when a fixture is not
      presented; `controls_replayed` lists executed kinds; `basis`
      states provenance (CLM-011-01).
- [x] T3 Verifier coverage for control outcomes (`export.py`):
      identity/coverage vs the committed registration, consistency
      with the stated run outcome, swap outcome vs the verifier's own
      replay on the bundle's ledger copy; absence noted, not failed
      (CLM-011-03).
- [x] T4 Falsifier wiring (`verification.py` + `ui/state.py`):
      the naming rule (resolved ∧ agree ∧ contradicts ∧ falsifier
      names the resolved record by DOI or first-author surname +
      year); `to_evidence_item(..., claim=None)` sets the flag on
      the contradicting branch only; `derive_evidence` passes the
      claim (CLM-011-04, -05).
- [x] T5 As-cited forms (`export.py` + `ui/state.py`):
      `export_bundle(..., citations=None)` → `verification.json`
      `as_cited`; workspace export passes the citations sidecar;
      verifier cross-check vs the ledger's `citation.checked`
      outcomes (CLM-011-06).
- [x] T6 Exclusion markers (`export.py`): `adjudication.json`
      `excluded_citations` from the queue-state replay (decided
      quarantine excludes only); verifier re-derives and compares;
      evidence files unchanged (CLM-011-07).
- [x] T7 README conversion mapping (`export.py`): HUMAN-README
      states the content-outcome → evidence conversion table
      (CLM-011-09).
- [x] T8 Tests (`tests/test_spec011.py`): parity battery, falsifier
      battery, bundle-alone audit end-to-end, three tamper cases,
      backward compatibility (eight frozen bundles, verdicts pinned;
      stripped-keys shape test) (CLM-011-08).
- [x] T9 Claims re-assessed at after_implement; dated assessment
      record; full suite green; PR opened (no merge).
