# Design Note 010 — The Stage Model: the engine's doctrine for public claims

**Date:** 2026-10-12 · **Status:** Adopted (owner directive, 2026-10-12).
**Decision source:** Owner brief, 2026-10-12. The doctrine below is adopted on the owner's direction as the program's standard for public claims.
**Scope:** Tekmerion product doctrine. The parallel adoption of this doctrine for the AEE framework itself is separate work in the AEE repos and is not governed by this note.

## Decision

Tekmerion's treatment of any public claim — above all a headline mathematical
result — follows eight points. Each point names the engine mechanism that
carries it; a point with no mechanism is a slogan, and this note adopts none.

| # | Point | Engine mechanism (where it lives) |
|---|-------------|-----------------------------------|
| 1 | A result passes five stages — **created, checked, explained, accepted, digested** — and creation + checking alone never settle it. | Verdict records distinguish the checked state (verification lane) from explained/accepted/digested states (acceptance lane). No code path promotes a lane-1 state into a settled result (Spec 003, `mathclaims`). |
| 2 | "Solved" decomposes into five claims: (i) the formal statement is **faithful** to the original problem; (ii) the proof is **verified**; (iii) the problem was **genuinely open**; (iv) **attribution is clean**, prior literature cited; (v) the result is **significant and explained**. | The theorem-claim schema: a parent claim plus five first-class sub-claims in the register, each with its own falsifier, evidence, and verdict. The parent verdict is a composition that can never outrun its weakest load-bearing sub-claim (Spec 003 §2). |
| 3 | **Digestion is first-class tracked work**: a named human explains the result. Verified-but-unexplained is a flagged risk state, not a footnote. | A digestion record per theorem claim: named explainer + explanation artifact, or the explicit state `UNEXPLAINED`, which raises a risk flag on the parent record wherever it is displayed or exported. |
| 4 | **Attribution is a claim.** A dispute is registered with both sides' evidence; contested attribution keeps the parent contested. | The attribution sub-claim carries both sides' retrieved evidence as register evidence; a live dispute is an adjudication item, and the composition rule holds the parent at *contested* while it stands. Disputes are appends, never edits. |
| 5 | **Anti-gradability:** easily graded metrics (counts, scores) never stand in for understanding. | Every theorem verdict carries a `remains_not_understood` field, written by the adjudicator, and no Tekmerion output or export publishes aggregate "solved" counts. Verdicts stay claim-by-claim (Article VII). |
| 6 | **Two lanes:** machine-speed verification vs human-paced acceptance, tracked separately; lane-1 completion never displays as lane-2 completion. | Lane fields on every math verdict record: `lane1_verification` (machine-checked state) and `lane2_acceptance` (unexplained / explained / accepted / digested). Lane 2 advances only on human evidence (a named explainer, an adjudicator's decision), never as a side effect of lane 1. |
| 7 | **Openness is protected:** provenance and registration establish priority, so openness is rewarded, not raced. | Registration is hash-chained and checkpointed at registration time (Axiomere record layer); audit bundles are publishable and externally anchored (AR-1, G2), so a claimant's priority is provable from the public record. |
| 8 | **Inspectable records:** every verdict ships an auditable evidence trail. | The audit bundle (WS4 §4) + Zenodo anchor is the standard output of a Tekmerion study — verdicts without a bundle and an anchor are drafts, whatever they say. |

## Effect

- Spec 003 (`specs/003-math-claims/`) is the first spec written under this
  doctrine: it defines the math layer (theorem schema, Lean ingestion,
  openness + attribution checks, digestion records, reliability seeding) and
  runs the doctrine's first worked study, on the 2026 public AI-mathematics
  claims.
- Where the doctrine conflicts with a metric the engine already produces
  (aggregate counts in coverage reports), the doctrine wins for *verdict*
  surfaces: coverage remains an internal completeness measure, never a
  verdict substitute (point 5).

## Falsifier for this decision

If a Tekmerion output is found presenting a machine-checked result as
accepted/digested understanding (lane confusion), or a parent theorem verdict
standing above a contested or unverified load-bearing sub-claim, or an
exported "solved count" offered as a verdict — the doctrine has failed in
the artifact, whatever this note says, and the defect is in the product, to
be fixed in the open.
