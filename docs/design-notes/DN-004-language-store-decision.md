# Design Note 004 — Implementation Language & Store (Phase 0, T201)

**Date:** 2026-10-11 · **Status:** Decided · **Gate:** G1 go-ahead given by owner 2026-10-11 (this note records both)

## Decision

- **Language/runtime:** Python 3.12+, **standard library only** for the record-service core. Dependencies enter later phases only with a recorded reason.
- **Write model:** one append-only **JSONL event log per study** (fsync on append), exactly the ledger prototype's hardened pattern (v0.11: single-writer discipline, replay verification).
- **Read model:** projections rebuilt from the log (in-memory / SQLite where persistence is needed). Projections are disposable; the log is the record (WS4 §1).
- **Integrity:** SHA-256 hash chain over canonical JSON (sorted keys, compact separators); each event carries `seq`, `prev_hash`, `hash`. Verification is a standalone function usable without the service (WS4 §3, OQ-4.2).

## Reasons

1. **Measured in-house prior art:** the epistemic-ledger prototype ran this exact stack (stdlib Python, JSONL log, SQLite projection) from v0.1 through v0.11.1, including replay verification and store hardening. Adopting it is adopting measurements, not fashion (WS2 §4's ADOPT row made concrete).
2. **20-year readability (WS4 §4):** JSONL + canonical JSON is inspectable with generic tools forever; no database server, no ORM, no binary format between a future auditor and the record.
3. **Single sequencing point is natural** in this shape: appends serialize through one writer path per study log; `seq` + `prev_hash` make forks and reorderings mechanically detectable (RT-2).
4. **Zero-dependency core** keeps the standalone verifier trustworthy: the component an integrity office runs to check a bundle should have the smallest possible supply chain.

## Rejected alternatives

- *PostgreSQL event table:* stronger concurrency story, but adds a server dependency to the custody component and weakens file-level portability of the record; the hybrid shape (DN-003) lets the record service stay file-based while shared services scale independently. Revisit only if a deployment's concurrency measurements demand it — recorded here so the revisit is a decision, not drift.
- *Rust/Go rewrite of ledger ideas:* performance is not the MVP's binding constraint; correctness evidence is. Python keeps the AEE/ledger lineage directly reusable.
