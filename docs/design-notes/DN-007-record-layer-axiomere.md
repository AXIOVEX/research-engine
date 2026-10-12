# Design Note 007 — The Record Layer Is Axiomere

**Date:** 2026-10-11 · **Status:** Adopted (follows owner directives: DN-005 + the Axiomere build order)
**Amends:** DN-004 (store technology superseded; language decision stands). **Implements:** DN-005 layers 2–5 for this framework.

## Decision

Tekmerion's record layer is **Axiomere** — AXIOVEX/axiomere (Rust core, MIT) via the Python package in AXIOVEX/axiomere-python. One study = one `.axmr` ledger. Claims, verdicts, freezes, and connector query logs are Axiomere events and snapshots; actors sign with Ed25519 keys; checkpoints close study phases; anchoring (Phase 5, AR-1/G2) deposits checkpoint roots externally.

DN-004 chose "Python 3.12 stdlib core, JSONL append-only log, SHA-256 chain" when the store was an internal component. DN-005 then raised the bar — content-addressed snapshot lineage, signed appends, Merkle checkpoints, no-delete semantics as a *product guarantee* — and the owner directed that the store be built as its own technology. Re-implementing those layers in this repo's Python would duplicate Axiomere badly and split the guarantee across two codebases. So: **the framework consumes the ledger; it does not contain one.**

## What stands, what is superseded

| DN-004 element | Status |
|---|---|
| Python 3.12 for framework logic | **Stands** |
| Append-only JSONL EventStore (`tekmerion/record.py`) | **Superseded as the record layer.** Kept in-repo as the Phase 1 prototype and the reference for the standalone-verifier pattern; new Spec 002 work writes through Axiomere |
| "Stdlib-only core" | **Superseded.** The framework now depends on the `axiomere` Python package + its Rust extension (built from AXIOVEX/axiomere; see that repo's install path and this repo's CI) |

## Mapping (binding on Phase 2+ work)

- Study → one `.axmr` file; study creation = `Database.create`.
- Claim registration/revision → Axiomere snapshots of the claim record (lineage = the claim's history; falsifier carried in content).
- Verdict issuance → typed append (`verdict.issued`) + a snapshot updating the claim's current state. A verdict is never edited; a superseding verdict is a new append.
- Withdrawal of any record → `Database.dead(...)` (status dead, reason mandatory, score 0.0). No other removal mechanism exists — in Axiomere, or here.
- Freeze → `Database.checkpoint(...)`: the Merkle root at freeze time is the freeze commitment; Phase 5 anchors it (AR-1).
- Connector query logs (Phase 2) → typed appends in the study ledger, so every retrieved item's provenance is itself chained and signed.

## Falsifier for this decision

If the Axiomere dependency measurably blocks the Phase 7 evaluation (install friction in the hosted pilot shape, or bindings instability under evaluation load), DN-007 is revisited with that evidence — and any fallback must still satisfy DN-005 in full (no delete, signed, checkpointed, anchored). Convenience is not a fallback criterion.
