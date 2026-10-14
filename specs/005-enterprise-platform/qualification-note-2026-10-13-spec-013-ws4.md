# Spec 005 — Qualification Note (2026-10-13): Spec 013 WS-4 platform authority remediation

**What this note is.** On 2026-10-13 an adversarial review (red team) of the
shipped platform found thirteen ways the service layer's authority rules were
weaker than this spec's own text states. Spec 013 (WS-4) fixed them in
`src/tekmerion/platform/`. This note qualifies the affected Spec 005 claims:
the claims' *statements* were correct as designed, but as of the Spec 005
build several of them held only at one surface (sign-in, the study-append
gate, the named export path) and not at the service layer as a whole. From
this remediation forward they hold at the service layer. Nothing in Spec
005's frozen claims bundle or its assessments is edited by this note; the
affected claims are named below for re-assessment.

**Form of the record.** Probes are cited by their red-team identifiers
(rt-c p01–p17). Each fix is covered by a ported regression test in
`tests/test_e7_redteam_platform.py`, verified failing against the
pre-remediation code and passing after it. The SAML, OIDC, and SCIM
batteries that already held (p13–p15) and the custody/key-storage/receiver
hygiene checks (p18) were re-run as regression tests and still hold.

## The qualifications, claim by claim

- **CLM-005-03 (every append is signed by an enrolled key) — qualified for
  the API-key path.** A bearer API key with an adjudicator-class scope could
  issue a verdict with no enrolled key, no signature, and no session (p04).
  Verdict-class appends are now refused on the API-key path outright
  (CLM-013-15); the enrolled-key + fresh-step-up rule holds on every path.
- **CLM-005-27 (MFA/step-up line) — held only at sign-in and the append
  gate.** Admin-plane mutations (role grants and revocations, IdP
  configuration on both the tenant and provisioning paths, API-key issuance,
  break-glass policy declaration and revocation) required only a valid
  session and the role — no step-up (p02), and a password-only session
  could perform them under a require-MFA policy (p01). These actions now
  require MFA evidence (where the actor's tenant policy requires MFA) and a
  fresh step-up, enforced at the service layer (CLM-013-16, CLM-013-17).
- **Step-up freshness (Spec 005 §2/§3) — was caller-asserted.** `step_up`
  accepted any ID token whose nonce matched a caller-chosen value, and never
  checked `auth_time`; a captured token could be replayed within its
  lifetime (p03). Step-up now requires a server-issued, single-use challenge
  (`begin_step_up`, mirroring the existing SAML step-up) and checks
  `auth_time` against the tenant's freshness window (CLM-013-18).
- **Grant plane separation — self-grants were possible.** A tenant admin
  could grant themselves the adjudicator role and then act on it (p05).
  A grant whose grantor and grantee are the same identity is now refused
  for any role the grantee does not already hold — the adjudicator case by
  name, and self as counterparty everywhere (CLM-013-19). Re-granting a
  role already held remains the recorded no-op it was.
- **CLM-005-04 (revocation semantics) — revocation was self-reversible for
  non-adjudicators.** The T522 countersign rule covered adjudicators only;
  any other holder could re-enroll the identical revoked public key alone
  and resume appending (p06). A revoked or closed public key is now burned
  for every role: re-enrolling that key requires a tenant-admin
  countersign, and the countersigned path exists for that case for all
  roles (CLM-013-20). Enrolling a *new* key is unchanged.
- **Key enrollment — small-order keys were enrollable.** A public key
  outside the prime-order subgroup (the identity point in the probe) makes
  the verification equation forgeable, and enrollment accepted it (p07).
  Enrollment now refuses such keys by name, and the append gate refuses
  them likewise (CLM-013-21).
- **CLM-005-10 / CLM-005-11 (break-glass named invokers; tenant
  isolation) — invoker roles were evaluated as a cross-tenant union.** An
  identity holding an invoker role only in another tenant could mint a
  break-glass session in the target tenant, and `break_glass_act` required
  no credential at act time — the bare session id was a bearer token (p09).
  Each declared invoker role is now checked in its own scope: a tenant
  role counts only as granted in the target tenant's ledger, the platform
  role only on the platform plane (a tenant's declaration may still name
  the platform plane, as Spec 005's own batteries exercise); roles from
  other tenants count for nothing. Acting requires the invoker's own
  session credential at act time (CLM-013-22).
- **CLM-005-08 (authenticated reads) — four reads were callable with no
  credential at all:** break-glass state, pending deliveries, active
  holds, residency pins (p10). All four now require an authenticated
  identity authorized for the scope (audit access for tenant reads; the
  platform plane for the deployment-wide views); tenant-plane callers see
  only their own tenant's pending deliveries (CLM-013-23).
- **CLM-005-17 (legal-hold semantics) — the hold bound only the named
  export path.** The break-glass audit-export action returned the full
  tenant ledger during an active hold (p11). The hold is now consulted on
  that path too; the platform plane's export-under-hold allowance does not
  extend to it (CLM-013-24).
- **CLM-005-29 (SPRS-input completeness) — evidence links were checked
  for presence only.** Assertion-shaped values moved the computed score
  (p12). An evidence link must now be a reference (a single token, not
  prose); a link claiming a platform-recorded target — a POA&M item, an
  audit export, a legal hold, or an anchored document row — must resolve
  in the same scope's ledger, with the anchor naming the requirement it
  evidences, and is refused at write time otherwise. The computed record
  now labels every input's link as *resolved*, *operator-attested* (the
  organization's own evidence reference, which the platform cannot
  verify), or *unresolved*, and lists unresolved links as a named check
  failure alongside completeness and agreement. Operator states remain
  the organization's own statements, as this spec designed; what changed
  is that they can no longer be entered as bare assertions or dressed as
  platform records, and the two kinds are never presented as the same
  (CLM-013-25).
- **CLM-005-12 / CLM-005-17 — `create_tenant` silently replaced an
  existing tenant's record,** resetting its residency pin, CUI marking,
  and policy under its live ledger, with no migration flow and no hold
  check (p16; the duplicate-check absence was first recorded by the E5
  console pass). Creating an existing tenant id is now a typed,
  ledgered refusal; nothing is reset (CLM-013-26).
- **Deployment-ledger integrity — unknown-tenant SCIM failures were an
  unbounded append channel.** Each failure against a nonexistent tenant id
  appended to the deployment ledger, at whatever rate an unauthenticated
  caller chose (p17). Recording is now capped deployment-wide
  (10 per minute) *before* any append; past the cap the request is
  rate-limited and nothing is recorded (CLM-013-27).

## What did not change

Session lifetimes (T530), the step-up scope at the adjudicator key gate,
the SAML/OIDC/SCIM protocol behavior, and every HELD defense the red team
verified remain as recorded. Frozen bundles, issued verdicts, and Spec
005's own claims bundle and assessments are untouched.
