CUI marking: none recorded — this artifact is UNMARKED.

# Platform audit export

Scope: tenant ledger for tenant `uni-a`.

This export is a snapshot of one append-only platform audit ledger, produced under Spec 005 T542 in the Phase 5 bundle pattern. It contains:

- `ledger/audit.axmr` — the ledger itself, copied byte-for-byte
- `events.json` — every event in the ledger, in order
- `poam.json` — the scope's POA&M register (T553), replayed
- `control-states.json` — the scope's SPRS-input control states and computed score (T552), where seeded
- `manifest.json` — the file manifest; its bundle hash binds this file set

Events: 8 · head seq 8 · checkpoint root `b4595425a06d83d508dfaed2a62957b1da755213100dbe65d7fe38e932509aba`

## Verify it yourself

From a Tekmerion checkout: `python -m tekmerion.platform.exports <this directory>` — the standalone verifier re-checks the file hashes, runs the production Axiomere verifier over the ledger copy, and cross-checks every projection against the ledger's own events, using the export alone.

What this export establishes: the record as exported is internally intact and matches the ledger it was taken from (whose continuing chain carries the `audit.exported` record of this export). What it does not establish: that events were never omitted before the fact — an append-only ledger proves the record it holds, and the anchor record (T543) is what binds this snapshot to the continuing chain.

CUI marking: none recorded — this artifact is UNMARKED.
