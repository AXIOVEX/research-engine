# Spec 005 — Enterprise Platform: identity, tenancy, administration

**Status:** DRAFT — claims first (this spec's `aee-claims.json` v0.1.0 assessed at `after_specify` 2026-10-12, outcome **gather_evidence**; see `assessment-2026-10-12.md`) · **Date:** 2026-10-12 · **Constitution:** v1.1.0 + Article XIV (DN-009, owner-approved 2026-10-12)
**Authority:** DN-011 (enterprise direction, adopted 2026-10-12) · DN-003 (deployment shapes) · DN-005 (append-only) · WS6 §1–§3 · Constitution Articles IV, IX, X, XII, XIII, XIV.
**Gate:** **No implementation code before the owner's G1-style go-ahead on this spec** (DN-011, mirroring the Spec 002 G1 precedent). Hosted-infrastructure choices that cost money return to the owner as their own decision (DN-003).
**Scope:** the platform plane that makes Tekmerion deployable by institutions — identity (SSO), provisioning, authorization, tenancy, administration, audit/compliance evidence, and the platform security baseline. The study plane (register, pipeline, verdicts, bundles) is Spec 002's and does not change except where §10 names a seam.

## 1. Purpose

Spec 002 built a defensible research record for one operator. Institutions cannot adopt it until the platform answers their questions: *our people sign in with our IdP; our admins manage membership; our auditors get evidence; nobody else's data is reachable; and none of this weakens the record.* This spec builds that plane — and holds it to the same discipline as the study plane: identity assertions end at the service boundary, authorization is mechanical, administrative acts are themselves signed records, and the compliance story claims only what exists (CLM-005-16).

## 2. Identity — OIDC and SAML 2.0, per tenant (CLM-005-01, CLM-005-02)

One internal identity model sits behind both protocols: an **identity** is `(tenant, issuer, subject)` plus mapped attributes (display name, email, affiliation). Everything downstream — authorization, key binding, audit — speaks only of identities, never of protocols.

- **OIDC (E1).** Relying-party support for the authorization code flow with PKCE (S256 required); per-tenant IdP configuration (issuer URL, client credentials held in the secrets store, attribute mapping); discovery via the issuer's `.well-known/openid-configuration`; JWKS fetched and rotated per issuer metadata. There is **no local password store and no local credential login** — the falsifier F-005-01 is a schema/API audit, not a penetration test.
- **SAML 2.0 (E2).** Service-provider support for the Web Browser SSO profile, SP- and IdP-initiated; per-tenant IdP metadata (entity ID, endpoints, signing certificates, attribute mapping — including `eduPersonPrincipalName` and `eduPersonScopedAffiliation` for Shibboleth/InCommon tenants). Assertions must be signed; an unsigned or wrongly-signed assertion is rejected, never repaired. Federation metadata aggregates (InCommon MDQ) are a v1.1 candidate (§11); v1 configures each tenant's IdP explicitly.
- **Step-up.** Verdict-signing and admin-plane actions require step-up authentication (tenant-configurable `acr`/`amr` policy, e.g. MFA at the IdP) regardless of protocol; a session that cannot step up cannot perform those actions.

## 3. Identity ↔ signing-key binding (CLM-005-03, CLM-005-04)

Article XIII: every append is signed with its actor's Ed25519 key. The enterprise layer governs *whose key counts*:

- **Enrollment.** In an authenticated (and, for adjudicator keys, stepped-up) session, the actor presents a public key and proves possession by signing a server nonce. The enrollment — identity, key fingerprint, custody mode, timestamp — is appended to the platform audit ledger (§8). An unenrolled key signs nothing the service will accept.
- **Custody modes** (the record distinguishes them; it never blurs them):
  - *Self-custody* — the private key never leaves the actor's device/secure enclave; appends are signed client-side. Strongest non-repudiation.
  - *Delegated custody* — the key lives in a KMS/HSM (platform-operated in the hosted shape, institution-operated self-hosted); signing happens server-side only inside an authenticated, authorized session, and the append's metadata records `custody: delegated` plus the authorizing session. The signature then attests exactly what is true: the platform signed on behalf of this bound identity under this recorded policy.
  A tenant's policy chooses permitted modes; adjudicator verdict-signing requires step-up in both modes.
- **Rotation** supersedes: a new enrollment event names the key it replaces; the old key stops being accepted for new appends at the rotation event and its historical signatures keep verifying (F-005-04). **Revocation** (by the actor, a tenant admin for their tenant, or platform security) is likewise an event, effective at the next request. **Recovery is re-enrollment**, never key retrieval — the old key is gone by design; adjudicator re-enrollment additionally requires a tenant-admin countersign event.
- **Multiple keys** per identity (per device) are ordinary; each is enrolled, rotated, and revoked independently.

## 4. Provisioning and lifecycle (CLM-005-05, CLM-005-06, CLM-005-07)

- **SCIM 2.0 (E3)** is the tenant's lifecycle source of truth where configured: Users create/update/deactivate; Groups map to role grants only through tenant-admin-approved mapping records (a group membership never silently becomes an adjudicator grant).
- **JIT provisioning** covers tenants without SCIM: first assertion creates the identity in the asserting tenant only, with **no study role** until a recorded grant.
- **Deprovisioning** (SCIM deactivate, tenant-admin action, or IdP lifecycle) appends the deactivation, revokes sessions, and closes the identity's keys to new appends — effective at the next authenticated request. History is untouched: the identity's appends, signatures, and attributions remain readable and verifiable (Article IV; F-005-05 tests both halves).
- **PII placement.** The identity directory (names, emails) lives *outside* every ledger, under ordinary data controls (DN-005 ingest discipline). Ledger payloads carry a stable, random **actor ID** and key fingerprints — never names or emails — so directory erasure under a legal duty never requires touching a chain, and chain attribution remains verifiable through the enrollment record.

## 5. Authorization (CLM-005-08, CLM-005-09, CLM-005-10)

- **Model.** Study roles are the WS6 §1 matrix, unchanged (researcher / reviewer / adjudicator / integrity officer; *System* is a service-account principal class under CLM-005-18). Two admin planes are added and are **disjoint** from study powers: *tenant admin* (their tenant's IdP config, membership, role grants, key revocations, audit export) and *platform admin* (tenant lifecycle, platform configuration, break-glass policy). No plane implies another (F-005-09). Role grants are appended events (grantor, grantee, role, scope); the effective role set is a projection, rebuildable from the record.
- **Enforcement.** A single authorization service is consulted by every endpoint, deny-by-default; the tenant context comes from the authenticated session, never from request parameters. Mutating decisions (actor, action, role basis) are recorded — study-plane mutations in the study ledger by construction, admin-plane actions in the platform audit ledger. UI affordance-hiding is presentation only (the Phase 6 wireframes already render role views this way; the service is where the rule lives).
- **Break-glass.** Per-tenant pre-declared policy: named invoker roles, a **second authorizer** (platform admin or tenant admin, per the tenant's declaration), a time box (default ≤ 4h, configurable down, never up silently), immediate alarm to tenant admins and the platform security log, every action under the session marked as break-glass in the audit record, and a post-use review item created automatically. Break-glass mints a *session*, never a credential; there is no standing backdoor (F-005-10).

## 6. Tenancy (CLM-005-11, CLM-005-12)

- **Organization = tenant.** Every study, identity, binding, and platform record is tenant-scoped at the data-access layer; study ledgers remain per-study `.axmr` files under tenant-partitioned storage (Axiomere itself is unchanged). Isolation is tested as a battery, not argued (E4): tenant A's credential against tenant B's resources across every endpoint class must return a uniform not-found and no tenant-B bytes (F-005-11).
- **Shapes (DN-003 extended).** Hosted multi-tenant and self-hosted single-tenant run one codebase and one authorization model; the hybrid shape (institution-held record store, hosted verification) remains an architectural target of the same split. Each tenant carries a recorded **residency pin** (shape, region); moving a pin is a migration: export + anchor the pre-migration state, move, and record the event.
- **Tenant budgets.** Per-tenant rate limits (§9) and per-tenant connector budgets extend Spec 002's query-budget discipline (RT2-2) to the tenant plane: one tenant's workload cannot starve another's, and exhaustion is a recorded stop, never a surprise.

## 7. Admin console (CLM-005-13)

Functional scope only — **this spec designs no screens.** The console manages: tenants; IdP configurations (OIDC/SAML, with metadata validation feedback); users and lifecycle state; role grants; keys and bindings (custody mode, enrollment/rotation/revocation state); the platform audit viewer and export; break-glass policy and session log. **Gate task T534-WF precedes any console code**: wireframes for the console are added to `docs/wireframes/` and the rendered screens owner-approved, per Article XIV. The console is a client of the same service-layer APIs as everything else — there are no console-only mutation paths.

## 8. Audit & compliance evidence (CLM-005-14 … CLM-005-17, CLM-005-22)

- **Platform audit ledger.** Administrative actions are append-only, Ed25519-signed, hash-chained events in Axiomere ledgers — one platform ledger per deployment for platform-plane events, and a per-tenant platform ledger for tenant-scoped admin events, so a tenant's complete admin record exports without disclosing other tenants'. Checkpointed and externally anchorable exactly like study ledgers (Article XIII). An actor's platform events and study appends join on the identity↔key binding (CLM-005-22).
- **Export.** The platform audit record exports in the Spec 002 Phase 5 pattern (`tekmerion.export`/`deposit`: manifest, per-file hashes, standalone verification, optional anchor) — a tenant or external auditor verifies the platform-plane record offline, and a tampered export fails (F-005-15).
- **SOC 2 readiness mapping (E6).** A maintained mapping from SOC 2 criteria to machinery and claims — CC6.1 logical access → §§2–5 (CLM-005-01…10); CC6.6 boundary protection → §6 (CLM-005-11/12); CC7.2 system operations → platform audit ledger + break-glass alarming (CLM-005-10/14); CC7.3/7.4 recovery → bundle export + anchoring (CLM-005-15); CC8.1 change management → the constitution/spec/wireframe gate record itself. The mapping is *readiness evidence*, labeled as such everywhere (CLM-005-16).
- **Retention & legal hold.** A hold is: a marker event, an export, an anchor, and access restriction. Nothing else. Retention schedules apply to off-ledger data classes only (session stores, directory PII of long-deactivated identities, per tenant policy). Erasure of chain content exists solely as DN-005's break-glass certificate — and, as DN-005 records, that protocol is specified but **not yet executable** until Spec 002's payload-encryption task (T223) lands; this spec inherits that dependency honestly rather than implying an erasure capability. GDPR posture: minimization (PII off-ledger, §4), residency pin (§6), no secondary use of tenant data (no training, no cross-tenant analytics over study content). FERPA posture: the tenant institution directs the processing; the platform's role is contractual (service provider / school-official terms), a contract posture — not a product certification, and never worded as one.

## 9. Platform security baseline (CLM-005-18, CLM-005-19, CLM-005-21)

- **Sessions:** server-side session records; idle lifetime (default 30 min) and absolute lifetime (default 12 h), tenant-configurable downward; cookies Secure + HttpOnly + SameSite; HTTP refused or redirected to TLS.
- **Headers & limits:** HSTS, Content-Security-Policy, X-Content-Type-Options, Referrer-Policy, frame-ancestors restrictions on every response; per-tenant and per-identity rate limits answering 429 (F-005-19 enumerates the battery).
- **Secrets:** IdP client secrets, SAML signing keys, egress secrets, and API-key material live in a secrets store (KMS-envelope in hosted; institution KMS or sealed file self-hosted), never in plaintext configuration payloads; rotations are recorded events.
- **API keys / service accounts:** keys are stored hashed with an identifying prefix, carry scopes that are a subset of the WS6 matrix (a key can never hold a power its role class denies a human), expire (≤ 1 year), record last use, and revoke immediately. Every service-account action is attributed and ledgered like a human's (F-005-18).
- **Webhook / event egress:** deliveries signed (HMAC-SHA256 with the tenant's egress secret, or Ed25519), timestamped with a stated replay window, retried with backoff, and delivery-logged as platform audit events; the spec ships a reference receiver whose rejections are the claim's test (F-005-21).

## 10. Composition with in-flight work

- **Phase 6 UI (Spec 002, branch `phase-6-ui`):** the approved wireframes already anticipate this spec — the actor block states *"identity arrives via the SSO hook and every action is appended under that name"* (WIREFRAMES.md §4). E1 supplies the real assertion→actor resolution behind that seam. The UI's code and wireframes are not changed by this spec; if E1's session model ever needs a UI change, it goes through Article XIV like any other.
- **Spec 003 (math layer) / Spec 004 (Lean service):** unaffected. Their machinery calls the register as researcher/System actors; once E1 lands, those calls bind to enrolled keys like any other actor's. Historical prototype ledgers (Phases 1–5) keep their actor strings; CLM-005-22's boundary records that they join by assertion, not by binding.
- **Domain adapters (post-Spec 004 program):** adapters consume and produce lane-1 evidence as *System* service-account principals under §9 — scoped, attributed, revocable.
- **Merging:** this spec's branch merges after the Phase 6 UI branch (coordinator sequences); enterprise phases then build on the merged tree.

## 11. Non-goals for v1 (scoped out, named)

- **SOC 2 (or any) certification engagement** — readiness and evidence only (CLM-005-16); an audit engagement is a future, separately gated decision.
- **HIPAA / BAA posture** — the biomedical adapters are lane-1 evidence tools, not PHI processing; a deployment that processes PHI is a new spec.
- **Direct LDAP/AD bind and the CAS protocol** — institutions reach directory services through Entra ID / Shibboleth; legacy CAS is declining and excluded.
- **Consumer social login** — Google *Workspace* via OIDC is institutional identity and in scope; consumer social accounts are not.
- **Cross-tenant study sharing / collaboration workspaces** — multi-institution studies are served by one hosting tenant with guest identities enrolled in it; true cross-tenant sharing is a future spec (it would need its own isolation claims).
- **Federation metadata aggregates (InCommon MDQ)** — v1.1 candidate; v1 configures IdPs per tenant.
- **Billing, payments, tenant self-signup** — commercial plumbing, not platform trust; tenant creation in v1 is a platform-admin act.
- **Self-service key recovery without countersign** — excluded by §3; recovery is re-enrollment.

## 12. Gates

- **G-ENT-1 (owner):** go-ahead on this spec before any E1 code (DN-011). This is the gate the spec package exists to earn.
- **Per-phase exit:** the phase's claims re-assessed at `after_implement` with build evidence; a claim that cannot gain evidence fails honestly and the phase does not close over it.
- **Article XIV gate** inside E5 (T534-WF): no console code before rendered-wireframe approval.
- **Pilot gate (G2 analog):** no institutional pilot on the enterprise build until the E4 isolation battery passes and a platform audit export has been demonstrated anchored — the AR-1 pattern applied to the platform plane.
- **Spend gate:** hosted infrastructure, KMS, or IdP test-tenancy costs return to the owner individually (DN-003's rule).
