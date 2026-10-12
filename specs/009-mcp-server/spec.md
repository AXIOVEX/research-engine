# Spec 009 — Tekmerion MCP Server, Agent Skill, and Easy Install

- **Date:** 2026-10-12 · **Status:** Claims first (bundle v0.1.0, assessed at after_specify); build follows this spec. Origin: owner directive 2026-10-12 — external outreach (the SAIR draft) is held until (a) the platform is fully tested and (b) others can install and try it easily: "we need a fully designed MCP server and agent skills.md for this, and that you can test from here as flawless."
- **Governing text:** Constitution Articles I (defensibility), II (no claim without a falsifier), IV (append-only), X (honest status), XII (spec before code). DN-005 (append-only, signed, anchored), DN-007 (record layer = Axiomere, real bindings, **no fallback**).

## 1. What this is

A third surface over the **same production services** the shipped UI drives — `tekmerion.store`, `claims`, `verification`, `freeze`, `verdicts`, `export`, `deposit`, `adapters/*`, `mathclaims`, orchestrated through the same workspace layer (`tekmerion.ui.state`) the UI uses. The MCP server adds **no record semantics of its own**: every ledger event a tool causes is an event a production service emits, with the same payloads, through the same code paths (CLM-009-01).

Deliverables:

1. `src/tekmerion/mcp/` — the MCP server package (entry point `tekmerion-mcp`).
2. Packaging: the core package stays dependency-free; the server ships as the optional extra `tekmerion[mcp]`. A three-wheel install set (Axiomere bindings wheel, `axiomere` wheel, `tekmerion` wheel) built locally; **PyPI publication is out of scope** (owner decision, §8).
3. `docs/install.md` — the one documented install path + copy-paste MCP client configuration + quickstart.
4. `skill/SKILL.md` — the agent skill, in-repo; installed to the workspace skills directory as part of acceptance.
5. A clean-room acceptance run (§7) whose transcript is this spec's exit evidence.

## 2. Transport and dependency posture

- **Transport: stdio**, the MCP standard for local install. Streamable HTTP is *designed for* (tool handlers take no transport-specific context; §5) but **not built** in this spec.
- **Dependency: the official MCP Python SDK** (`mcp`, verified installable in this environment at 2.3.0; its server class is `mcp.server.mcpserver.MCPServer`, run via `run(transport="stdio")`). Chosen over a hand-rolled JSON-RPC stdlib implementation because the SDK is the reference implementation of the protocol the clients speak — a hand-rolled subset is exactly the kind of almost-compatible surface this project refuses to ship. Pinned as `mcp>=2,<3` in the `mcp` extra so a future major's API break cannot arrive silently. The **core package gains no dependency** (CLM-009-05): `import tekmerion` works with no SDK installed; only the `tekmerion-mcp` entry point requires the extra and says so in its error.

## 3. Actor identity and authorization

- One server instance = **one actor identity + one WS6 role**, fixed at launch by environment: `TEKMERION_ACTOR` (required — the entry point refuses to start without it; an unnamed actor is an anonymous append and this system has none), `TEKMERION_ROLE` ∈ {researcher, reviewer, adjudicator, integrity} (default `researcher`), `TEKMERION_WORKSPACE` (workspace root, default `./tekmerion-workspace`).
- Every append carries the configured actor (Article XIII). **Multi-actor work = multiple configured instances** against the same workspace — stated plainly, as with the UI's SSO-hook identity (WS6 §1: event actors are recorded from the identity, never typed per action). No tool accepts an `actor` parameter.
- Role enforcement uses **the shipped UI's WS6 §1 permission matrix** (`tekmerion.ui.server.PERMISSIONS`), imported — not re-typed — so the two surfaces cannot drift; a test asserts the tool layer's matrix *is* that object. Denials are the surface's own refusal (action, role, required roles named), raised before any engine call.
- Deposit transports are configuration, mirroring the UI workspace: `TEKMERION_DEPOSIT_ROOT` (local transport) or `TEKMERION_ZENODO_TOKEN` (Zenodo). Neither set → the deposit tool refuses with the workspace's own message. **Approval is never configuration**: `approved_by` is a per-call tool parameter, empty by default, and the engine's mechanical gate (WS5 §3) decides.

## 4. Tool surface

Success results are JSON objects (`{"ok": true, ...}`). Engine refusals surface as MCP error results carrying the engine exception's text **verbatim** (CLM-009-02). "Events" names the ledger appends the call causes.

### Studies
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `list_studies` | `ui.state.Workspace.list_study_ids` + meta | any | — |
| `create_study(study_id, title)` | `Workspace.create_study` → `StudyStore.create` | researcher, adjudicator | ledger creation |
| `get_study_status(study_id)` | projections: `rebuild_register`, `frozen_event`, `run_projection`, `anchor_receipts`, `store.verify()` | any | — |

### Claims and evidence
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `register_claim(study_id, claim_id, statement, falsifier, kind?, dependencies?, margin?, sufficiency_floor?, supersedes?)` | `claims.Claim` → `ui.state.action_register_claim` (engine `ClaimRegister.register` validates **before** any append) | researcher, adjudicator | `record.snapshot` |
| `list_claims(study_id)` / `get_claim(study_id, claim_id)` | `rebuild_register` + `group_masses` + `verdicts_by_claim` | any | — |
| `withdraw_claim(study_id, claim_id, reason)` | `StudyStore.withdraw` (dead snapshot, reason mandatory, score 0.0) | researcher, adjudicator | dead snapshot |
| `attach_citation(study_id, citation_id, claim_id, proposition, doi?, title?, authors?, year?, venue?)` | `verification.Citation` → `ui.state.action_attach_citation` (stages 1–3 via connectors) | researcher, adjudicator | `citation.checked`, `connector.query`, any `adjudication.enqueued` |

There is **no free-floating evidence attach and no detach tool**, because the engine has none: evidence enters a claim's basis only as checked citations, adapter runs, or math proof items (Article V), and leaves it only by an adjudicator's `exclude` decision. The tool surface mirrors the engine rather than inventing a softer path (§6, CLM-009-10).

### Verification and adjudication
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `list_adjudication_queue(study_id)` | `ui.state.queue_view` (pending/decided, RT-4 sample + report) | any | — |
| `decide_adjudication(study_id, queue_id, decision, rationale?)` | `verification.decide` → `StudyStore.decide_adjudication` (actor = configured identity) | adjudicator | `adjudication.decided` |
| `record_second_review(study_id, queue_id, agrees)` | `StudyStore.log_second_review` | reviewer, adjudicator | `adjudication.second_review` |

### Freeze, run, verdicts
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `freeze_study(study_id, mode?, linked_exploratory?, controls?, deployment_shape?)` | `ui.state.action_freeze` → `freeze.freeze` (fail-closed check; `FreezeError` verbatim). `controls` omitted → the UI's default control fields | adjudicator | `study.frozen`, checkpoint |
| `run_evaluation(study_id)` | `ui.state.action_run` → `verdicts.evaluate_run` via the workspace driver | adjudicator | `verdict.issued` per claim (**valid runs only**; an INVALID run appends nothing, WS3 §1) |
| `get_verdicts(study_id)` | `verdicts_by_claim` + `run_projection` (an INVALID replay is returned as INVALID with the engine's reasons) | any | — |

### Export and anchoring
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `export_bundle(study_id)` | `ui.state.action_export` → `export.export_bundle` + `record_export` + standalone re-verify | researcher, reviewer, adjudicator | `export.generated` |
| `verify_bundle(bundle_dir)` | `export.verify_bundle` — consumes **only the bundle** | any | — |
| `verify_anchor(bundle_dir, public_record)` | `export.verify_anchor` | any | — |
| `deposit_bundle(study_id, approved_by="")` | `ui.state.action_deposit` → `deposit.deposit_bundle` + `record_anchor`. The gate is the engine's: no named approver → `DepositError` verbatim, nothing appended | adjudicator | `anchor.recorded` (on success only) |

### Adapters — lane-1 evidence only (DN-010; Spec 004 §2)
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `run_checkcif(study_id, cif_path?, recorded_output_path?, claim_id?, item_id?, origin_group?)` | `adapters.checkcif.run_checkcif` (live PLATON where a binary exists, else recorded output, else `not_runnable_here`) | researcher, adjudicator | `adapter.run` (+ evidence via `emit_adapter_evidence`) |
| `run_codecheck(study_id, certificate_id, claim_id?, item_id?, origin_group?, work_outputs?)` | `adapters.codecheck.ingest_codecheck_certificate` (fetches the named certificate from the public register; retrieval failure is a ledgered state, never an invented certificate) | researcher, adjudicator | `adapter.run` (+ evidence) |
| `run_grim(study_id, cases, claim_id?, item_id?, origin_group?)` | `adapters.statconsistency.run_grim_family` (`cases`: [{label, mean, sd?, n, items?}]) | researcher, adjudicator | `adapter.run` (+ evidence) |
| `run_statcheck(study_id, manuscript_path?, recorded_output_path?, claim_id?, ...)` | `adapters.statconsistency.run_statcheck` (live R seam where an R runtime exists, else recorded/`not_runnable_here`) | researcher, adjudicator | `adapter.run` (+ evidence) |
| `list_adapter_runs(study_id, adapter_id?)` | `adapters.core.adapter_runs` — replay of the ledger records | any | — |

Adapter honesty states (`run_by_us` / `recorded_output` / `not_runnable_here`) pass through **unchanged** (CLM-009-08). Session scope: adapter evidence attaches to the calling session's register (the adapters' own design — `emit_adapter_evidence` mutates a register; Specs 006–008 ship run-record replay, not register-evidence replay). The server keeps a per-study session register, rebuilt from the ledger whenever the ledger's head moves (another instance appended), with the session's adapter items re-applied. The durable cross-session record is the `adapter.run` event, replayable via `list_adapter_runs`. This boundary is stated here and in the skill, not papered over.

### Math claims (Spec 003)
| Tool | Service path | Roles | Events |
|---|---|---|---|
| `register_theorem(study_id, parent_id, headline, claimant, problem, margin?, sufficiency_floor?, statements?)` | `mathclaims.register_theorem` (parent + five sub-claims, each with its registered falsifier) + one snapshot per claim | researcher, adjudicator | `record.snapshot` ×6 |
| `pin_faithfulness(study_id, claim_id, formal_statement, original_statement, original_source)` | `mathclaims.pin_faithfulness` | researcher, adjudicator | `math.faithfulness_pinned` |
| `ingest_lean(study_id, url, theorem_name?, source_compile_claim?)` | `mathclaims.ingest_lean_artifact` — fetch + SHA-256 + sorry/admit counts + compile state (`not_attempted` / `claimed_by_source` / `run_by_us` / `not_runnable_here`), never upgraded | researcher, adjudicator | `math.lean_ingested` |
| `record_digestion(study_id, claim_id, explainer, artifact_ref, claimant_explanation?)` / `record_acceptance(study_id, claim_id, stage, by, evidence_ref)` | `mathclaims.record_digestion` / `record_acceptance` — **lane-2 records**: they document human explanation/acceptance; they issue no verdict | researcher, adjudicator | lane-2 appends |
| `get_theorem_state(study_id, claim_id)` | `mathclaims.lane1_summary` + `lane2_state` + `digestion_state` + `faithfulness_pair` + `ingestions_for` | any | — |

## 5. Error shapes

- **Engine refusal** (RegistrationError, FreezeError, ExportError, DepositError, AdapterEvidenceError, IngestionError, verification/adjudication errors): MCP error result carrying `str(exc)` **verbatim**. Nothing is appended by a refused call (registration validates before append by construction; freeze/deposit fail closed). Wire mechanism, verified against SDK 2.3.0 during the build: the SDK masks non-`ToolError` exceptions by design (a client would see only "Error executing tool <name>"), so the shell converts every handler exception to a `ToolError` carrying `str(exc)` — the SDK's channel for deliberate, client-facing errors — and the client receives `Error executing tool <name>: <verbatim engine text>`.
- **Surface refusal** (role denial, unconfigured deposit transport, unknown study): MCP error result in the surface's own words, naming the action, the configured role, and what is required — the same information the UI's refusal banner shows.
- **Malformed input** (missing required argument, bad enum): MCP error result naming the argument. The server never guesses a falsifier, a margin, or an approver.

## 6. Non-goals

- No delete, update-in-place, or history-rewriting tool — of any kind (Article IV; DN-005). Withdrawal is the dead-snapshot path.
- No PyPI publication, no hosted/remote transport, no multi-actor single instance, no new record semantics, no changes to Specs 001–008 code or the UI.
- No production Zenodo deposit in acceptance (the refusal path is exercised; a successful local-transport deposit is covered by unit tests).

## 7. Acceptance — "flawless from here" (exit gate)

A clean-room run, executed from this environment but **outside the repo**:

1. Fresh venv; install **only** the three built wheels + the `mcp` extra's SDK dependency from the package index (the SDK is a public package; everything Tekmerion/Axiomere comes from the built artifacts). No repo checkout on `sys.path`, no editable installs.
2. Configure two instances (researcher + adjudicator) against one clean workspace, exactly as `docs/install.md` documents.
3. Drive the **full flow through MCP tool calls only** (scripted MCP client over stdio): create study → falsifier-less registration **refused verbatim**, ledger unchanged → register claims (two instances; early events carry both actors) → check citations (one real DOI resolved live via Crossref; one fabricated DOI → `not_found`, quarantined) → adjudicate the quarantine (`exclude`) → GRIM adapter run (fixture with a known impossibility → falsifier-observation evidence) → researcher freeze attempt **denied by role** → freeze (adjudicator) → run → verdicts read back → export → `verify_bundle` from the bundle alone → deposit without `approved_by` **refused by the gate**, no anchor event.
4. Every flaw found is fixed in the server/skill/docs and the run is **repeated from clean**; the final transcript (every tool call + result) is recorded in `acceptance-2026-10-12.md`. A flaw that is an engine behavior (not a server defect) is recorded as engine behavior, not fixed from this spec.

## 8. What remains an owner decision after this spec

- PyPI (or any index) publication of the three wheels, and the versioning/support promise that publication implies.
- Streamable-HTTP transport + hosted MCP (engages Spec 005 identity; not this spec).
- Cross-session adapter-evidence replay into rebuilt registers (belongs to the adapter specs' seam, Spec 004 §2).
