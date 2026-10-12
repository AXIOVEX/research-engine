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

Status: **open, narrowed.** Follow-up reads once the egress path
recovered (same day):

- The project log (`/v2/nodes/dvrew/logs/`) records exactly two
  events — `project_created` (14:52:59Z) and `registration_initiated`
  (14:56:10Z). **No cancellation, withdrawal, or removal event
  exists.** The project and its components are intact.
- The embargo test registration `kcysa` (pending embargo approval)
  remains fetchable; `h94bf` (pending *registration* approval)
  consistently reads 410 and is absent from the project's
  registration list.

The observables are consistent with the pending record being held in
OSF's approval queue — served in the immediate post-submit read,
then not served until an admin approves through OSF's email-link
channel — and inconsistent with any removal: nothing in the
provider's own log removes it. That mechanism is recorded as the
leading explanation, not as established fact; the discriminating
event is the approval itself (T-P4b): if `h94bf` becomes a served,
final registration after the admin approval, the explanation holds;
if it does not, the record here is wrong and must be revisited. No
second registration has been created: the deposit state names h94bf,
and any re-run resumes against it rather than duplicating it.

Follow-on observation, 2026-10-12 (coordinator, on the owner's
forwarded OSF failure email):

- OSF's email ("Issue registering [/dvrew/]Tekmerion audit bundle —
  spec002-phase7-evaluation … errors copying files to the
  registration. Our development team is investigating") confirms the
  cause server-side: registration **h94bf** died at the provider's
  archive/copy step. Re-verified live at fix time: `GET
  /v2/registrations/h94bf/` → HTTP 410 "no longer available"
  (`flagged_content: false`); `GET /v2/nodes/dvrew/registrations/`
  → empty. The project, its five components, and the 13 uploaded
  files were never harmed — only the registration object died.
- Fix executed by resume against the existing state (no second
  project, no re-upload): the deposit correctly treated the 410 as a
  dead registration, created a fresh submission from the intact
  project, and recorded the replacement in
  `demo-deposit-state.json`: **registration 84dk7**, stage
  `submitted`, `reviews_state: "initial"`,
  `pending_registration_approval: true` — the same honest non-final
  state as the original run. Admin approval runs through OSF's
  email-link channel (or the approval window lapsing); the deposit
  completes only when the record is final and a resume re-run issues
  the receipt. Until then 84dk7 must not be cited as an anchor.

Finalize observation, 2026-10-12 (T-P4b completion):

- Admin approval completed through OSF's email-link channel (the
  coordinator's browser approval, ~11:35 EDT). The registration was
  re-fetched through the transport and finality read from the record
  itself (`records/demo-registration-final.json`): `reviews_state:
  "accepted"`, `revision_state: "approved"`, `public: true`,
  `pending_registration_approval: false`, `withdrawn: false`,
  `date_registered: 2026-10-12T15:21:45Z`, registered from project
  `dvrew`. Registration DOI: **10.17605/OSF.IO/84DK7**
  (https://osf.io/84dk7/).
- The deposit resume/finalize re-ran against this state file: it
  resumed against the existing registration (`already_existed:
  true` — no second registration, no new project, no re-upload) and
  issued the receipt, now embedded in this state file at stage
  `complete` and saved standalone as `records/demo-receipt.json`
  (mechanism `osf`; root `7c277327…`; bundle hash `a325a09a…`;
  registration hash `977c1db1…`; anchored_at
  `2026-10-12T15:21:45.605580`; approver "Tristen Pierson (owner
  authorization DN-012)"; embargoed false).
- Public verification (`verify_osf_anchor`, unauthenticated fetch)
  **passed** (`records/demo-verification.json`): the registration
  record states the bundle's anchor values; the project structure
  matches the component mapping exactly (five components, the 13
  mapped files per component); the contributor (Tristen Pierson)
  matches the mapping's creator. One earlier verify attempt failed
  on a sandbox-egress HTTP 502 (proxy error page, not an OSF
  response); the re-run passed — the transient is recorded here,
  not edited away.
- The Phase 7 study directory remains byte-identical (30 files;
  `records/study-dir-hashes-finalize.json` equals the before/after
  sets). 84dk7 is now final and may be cited as the demonstration's
  OSF anchor.
