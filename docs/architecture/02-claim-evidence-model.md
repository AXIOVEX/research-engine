# WS2 — Claim & Evidence Model

**Status:** Draft v0.1, 2026-10-11 · Governs: FR-002, FR-004 · Constitution: Articles II, IV, V, VII

## 1. The claim record

A claim is the atomic unit of the engine. Nothing is asserted by the system except through a claim record.

| Field | Content | Rule |
|-------|---------|------|
| `claim_id` | Stable ID, `CLM-<study>-<nnn>`, never reused | Assigned at registration or append time |
| `kind` | `empirical` · `definitional` · `methodological` · `scope` · `design` | Fixed vocabulary; new kinds by design note |
| `statement` | One proposition, plainly stated | Compound statements are split — a claim that contains "and" usually hides two verdicts |
| `falsifier` | The observation that would overturn it | Mandatory. No falsifier → not registered (Article II) |
| `margin` | The practical margin within which the claim counts as supported | Set at freeze; reported with an interval (Article VII) |
| `dependencies` | Claim IDs and evidence-group IDs this claim rests on | Forms the dependency graph (§4) |
| `status` | Lifecycle state (below) | Transitions are appended events, never edits |

**Lifecycle:** `proposed → registered (frozen) → under-review → verdicted → (superseded | revisited)`. A claim's *statement* never changes after registration; a changed statement is a new claim that supersedes the old one, with the link recorded both ways.

*Rejected alternative:* claims as rows in a mutable table with a `current_verdict` column. Rejected because it destroys exactly what the product sells — the history of what was believed and why (Article IV).

## 2. The evidence item and the origin group

An **evidence item** is one retrieved artifact: `item_id`, `source_id` (WS1 connector), source-native identifier (DOI preferred), retrieval timestamp, query-log reference, content hash, license/rights stub (WS1/WS5), and a stance extraction (supports / contradicts / contextual, with the extractor identified — model name and version, or human).

An **origin group** is the set of items that trace to one underlying origin: the same study, dataset, or document, however many times it is republished, summarized, cited, or re-retrieved. Grouping keys, in precedence order:

1. Same DOI / source-native ID.
2. Same underlying dataset or registration ID (e.g., trial registration, OSF/Zenodo record).
3. Explicit derivation link (item states it summarizes/reports item X).
4. Near-duplicate content hash + shared authorship/venue fingerprint — flagged for human adjudication, never auto-merged silently.

**Counting rule (Article V):** weights accrue to *groups*. A claim supported by 4 groups is stronger than one supported by 40 items in 1 group, and every display, score, and export in the system must show group counts — an item count shown without its group count is a defect.

*Hard case, recorded honestly:* two papers from one dataset are two groups or one? Decision: the **dataset** is the origin for data claims; the **paper** is the origin for interpretation claims. The claim kind decides which grouping applies, and the choice is recorded per claim at registration so it cannot be tuned after results arrive.

## 3. Dependency graph

Claims depend on claims and on evidence groups. The graph is a DAG within a study (a cycle is a registration error — it means two claims are each other's justification, which is circular support, and the freeze check rejects it). The graph drives:

- **Revisit propagation** — when an evidence group is corrected or retracted upstream, exactly the claims reachable from it are flagged for re-verdict (WS3).
- **Audit traversal** — an adjudicator walks from any verdict down to raw provenance in bounded steps (K3 budget).
- **Weakest-link display** — a derived claim's display strength never exceeds its weakest load-bearing dependency.

## 4. Relationship to the epistemic ledger — adopt / adapt / supersede (OD-3)

The ledger (`AXIOVEX/epistemic-ledger`) is a research prototype with measured results. Transfer map, per mechanism:

| Ledger mechanism | Decision | Reason |
|------------------|----------|--------|
| Append-only event log; state as replay | **ADOPT** | Directly implements Article IV; replay verification is measured, not speculative |
| Bitemporal records (valid time / transaction time) | **ADOPT** | "What did we believe at T" is a core audit query for integrity offices |
| Fluid certainty scores on every conclusion | **ADAPT** | Product verdicts are categorical-with-intervals (Article VII), because institutions adjudicate decisions, not credences. Scores survive *inside* the engine as one input to verdicts, with D–S-style intervals where ignorance must be explicit; they are never the exported headline |
| Dependency-propagated revisit loop + materiality cutoff | **ADOPT with product tuning** | The trigger ladder (dirty-flag → precise invalidation → materiality) is adopted; thresholds are per-study registered parameters, not global constants, because materiality is domain judgment |
| Learned entrenchment (which belief yields in a contradiction) | **ADAPT** | Entrenchment ordering is adopted for contradiction handling, but in institutional use the order is *declared at registration* (e.g., primary data > secondary analysis > commentary), not learned silently — an adjudicator must be able to read the rule that decided a conflict |
| Writer trust tiers / governance (signed verdicts, escalation) | **ADAPT** | Signed verdicts map to the human adjudication sign-off (FR-010). Writer tiers map to role permissions (WS5), simplified: institutions bring their own identity, the engine brings the record |
| Contradiction detection (score opposition under shared ancestry) | **ADOPT** | Shared-ancestry contradiction is precisely the origin-group problem viewed from the other side |
| Caller-owned abstention | **ADOPT** | The engine may abstain (INCONCLUSIVE); whether to accept an abstention, escalate, or re-run is the adjudicator's call, never the engine's |

*Superseded:* nothing yet. Any future supersession requires a design note stating the measurement or argument that defeats the ledger result it replaces.

## 5. Open questions in this workstream

- OQ-2.1 Falsifier representation: free text vs. structured (observable, threshold, source)? Leaning structured-with-text: free text alone is not machine-checkable; structure alone is too rigid for novel claims. Needs a red-team case.
- OQ-2.2 Cross-study claim identity: can a claim in study B depend on a verdict in study A? Leaning yes, by reference (study A's bundle hash), never by copy — a copy would fork the record.
