# Spec 011 — Evaluation-Machinery Completion (Control Outcomes, Falsifier Wiring, Bundle Citation Completeness)

- **Date:** 2026-10-12 · **Status:** Specified 2026-10-12 (claims first; assessed at after_specify before any code). Build follows in this same spec package.
- **Requirements source:** Spec 002 Phase 7 `EVALUATION-REPORT.md` — §4 findings (7) and (8), and the §2.3 K3 auditor friction items (1), (2), (5), (6). The evaluation proved these gaps on a live run; this spec closes them.
- **Scope discipline:** this spec is about **recording what the machinery already decides**. No verdict mathematics, threshold, or control semantics changes. No UI changes (Article XIV). No edits to any frozen study artifact. Every change is additive: new fields, new projection keys, new verifier checks that engage only when the new fields are present.

## The three gaps

1. **Control outcomes are ephemeral** (Phase 7 §4.7; §2.3 friction 1). `run_controls`
   returns failure strings into the run evaluation and a valid run silently implies
   success. The exported bundle carries control *definitions* (`controls.json`) and a
   `run_outcome` whose `controls_replayed` is `[]` for every issued run — so from the
   artifact alone, an auditor cannot determine whether any control ever ran, which
   ones, or with what result. Yet the controls' own rationales tell auditors the
   verdicts are meaningless if the controls fail.
2. **The falsifier path is unreachable from pipeline evidence** (Phase 7 §4.8;
   §2.3 friction 2). `to_evidence_item` never sets `falsifier_observation`, so a
   citation whose checked content *is* the registered falsifying observation still
   enters as ordinary contradicting mass and the verdict fires via the interval
   path. CLM-E-004's registration named the Wandel 2010 conclusion as its falsifying
   observation; its CONTRADICTED verdict rests on the interval (−1.0, −0.6) alone,
   and the registration's mechanism attribution is imprecise. (The verdict was sound;
   the *attribution* is the defect.)
3. **The bundle's citation record is incomplete** (§2.3 friction 5 and 6).
   (a) The **as-cited forms** of citations — what the researcher actually typed,
   including the fabricated DOI itself and a corrupted citation's wrong fields —
   are absent from the bundle; only resolved records and mismatch field *names*
   are carried, so the inputs cannot be re-inspected. (b) **Excluded citations
   vanish** from the evidence files without a marker: recoverable only by
   cross-referencing `verification.json`/`adjudication.json` by hand.

## Design

### Fix 1 — Per-control outcomes in the run projection

- **One execution, structured.** `tekmerion.verdicts` gains
  `run_controls_report(controls, store, store_path) -> list[dict]`: it executes
  each control through exactly the production paths `run_controls` uses today
  (`evaluate_claim` for fixture controls; `swap_control_report` for the swap
  control) and returns one outcome dict per control, in registration order:
  `{kind, failure_mode, expected, observed, passed, executed, fixture, detail}`.
  `run_controls` is reimplemented as the failure-projection of that report —
  **the same failure strings, in the same order** (CLM-011-02). There is no
  second control path (RT-1).
- **Fixture identity.** For a positive/negative control, `fixture` is
  `{"claim_id": <fixture claim id>, "sha256": <SHA-256 of the canonical
  {"claim": …, "groups": …} fixture>}` — a reader holding a fixture can tell
  whether it is the fixture that ran. For the swap control, `fixture` is
  `{"construction": <the tamper construction the production report names>}` —
  the swap control's fixture *is* the study ledger, and the construction is
  its identity. `observed` is the verdict string for fixture controls and
  `"detected"` / `"not_detected"` for the swap control (whose registered
  `expected` is null — a swap has no expected verdict; detection is its
  operative expectation, and `observed`/`passed` record exactly that).
- **The run carries them.** `RunResult` gains `control_outcomes` (additive,
  default empty); `evaluate_run` populates it on both the valid and invalid
  return paths, so every live consumer (workspace, MCP) sees the same record
  the bundle will carry.
- **The bundle records them.** `run_outcome_projection` (the NC-6 projection
  in `verdicts.json`) gains a `controls` key in **all three** branches:
  - *invalid / not-run*: the outcomes of the export-time replay's own
    `evaluate_run` — the replay is the run being reported, and its outcomes
    are recorded as executed.
  - *valid (issued)*: the controls are **re-executed at export time** through
    the production path on the controls presented to the exporter and the
    study's ledger — the same deterministic computation the issuing run
    performed (fixture evaluation is a pure function of the fixture; the
    swap control runs on the ledger being exported). The projection's
    `basis` states this provenance verbatim. `controls_replayed` now lists
    the kinds actually executed instead of `[]`.
  - *Fixture not presented at export* (a caller presents definition-only
    controls for an issued study): the outcome records `executed: false`,
    `passed: null`, and a `detail` stating the pass is attested by the run's
    `verdict.issued` events (an invalid run issues none, WS3 §1). The
    projection never states an outcome the machinery did not produce.
- **The verifier covers them** — to exactly the extent decidable from the
  bundle alone, in the existing `run_outcome` cross-check section:
  (i) the outcomes' `(kind, failure_mode, expected)` multiset equals the
  registration's committed control set (`registration.json`, hash-verified
  against the ledger — payload vs committed record); (ii) a stated `valid`
  outcome contradicts any outcome with `passed: false`; a stated `invalid`
  outcome whose reasons cite a control failure contradicts a record in which
  every control passed; (iii) each executed swap outcome's `passed` must
  equal the verifier's **own swap replay** on the bundle's ledger copy (the
  K2 pattern: recomputation, not trust). Fixture controls' observed verdicts
  are not recomputable bundle-alone (fixtures are registration-external
  evaluation inputs, identified by hash); they are attested by the
  export-time production-path execution and bound by the manifest hashes —
  the same trust basis the NC-6 projection already documents for
  fixture-dependent outcomes. When `controls` is absent (pre-Spec-011
  bundles), the checks note the absence and do not fail.

### Fix 2 — `falsifier_observation` wired from pipeline evidence

- **The mapping.** `to_evidence_item` gains an optional `claim` argument.
  On the contradicting branch only, it sets `falsifier_observation=True`
  if and only if **all** of the following hold:
  1. the citation **resolved** and stage 2 judged **agreement = agree** —
     the resolved record *is* the cited work (a quarantined citation never
     carries the observation);
  2. the stage-3 content check judged the retrieved content **contradicts**
     the proposition (the observation was actually checked, not inferred);
  3. the claim's registered **falsifier text names the resolved record**,
     by either conventional citation form: the citation's normalized DOI
     appears in the falsifier text, **or** the resolved record's
     **first-author surname and year** both appear in it.
  The naming test reads identity **only from the resolved record** (and the
  citation's DOI) — never from the as-cited fields, which are precisely what
  stage 2 exists to distrust (Phase 7's CIT-E-202 carried wrong as-cited
  author/year fields about a real paper).
- **The boundary (when in doubt, the field stays unset).** A generic
  falsifier ("a powered test finds no effect") names no record and can
  never produce a pipeline falsifier observation. A falsifier naming a
  record by title alone does not fire the rule. Metadata-only evidence
  never fires it (no content was checked). If the resolved record is not
  available to the conversion, the flag stays unset. The registration
  discipline this implies is stated for study authors: a study whose
  falsifier is a designated observation names that record in the falsifier
  text by DOI or by first-author surname + year — the forms registrations
  already use (CLM-E-004's falsifier names "the Wandel 2010 network
  meta-analysis's conclusion", which this rule fires on).
- **No verdict mathematics changes.** `evaluate_claim` already consumes
  the flag (falsifier branch: any group with the observation and
  contradiction mass ≥ margin → CONTRADICTED, "falsifier test fired").
  The wiring only populates a field the math already reads; intervals,
  points, floors, and the RT-5 cap are untouched. The workspace's shared
  evidence derivation (`ui/state.py::derive_evidence` — the path the UI
  and MCP both consume) passes the claim through, so the flag is derived
  from the ledger's own citation outcomes everywhere the register is
  rebuilt.

### Fix 3 — Bundle citation completeness

- **As-cited forms.** `export_bundle` gains an optional `citations`
  argument (citation_id → `Citation` or its dict form). When presented,
  `verification.json` gains an `as_cited` object carrying each citation's
  full as-cited form (the `Citation.as_dict()` shape: proposition, DOI,
  title, authors, year, venue, dataset/derivation keys) alongside the
  resolved outcomes already there. The workspace exporter passes the
  study's citation-input sidecar, so UI/MCP exports carry them by
  default. When not presented, the key is absent — noted by the verifier,
  not failed (the same absence convention as `run_outcome` in pre-NC-6
  bundles).
- **Verifier cross-check.** Each `as_cited` entry must key-match its
  citation_id, and its `claim_id` must equal the claim_id of that
  citation's `citation.checked` ledger outcome — payload vs ledger, the
  K2 pattern. An as-cited form for a citation with no ledger outcome is a
  contradiction and fails.
- **Excluded-citation markers.** `adjudication.json` gains
  `excluded_citations`: one marker per citation excluded by a decided
  quarantine item — `{citation_id, claim_id, queue_id, decision:
  "exclude", rationale}` — derived from the same queue-state replay that
  produces the file's pending/decided lists. Grouping decisions and
  `variant` rulings are not exclusions and produce no marker. The marker
  re-admits nothing: excluded citations remain absent from
  `evidence/items.json` and `evidence/groups.json`.
- **Verifier cross-check.** The marker set must equal the set the
  verifier re-derives from its own replay of the bundle's ledger (queue
  state is already replayed for the adjudication cross-check). Absence
  of the key in a pre-Spec-011 bundle is noted, not failed.

### The one in-scope §2.3 item

The Phase 7 auditor found CIT-E-302's outcome stated as `metadata_only`
in one file and stance `contextual` in another "with no stated mapping".
The mapping exists (it is `to_evidence_item`'s conversion table) but the
bundle never states it. This spec states it: the bundle's HUMAN-README
gains the conversion table (content outcome → evidence stance/mass,
including the quarantined and metadata-only rows). One stated mapping,
in the artifact an auditor actually reads (CLM-011-09).

## Requirements

- **CLM-011-01** (requirement): Every bundle exported after this change records, in `verdicts.json`'s `run_outcome`, one outcome entry per registered control — kind, failure mode, expected, observed, pass/fail (or an explicit non-executed attestation with `passed: null`), and fixture identity — for valid, invalid, and not-run outcomes alike; the same outcomes are carried on the run's own `RunResult` for live consumers.
- **CLM-011-02** (requirement): `run_controls`' failure contract is preserved exactly — same failure strings, same order, same conditions — with the structured report and the legacy function executing one and the same control path (RT-1).
- **CLM-011-03** (requirement): The standalone verifier fails a bundle whose recorded control outcomes contradict the bundle's own committed registration, its stated run outcome, or the verifier's own swap-control replay on the bundle's ledger copy; bundles without recorded outcomes verify as before.
- **CLM-011-04** (requirement): Pipeline-converted evidence carries `falsifier_observation=True` exactly when the registered falsifier names the resolved record (by DOI, or by first-author surname + year) and that record resolved, agreed, and content-contradicts — so a claim whose falsifier is observed verdicts CONTRADICTED via the falsifier path, with the falsifier reason stated.
- **CLM-011-05** (requirement): In every other case the flag stays unset — generic falsifiers, title-only naming, unresolved or disagreeing citations, metadata-only evidence, and conversions without the resolved record — and no verdict mathematics (intervals, points, floors, caps, thresholds) changes.
- **CLM-011-06** (requirement): When citation inputs are presented at export, the bundle's `verification.json` carries every citation's as-cited form, and the standalone verifier fails a bundle whose as-cited form disagrees with the ledger (unknown citation, or a claim linkage different from its `citation.checked` outcome).
- **CLM-011-07** (requirement): The bundle's `adjudication.json` carries an exclusion marker (citation, claim, queue item, decision, rationale) for exactly the citations a decided quarantine item excluded — no more, no fewer — the verifier re-derives the set from the ledger replay and fails on any divergence, and excluded citations remain absent from the evidence files.
- **CLM-011-08** (requirement): Backward compatibility: all eight previously frozen bundles (Phase 5 demo v1–v4, Spec 003 math study v1–v2, Phase 7 evaluation v1–v2) verify standalone under the new code with their issued verdicts byte-identical, and a bundle lacking any of the new fields verifies as before, with the absences noted in the verifier's checks rather than failed.
- **CLM-011-09** (requirement): The exported bundle's HUMAN-README states the pipeline's content-outcome → evidence conversion mapping (supports / contradicts / contextual / metadata_only / quarantined → stance, mass, and flags), so no bundle file's vocabulary is left unmapped against another's.

## Non-goals (named, with reasons)

- **§2.3: `claims.json` showing every claim `status: "proposed"`.** Out —
  and not a defect: `claims.json` *is* the frozen registration document's
  register (the verifier binds `claims.json` ≡ `registration.json`
  payload-for-payload), and at the freeze instant the claims' statuses
  were `proposed`. Rewriting them to post-freeze lifecycle statuses would
  falsify the frozen record to fix a display impression. The remedy is
  explanatory text (auditors read `registration.json` as the as-frozen
  register), not a projection change.
- **§2.3: the RT-4 second-review aggregate naming its target.** Out —
  not a one-line fix under this spec's compatibility constraint:
  `second_review_report`'s shape is compared for equality by the
  standalone verifier against every pre-existing bundle's stored report;
  adding a field would make all eight frozen bundles fail verification
  unless the verifier grew a shape-tolerance carve-out in its
  honesty-critical equality check. Named for a future spec that takes
  that trade deliberately.
- **§4.3 (grouping-suspect rule not filtering unresolved citations)** and
  **§4.2 (stance checker sentence-negation weighting)**: named by the
  evaluation itself as future-spec candidates; they change machinery
  behavior, not its recording. Out.
- **§4.9 (bundle-v2's own hash anchored nowhere)**: an anchoring-protocol
  question (DN-005 pattern), not an evaluation-machinery recording gap.
  Out.
- No changes to `registration_document` (fixture payloads do **not** enter
  the frozen registration — fixture *identity* is recorded, the fixture
  itself stays a registration-external evaluation input, as today).
- No new ledger event types; no changes to frozen artifacts; no UI.
