# Design Note 005 — Absolute Append-Only: No Deletions, Ever

**Date:** 2026-10-11 · **Status:** Owner decision record + constitution amendment · **Decided by:** Tristen Pierson
**Amends:** Constitution Article IV (→ v1.1.0); WS4 §5; WS2 lifecycle. **Applies as a pattern to all Axiovex hash-chained ledgers** (the epistemic ledger aligns by its own follow-on note; its signed-verdict machinery is reused here, not reinvented).

## The rule

**Records are never deleted. There is no delete operation — not in the API, not in the UI, not as an admin function.** Records change only by appending new snapshots of older records, git-style: every snapshot is content-addressed, names its parent, and the full lineage stays readable forever. The "current view" is a fold over snapshots, never a mutation of them.

## Removal semantics (the only three, all appends)

| Need | Mechanism |
|------|-----------|
| Record revised | New snapshot; the old is **superseded**, linked both ways |
| Record withdrawn / wrong / duplicate | New snapshot with `status: dead`, a mandatory reason code (`retracted` · `entered-in-error` · `duplicate-of-<id>`), **and `score: 0.0`** — status for correct consumers, 0.0 so score-only consumers also stop using it |
| Score correction | New snapshot carrying the new score; the old score stays in history |

Score and status are distinct fields on purpose: score is epistemic (how much we believe it), status is lifecycle (whether it may be used at all). Dead sets both.

## Cryptographic guarantee — five layers

1. **Hash chain** (built, Phase 1): SHA-256 over canonical event form; alteration/insertion/deletion/reorder breaks verification.
2. **Content addressing**: snapshot ID = hash(content + parent snapshot ID); tampering invalidates descendants.
3. **Ed25519 signatures on appends**: the actor's key signs each event; the claim upgrades from "chain intact" to "chain intact *and this keyholder appended this*."
4. **Merkle checkpoints**: periodic signed Merkle roots over event ranges, appended as checkpoint events.

**Implementation status (corrected at commit, 2026-10-11):** layers 3–4 were originally planned as a Python v0.2 of this repo's record service. Before that code landed, the owner directed that the store become its own product — it was built instead as **Axiomere** (AXIOVEX/axiomere, Rust, MIT), where layers 2–4 are implemented and tested (7 integration tests incl. seeded tamper/forgery cases). This framework adopts Axiomere as its record layer per DN-007; the interim Python EventStore keeps layer 1 and loses its redaction machinery in this same commit. The vendored `ed25519.py` copied here during the v0.2 attempt was removed uncommitted — signatures live in Axiomere now.
5. **External anchoring** (gate G2/AR-1, Phase 5 transport): checkpoint roots are deposited where the operator does not control them (OSF/Zenodo DOI, RFC 3161 TSA, or equivalent). This is the layer that makes rewriting history detectable *by anyone*: a sole-copy operator could otherwise recompute a chain from genesis. Layers 1–4 make tampering evident to us; layer 5 makes it evident to the world.

## Ingest discipline (the first line of defense)

The chain holds research records. Personal data and secrets **never enter payloads**: where a payload would need them, it stores a hash plus an external reference, and the sensitive material lives outside the chain under ordinary data controls. Most erasure pressure is designed out here, before it can exist.

## The single exception — break-glass erasure certificate

For documented legal compulsion only (court order, statutory erasure duty covering chain content despite ingest discipline, unlawful content): payloads are encrypted under per-record keys, an **owner-signed erasure certificate** is appended to the chain (authority, order reference, scope, timestamp), and that record's key — and only that key — is destroyed. The event, its hash, its signature, and the certificate remain; the chain still verifies; only the payload becomes unrecoverable. There is no routine path, no UI, and no other use. Payload encryption at ingest is Spec 002 work (task T223); until it lands, this protocol is specified but not yet executable — recorded honestly rather than implied.

## What this note kills

WS4 §5's routine tombstone-redaction (payload masking in projections/exports, shipped in Phase 1) is **removed**: masking is a soft delete and this rule forbids it. Ordinary withdrawal is the dead-snapshot mechanism above. The Phase 1 code is amended in the same commit series as this note, and its redaction test is replaced by dead-semantics and certificate tests.
