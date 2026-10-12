# T-P4 demonstration deposit — observation record, 2026-10-12

Deposit run (driver `tekmerion_osf.py deposit`, state
`demo-deposit-state.json` in this directory):

- Bundle: `specs/002-mvp-implementation/evaluation/study/bundle-v2/`
  (the Phase 7 evaluation study; already public via Zenodo DOI
  10.5281/zenodo.23319126). Approver recorded:
  "Tristen Pierson (owner authorization DN-012)". Subject:
  "Medicine and Health Sciences" (resolved by exact text).
- Created: project **dvrew** ("Tekmerion audit bundle —
  spec002-phase7-evaluation"), components registration `rfu23`,
  evidence `g3a4e`, verification `nhzky`, verdicts `cz82m`, record
  `6vwhq`; **13 files uploaded** (the bundle's full mapped set);
  `evidence/content/` recorded absent (the bundle has no content
  files). One draft; one registration submitted: **h94bf**.
- Finalize read the record back: `reviews_state: "initial"`,
  `pending_registration_approval: true`, `public: false`. Per the
  state machine established on the embargo test object, the deposit
  correctly refused to issue a receipt: **the deposit is not complete**
  until the provider finalizes the record (admin approval through
  OSF's own channel — the approval email link — or the provider's
  approval window lapsing).

Subsequent observation (same day, minutes later):

- Authenticated `GET /v2/registrations/h94bf/` returns **HTTP 410**,
  "The requested registration is no longer available"
  (`flagged_content: false`), and `GET /v2/nodes/dvrew/registrations/`
  returns an empty list. The embargo test registration (kcysa) could
  not be re-checked at the same time — the sandbox egress proxy was
  in one of its outage windows (all-host timeouts), and the runtime
  fetcher was unavailable for an independent public read.
- The Phase 7 study directory is byte-identical before/after the
  deposit: 30 files, SHA-256 sets equal
  (`study-dir-hashes-before.json` / `study-dir-hashes-after.json`).

Status: **open.** The registration's fate (approval-window mechanics
vs withdrawal vs a provider-side removal) must be read from the
provider's own record — the project log (`/v2/nodes/dvrew/logs/`) and
a re-fetch of both registrations — once the egress path is reliable.
No conclusion is recorded here beyond the observations above, and no
second registration has been created: the deposit state names h94bf,
and any re-run resumes against it rather than duplicating it.
