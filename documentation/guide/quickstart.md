# Quickstart: one study, end to end

This is the evidence-question playbook, run entirely through the MCP
tools (see the [tools reference](../reference/mcp-tools.md)). It assumes
two configured instances — researcher and adjudicator — against one
workspace ([installation](installation.md)).

## 1. Create the study

`create_study` — `{"study_id": "demo", "title": "Demo study"}` (either
instance). A study is one append-only Axiomere ledger.

## 2. Register claims — falsifier first

From the researcher instance, then a second claim from the adjudicator
instance:

`register_claim(study_id, claim_id, statement, falsifier, margin,
sufficiency_floor)` — e.g. `margin` 0.1, `sufficiency_floor` 1 (the
minimum number of independent origin groups that must support the claim).

Registering the first claims from **two different instances** matters:
the swap control needs early ledger events from different actors to
bite.

Try one registration *without* a falsifier first if you want to see the
point of the system:

- Omit the argument entirely and the tool's schema refuses the call
  (`falsifier … Field required`) before the engine is reached.
- Pass it empty and the engine itself refuses, verbatim —
  `…: no falsifier — not registered (Article II)` — and appends nothing.

If you cannot state what observation would falsify the claim, the claim
is not ready.

## 3. Attach citations

`attach_citation(study_id, citation_id, claim_id, proposition, doi,
title, authors, year, venue)` per citation. Each citation is resolved
live (Crossref → OpenAlex, with CORE as a content-enrichment stage) and
content-checked where the record's licence basis permits. Exactly one
outcome is ledgered per citation:

- `resolution`: `resolved` / `not_found` / `error`
- `agreement`: `agree` / `disagree` (when resolution succeeded)
- `content`: `supports` / `contradicts` / `contextual` /
  `metadata_only` (when content was checked)

Attach a real DOI and watch it resolve; attach a fabricated DOI and
watch it land in the adjudication queue as `not_found`. Metadata-only
evidence accumulates verdict mass of zero by design — a claim backed
only by metadata can at best be inconclusive. That cap is the machinery
working.

## 4. Adjudicate the queue

`list_adjudication_queue(study_id)`, then the **adjudicator instance**
calls `decide_adjudication(study_id, queue_id, decision, rationale)`:

- For a **quarantine** item: `exclude` (fabricated, wrong, or ineligible
  evidence leaves the basis) or `variant` (a metadata mismatch ruled a
  legitimate variant; the item stands).
- For a **grouping** item: `same_origin` or `separate_origin` (whether
  the pair counts as one origin group).
- `record_second_review(study_id, queue_id, agrees)` records an
  independent second review where the queue view samples the item.

Decisions are appends; a decided item cannot be re-decided.
**Undecided queue items make the run INVALID** — decide every pending
item before you run.

## 5. Freeze

`freeze_study(study_id, linked_exploratory, controls)` — adjudicator
instance; mode defaults to `"confirmation"`. The freeze registers the
design — claims, margins, floors, controls, and the exploratory-linkage
disclosure — before outcomes are seen, and fails closed with every
failed check listed.

**Controls must be passed explicitly**: a `positive` control (must
reach its expected verdict), a `negative` control (must be
contradicted), and a `swap` control (a provenance swap between early
ledger lines must be detected). Each names the failure mode it exists
to catch; the positive control carries a `representative_rationale`.
Controls that cannot differentially fail mark the run invalid rather
than passing it.

## 6. Run and read the verdicts

`run_evaluation(study_id)`, then `get_verdicts(study_id)`.

- On an unfrozen study the run returns INVALID with the freeze-wall
  reason and issues nothing — verdicts exist only against a frozen
  registration.
- A valid run issues one verdict per claim — **supported**,
  **contradicted**, or **inconclusive** — each with its interval and
  reason.
- **INVALID means stop.** An invalid run issues no claim verdicts.
  Report it as INVALID with the engine's reasons; never salvage or
  paraphrase verdicts from one.

## 7. Export and verify the bundle

`export_bundle(study_id)`, then `verify_bundle(bundle_dir)` — the
verifier consumes **only the bundle**: the claim register, evidence,
verdicts, and the ledger must re-verify standalone, without the live
store. A bundle that does not verify standalone is not done, whatever
the study screen says.

## 8. Deposit (gated)

Only when a transport is configured and a named human adjudicator
approves: `deposit_bundle(study_id, approved_by="<the approver's
name>")`. With `approved_by` empty the engine refuses and nothing is
appended — that refusal is the gate working. Afterwards,
`verify_anchor(bundle_dir, public_record)` checks the bundle against
the independently fetched deposit record (Zenodo or OSF).
