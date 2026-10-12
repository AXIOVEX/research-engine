# Spec 009 clean-room acceptance — 2026-10-12

Executed per spec §7. Environment: fresh venv at `~/workspace/tekmerion-mcp-acceptance/venv` (outside the repo), installed **only** from the built wheel set + the MCP SDK from the public index; no repository on `sys.path`, no editable installs. Import locality asserted before the run (`tekmerion.__file__` inside the acceptance venv). Driver: `~/workspace/tekmerion-mcp-acceptance/drive_acceptance.py` — a scripted MCP client over stdio (SDK `ClientSession`); server processes launched from the venv's `tekmerion-mcp` entry point; two instances (researcher `acceptance-researcher`, adjudicator `acceptance-adjudicator`) against one clean workspace. Full machine transcript: `~/workspace/tekmerion-mcp-acceptance/transcript.jsonl`.

Wheel set (`~/workspace/tekmerion-mcp/dist/`, final builds):
- `axiomere_py-0.1.0-cp312-cp312-manylinux_2_34_x86_64.whl` — sha256 `ff5c84b3a2e73715d7e61480a6d74509e9bde2b4f4726256b8d4ae881afac4fe` (maturin release build of axiomere origin/main @ 40d6933, incl. the float-roundtrip fix)
- `axiomere-0.1.0-py3-none-any.whl` — sha256 `f524479bfd1cde289b0da2eb359a79319bd6e0392f4be6b6128364c291b2d06c`
- `tekmerion-0.1.0-py3-none-any.whl` — sha256 `f2a530e539eb27fd74f41ce8030ba3951a1e424b3434ba84c221d2a83b726eee`

## Final run — all 21 steps passed

| Step | Call | Result |
|---|---|---|
| 0 | `list_tools` | 29 tools registered |
| 1 | researcher `list_studies` | ok; actor/role echoed (`acceptance-researcher`, researcher) |
| 2 | researcher `create_study` | ok |
| 3 | `get_study_status` | chain ok, 0 events |
| 4 | researcher `register_claim` CLM-A-000, falsifier blank | **refused on the wire**: `Error executing tool register_claim: CLM-A-000: no falsifier — not registered (Article II)` |
| 5 | `get_study_status` | event count unchanged (nothing appended by the refusal) |
| 6 | researcher `register_claim` CLM-A-001 (Einstein 1905) | ok |
| 7 | adjudicator `register_claim` CLM-A-002 (GRIM consistency) | ok |
| 8 | researcher `freeze_study` | **refused**: `role 'researcher' may not call freeze_study … (WS6 §1)` verbatim |
| 9 | researcher `attach_citation` CIT-1, DOI 10.1002/andp.19053221004 | `resolved`, `agree`, content `metadata_only` (live Crossref; no abstract for the 1905 paper) |
| 10 | researcher `attach_citation` CIT-2, fabricated DOI | `not_found`, quarantined (ADQ-001) |
| 11 | adjudicator `decide_adjudication` ADQ-001 `exclude` | appended, actor `acceptance-adjudicator` |
| 12 | adjudicator `run_grim` (mean "5.19", n=28) | `run_by_us`, `grim_impossibility` finding, scope CLM-008-02 |
| 13 | adjudicator `freeze_study` (fixtures incl. positive rationale) | registration hash `b52a28a9…181b` — identical across both full runs (deterministic) |
| 14 | adjudicator `run_evaluation` | **valid run**; CLM-A-001 **INCONCLUSIVE** ("entire supporting basis is metadata-only — capped at inconclusive (RT-5)"), CLM-A-002 **CONTRADICTED** (GRIM falsifier observation) |
| 15 | researcher `get_verdicts` | both verdicts read back from the ledger |
| 16 | researcher `export_bundle` | ok; export-time standalone verification passes |
| 17 | adjudicator `verify_bundle` | standalone: ok, no failures (bundle hash `e5a868a2…dc2e`) |
| 18 | adjudicator `deposit_bundle(approved_by="")` | **refused on the wire**: `deposit refused: deposits are adjudicator-approved actions (WS5 §3) — name the approver; without one the bundle stays internal` |
| 19 | `get_study_status` | anchors `[]` (refusal recorded nothing); chain ok; 12 events |
| 20 | researcher `list_adapter_runs` | the GRIM `adapter.run` record replayed from the ledger |
| 21 | summary | verdicts {CLM-A-001: inconclusive, CLM-A-002: contradicted} — the machinery's, unscripted |

The verdicts deserve one sentence: they were not chosen by the script. CLM-A-001's only evidence is a metadata-only Crossref record, and the engine caps such a basis at INCONCLUSIVE by design (RT-5) — a live demonstration of the cap on real data.

## Flaws found by the acceptance process (all fixed, run repeated from clean)

1. **The wheel shipped an unimportable package.** `tekmerion.ui.server` reads `ui/style.css` at import time; the wheel contained only `.py` files, so `import tekmerion.ui.server` (and therefore the MCP server, which imports the permission matrix) raised `FileNotFoundError` from any wheel install — invisible in every repo/editable context, i.e. in all prior testing. This was a latent defect of the installable product, not only of Spec 009. Fix: `[tool.setuptools.package-data] "tekmerion.ui" = ["style.css"]`; wheel rebuilt and verified to contain the stylesheet. (First acceptance attempt died at server startup with this traceback.)
2. **Refusal text did not cross the wire.** SDK 2.x masks non-`ToolError` exceptions by design: clients saw only "Error executing tool <name>". Fix: the shell converts every handler exception to a `ToolError` carrying `str(exc)` verbatim (spec §5 amended to record the mechanism); unit test `test_sdk_shell_carries_refusals_verbatim` pins it, and steps 4/8/18 above read the verbatim texts off the wire.
3. **Driver defects (acceptance tooling, not the product):** `CallToolResult.isError` → `is_error` (SDK 2.x naming); a wrong expected adapter id (`statcheck-grim` is the shipped id). Fixed in the driver; the final run above is from a clean workspace with the fixed wheels.

Two build-side incidents, recorded for honesty: an early wheel-build status was reported complete by a background-process notification while the chain was still running (its `ls` output was a stale read); ground truth was re-established by direct inspection before any claim rested on it. A wait-loop then self-matched its own `pgrep` pattern; harmless, killed.

## Remains not covered by this acceptance

- No Zenodo deposit was attempted (boundary: refusal path only). The approved-deposit path is covered by unit tests against the local transport.
- The skill's sufficiency (CLM-009-09) is **not** assessed by this run — its falsifier is a separate skill-only study run by the coordinator from the main environment, still to happen.
- Live PLATON / live statcheck remain `not_runnable_here` in this environment (Specs 006/008 T4 items, unchanged).

---

## Addendum — 2026-10-12 (coordinator's skill-only exercise; follow-up fixes)

The coordinator ran CLM-009-09's falsifier exercise personally,
skill-only (installed skill + `list_tools` schemas, the clean-room
acceptance venv, own driver; transcript at
`~/workspace/tekmerion-skill-exercise/transcript.jsonl`). The run
was **not flawless**. Three findings; CLM-009-09 is **not** moved
by this addendum — the coordinator re-runs the exercise on the
fixed skill + server and moves the claim (or not) on that
evidence.

### F1 — freeze/run/export inconsistency (engine defect; fixed)

Wire sequence from the exercise: `freeze_study` refused (RT-6,
positive control lacks a representative rationale) →
`run_evaluation` returned `run_verdict: "valid"` and **issued
verdicts** (`verdict.issued` at seq 9–10; `get_verdicts` state
"valid", issued true; no `study.frozen` event in the 10-event
chain) → `export_bundle` refused: "study is not frozen — bundles
export frozen registrations (WS4 §4)".

Diagnosis (from source):

- `run_evaluation` never freezes and never checked for a freeze
  event. `evaluate_workspace_run` (ui/state.py) derived the run
  mode from the ledger: `mode = fe.payload.mode if fe else
  "exploratory"`. A refused freeze appends nothing (freeze.py runs
  the check before any append), so the absence of the event
  silently re-moded the run to exploratory — and `evaluate_run`
  (verdicts.py) requires a frozen registration **only** in
  confirmation mode (the WS3 §4 wall, CLM-002-09), by design:
  exploratory is a legitimate engine-level mode (WS3 §4).
- `export_bundle` (export.py) scans the ledger for `study.frozen`
  and refuses without one — correct against WS4 §4 and
  CLM-002-24 (the bundle binds to the frozen commitment).
- The wrong side is the run path's mode derivation. Evidence for
  the codebase's intended design: neither workspace surface (UI
  `act_run`, MCP `run_evaluation`) offers a run-mode choice and
  both freeze in confirmation by default; WS3 §4 requires an
  exploratory register to be *labeled* exploratory at every level,
  and nothing shipped labels it (verdict payloads carry no mode,
  projections report bare "valid", export has no exploratory
  path); `run_projection` already treats an unfrozen study as
  run-state "none"; every production flow (Phase 5 demo, Phase 7
  driver, all UI/MCP flow tests) froze before running.

Fix (shared service layer, so UI and MCP cannot drift):
`evaluate_workspace_run` now returns an INVALID `RunResult` —
"confirmation run without a frozen registration (WS3 §4 wall):
no study.frozen event in the ledger — freeze the study before
running; verdicts are issued only against a frozen registration"
— when the ledger has no `study.frozen` event, and reads mode +
linked-exploratory from the freeze event otherwise (fallback mode
"confirmation", matching `freeze()`'s own default). A study
frozen in exploratory mode still runs exploratory — against its
recorded freeze, and exportable. Engine-level
`evaluate_run(mode="exploratory")` is unchanged (it appends
nothing; controls and Phase 3 tests use it directly).

Regression tests (all three fail on the pre-fix code, pass after):
`tests/test_mcp_server.py::test_run_after_failed_freeze_issues_nothing`
(wire sequence: refused default-controls freeze → run INVALID,
zero `verdict.issued` events, `get_verdicts` issued=false →
export refuses "not frozen" → real freeze → valid run → export
verifies) and `tests/test_workspace_run_wall.py` (service level:
unfrozen `evaluate_workspace_run`/`action_run` INVALID and
appending nothing; failed-freeze → run INVALID → freeze → valid
run → `action_export` verifies).

Because tool behavior changed (unfrozen runs now return INVALID
instead of issuing exploratory verdicts), the clean-room
acceptance driver was re-run from clean against a rebuilt wheel —
see F4 and the re-run note at the end of this addendum.

### F4 — the ToolError conversion was never committed (record defect; restored)

Rebuilding the wheel from the committed branch for the F1 re-run
exposed a worse discrepancy: the rebuilt server **masked refusal
text on the wire** (clients saw only "Error executing tool
<name>") at acceptance steps 4/8/18. Diffing the branch source
against the originally accepted installed package showed exactly
one delta in the whole package: the `reg` wrapper in
`build_server` — the ToolError conversion described in spec §5,
in flaw #2 above, and in the build assessment — existed only in
the installed package and the (untracked) `dist/` wheel. Commit
`0b3d957`, whose message names the conversion, in fact touched
only `pyproject.toml` and `spec.md`; the conversion and its unit
test `test_sdk_shell_carries_refusals_verbatim` were never
committed, so the branch as committed did **not** satisfy
CLM-009-02 on the wire despite the records saying it did. (The
coordinator's exercise transcript shows the same masking in its
step-2 probe shape.) Restored: the wrapper is now in
`src/tekmerion/mcp/server.py` byte-identical to the accepted
installed copy, and the missing test now exists in
`tests/test_mcp_server.py` — it passes with the conversion and
fails without it (verified by stash-revert). The acceptance
verdicts of the original run stand (that run drove the converted
server, which is the behavior now committed); what was wrong was
the branch, not the run.

### F2 — skill text wrong against shipped behavior (fixed)

The skill is corrected in both copies (`skill/SKILL.md` in-repo
and `~/workspace/skills/tekmerion/SKILL.md`, kept byte-identical):

- **Playbook A step 6 (the F2 finding).** Before: "Controls: the
  default set (positive/negative/swap, no fixtures) is fine for a
  first study; a positive control with an evaluation fixture
  needs a `representative_rationale`." In fact `_default_control_fields`
  gives the positive control `representative_rationale: ""`, so
  freezing with `controls` omitted is refused by RT-6 — the
  exercise hit exactly this. After: controls "must be passed
  explicitly", with the three kinds, the field dict shape
  (`kind`, `failure_mode`, `expected`, fixture shape), the
  positive control's non-empty rationale requirement, and the
  rule that fixture-less positive/negative controls do not
  execute at run time (only swap does). Step 6 also now states
  the `linked_exploratory` truth: omitted over MCP, the tool
  records the empty disclosure itself (the Session converts
  `None` → `[]` before the engine's RT-3 check can fire) — the
  earlier text claimed absence is a freeze failure, which is the
  engine-level behavior the MCP surface does not expose.
- **Step 3 outcome vocabulary.** Before: resolution "(resolved /
  not_found / ambiguous)", content "(supports / contradicts /
  no_content / metadata_only...)". Shipped (verification.py):
  resolution ∈ {`resolved`, `not_found`, `error`}; agreement ∈
  {`agree`, `disagree`}; content ∈ {`supports`, `contradicts`,
  `contextual`, `metadata_only`}. `ambiguous` and `no_content`
  do not exist. Corrected.
- **Step 4 decision vocabulary.** Before: decisions listed as
  `exclude`, `variant`, `agree`, `disagree_quarantine`. Shipped
  `DECISIONS` (verification.py) is `exclude`, `variant`,
  `same_origin`, `separate_origin` — `agree`/`disagree_quarantine`
  would be refused as unknown decisions (agreement is the
  second-review axis). Corrected, with quarantine vs grouping
  items distinguished, and `study_id` restored to the
  `decide_adjudication` / `record_second_review` /
  `list_adjudication_queue` call shapes (all tools take it).
- **Step 5.** Before: "Clear the queue before freezing." Freeze
  does not check the queue; an undecided quarantined item stays
  unverified and invalidates the **run**. Corrected to "decide
  every pending item before you run."
- **Step 7 + troubleshooting (consequence of F1).** Step 7 now
  states the freeze-first invariant and the wall reason text;
  new troubleshooting rows for the RT-6 freeze failure and the
  WS3 §4 wall run refusal; rule 3's reason list gains "no frozen
  registration".

All other Playbook A steps were checked against the shipped
signatures, the WS6 permission tuples imported from the UI matrix,
and the engine error texts (role denials, `TEKMERION_ACTOR is not
set`, the deposit gate) and matched.

### F3 — falsifier-omission error shape (skill text fixed)

Before, rule 2 + the troubleshooting table quoted only the
engine shape. In fact: omitting the `falsifier` argument entirely
is refused by the SDK's argument validation (Pydantic
`falsifier … Field required`) before the engine is reached —
that is the shape in the exercise transcript; passing it **empty**
reaches the engine, whose refusal is verbatim
(`{claim_id}: no falsifier — not registered (Article II)`,
claims.py). Both append nothing. Rule 2 and the troubleshooting
table now describe both shapes and name the invariant (no
falsifier, no append) as the point.

### Re-run note (2026-10-12, after F1 + F4)

The clean-room acceptance driver was re-run from clean
(`~/workspace/tekmerion-mcp-acceptance-rerun/`: fresh venv, fresh
workspace, the two unchanged Axiomere wheels + a tekmerion wheel
rebuilt from the branch, sha256 `80d773c1bdc2bbf5…`, content-
asserted before the run to carry both the F1 wall and the
restored ToolError conversion). **All 21 steps pass**, including
the three verbatim wire refusals (steps 4/8/18), the deterministic
freeze (registration hash `b52a28a9…181b`, identical to the
original run), the valid run with the machinery's own verdicts
(CLM-A-001 INCONCLUSIVE by the RT-5 metadata-only cap, CLM-A-002
CONTRADICTED), export, and standalone bundle verification. A
first re-run attempt against a wheel built before F4's restore
failed steps 4/8/18 on masked refusal text — that failure is
what exposed F4; it is recorded here rather than silently
superseded.

### Not a defect (recorded in the exercise, no action)

The exercise ran during a VM egress stall: the real DOI's
resolution returned `not_found` / "resolution failed" and the
citation was quarantined and excluded — the machinery recording
a failed resolution honestly. Chain verified ok throughout; both
claims' INCONCLUSIVE ("no evidence groups") verdicts were
consistent with both citations excluded.
