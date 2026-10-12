# Spec 010 — OSF Registration — tasks

Mapping to pilot DESIGN §4.3 (T-P1…T-P4). T-P5 (UI) is excluded by the
Article XIV gate and appears nowhere in this spec.

- [x] T0 Spec + claims bundle v0.1.0 + assessor run at after_specify.
- [ ] T-P1 OSF transport (`src/tekmerion/osf_deposit.py`): project +
      components + file upload behind the adjudicator-approval gate;
      payloads derived from `osf_metadata`; deposit-state persistence;
      seeded failure tests (gate refusals create nothing, provider errors
      surface verbatim, partial state resumes).
- [ ] T-P2 Registration action incl. embargo path: draft from the
      by-name-resolved Open-Ended Registration schema, summary = anchor
      statement, submit (immediate or embargoed), approval actions the
      record offers performed and final state read from the fetched
      record; embargo demonstrated live on a test registration and
      fetched back (CLM-010-07).
- [ ] T-P3 Receipt + verification: receipt in the Zenodo shape discipline;
      `record_anchor` ledgering exercised on a fixture study;
      `verify_osf_anchor` — independent fetch, anchor-value comparison,
      component-structure comparison; mismatch never passes.
- [ ] T-P4 Live demonstration on the Phase 7 evaluation study (bundle-v2):
      study-directory hashes recorded before; deposit submitted public
      with `approved_by` naming the DN-012 authorization; idempotency
      re-run refused with the existing registration named; independent
      unauthenticated fetch verifies the public record; study-directory
      hashes re-recorded after (identical); receipt + fetched records in
      `records/`; claims re-assessed at after_implement.
