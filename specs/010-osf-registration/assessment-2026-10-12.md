# Spec 010 — OSF Registration — assessment record, 2026-10-12

## after_specify (claims bundle v0.1.0)

Claims-first bundle: 8 claims (CLM-010-01…08), all `draft`, evidence =
the spec's own asserted design decisions only. Assessed with AEE engine
1.0.4 (`aee assess`, threshold 0.70), phase `after_specify`:
**outcome `iterate` — all 8 claims at 0.481, below threshold**, 15 failure
modes found. That is the honest specify-time state: nothing is built, no
provider behavior has been observed, and no claim is scored as if it had.
Build proceeds under DN-012 (the workstream authorization is the owner's
ratification, not the assessor's score); claims move only on shipped-test
and live-fetch evidence at after_implement.

Full assessor output: `aee-assessment.json` (this directory; regenerated
at after_implement).

## after_implement (claims bundle v0.2.0)

Built: `src/tekmerion/osf_deposit.py` (transport + deposit action +
`verify_osf_anchor`) and `tests/test_osf_deposit.py` (8 tests; full
suite 230 passed locally). Live work on the owner's OSF account: the
embargo demonstration (T-P2) and the T-P4 demonstration deposit on the
Phase 7 evaluation study (project `dvrew`, 13 files, registration
`h94bf` submitted). Assessed with AEE engine 1.0.4, phase
`after_implement`: **outcome `clarify`** — six claims at 0.98–1.00 /
supported (CLM-010-01, 02, 03, 04, 06, 08); **CLM-010-05 and
CLM-010-07 at 0.25 / partially_supported**, held there by
contradicting-direction residue evidence recorded in the bundle
itself: both live registrations sit in OSF's admin-approval window,
which the token API cannot complete (review-actions HTTP 409 —
unmoderated provider; schema-response approval HTTP 403 — account
"not a pending approver"); approval runs through OSF's email-link
channel. No live receipt has issued, and the public verification is
outstanding. The demo registration additionally read HTTP 410 /
absent from the project list on re-fetch (see
`records/demo-deposit-observation.md` — recorded as an open
observation, not explained away; sandbox egress outages prevented
further provider reads at build exit).

Provider behaviors established live and now encoded in the transport:
child nodes require a category; WaterButler folder creation needs
chunked empty-body framing through this egress (411/413 otherwise);
registration create fields as the provider's validation names them;
subjects required on the draft (caller-named, resolved by exact
text); embargo requires `lift_embargo` as a datetime; pending
records are resumable non-final states, never anchors.

## T-P4b finalize (claims bundle v0.3.0) — the demonstration completes

The narrative, in order (full detail:
`records/demo-deposit-observation.md`):

1. **h94bf died at the provider.** The build exit left the demo
   registration (`h94bf`) reading HTTP 410 with no explanation. The
   owner's forwarded OSF failure email supplied the cause from the
   provider itself: OSF's registration archive/copy step errored
   ("errors copying files to the registration. Our development team
   is investigating"). The project `dvrew`, its five components, and
   the 13 uploaded files were never harmed — only the registration
   object died.
2. **84dk7 replaced it by resume, not by a new deposit.** A resume
   run against the recorded state treated the 410 as a dead
   registration and submitted a fresh registration from the intact
   project: **84dk7**, stage `submitted`,
   `pending_registration_approval: true`.
3. **Approval completed 2026-10-12 via OSF's email-link channel**
   (the coordinator's browser approval, ~11:35 EDT; the token API
   cannot perform it — 409/403 at build). The record then read
   final: `reviews_state: "accepted"`, `revision_state: "approved"`,
   public, `date_registered: 2026-10-12T15:21:45Z`. Registration
   **DOI 10.17605/OSF.IO/84DK7** — https://osf.io/84dk7/.
4. **Receipt issued.** The finalize re-run (T-P4b, this record)
   re-fetched 84dk7, read finality from the fetched record
   (`records/demo-registration-final.json`), resumed against the
   existing registration (`already_existed: true` — no second
   registration), and issued the receipt:
   `records/demo-receipt.json` (mechanism `osf`; root `7c277327…`;
   bundle hash `a325a09a…`; registration hash `977c1db1…`;
   anchored_at `2026-10-12T15:21:45.605580`; approver "Tristen
   Pierson (owner authorization DN-012)"; embargoed false). The
   deposit state is at stage `complete`.
5. **Public verification passed.** `verify_osf_anchor` on an
   unauthenticated fetch returned `ok: true`
   (`records/demo-verification.json`): anchor values stated in the
   registration record; component structure and per-component file
   sets match the mapping exactly; contributor matches the mapping
   creator. (One earlier attempt failed on a sandbox-egress HTTP
   502 — a proxy error page, not an OSF response; recorded in the
   observation record, re-run passed.)
6. **The frozen study is untouched.** The Phase 7 study directory
   hashes after finalize equal the before/after sets (30 files;
   `records/study-dir-hashes-finalize.json`).

Claim movement (bundle v0.2.0 → v0.3.0): **CLM-010-05
partially_supported → supported** — its build-exit contradicting
residue (no live receipt; public verification outstanding; h94bf's
fate unresolved) is retained in the bundle as explicitly superseded
evidence, replaced by the issued receipt and the passed public
verification. One factual correction rides along in CLM-010-03's
evidence (the demo state now names 84dk7, not the dead h94bf); its
status and basis are unchanged. **CLM-010-07 remains
partially_supported**: the embargo test registration `kcysa` still
awaits its own admin approval through OSF's channel — untouched by
this finalize, by design. Re-assessed with AEE engine 1.0.4, phase
`after_implement`, threshold 0.70: **outcome `clarify`** (one claim
below threshold: CLM-010-07) — seven claims at 0.98–1.00 /
supported; **CLM-010-05 at 1.00 / supported**; CLM-010-07 at 0.25 /
partially_supported. Full assessor output: `aee-assessment.json`
(regenerated).

## kcysa close-out (claims bundle v0.4.0) — Spec 010 closes

The one claim T-P4b deliberately left open completes, through the
same channel that completed the demo registration:

1. **Approval completed 2026-10-12 via OSF's email-link channel.**
   The embargo test registration `kcysa` sat in OSF's approval
   window from build exit: its embargo terms were accepted and
   recorded by the provider, but OSF takes an embargo into effect
   only on admin approval, and that approval is not performable
   through the token API (409/403 at build). On the owner's
   decision (2026-10-12), the coordinator's guarded browser task
   followed the admin-notification token link in the owner's Gmail
   (~14:27 EDT) and approved the embargo. The OSF page then read:
   "Embargoed registration — This registration is embargoed. It
   will remain private until Mon Oct 11 2027" — the EDT display of
   the 2027-10-12T00:00:00Z embargo end as set. The "End embargo
   early" button was **not** clicked; the embargo runs to its set
   end date. Registrations `84dk7` and project `dvrew` were
   untouched.
2. **The state is verified from the provider's own record.**
   An authenticated re-fetch of `kcysa` through the OSF API (the
   Spec 010 machinery, `tekmerion_osf.py get-registration`) shows:
   `embargoed: true`, `embargo_end_date: 2027-10-12T00:00:00Z`
   (as set), `public: false`, `pending_embargo_approval: false`,
   `reviews_state: "embargo"`, `revision_state: "approved"`
   (`records/embargo-test-verification.json`, with the
   build-exit state recorded alongside for comparison). An
   unauthenticated fetch of the same record returns HTTP 401 —
   the registration is not publicly fetchable while the embargo
   runs, as expected.
3. **That is exactly the showing CLM-010-07 and its falsifier
   F-010-7 demand**: embargo support is claimed only on a
   fetched-back test registration record showing `embargoed =
   true` and the embargo end date as set. The claim's text
   required the demonstration, not an assertion; the
   demonstration is now complete end to end.

Claim movement (bundle v0.3.0 → v0.4.0): **CLM-010-07
partially_supported → supported** — its build-exit contradicting
residue (the fetched record read `embargoed: false` with
`pending_embargo_approval: true`) is retained in the bundle as
explicitly superseded evidence, per the CLM-010-05 precedent at
T-P4b, replaced by the approval readback and the authenticated
verification record. No other claim's text, evidence, or status
changed. Re-assessed with AEE engine 1.0.4, phase
`after_implement`, threshold 0.70: **outcome `iterate`** as
computed (15 failure modes; the bundle outcome is recorded as
computed, not rounded up) — **all 8 claims supported, 0 below
threshold**; CLM-010-07 at **1.00** (contradiction penalty 0);
the other seven at 0.98–1.00, unchanged. (The assessor exited 1
while writing a valid assessment — the standing quirk observed at
E3/E4; scores were verified by an identical re-run reproducing
every score exactly.) Full assessor output: `aee-assessment.json`
(regenerated).

**Spec 010 final state: 8/8 claims supported, all at the checked
stage** (DN-010: checking, not settlement — every live read-back
here is the author's own runs against the provider's record).
The embargo itself runs until 2027-10-12T00:00:00Z, when OSF
lifts it automatically; nothing in this close-out shortens,
extends, or otherwise touches it, and no further OSF writes were
performed by the verification (read-only fetch).
