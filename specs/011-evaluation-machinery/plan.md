# Spec 011 — Evaluation-Machinery Completion — plan

1. Claims + assessment at after_specify (this package, bundle v0.1.0) —
   before any implementation. The requirements source (Spec 002 Phase 7
   EVALUATION-REPORT §4.7, §4.8, §2.3 friction 1/2/5/6) is quoted in
   spec.md; every design decision below is recorded there or here, not
   left in code comments alone.
2. `src/tekmerion/verdicts.py`: add `run_controls_report` (the one
   execution, structured) and reimplement `run_controls` as its
   failure-projection; add `RunResult.control_outcomes`; `evaluate_run`
   populates it on both return paths. Fixture identity = fixture claim id
   + SHA-256 of the canonical fixture dict; swap identity = the
   construction string from `swap_control_report`.
3. `src/tekmerion/verification.py`: the falsifier naming rule
   (`_falsifier_names_record`) + `to_evidence_item(..., claim=None)`.
   `src/tekmerion/ui/state.py`: `derive_evidence` passes the claim;
   `action_export` passes the citations sidecar into the exporter.
4. `src/tekmerion/export.py`: `run_outcome_projection` records per-control
   outcomes in all branches (replay outcomes for invalid/not-run;
   export-time re-execution for issued runs, with the attested
   `passed: null` fallback when a fixture is not presented);
   `export_bundle(..., citations=None)` writes `verification.json`'s
   `as_cited` and `adjudication.json`'s `excluded_citations`;
   HUMAN-README gains the conversion-mapping table; `verify_bundle`
   gains the three cross-checks (control outcomes vs registration +
   outcome consistency + swap recomputation; as-cited vs ledger
   outcomes; exclusion markers vs replayed queue state), each engaging
   only when its field is present, absences recorded in `checks`.
5. Tests `tests/test_spec011.py`: control-report parity against the
   pre-change failure strings; the falsifier-rule battery (fires on
   surname+year and on DOI; silent on every boundary case); an
   end-to-end fixture study whose falsifier IS observed (verdict via
   the falsifier path; excluded citation; export with citations) read
   back **from the bundle alone**; tamper cases for each new check
   (flipped control outcome, altered as-cited claim, dropped exclusion
   marker — each rehashed, each detected); backward compatibility over
   the eight frozen bundles (in-repo Phase 7 pair unconditionally;
   the Phase 5 / math sets when their directories are present) with
   verdicts pinned to their recorded values, plus a stripped-new-keys
   shape test that runs anywhere.
6. Claims re-assessed at after_implement on the built evidence; dated
   assessment record; branch CI green by `gh` read-back. PR opened;
   no merge (coordinator verifies and merges).

## Ambiguities in the source findings, and the resolutions taken

1. **§4.7 says "record control results in the run projection from
   `evaluate_run`'s own execution".** For an issued run, export happens
   after (and in the MCP surface, in a different process than) the
   issuing run, and nothing about the issuing run's control execution
   is persisted today — persisting it would take a new ledger event
   type, which this spec excludes. Resolution: the projection records
   outcomes from the production path executed at projection time —
   the export-time replay for unissued runs (already the NC-6
   pattern), and a deterministic re-execution for issued runs
   (fixture evaluation is a pure function of the fixture; the swap
   control runs on the very ledger being exported). The `basis` text
   states the provenance; the swap outcome — the one control whose
   fixture is in the bundle — is independently recomputed by the
   verifier, and fixture controls are bound by fixture identity hash +
   manifest hashes. The live run's own `RunResult` carries the
   issuing execution's outcomes for its consumers.
2. **§4.8 offers two fixes: "closed in the conversion … or the
   registration language should stop implying it".** Resolution: close
   it in the conversion (the tasking for this spec), with the naming
   rule as the precise, conservative mapping, and record the
   registration-language discipline the rule implies (a designated
   observation is named by DOI or first-author surname + year) in
   spec.md's boundary. A broader semantic match (title-only, fuzzy)
   was rejected: a false falsifier firing is worse than an unset flag,
   because the falsifier path bypasses the sufficiency floor by
   design — precision over recall, doubt → unset.
3. **`controls_replayed` semantics.** The field currently lists kinds
   for replayed runs and `[]` for issued runs. Resolution: it now
   lists the kinds whose outcomes the projection records as executed
   (all branches); the per-control record supersedes it in detail,
   and the field stays for shape compatibility with existing readers.
4. **Where as-cited forms live in the bundle.** `verification.json`
   (beside the outcomes they are inputs to), not a new file: the
   bundle's file set is manifest-bound and a new file would be a
   format change for every consumer (OSF mapping included) for no
   audit gain.
5. **Exclusion markers: which decisions count.** Only decided
   **quarantine** items with decision `exclude`. Grouping items (their
   "exclusion" is not a citation removal — and one fixture suite
   records `exclude` decisions on grouping items, which must not
   mint markers) and `variant` rulings (the item stands) are not
   exclusions. Undecided quarantined items are not excluded — they
   hold the run invalid, a different recorded state.
