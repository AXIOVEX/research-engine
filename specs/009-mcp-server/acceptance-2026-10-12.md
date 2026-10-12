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
