# Spec 010 — OSF Registration — tasks

Mapping to pilot DESIGN §4.3 (T-P1…T-P4). T-P5 (UI) is excluded by the
Article XIV gate and appears nowhere in this spec.

- [x] T0 Spec + claims bundle v0.1.0 + assessor run at after_specify.
- [x] T-P1 OSF transport (`src/tekmerion/osf_deposit.py`): project +
      components + file upload behind the adjudicator-approval gate;
      payloads derived from `osf_metadata`; deposit-state persistence;
      seeded failure tests (gate refusals create nothing, provider errors
      surface verbatim, partial state resumes).
- [x] T-P2 Registration action incl. embargo path: draft from the
      by-name-resolved Open-Ended Registration schema, summary = anchor
      statement, submit (immediate or embargoed); embargo demonstrated
      live on a test registration and fetched back (CLM-010-07) —
      registration `kcysa`, embargo to 2027-10-12, terms recorded by the
      provider, non-public. Correction to the original task text: no
      approval action is performable through the token API (409/403
      observed); admin approval runs through OSF's email-link channel,
      and the finalize step reads finality from the fetched record.
- [ ] T-P3 Receipt + verification: receipt in the Zenodo shape discipline;
      `record_anchor` ledgering exercised on a fixture study;
      `verify_osf_anchor` — independent fetch, anchor-value comparison,
      component-structure comparison; mismatch never passes.
      **Status: machinery built and unit-proven; the live receipt +
      public verification are outstanding** — both wait on T-P4b
      (provider-side finalization). CLM-010-05 partially_supported.
- [ ] T-P4 Live demonstration on the Phase 7 evaluation study (bundle-v2):
      study-directory hashes recorded before; deposit submitted public
      with `approved_by` naming the DN-012 authorization; idempotency
      re-run refused with the existing registration named; independent
      unauthenticated fetch verifies the public record; study-directory
      hashes re-recorded after (identical); receipt + fetched records in
      `records/`; claims re-assessed at after_implement.
      **Status: deposit executed** (project `dvrew`, 13 files,
      registration `h94bf` submitted; study directory byte-identical
      before/after, 30 files). Completion (receipt + public verify +
      idempotency re-run against the final record) waits on T-P4b.
- [ ] T-P4b (OPEN, operator) Resolve registration `h94bf`'s
      provider-side fate and complete the demonstration: re-fetch the
      registration and the project log (`/v2/nodes/dvrew/logs/`) when
      the egress path is reliable (at build exit the record read
      HTTP 410 / absent from the project list minutes after a
      successful finalize read — `records/demo-deposit-observation.md`);
      admin approval via OSF's email-link channel as applicable; then
      re-run the deposit (it resumes against the recorded state —
      no second registration) to issue the receipt, run the public
      `verify_osf_anchor`, and record both in `records/`.
