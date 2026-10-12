# Audit bundle — spec002-phase7-evaluation

This bundle is the complete, self-describing record of one Tekmerion
study run. It is designed to be audited with generic tools (JSON +
Markdown, UTF-8) without the engine that produced it.

## What is in here

- `ledger/study.axmr` — the study's append-only ledger, copied
  byte-for-byte: hash-chained, Ed25519-signed events (Axiomere).
- `registration.json` — the frozen study design. Its SHA-256
  registration hash is committed inside the ledger itself
  (`study.frozen` event, seq 35).
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
  `queries.json` — the run's outcome and verdicts, controls,
  human decisions, and every connector query, verbatim. The
  outcome (`valid` / `invalid` / `not-run`) is stated in
  `verdicts.json` itself: an invalid run issues no verdicts,
  so without it the bundle could not show that the run failed.
- `anchors/` — external anchor receipts, if any (see below).
- `manifest.json` — the file list with SHA-256 hashes, the Merkle
  checkpoint root, and the bundle hash that binds the set.

## The study in numbers

- Ledger events: 41
- Run outcome: **valid** (see `verdicts.json`)
- Claims in the register: 5
- Adjudication items decided: 4; pending: 0
- Merkle checkpoint root: `a4c798715c05ae151849ddf0e7c4a3dcb7b119620757b088686bd18d24e6c049`
- Registration hash: `977c1db162e9ba06b3e34c633a5bbae96fe4779aa49c43356b564cc8c3b9ac9b`
- Bundle hash: stated in `manifest.json` (`bundle_hash`).

## Anchoring

This bundle is **not externally anchored**. Its chain proves
internal consistency, not history: only an external anchor
(DN-005 layer 5) makes rewriting detectable by anyone. Do not
rely on this bundle institutionally until it is anchored.

## Content substitutions (WS5 §4)

- `CIT-E-101`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-102`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-201`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-301`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-401`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-501`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)
- `CIT-E-502`: licence basis does not permit redistribution: openalex-metadata (no licence asserted) → provenance stub (evidence/items.json + verification.json)

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
