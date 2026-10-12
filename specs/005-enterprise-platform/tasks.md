# Spec 005 — Tasks

**Date:** 2026-10-12 · Status: `[ ]` open · `[!]` gated · `[x]` done. All build tasks follow the claims-first assessment of 2026-10-12 (`aee-assessment.json`, outcome **gather_evidence**) and the owner's G-ENT-1 gate.

## Gates

- [x] Claims first: CLM-005-01…22 authored + assessed at `after_specify` before any design code (`aee-claims.json` v0.1.0; `assessment-2026-10-12.md`).
- [!] **G-ENT-1 (owner):** go-ahead on this spec before any E1 implementation code (DN-011; Spec 002 G1 precedent).
- [!] No spend, no new accounts: hosted infra, KMS, or IdP test-tenancy costs return to the owner individually (DN-003 rule).
- [!] Article XIV: no admin-console code before T534-WF (rendered wireframes approved).
- [!] DN-005 invariant: no task may introduce a delete/mutation path for any ledger, in any plane.

## Phase E1 — Identity core (OIDC + key binding + service-layer RBAC)

- [x] T501 Internal identity model `(tenant, issuer, subject)` + attribute mapping; protocol-neutral downstream of the boundary.
- [x] T502 Per-tenant IdP configuration records (OIDC first) as platform-ledger events; secrets in the secrets store, never in config payloads.
- [x] T503 OIDC relying party: discovery, authorization code + PKCE (S256 required), JWKS rotation; F-005-01 audit — no local credential path exists. [CMMC §13.5: tenant IdP policy records required acr/amr (MFA); a session without MFA evidence cannot mutate or step up (CLM-005-27).]
- [x] T504 Key enrollment ceremony: authenticated session, proof of possession (nonce signature), enrollment event to the platform audit ledger.
- [x] T505 Key registry: rotation (superseding enrollment), revocation, multi-key per identity; pre-revocation signatures keep verifying (F-005-04).
- [x] T506 Custody modes: self-custody signing path + delegated (KMS/HSM) signing with `custody` recorded in append metadata; step-up required for verdict-class signing in both modes.
- [x] T507 Service-layer append gate: appends accepted only under an enrolled, unrevoked key bound to the session identity (F-005-03). [CMMC: gate refusals are audit events (T550).]
- [x] T508 Authorization service: WS6 §1 matrix as policy; deny-by-default; tenant context from session only; decision records for mutations.
- [x] T509 Admin planes: tenant-admin and platform-admin roles disjoint from study roles and each other (F-005-09 model tests).
- [x] T510 Platform audit ledger core (Axiomere): admin-action events — IdP config, grants, key lifecycle — signed, chained, checkpointable. [CMMC §13.4: the AU event classes of T550 are in scope from the first commit, not retrofitted.]
- [x] T511 API keys / service accounts: hashed storage, prefix IDs, scopes ⊆ WS6 matrix, expiry ≤ 1y, revocation; actions attributed + ledgered (F-005-18).
- [x] T549 [CMMC] Crypto inventory (E1): every cryptographic operation in the platform plane listed in `specs/005-enterprise-platform/crypto-inventory.md` with algorithm, implementation, and FIPS validation status; an unlisted operation is a defect (CLM-005-25). No FIPS claim anywhere it does not exist.
- [x] T550 [CMMC] AU event-class completeness (E1): the §3.3.1/§3.3.2 classes — account creation/modification, authentication successes AND failures, authorization decisions incl. denials, admin actions, key lifecycle, session lifecycle, API-key lifecycle — each with the AU content set (actor, type, timestamp, target, outcome); sweep test = every E1 mutation/auth path produces its event (CLM-005-26).
- [x] T512 Phase exit: phase claims re-assessed; Spec 002 battery green unchanged (CLM-005-20).

## Phase E2 — SAML 2.0

- [x] T513 SAML SP: Web Browser SSO profile, SP- and IdP-initiated; per-tenant metadata import + validation.
- [x] T514 Assertion validation: signatures required; wrong-IdP and unsigned assertions rejected (F-005-02 seeded defects).
- [x] T515 Attribute mapping incl. `eduPersonPrincipalName` / `eduPersonScopedAffiliation`; mapping into the §2 identity model.
- [x] T516 Shibboleth-class test IdP harness in CI (test tenant only; no external federation dependency).
- [x] T517 Step-up parity for SAML sessions (verdict/admin actions); phase exit re-assessment + Spec 002 battery.

## Phase E3 — Provisioning & lifecycle (SCIM)

- [x] T518 SCIM 2.0 server: Users create/update/deactivate; conformance-style cycle tests (F-005-06).
- [x] T519 Group→role mappings: tenant-admin-approved mapping records only; no silent grants from group membership.
- [x] T520 JIT provisioning: assertion-created identity, asserting tenant only, zero study roles until a grant event (F-005-07).
- [x] T521 Deprovisioning pipeline: deactivation event → sessions revoked, keys closed to new appends, next-request effective (F-005-05, both halves).
- [x] T522 Key-lifecycle completion: adjudicator re-enrollment with tenant-admin countersign; deprovisioned-identity key sweep.
- [x] T523 Identity directory: PII off-ledger under ordinary data controls; random actor IDs; directory erasure path that never touches a chain.
- [x] T524 Lifecycle admin API (no console yet): tenant admins manage membership, grants, revocations — all as platform-ledger events.
- [x] T525 Phase exit: re-assessment + Spec 002 battery.

## Phase E4 — Tenancy hardening + isolation battery

- [x] T526 Tenant scoping at the data-access layer: every entity tenant-bound; tenant context never taken from request parameters.
- [x] T527 Isolation battery: tenant A credential vs tenant B resources across every endpoint class — uniform not-found, zero B bytes (F-005-11).
- [x] T528 Cross-plane battery: platform-admin cannot sign study verdicts; tenant-admin cannot cross tenants (F-005-09).
- [x] T529 Break-glass: per-tenant declared policy, dual authorization, time box, alarm to tenant admins + security log, session-marked audit events, automatic post-use review item (F-005-10). [CMMC: break-glass use is an IR egress event class (T554).]
- [x] T530 Session/transport baseline: cookie attributes, idle/absolute lifetimes, TLS-only, header set, per-tenant 429 limits — battery per F-005-19's enumeration.
- [x] T531 Webhook egress: signed deliveries (HMAC-SHA256 or Ed25519), replay window, retry/backoff, delivery audit events; reference receiver + rejection tests (F-005-21). [CMMC: carries the IR security-event classes of T554.]
- [x] T532 Reconciliation join: platform events ↔ study appends on the identity↔key binding; auditor walk + no-cross-identity test (F-005-22).
- [x] T554 [CMMC] IR security-event classes (E4): authentication-failure bursts, break-glass use, revocation storms, audit-verification failures are first-class signed egress events over the T531 channel (CLM-005-30, IR half).
- [x] T533 Phase exit: re-assessment + Spec 002 battery. **Pilot gate (G2 analog) is evaluated here:** isolation battery green + platform audit export demonstration scheduled in E6.

## Phase E5 — Admin console (wireframe-gated)

- [!] T534-WF **Wireframe gate (owner):** console screens (tenant, IdP, user, role, key, audit, break-glass log) added to `docs/wireframes/` as full-fidelity renders; owner approves rendered screenshots at desktop + mobile (Article XIV). No T535+ work before this gate. — *Package delivered 2026-10-12: `docs/wireframes/console/` (10 screens, 20 rendered screenshots, README with screen→phase mapping + open questions Q1–Q8), branch `enterprise/e5-wireframes`. Gate NOT passed: owner approval of the renders is outstanding; the box stays unchecked until he approves.*
- [ ] T535 Console shell + tenant management, as a client of the service APIs only.
- [ ] T536 IdP configuration screens (OIDC + SAML) with metadata validation feedback.
- [ ] T537 User, role-grant, and lifecycle screens (grant/revoke/deactivate as event-issuing actions).
- [ ] T538 Key & binding screens: custody mode, enrollment/rotation/revocation state, countersign flows.
- [ ] T539 Audit viewer + export initiation; break-glass policy + session log screens.
- [ ] T540 Phase exit: rendered-UI vs approved-wireframe conformance screenshots; re-assessment + Spec 002 battery.

## Phase E6 — Compliance evidence (SOC 2 readiness + CMMC Level 2 support) + self-hosted shape

- [x] T541 Residency pin: recorded tenant configuration (shape, region); pin change = export + anchor + migration event flow.
- [x] T542 Platform audit export: Phase 5 bundle pattern (manifest, hashes, standalone verifier) for platform + per-tenant ledgers. [CMMC: POA&M register (T553) exports with it.]
- [x] T543 Anchored demonstration: a platform audit export anchored and verified standalone from the committed bundle (records/e6-audit-export-demonstration.md). [E6 completion note: executed under the phase's no-external-accounts/no-uploads boundary — the anchor is the ledger's audit.export_anchored record + the committed demonstration record; the public-deposit leg (AR-1/Zenodo pattern) was NOT executed and stands as recorded residue in the demonstration record, not as done.]
- [x] T544 SOC 2 readiness mapping document: criteria → machinery → claim IDs; every entry resolvable (F-005-16); labeled readiness, never certification. [CMMC: §13 framing sweep rides this task — no unqualified CMMC language (CLM-005-23).]
- [x] T545 Retention & legal hold: hold = marker event + export + anchor + access restriction; off-ledger retention schedules only; zero deletion paths (F-005-17 audit).
- [x] T551 [CMMC] CUI marking support: banner/footer marking fields in bundle manifest + HUMAN-README, populated from recorded study/tenant marking fields (CLM-005-28).
- [x] T552 [CMMC] SPRS self-assessment support: platform control states maintained in SPRS-input form — per-requirement state, DoD weighted deduction class for unimplemented requirements, evidence link; matrix/state agreement check (CLM-005-29).
- [x] T553 [CMMC] POA&M register: append-only register (items, affected requirements, milestones, status as events) in the platform plane, seeded with the §3.13.11 FIPS gap (CLM-005-30, POA&M half; CLM-005-25).
- [x] T546 Self-hosted packaging: single-tenant deployment of the same codebase/role model; institution KMS option; upgrade path; shape-parity battery vs hosted (F-005-12).
- [x] T547 Wording sweep: product surfaces checked against CLM-005-16 (no certification claims; FERPA/GDPR as constraints only).
- [x] T548 Final re-assessment of all claims at `after_implement` (31 claims — the task text's '22' predates the CMMC amendment's nine; all 31 re-assessed, bundle v0.7.0); Spec 002 battery green; spec close-out record.
