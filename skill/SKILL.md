---
name: "tekmerion"
description: "Run defensible research studies through the Tekmerion MCP server: register claims with falsifiers, verify citations, adjudicate, freeze, evaluate, export audit bundles, deposit, run domain adapters (checkCIF, CODECHECK, GRIM/statcheck) and Lean/math claim flows. Use when a task involves Tekmerion, evidence-question studies, systematic-review records, claim verdicts, or the tekmerion-mcp tools."
metadata: {"includeInPrompt": true}
---

# Tekmerion — operating manual for agents

Tekmerion is a research engine whose product is **defensibility**:
every claim carries its falsifier, registrations freeze before
evaluation, verdicts are issued only by the machinery against a
valid frozen run, and the whole record is append-only and
hash-verified. You operate it through the `tekmerion-mcp` server
(29 tools). The server is a surface over the engine — it has no
semantics of its own, and neither do you when you use it.

## The rules (these are operating instructions, not flavor)

1. **Never report a verdict the machinery didn't issue.** A verdict
   exists only if a `verdict.issued` event exists — read it back
   with `get_verdicts`. "The evidence looks strong" is not a
   verdict. INCONCLUSIVE is a result, not a failure of your work;
   report it as issued.
2. **Write the falsifier first.** `register_claim` without a
   falsifier is refused by the engine, verbatim, and nothing is
   appended. If you cannot state what observation would falsify
   the claim, the claim is not ready — say so instead of weakening
   the falsifier until it fits.
3. **INVALID means stop.** An invalid run issues no claim verdicts.
   Report the run as INVALID with the engine's reasons (control
   failures, broken chain, undecided adjudication items). Never
   salvage, paraphrase, or "interpret" verdicts from an invalid
   run, and never re-run hoping for a different answer without
   changing something real on the record.
4. **Refusals are final.** Engine refusals (RegistrationError,
   FreezeError, DepositError, role denials) come back as MCP errors
   carrying the engine's text. Surface them to the user as-is. Do
   not rephrase a refusal into a success, do not route around it
   (no direct file edits, no second tool that "also" does the
   thing), and do not retry a refused append unchanged.
5. **Two lanes, always separate.** Lane 1 is machine checking
   (citation checks, adapters, Lean compiles, verdicts). Lane 2 is
   human-paced work (explanation, acceptance, digestion). Never
   present lane-1 output as lane-2 progress: a checked claim is not
   "accepted", and adapter evidence is not "understanding". For
   theorem claims, report lane 1 and lane 2 in separate sentences,
   and state what remains not understood.
6. **The record is append-only.** There is no delete or edit tool,
   deliberately. Corrections are new appends: a superseding claim
   (`supersedes`), an adjudication decision, a withdrawal with a
   reason (the claim stays on the record, marked dead, score 0.0).
7. **Honesty states are data.** Adapter and Lean results carry
   their provenance state (`run_by_us`, `recorded_output`,
   `not_runnable_here`, `claimed_by_source`, `not_attempted`).
   Report the state with the result. `not_runnable_here` means the
   check did not happen here — never upgrade it in prose.

## Configuration (before any tool call)

One server instance = **one actor + one role**. Check which
instance you are talking to with `list_studies` (it echoes the
actor and role).

- `TEKMERION_ACTOR` — required; the server will not start without
  it. There is no anonymous mode and no per-call actor override.
- `TEKMERION_ROLE` — `researcher` (create/register/attach/export),
  `reviewer` (reads + second reviews), `adjudicator` (decisions,
  freeze, run, deposit, also register/export), `integrity`
  (read-only).
- Multi-actor studies need **multiple configured instances**
  against the same `TEKMERION_WORKSPACE`. This is the designed
  shape, not a workaround: WS6 role separation is what gives the
  record its meaning, and the swap control needs early ledger
  events from different actors to bite.

## Playbook A — an evidence-question study, end to end

1. `create_study(study_id, title)` — researcher or adjudicator
   instance.
2. Register every claim **before** gathering evidence:
   `register_claim(study_id, claim_id, statement, falsifier,
   margin, sufficiency_floor)`. Set `margin` (e.g. 0.1) and
   `sufficiency_floor` (minimum supporting origin groups, e.g. 1)
   now — freeze refuses claims that lack them. Register the first
   claims from **two different instances** (researcher +
   adjudicator) so the swap control can bite later.
3. `attach_citation(study_id, citation_id, claim_id, proposition,
   doi, title, authors, year, venue)` per citation. Exactly one
   outcome is ledgered per citation. Read the result: `resolution`
   (resolved / not_found / ambiguous), `agreement`, `content`
   (supports / contradicts / no_content / metadata_only...).
   Metadata-only evidence accumulates verdict mass of zero by
   design (WS5 §4) — a claim backed only by metadata can at best
   be inconclusive; that cap is the machinery working.
4. Work the queue: `list_adjudication_queue`, then the
   **adjudicator instance** calls `decide_adjudication(queue_id,
   decision, rationale)` — decisions: `exclude` (fabricated,
   wrong, or ineligible evidence leaves the basis), `variant`
   (ruled a legitimate variant; it stands), `agree`,
   `disagree_quarantine`. Decisions are appends; a decided item
   cannot be re-decided. `record_second_review(queue_id, agrees)`
   from a reviewer/adjudicator instance when the queue view shows
   the item in the RT-4 sample.
5. **Undecided queue items make the run INVALID.** Clear the queue
   before freezing.
6. `freeze_study(study_id, linked_exploratory, controls?)` —
   adjudicator instance. For confirmation mode,
   `linked_exploratory` must be a list (`[]` = "none" — the
   disclosure is mandatory, its absence is a freeze failure).
   Controls: the default set (positive/negative/swap, no fixtures)
   is fine for a first study; a positive control with an evaluation
   fixture needs a `representative_rationale`. A FreezeError lists
   **every** failed check — fix them on the record (register the
   margin, clear the queue), never by editing files.
7. `run_evaluation(study_id)` — adjudicator instance. If the run
   is INVALID, see rule 3. If valid, `verdict.issued` events now
   exist; read them with `get_verdicts` and report exactly those.
8. `export_bundle(study_id)` — researcher/reviewer/adjudicator.
   Then `verify_bundle(bundle_dir)` — the verifier consumes only
   the bundle; a bundle that does not verify standalone is not
   done, whatever the study screen says.
9. Deposit (only when a transport is configured and a human
   adjudicator approves): `deposit_bundle(study_id,
   approved_by="<the approver's name>")` — adjudicator instance.
   With `approved_by` empty the engine refuses and nothing is
   appended; that refusal is the gate working, not an error to
   fix. Afterwards `verify_anchor(bundle_dir, public_record)`
   against the independently fetched deposit record.

## Playbook B — adapter evidence (lane 1 only)

Adapters attach *scoped* evidence to a claim; each carries a
registered scope claim stating what the check cannot establish.
Adapter evidence never skips adjudication-grade judgment and never
moves lane 2.

- `run_grim(study_id, cases, claim_id, item_id, origin_group)` —
  GRIM/GRIMMER consistency of reported statistics. Cases are
  `{label, mean, sd?, n, items?}` with `mean`/`sd` as **strings**
  (precision is data). A `grim_impossibility` finding attaches a
  falsifier observation to a reporting-consistency claim — phrase
  the claim that way ("the reported means are arithmetically
  possible"), not as "the paper is fraudulent".
- `run_statcheck(study_id, manuscript_path | recorded_output_path,
  ...)` — live only where an R runtime exists; otherwise recorded
  output or `not_runnable_here`. Extraction coverage is in every
  record: "no statistics extracted" is not "no errors found".
- `run_checkcif(study_id, cif_path | recorded_output_path, ...)` —
  an A-level alert contradicts; B-level partially contradicts;
  C/G alerts and clean reports are context only. **A clean checkCIF
  is never support** — the scope claim (CLM-006-02) says what the
  check cannot see.
- `run_codecheck(study_id, certificate_id, ...)` — a certificate
  attests scoped re-execution of named outputs, capped by its own
  stated scope; it never certifies correctness.
- `list_adapter_runs(study_id)` replays every run record with
  provenance. Note: adapter evidence attached in one server
  session is held by that session — run the freeze/evaluation for
  an adapter-backed claim in the **same instance session** that
  ran the adapter, or the adapter evidence will not be in the
  register (the `adapter.run` event is always in the ledger; the
  evidence attachment is session-scoped in this version).

## Playbook C — a math / theorem study (Spec 003 shape)

1. `register_theorem(study_id, parent_id, headline, claimant,
   problem)` — parent ids end in `10` (e.g. `CLM-M-110`); creates
   the parent + five sub-claims (faithful, proof, open,
   attribution, significance), each with its own falsifier.
2. `pin_faithfulness(study_id, <faithful sub-claim id>,
   formal_statement, original_statement, original_source)` — pin
   the pair verbatim; paraphrase is how faithfulness dies.
3. `ingest_lean(study_id, url, theorem_name?)` per artifact. The
   compile state comes back as it is. On a machine without the
   claimant's pinned toolchain + Mathlib build, expect
   `not_runnable_here` — that caps the proof sub-claim; say so.
4. Attribution disputes are recordable only with **two evidenced
   parties**; a contested attribution caps the parent verdict.
5. Lane 2: `record_digestion(study_id, claim_id, explainer,
   artifact_ref)` when a named human has actually explained the
   result (claimant self-explanation is labeled as such);
   `record_acceptance(study_id, claim_id, stage, by,
   evidence_ref)` for accepted/digested on human evidence.
6. Report with `get_theorem_state`: lane-1 summary and lane-2
   state separately, plus **remains not understood** — the open
   questions the checking did not settle. Never give an aggregate
   score for a theorem claim.

## Troubleshooting (keyed to the real error shapes)

| You see | What it means | What to do |
|---|---|---|
| `…: no falsifier — not registered (Article II)` | Registration refused before any append. | Write a real falsifier; re-register. Nothing was recorded. |
| `role 'researcher' may not call freeze_study …` | The action belongs to another WS6 role. | Switch to the instance configured with that role. |
| `freeze check failed: …` (FreezeError) | Fail-closed list of every blocker. | Fix each named item on the record; freeze again. |
| `run_verdict: invalid` + reasons naming an undecided adjudication item | Quarantined evidence was never decided. | Decide it (adjudicator), then re-run. |
| `run_verdict: invalid` + "swap control failed: provenance swap NOT detected" | The study's first ledger lines share one actor (single-actor study), so the swap was a no-op — the Phase 5 demo defect. | This run is INVALID; report it. For the next study, register early claims from two instances. |
| `deposit refused: deposits are adjudicator-approved actions …` | `approved_by` was empty at the gate. | Get a named adjudicator approval; pass it. Never invent a name. |
| `no deposit transport is configured …` | Neither `TEKMERION_DEPOSIT_ROOT` nor `ZENODO_ACCESS_TOKEN` is set for this instance. | Configure a transport, or leave deposit to an instance that has one. |
| `TEKMERION_ACTOR is not set …` (server exits at startup) | Identity is not optional. | Configure actor + role and relaunch. |
| adapter run `outcome: not_runnable_here` | The checker genuinely cannot run here (no PLATON binary, no R runtime). | Supply a recorded output with provenance, or report the state as-is. |
| verdict INCONCLUSIVE on well-cited claims | Often metadata-only evidence (mass 0 by design) or too few independent origin groups. | Report as issued; if content checking matters, cite sources whose content the connectors may actually read under their licence basis. |

## What you must not do

- Do not open the workspace's `.axmr` ledgers or sidecar files
  directly to "fix" anything — the ledger is the record; edits
  break the hash chain and every downstream verification.
- Do not call the Python services yourself when the MCP tools are
  the assigned surface — mixed surfaces make the acceptance story
  (and the audit) untrue.
- Do not describe the system as "certified", a study as "proven",
  or a bundle as "published" unless the corresponding record
  (verdict event, anchor receipt) exists and you have read it
  back.
