# MCP tools reference

The `tekmerion-mcp` server exposes **29 tools**, generated 1:1 from the
production engine services: the server is a surface over the engine and
has no semantics of its own. This page is generated from the tool
definitions in `src/tekmerion/mcp/server.py` (Spec 009); the docstring
under each signature is the server's own.

One server instance runs as **one actor with one WS6 role**
(`TEKMERION_ACTOR`, `TEKMERION_ROLE` — see
[Installation](../guide/installation.md)). Role denials are part of the record:
a tool called by the wrong role is refused, and the refusal is returned
verbatim.

## Studies

### `list_studies`

```text
list_studies()
```

List the studies in this instance's workspace.

### `create_study`

```text
create_study(study_id: str, title: str = '')
```

Create a study (one append-only Axiomere ledger). Roles: researcher, adjudicator.

### `get_study_status`

```text
get_study_status(study_id: str)
```

Study projection: chain verification, claims, freeze state, run state, verdicts, anchors, adapter runs.

## Claims

### `register_claim`

```text
register_claim(study_id: str, claim_id: str, statement: str, falsifier: str, kind: str = 'data', dependencies: Optional[list[str]] = None, margin: Optional[float] = None, sufficiency_floor: Optional[int] = None, supersedes: Optional[str] = None)
```

Register a claim. The falsifier is mandatory — without one the engine refuses and nothing is appended.

### `list_claims`

```text
list_claims(study_id: str)
```

All claims in registration order, with origin-group masses and any issued verdict.

### `get_claim`

```text
get_claim(study_id: str, claim_id: str)
```

One claim with its evidence groups and verdict.

### `withdraw_claim`

```text
withdraw_claim(study_id: str, claim_id: str, reason: str)
```

Withdraw a claim the only way that exists: a dead snapshot with the reason on the record (score 0.0). There is no delete.

## Citations & adjudication

### `attach_citation`

```text
attach_citation(study_id: str, citation_id: str, claim_id: str, proposition: str, doi: Optional[str] = None, title: str = '', authors: Optional[list[str]] = None, year: Optional[int] = None, venue: Optional[str] = None)
```

Attach a citation to a claim and run the verification pipeline (resolution, agreement, content check). Exactly one outcome is ledgered per citation; disagreements are quarantined to the adjudication queue.

### `list_adjudication_queue`

```text
list_adjudication_queue(study_id: str)
```

Pending and decided adjudication items, the RT-4 second-review sample, and the rubber-stamp report.

### `decide_adjudication`

```text
decide_adjudication(study_id: str, queue_id: str, decision: str, rationale: str = '')
```

Record a named adjudication decision (adjudicator role only). Decisions are appends; a decided item cannot be re-decided.

### `record_second_review`

```text
record_second_review(study_id: str, queue_id: str, agrees: bool)
```

Record an independent second review of an adjudication decision (reviewer or adjudicator).

## Freeze, run, verdicts

### `freeze_study`

```text
freeze_study(study_id: str, mode: str = 'confirmation', linked_exploratory: Optional[list[str]] = None, controls: Optional[list[dict]] = None, deployment_shape: str = 'hosted')
```

Freeze the registration (adjudicator only). Fails closed: the engine's FreezeError names every failed check. For confirmation mode, linked_exploratory must be disclosed — pass [] to state 'none'.

### `run_evaluation`

```text
run_evaluation(study_id: str)
```

Run the evaluation against the frozen registration (adjudicator only). A valid run appends verdict.issued per claim; an INVALID run appends nothing and says why.

### `get_verdicts`

```text
get_verdicts(study_id: str)
```

Issued verdicts, or the run projection: an INVALID replay is returned as INVALID with the engine's reasons.

## Bundles & deposit

### `export_bundle`

```text
export_bundle(study_id: str)
```

Export the audit bundle and re-verify it standalone. Refuses (ExportError) on a broken chain or an unfrozen study.

### `verify_bundle`

```text
verify_bundle(bundle_dir: str)
```

Standalone bundle verification — consumes only the bundle directory.

### `verify_anchor`

```text
verify_anchor(bundle_dir: str, public_record: dict)
```

Check a bundle against a public anchor record (e.g. its Zenodo record JSON).

### `deposit_bundle`

```text
deposit_bundle(study_id: str, approved_by: str = '')
```

Deposit the latest exported bundle through the configured transport (adjudicator only). The adjudicator-approval gate is mechanical: with approved_by empty the engine refuses and nothing is appended.

## Domain adapters (lane 1)

### `run_checkcif`

```text
run_checkcif(study_id: str, cif_path: Optional[str] = None, recorded_output_path: Optional[str] = None, claim_id: Optional[str] = None, item_id: Optional[str] = None, origin_group: Optional[str] = None)
```

checkCIF/PLATON adapter (P2, lane-1): live PLATON where a binary exists, else a recorded output, else the run records not_runnable_here. A clean check is context, never support (CLM-006-02).

### `run_codecheck`

```text
run_codecheck(study_id: str, certificate_id: str, claim_id: Optional[str] = None, item_id: Optional[str] = None, origin_group: Optional[str] = None, work_outputs: Optional[list[str]] = None)
```

CODECHECK adapter (P3, lane-1): ingest a certificate from the public register as scoped re-execution evidence. A certificate never certifies correctness (CLM-007-02).

### `run_grim`

```text
run_grim(study_id: str, cases: list[dict], claim_id: Optional[str] = None, item_id: Optional[str] = None, origin_group: Optional[str] = None)
```

GRIM/GRIMMER adapter (P7, lane-1): cases are {label, mean, sd?, n, items?} with mean/sd as strings (precision is data). An impossibility is a falsifier observation for a reporting-consistency claim.

### `run_statcheck`

```text
run_statcheck(study_id: str, manuscript_path: Optional[str] = None, recorded_output_path: Optional[str] = None, claim_id: Optional[str] = None, item_id: Optional[str] = None, origin_group: Optional[str] = None)
```

statcheck adapter (P7, lane-1): live R seam where an R runtime exists, else recorded output, else not_runnable_here. Extraction coverage is part of every record — no flags is not a clean paper.

### `list_adapter_runs`

```text
list_adapter_runs(study_id: str, adapter_id: Optional[str] = None)
```

Replay every adapter run record in the ledger, provenance intact.

## Theorem claims (Spec 003)

### `register_theorem`

```text
register_theorem(study_id: str, parent_id: str, headline: str, claimant: str, problem: str, margin: float = 0.1, sufficiency_floor: int = 1, statements: Optional[dict[str, str]] = None)
```

Register a theorem claim as a parent plus its five Spec 003 sub-claims (faithful, proof, open, attribution, significance), each with its registered falsifier.

### `pin_faithfulness`

```text
pin_faithfulness(study_id: str, claim_id: str, formal_statement: str, original_statement: str, original_source: str)
```

Pin a formal statement beside the original problem statement, verbatim — the pair the faithful sub-claim is judged from.

### `ingest_lean`

```text
ingest_lean(study_id: str, url: str, theorem_name: Optional[str] = None, source_compile_claim: Optional[dict] = None)
```

Ingest a Lean artifact: fetch, SHA-256, sorry/admit counts, axiom audit where a toolchain exists. The compile state is recorded as it is (not_attempted / claimed_by_source / run_by_us / not_runnable_here) — never upgraded.

### `record_digestion`

```text
record_digestion(study_id: str, claim_id: str, explainer: str, artifact_ref: str, claimant_explanation: bool = False)
```

Lane-2 record: a named human's explanation of a result. Claimant self-explanation is recorded but labeled as the claimant's.

### `record_acceptance`

```text
record_acceptance(study_id: str, claim_id: str, stage: str, by: str, evidence_ref: str)
```

Lane-2 record: stage advancement (accepted|digested) on named human evidence. Lane-1 activity can never move lane 2.

### `get_theorem_state`

```text
get_theorem_state(study_id: str, claim_id: str)
```

Lane-1 summary and lane-2 state for a theorem claim, stated separately — lane 1 never displays as lane 2.
