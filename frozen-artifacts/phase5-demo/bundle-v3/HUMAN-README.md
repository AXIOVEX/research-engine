# Audit bundle — ar1-demo-1905

This bundle is the complete, self-describing record of one Tekmerion
study run. It is designed to be audited with generic tools (JSON +
Markdown, UTF-8) without the engine that produced it.

## What is in here

- `ledger/study.axmr` — the study's append-only ledger, copied
  byte-for-byte: hash-chained, Ed25519-signed events (Axiomere).
- `registration.json` — the frozen study design. Its SHA-256
  registration hash is committed inside the ledger itself
  (`study.frozen` event, seq 10).
- `claims.json` — the full claim register, falsifiers included.
- `evidence/` — evidence items, origin groups, and retrieved
  content *only where the source licence permits redistribution*;
  everything else is a provenance stub (see substitutions below).
- `verification.json` — every citation's pipeline outcome
  (resolution / agreement / content check) and the second-review
  report (RT-4).
- `coverage.json` — support-check coverage per claim (WS5 §2):
  how many origin groups were content-checked vs metadata-only.
- `verdicts.json`, `controls.json`, `adjudication.json`,
  `queries.json` — the run's verdicts, controls, human decisions,
  and every connector query, verbatim.
- `anchors/` — external anchor receipts, if any (see below).
- `manifest.json` — the file list with SHA-256 hashes, the Merkle
  checkpoint root, and the bundle hash that binds the set.

## The study in numbers

- Ledger events: 18
- Claims in the register: 1
- Adjudication items decided: 2; pending: 0
- Merkle checkpoint root: `52e08f7ac25b18dd26fbb90f6a8cdfd52bb36a7a208982c6e46e0510c5e37223`
- Registration hash: `238b1eb802de495016f0d71b03a398574b7a70540d7119c5991688a15b3950ff`
- Bundle hash: stated in `manifest.json` (`bundle_hash`).

## Anchoring

- Anchored via **zenodo**: root `7434209696ea39ba8e97a33b5caa0ae08928269ea81c7d6407f423191e86e317` at 2026-10-12T06:46:48.160573+00:00 — locator: https://doi.org/10.5281/zenodo.23311479 (approved by Tristen Pierson (owner; Phase 5 go-order, 2026-10-12)). The receipt is also an event in the ledger (`anchor.recorded`).

## Content substitutions (WS5 §4)

None — every retrieved item with content was either redistributable or carried no content.

## How to verify this bundle

1. Recompute the SHA-256 of every file listed in `manifest.json`
   and compare — any mismatch means the bundle was altered.
2. Verify the ledger with any Axiomere verifier
   (`axiomere verify-file ledger/study.axmr`): the hash chain and
   every signature must check out, and the latest checkpoint's
   Merkle root must equal `checkpoint_root` in the manifest.
3. Recompute the registration hash from `registration.json`
   (canonical JSON, SHA-256) and compare it with the
   `study.frozen` event inside the ledger.
4. Or run the standalone verifier, which does all of the above
   and the cross-checks between files:
   `python -m tekmerion.export <bundle-dir>` from the Tekmerion
   repository (it reads only the bundle).

Projections in this bundle (claims, coverage, adjudication) are
cross-checked against the ledger they project. Content that is
not represented in the ledger is bound by the manifest hashes —
and, once anchored, by the bundle hash stated in the public
anchor record.
