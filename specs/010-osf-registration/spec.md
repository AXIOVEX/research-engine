# Spec 010 — OSF Registration (Pilot Workstream, DESIGN §4)

- **Date:** 2026-10-12 · **Status:** Specified 2026-10-12 (claims first; assessed at after_specify before any code). Build follows in this same spec package.
- **Governs:** pilot DESIGN §4 (`docs/pilot/DESIGN.md`), tasks T-P1…T-P4. **T-P5 (UI surfacing) is excluded** — Article XIV wireframe gate, untouched by this spec.
- **Authorization:** DN-012 (owner ratification, 2026-10-12): the OSF registration workflow is in pilot scope, sequenced before partner onboarding; DN-008's reserved decision is discharged. Spend: standing G4 only (OSF is free; the owner's OSF account token is a free key on an owner account).
- **Starting point:** `tekmerion.deposit.osf_metadata` already produces the deposit-ready OSF document from a bundle manifest (title, description = the anchor statement, category, tags, creators, the WS4 §4 component mapping, `anchor_values`). What does not exist before this spec: any OSF transport, any registration action, any OSF receipt or verification path. The executable deposit in `tekmerion.deposit` targets Zenodo only.

## Function

Give Tekmerion an OSF anchor alongside the Zenodo anchor: from a verified audit
bundle, create an OSF project whose components and files follow the
`osf_metadata` component mapping, then take an OSF **registration** (the
registry snapshot) of that project at the study's frozen state, with the
bundle's anchor values (Merkle checkpoint root, bundle hash, registration
hash) stated in the registration itself. Record the receipt; verify it later
by fetching the public OSF record independently and comparing the stated
values — the same read-back standard as AR-1.

## Design decisions (recorded here; ambiguities in DESIGN §4 resolved in plan.md)

- **Transport shape.** A dedicated module `src/tekmerion/osf_deposit.py`,
  following `deposit.py`'s patterns: stdlib `urllib` only; serial requests
  with ≥ 1 s spacing; an HTTP 429 is a stop, never a retry; every provider
  error surfaces verbatim (status + body excerpt) inside `DepositError`.
  Auth is the caller's: a token (env `OSF_ACCESS_TOKEN`) or an `auth_hook`
  decorating each request — the same seam `ZenodoTransport` already exposes
  for the operator's credential-vault pattern. No credential value is read,
  stored, or logged by this module beyond what the caller injects per request.
- **The mapping is the contract** (DESIGN §4.2.2). Project title, description,
  category, tags, the component set, and each component's file set are
  computed from `osf_metadata(manifest)` at deposit time. No caller-supplied
  title or description reaches the OSF record. Bundle-relative paths are
  preserved inside components (folders created in OSF storage where a mapped
  path is nested, e.g. `ledger/study.axmr`). A mapped path absent from the
  bundle (e.g. `evidence/content/` when no content files exist) is recorded
  as absent in the deposit record — never silently dropped, never fatal.
- **Registration schema.** "Open-Ended Registration", resolved **by name** at
  deposit time via the OSF API (`/v2/schemas/registrations/`), never a
  hardcoded GUID. Its summary field carries the anchor statement verbatim —
  that is how the registration itself states the anchor values
  (DESIGN §4.2.3). Subjects are set on the draft if the provider requires
  them for submission; the requirement, if hit, is recorded.
- **Approval gate.** The mechanical adjudicator-approval gate of
  `deposit_bundle` applies identically (DESIGN §4.2.1): no named approver →
  refused; a bundle that does not verify standalone → refused; a bundle with
  no freeze binding (no `registration_hash` / `checkpoint_root` in its
  manifest) → refused as unfrozen. Refusals happen before any OSF object is
  created.
- **Submission state.** A completed deposit is a **submitted** registration,
  not a draft: public/immediate by default; with an embargo end date it is
  submitted under embargo. Where the provider interposes an admin-approval
  step, the deposit is complete only when the fetched record is final —
  it never reports "submitted" for a record the provider still shows as
  pending. *Correction (2026-10-12, from the live build): the approval
  step is not performable through the token API at all — plain OSF is
  unmoderated (review-actions refused, HTTP 409) and the depositing
  account is "not a pending approver" for the schema response
  (HTTP 403). Admin approval runs through OSF's own channel (the
  approval email link). A provider-held pending record is therefore a
  recorded, resumable non-final deposit state, and the finalize step
  raises with the observed state named rather than acting on it.*
- **Deposit state + idempotency.** Progress is persisted to a deposit-state
  JSON (caller-chosen path; for the demonstration, in this spec's records —
  never inside the bundle, never inside a frozen study directory). Before
  creating a draft registration, the action checks for an existing
  registration binding this bundle's `registration_hash` under the same
  schema — via the deposit state, and, when a project GUID is known, via the
  project's own registration list. A repeat run creates no second
  registration and reports the existing one's GUID + URL. Partial state
  (project created, registration failed) resumes from the state file; it is
  a recorded deposit state, never presented as an anchor (DESIGN §4.2.5).
- **Receipt.** Same shape discipline as the Zenodo receipt: mechanism `osf`,
  checkpoint root, bundle hash, registration hash, project GUID,
  registration GUID, registration URL (+ DOI if the provider issues one),
  `approved_by`, `anchored_at` (the record's `date_registered`), embargo
  state. For a live study, the receipt appends to the study ledger through
  the existing `tekmerion.deposit.record_anchor` (`anchor.recorded`) —
  that function is transport-agnostic. For the T-P4 demonstration the study
  is a frozen artifact and the receipt is recorded in this spec's records
  only (CLM-010-06).

## Requirements

- **CLM-010-01** (requirement): Every OSF-visible field of a deposit — project title, description, category, tags, the component set, each component's file set, and the registration's summary — is computed from `osf_metadata` of the deposited bundle's manifest. No code path accepts a caller-supplied title, description, or component structure for the record.
- **CLM-010-02** (requirement): The deposit refuses, before creating any OSF object, when `approved_by` is empty, when the bundle does not verify standalone, or when the bundle's manifest carries no freeze binding (missing `registration_hash` or `checkpoint_root`).
- **CLM-010-03** (requirement): Submission is idempotent: before creating a draft registration the action checks for an existing registration binding the same `registration_hash` under the same schema (deposit state first; the project's registration list when a project GUID is known), and a repeat attempt creates no second registration — it reports the existing registration's GUID and URL.
- **CLM-010-04** (requirement): Provider failures abort the action with the provider's actual HTTP status and response body carried in the error; an ambiguous create is never retried blind into a duplicate; partial progress is persisted to the deposit state and a later run resumes from it instead of starting over.
- **CLM-010-05** (requirement): A completed deposit returns a receipt (mechanism, root, bundle hash, registration hash, project GUID, registration GUID, URL/DOI, approver, anchored-at, embargo state), and `verify_osf_anchor` independently re-fetches the registration from the OSF API and passes only if the fetched record states the mapping's anchor values and the project structure matches the component mapping.
- **CLM-010-06** (requirement): The T-P4 demonstration modifies nothing in the Phase 7 study directory: every file's bytes are identical before and after (hashes recorded), and the registration references the study externally — the receipt lives in this spec's records, not in the frozen study's ledger or bundles.
- **CLM-010-07** (requirement): The embargo path is demonstrated, not asserted: a test registration created with an embargo end date is fetched back showing the embargoed state (not public, the embargo end date as set) before embargo support is claimed anywhere.
- **CLM-010-08** (requirement, scope): An OSF registration is an anchor and a discovery record, not a validation: it certifies that this bundle, stating these anchor values, was snapshotted at a point in time. It does not certify the study's verdicts, is not lane-2 acceptance of anything, and — because the OSF *project* remains editable after registration — anchor verification reads the values from the *registration* record, never from the live project.

## Non-goals

No UI (T-P5, Article XIV). No partner data — Axiovex-owned studies only. No
changes to the Zenodo path, to `osf_metadata`, or to any frozen artifact. No
OSF features beyond project + components + files + registration + receipt
verification (no forks, no collections, no preprint flows). No deletion
workflow: OSF registrations cannot be deleted, and this spec creates no
machinery that pretends otherwise (withdrawal is a provider action with its
own record, out of scope here).
