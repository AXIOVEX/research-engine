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
- [x] T-P3 Receipt + verification: receipt in the Zenodo shape discipline;
      `record_anchor` ledgering exercised on a fixture study;
      `verify_osf_anchor` — independent fetch, anchor-value comparison,
      component-structure comparison; mismatch never passes.
      **Status: complete (T-P4b finalize, 2026-10-12)** — the live
      receipt issued (`records/demo-receipt.json`) and the public
      unauthenticated verification passed
      (`records/demo-verification.json`). CLM-010-05 supported.
- [x] T-P4 Live demonstration on the Phase 7 evaluation study (bundle-v2):
      study-directory hashes recorded before; deposit submitted public
      with `approved_by` naming the DN-012 authorization; idempotency
      re-run refused with the existing registration named; independent
      unauthenticated fetch verifies the public record; study-directory
      hashes re-recorded after (identical); receipt + fetched records in
      `records/`; claims re-assessed at after_implement.
      **Status: complete (via T-P4b)** — deposit executed (project
      `dvrew`, 13 files); the first registration `h94bf` died at the
      provider's archive step and was replaced on resume by `84dk7`,
      now final and public (DOI 10.17605/OSF.IO/84DK7); the finalize
      re-run resumed against it (`already_existed: true`, no second
      registration) and issued the receipt; public verify passed;
      study directory byte-identical before/after/finalize (30 files).
- [x] T-P4b Resolve registration `h94bf`'s provider-side fate and
      complete the demonstration. **Status: complete, 2026-10-12.**
      Outcome: OSF's own failure email confirmed `h94bf` died at the
      provider's archive/copy step (project, components, and files
      unharmed); a resume run submitted replacement registration
      `84dk7` from the intact project; admin approval completed via
      OSF's email-link channel (2026-10-12, ~11:35 EDT); the finalize
      re-run re-fetched the final record
      (`records/demo-registration-final.json`), issued the receipt
      (`records/demo-receipt.json`, state at stage `complete`), and
      the public `verify_osf_anchor` passed
      (`records/demo-verification.json`). Registration DOI:
      10.17605/OSF.IO/84DK7. Full narrative:
      `records/demo-deposit-observation.md` + the T-P4b section of
      `assessment-2026-10-12.md`.
