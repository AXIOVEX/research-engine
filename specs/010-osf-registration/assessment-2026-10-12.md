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
