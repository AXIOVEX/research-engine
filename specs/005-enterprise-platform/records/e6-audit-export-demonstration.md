# E6 Audit-Export Demonstration Record (T543; discharges the demonstration half of the §12 pilot gate, T533)

**Date:** 2026-10-12 · **Phase:** Spec 005 E6 · **Operator:** the E6
build agent, in the E1 fixture world (specimen identities — the
same labeled specimen basis as the console wireframes).

## What was run

The pilot-gate demonstration E4's exit record scheduled: a tenant
audit-ledger export, exercised end to end by the tenant's own
admin, and verified standalone.

1. A two-scope world was built on the E1 fixtures (platform admin,
   tenant `uni-a`, tenant admin). The deployment scope was seeded
   with the POA&M register's §3.13.11 item (T553) and the
   deployment-scope control states (T552); the tenant scope was
   seeded with its control states and one tenant POA&M item.
2. `export_tenant_audit` (tenant admin session) produced
   `records/e6-demonstration-bundle/` in the Phase 5 pattern:
   ledger copy, `events.json`, `poam.json`, `control-states.json`,
   HUMAN-README, hash manifest.
3. The standalone verifier (`python -m
   tekmerion.platform.exports`, bundle-alone — run again from a
   clean process against the committed bundle) returned **ok**,
   with the ledger copy passing the production Axiomere verifier
   and every projection cross-checked against it.
4. The anchor record (`audit.export_anchored`, tenant ledger seq
   10) binds the export to the continuing chain, naming this
   record as the anchor's location.

## The evidence

| Field | Value |
|---|---|
| Export ID | `exp-7c58b02bf93b` |
| Bundle hash | `7c58b02bf93b260c824572ada4ad4d34190157fb9564958ec01c9d833d703344` |
| Events exported | 8 |
| Checkpoint (Merkle) root | `b4595425a06d83d508dfaed2a62957b1da755213100dbe65d7fe38e932509aba` |
| Standalone verification | **ok** — 5 files hash-bound; ledger verify ok (8 events); events projection exact; control-states replay exact |
| SPRS self-score (seed inputs, computed) | **−156** of 110 — total deduction 266, of which §3.13.11 contributes **3** (the §5(e) partial: encryption employed, not FIPS-validated) |
| CUI marking on the export | unmarked (stated in the manifest and the README banner) |
| Residency pin after | `uni-a`: hosted, region unpinned, 0 migrations |

Machine-readable summary: `records/e6-demonstration-summary.json`.

## Dispositions

- **T533 (pilot gate): DISCHARGED.** Its isolation half passed at
  E4; its audit-export demonstration half is this record. The
  gate's own text asks for "cross-tenant isolation + a clean
  audit-export demonstration" before the first real tenant's
  data — both halves now stand on evidence.
- **T543's public-anchor leg: NOT EXECUTED, recorded as residue.**
  tasks.md phrases T543 with a deposit/anchor against a public
  record (the AR-1 pattern). This phase ran under an explicit
  no-external-accounts / no-uploads boundary, so the anchor
  executed here is the ledger-internal anchor record + this
  committed demonstration record. Depositing a platform audit
  export to a public anchor (e.g. Zenodo, as the study bundles
  do) remains available machinery (`src/tekmerion/deposit.py`)
  and is a named, still-open leg — it is not claimed as done.
- **The SPRS number's meaning, stated plainly:** −156 is the
  computed output of the *seed input set* — the platform's own
  inputs with every operator-side remainder unimplemented. It is
  the machinery's honest output over recorded inputs, not an
  assessment of any organization, and it is reported here because
  the machinery's job is to compute it, not to flatter it.
