# Spec 001 — Axiovex Research Engine (Design Phase)

**Status:** Draft for owner review · **Date:** 2026-10-11 · **Constitution:** v1.0.0
**Scope of this spec:** the *design* of the engine and the definition of its MVP slice. Implementation is a later spec, gated on owner approval of this one (Constitution, Article XII).

## 1. Problem statement

Universities are adopting AI research tools whose outputs cannot be inspected: citations that may not exist, methods that shift mid-run, summaries with no provenance. Institutions need AI-assisted research whose every conclusion can be traced to real evidence, tested against a stated falsifier, and reproduced from a frozen design. No incumbent tool provides that end-to-end (competitor analysis: `docs/architecture/06-product-shape.md` appendix, when complete).

## 2. Users

| ID | User | Need |
|----|------|------|
| U1 | Research integrity officer | Inspect how a conclusion was reached; adjudicate disputes from the record alone |
| U2 | Systematic-review / meta-analysis team | Reproducible search + auditable screening + honest evidence counts |
| U3 | Graduate program instructor | Assign AI-assisted research that students must defend claim by claim |
| U4 | Librarian / lab manager | Keep, deposit, and re-run research records over years |

## 3. Functional requirements

- **FR-001 Registration.** Before any retrieval, the system records a frozen registration: question, claim list (or the rule that generates it), sources, inclusion/exclusion criteria, verdict rules, controls, margins. The registration is timestamped and hash-chained (WS3/WS4).
- **FR-002 Claim register.** Every finding is a claim with stable ID, kind, statement, falsifier, status, and dependency links. Claims are never edited; state changes are appended events (WS2).
- **FR-003 Provenanced retrieval.** All evidence enters via source connectors with logged queries; each item carries source, identifier (DOI or source-native ID), retrieval time, and content hash (WS1).
- **FR-004 Origin grouping.** Evidence items are grouped by origin; counts and weights use groups, never raw item counts (WS2).
- **FR-005 Citation verification.** Every citation is resolved against its source of record (Crossref/DOI or source-native record) before use. An unresolvable citation fails the run (Constitution, Article VIII).
- **FR-006 Controls.** Each run executes its registered positive and negative controls. A control that cannot differentially fail marks the run INVALID (WS3).
- **FR-007 Verdicts.** Per-claim verdicts from the fixed taxonomy (INVALID / INCONCLUSIVE / CONTRADICTED / SUPPORTED), each with margin and interval, each linked to the evidence groups and falsifier test that produced it (WS3).
- **FR-008 Append-only store + replay.** The full record is an append-only, hash-chained event store; any frozen run can be replayed and its verdicts re-derived or the divergence flagged (WS4).
- **FR-009 Export.** One action exports an audit bundle: registration, claim register, evidence provenance, verdicts, adjudication record — in durable formats, with OSF/Zenodo deposit paths (WS4).
- **FR-010 Adjudication.** Verdict sets leaving the system carry a named human adjudicator's sign-off, recorded in the bundle (WS5).
- **FR-011 Exploratory mode.** Unregistered exploration is permitted, clearly labeled EXPLORATORY end-to-end; exploratory results can never be relabeled as confirmation — confirmation requires a new frozen registration (WS3).
- **FR-012 Source rights.** Connectors enforce per-source storage/redistribution terms; exports exclude content a source's terms do not permit redistributing, while preserving its provenance stub (WS1/WS5).

## 4. Success criteria (design phase)

- **SC-1** Architecture documents for all six workstreams exist, are internally consistent, and survive the red-team pass with all critical findings either fixed or recorded as accepted risks with reasons.
- **SC-2** The MVP slice is defined with explicit kill criteria (§6) the owner has approved.
- **SC-3** Every requirement above traces to ≥1 architecture section and ≥1 AEE claim in `aee-claims.json`.
- **SC-4** No document in the repo contains an unmeasured performance, accuracy, or adoption claim (Article X).

## 5. Non-requirements (this phase)

No code, no vendor selection that costs money, no external signups beyond free API keys on owner accounts, no UI design beyond the role/workflow sketch in WS6.

## 6. MVP slice + kill criteria — PROPOSED, owner decision OD-1

**Proposed slice:** one workflow end-to-end — *a systematic-review-style evidence question* (U2): registration → scholarly retrieval (OpenAlex + Crossref first) → claim register → origin-grouped evidence → verdicts → audit bundle export. It exercises every constitutional article in the smallest complete loop.

**Kill criteria (any one kills or re-scopes the slice):**

- **K1 Citation reality:** in a frozen evaluation run, <100% of exported citations resolve to real records. (The bar is 100%: this is the product's reason to exist. A miss re-scopes to fixing verification before any other work.)
- **K2 Replay integrity:** a replayed frozen run diverges from its recorded verdicts without the divergence being detected and flagged.
- **K3 Adjudicator burden:** a competent reviewer cannot audit a completed bundle — reach every verdict's evidence and falsifier test — within a pre-registered time budget (budget set at freeze of the evaluation, not after).
- **K4 Origin honesty:** derivative sources inflate an evidence count in any exported artifact.
- **K5 Cost shape:** per-question marginal cost at MVP scale exceeds the per-question value an institution demonstrably pays for review tooling (threshold set with the owner before the evaluation run, recorded by amendment).

## 7. Open decisions

OD-1 MVP slice approval · OD-2 deployment shape · OD-3 ledger scoring adoption map · OD-4 per-source rights table · OD-5 K3/K5 numeric thresholds. Each is settled in its architecture document, then ratified here by amendment (Article III).
