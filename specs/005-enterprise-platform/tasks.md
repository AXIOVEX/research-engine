# Spec 005 — Tasks

**Date:** 2026-10-12 · Status: `[ ]` open · `[!]` gated · `[x]` done. All build tasks follow the claims-first assessment of 2026-10-12 (`aee-assessment.json`, outcome **gather_evidence**) and the owner's G-ENT-1 gate.

## Gates

- [x] Claims first: CLM-005-01…22 authored + assessed at `after_specify` before any design code (`aee-claims.json` v0.1.0; `assessment-2026-10-12.md`).
- [!] **G-ENT-1 (owner):** go-ahead on this spec before any E1 implementation code (DN-011; Spec 002 G1 precedent).
- [!] No spend, no new accounts: hosted infra, KMS, or IdP test-tenancy costs return to the owner individually (DN-003 rule).
- [!] Article XIV: no admin-console code before T534-WF (rendered wireframes approved).
- [!] DN-005 invariant: no task may introduce a delete/mutation path for any ledger, in any plane.

## Phase E1 — Identity core (OIDC + key binding + service-layer RBAC)

- [ ] T501 Internal identity model `(tenant, issuer, subject)` + attribute mapping; protocol-neutral downstream of the boundary.
- [ ] T502 Per-tenant IdP configuration records (OIDC first) as platform-ledger events; secrets in the secrets store, never in config payloads.
- [ ] T503 OIDC relying party: discovery, authorization code + PKCE (S256 required), JWKS rotation; F-005-01 audit — no local credential path exists.
- [ ] T504 Key enrollment ceremony: authenticated session, proof of possession (nonce signature), enrollment event to the platform audit ledger.
- [ ] T505 Key registry: rotation (superseding enrollment), revocation, multi-key per identity; pre-revocation signatures keep verifying (F-005-04).
- [ ] T506 Custody modes: self-custody signing path + delegated (KMS/HSM) signing with `custody` recorded in append metadata; step-up required for verdict-class signing in both modes.
- [ ] T507 Service-layer append gate: appends accepted only under an enrolled, unrevoked key bound to the session identity (F-005-03).
- [ ] T508 Authorization service: WS6 §1 matrix as policy; deny-by-default; tenant context from session only; decision records for mutations.
- [ ] T509 Admin planes: tenant-admin and platform-admin roles disjoint from study roles and each other (F-005-09 model tests).
- [ ] T510 Platform audit ledger core (Axiomere): admin-action events — IdP config, grants, key lifecycle — signed, chained, checkpointable.
- [ ] T511 API keys / service accounts: hashed storage, prefix IDs, scopes ⊆ WS6 matrix, expiry ≤ 1y, revocation; actions attributed + ledgered (F-005-18).
- [ ] T512 Phase exit: phase claims re-assessed; Spec 002 battery green unchanged (CLM-005-20).

## Phase E2 — SAML 2.0

- [ ] T513 SAML SP: Web Browser SSO profile, SP- and IdP-initiated; per-tenant metadata import + validation.
- [ ] T514 Assertion validation: signatures required; wrong-IdP and unsigned assertions rejected (F-005-02 seeded defects).
- [ ] T515 Attribute mapping incl. `eduPersonPrincipalName` / `eduPersonScopedAffiliation`; mapping into the §2 identity model.
- [ ] T516 Shibboleth-class test IdP harness in CI (test tenant only; no external federation dependency).
- [ ] T517 Step-up parity for SAML sessions (verdict/admin actions); phase exit re-assessment + Spec 002 battery.

## Phase E3 — Provisioning & lifecycle (SCIM)

- [ ] T518 SCIM 2.0 server: Users create/update/deactivate; conformance-style cycle tests (F-005-06).
- [ ] T519 Group→role mappings: tenant-admin-approved mapping records only; no silent grants from group membership.
- [ ] T520 JIT provisioning: assertion-created identity, asserting tenant only, zero study roles until a grant event (F-005-07).
- [ ] T521 Deprovisioning pipeline: deactivation event → sessions revoked, keys closed to new appends, next-request effective (F-005-05, both halves).
- [ ] T522 Key-lifecycle completion: adjudicator re-enrollment with tenant-admin countersign; deprovisioned-identity key sweep.
- [ ] T523 Identity directory: PII off-ledger under ordinary data controls; random actor IDs; directory erasure path that never touches a chain.
- [ ] T524 Lifecycle admin API (no console yet): tenant admins manage membership, grants, revocations — all as platform-ledger events.
- [ ] T525 Phase exit: re-assessment + Spec 002 battery.

## Phase E4 — Tenancy hardening + isolation battery

- [ ] T526 Tenant scoping at the data-access layer: every entity tenant-bound; tenant context never taken from request parameters.
- [ ] T527 Isolation battery: tenant A credential vs tenant B resources across every endpoint class — uniform not-found, zero B bytes (F-005-11).
- [ ] T528 Cross-plane battery: platform-admin cannot sign study verdicts; tenant-admin cannot cross tenants (F-005-09).
- [ ] T529 Break-glass: per-tenant declared policy, dual authorization, time box, alarm to tenant admins + security log, session-marked audit events, automatic post-use review item (F-005-10).
- [ ] T530 Session/transport baseline: cookie attributes, idle/absolute lifetimes, TLS-only, header set, per-tenant 429 limits — battery per F-005-19's enumeration.
- [ ] T531 Webhook egress: signed deliveries (HMAC-SHA256 or Ed25519), replay window, retry/backoff, delivery audit events; reference receiver + rejection tests (F-005-21).
- [ ] T532 Reconciliation join: platform events ↔ study appends on the identity↔key binding; auditor walk + no-cross-identity test (F-005-22).
- [ ] T533 Phase exit: re-assessment + Spec 002 battery. **Pilot gate (G2 analog) is evaluated here:** isolation battery green + platform audit export demonstration scheduled in E6.

## Phase E5 — Admin console (wireframe-gated)

- [!] T534-WF **Wireframe gate (owner):** console screens (tenant, IdP, user, role, key, audit, break-glass log) added to `docs/wireframes/` as full-fidelity renders; owner approves rendered screenshots at desktop + mobile (Article XIV). No T535+ work before this gate.
- [ ] T535 Console shell + tenant management, as a client of the service APIs only.
- [ ] T536 IdP configuration screens (OIDC + SAML) with metadata validation feedback.
- [ ] T537 User, role-grant, and lifecycle screens (grant/revoke/deactivate as event-issuing actions).
- [ ] T538 Key & binding screens: custody mode, enrollment/rotation/revocation state, countersign flows.
- [ ] T539 Audit viewer + export initiation; break-glass policy + session log screens.
- [ ] T540 Phase exit: rendered-UI vs approved-wireframe conformance screenshots; re-assessment + Spec 002 battery.

## Phase E6 — Compliance evidence + self-hosted shape

- [ ] T541 Residency pin: recorded tenant configuration (shape, region); pin change = export + anchor + migration event flow.
- [ ] T542 Platform audit export: Phase 5 bundle pattern (manifest, hashes, standalone verifier) for platform + per-tenant ledgers.
- [ ] T543 Anchored demonstration: a platform audit export deposited/anchored and verified against the public record (AR-1 pattern, platform plane).
- [ ] T544 SOC 2 readiness mapping document: criteria → machinery → claim IDs; every entry resolvable (F-005-16); labeled readiness, never certification.
- [ ] T545 Retention & legal hold: hold = marker event + export + anchor + access restriction; off-ledger retention schedules only; zero deletion paths (F-005-17 audit).
- [ ] T546 Self-hosted packaging: single-tenant deployment of the same codebase/role model; institution KMS option; upgrade path; shape-parity battery vs hosted (F-005-12).
- [ ] T547 Wording sweep: product surfaces checked against CLM-005-16 (no certification claims; FERPA/GDPR as constraints only).
- [ ] T548 Final re-assessment of all 22 claims at `after_implement`; Spec 002 battery green; spec close-out record.
