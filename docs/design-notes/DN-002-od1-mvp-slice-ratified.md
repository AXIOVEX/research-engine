# Design Note 002 — OD-1 Ratified: The MVP Slice

**Date:** 2026-10-11 · **Status:** Owner decision record · **Decided by:** Tristen Pierson
**Supersedes:** the "PROPOSED" status of Spec 001 §6 and claim CLM-001-07. Per DN-001's rule, this note is appended; DN-001 and the original §6 text are not rewritten — §6's status line is updated to point here.

## Decision

The MVP slice is **approved as proposed** in Spec 001 §6:

- **Workflow:** one systematic-review-style evidence question, end-to-end (audience U2, research teams).
- **Loop:** registration → scholarly retrieval → claim register → origin-grouped evidence → per-claim verdicts with controls → adjudicator sign-off → audit-bundle export (OSF/Zenodo-depositable).
- **First connectors:** Crossref (resolution backbone) + OpenAlex (discovery/graph), per WS1 OQ-1.2.
- **Kill criteria K1–K5 stand as written**, including K1 at 100%: every exported citation resolves to a real record, no exceptions threshold. K3/K5 numeric thresholds remain OD-5, to be set before the evaluation run's registration is frozen — not after.

## Effect

- CLM-001-07 (the slice is the smallest workflow exercising every constitutional article) moves from `proposed-pending-owner` to `ratified-by-owner`. Its falsifier remains live: a smaller complete workflow, or a demonstration that this slice omits an article, still defeats it.
- The implementation spec (Spec 002) may now be drafted. It may not be *executed* past its own gates: the AR-1 hash-anchor gate (RED-TEAM-01) and OD-2 (deployment shape) both bind it.
- The MVP evaluation is itself a frozen registration inside the engine (WS6 §4): the product's first study is the evaluation of the product.

## Next decision in queue

OD-2 — deployment shape. Prepared recommendation in WS6 §3: design for **hybrid** (institution-held record store, shared connector/verification services), **hosted-first for the pilot**, with bundle export guaranteeing exit. Presented to the owner as its own single decision, per the founding brief.
