# Design Note 011 — Enterprise Platform: Direction

**Date:** 2026-10-12 · **Status:** Adopted as direction (owner directive); **gate G-ENT-1 GIVEN by the owner 2026-10-12** — E1 implementation authorized (see "Gate" below).
**Decided by:** Tristen Pierson · **Governs:** Spec 005 (enterprise platform) · **Extends:** DN-003 (deployment shapes) · **Bound by:** Constitution Articles IV, XII, XIII, XIV (draft); DN-005.

## The directive

Owner, 2026-10-12: *"make tekmerion a full enterprise solution with SSO and other enterprise features."* This note records the direction decisions that directive embodies, so the spec that follows from it (Spec 005) argues from recorded decisions rather than re-litigating them. The build itself is **not** authorized by this note: like Spec 002 before it, the enterprise platform gets a G1-style owner gate on its spec (claims assessed, plan and tasks drafted) before any implementation code.

## Decisions

1. **Identity protocols: OIDC and SAML 2.0, both.** Universities do not run one identity stack. Campus and cloud tenants authenticate through Microsoft Entra ID or Google Workspace (OIDC); the research/education federation world — Shibboleth IdPs, InCommon and peer federations — speaks SAML 2.0 and is how multi-institution collaborations actually sign in. A Tekmerion that speaks only OIDC excludes the federation institutions; one that speaks only SAML excludes the cloud-first programs. One-protocol is a non-starter in higher education, so the platform is a service provider for both, with per-tenant IdP configuration.
2. **Identity binds to the signing key; it does not replace it.** Article XIII already makes every append an Ed25519-signed act by an actor. Enterprise identity therefore *enrolls and governs* keys — an IdP-authenticated identity (issuer + subject) is bound to a keypair by a recorded enrollment event — rather than substituting session authentication for signatures. Session login proves who is at the keyboard; the key is what the record believes. Enrollment, rotation, and revocation are themselves recorded events.
3. **Provisioning is lifecycle, and deprovisioning respects DN-005.** SCIM 2.0 from the tenant IdP plus just-in-time provisioning govern account creation; deprovisioning ends the identity's ability to append or read, promptly — and deletes nothing. People leave; the record of what they signed while they were members does not (DN-005: there is no delete operation, in any plane).
4. **Deployment shapes extend DN-003.** Hosted multi-tenant (Axiovex-operated, organizations as tenants) and self-hosted single-tenant (the institution-local shape of DN-003, productized) are the two v1 shapes, on one codebase and one role model. The hybrid shape of DN-003 (institution-held record store, hosted verification) remains a first-class target of the same architecture.
5. **Authorization is the WS6 role matrix, enforced in the service layer.** Researcher / reviewer / adjudicator / integrity officer (WS6 §1) plus two admin planes (tenant admin, platform admin) that confer no study powers. UI-hidden affordances are presentation, never enforcement.
6. **The admin console is UI, so it is wireframe-gated.** Console screens do not exist until `docs/wireframes/` carries them and the owner has approved the rendered screens (Article XIV). Spec 005 scopes the console functionally only.

## What "enterprise" will NOT claim in v1

- **No SOC 2 certification.** v1 delivers SOC 2 *readiness*: a control mapping from the SOC 2 criteria to machinery that exists, plus the evidence exports an auditor would consume. A certification is an auditor's act over an observation window; claiming one before that would be exactly the kind of unverified status Article X forbids.
- **No "FERPA-certified" or "GDPR-certified" language** — no such certifications are held, and for FERPA none exists to hold. The spec states FERPA/GDPR posture as design constraints (data minimization, PII kept out of ledger payloads per DN-005 ingest discipline, residency pinning, erasure handled under ordinary data controls and DN-005's certificate protocol), never as compliance claims.
- **No deletion-based retention.** Retention and legal hold are export, anchor, and access-restriction. Any feature sketch that deletes or masks record content outside DN-005's break-glass erasure certificate is out of scope by constitution, not by preference.
- **No SSO-only "identity" that bypasses signatures.** A deployment mode in which appends are accepted on session assertion alone, unsigned by an enrolled key, would silently repeal Article XIII and is excluded.
- **No "CMMC compliant product" or "CMMC certified" language.** CMMC (32 CFR Part 170) certifies *organizations and their assessment boundaries*, never software products; there is no product certification to claim. Tekmerion's truthful claim is **CMMC Level 2 alignment / compliance support** (see "CMMC posture" below). Any surface that drops the qualifier structure violates Article X exactly as a SOC 2 certification claim would.

## CMMC posture (owner directive, 2026-10-12: *"also make this tool CMMC compliant"*)

The directive is adopted in its truthful form. CMMC certification attaches to an organization operating within a defined assessment boundary; a product can only be built so that an organization can operate it inside a CMMC Level 2 boundary and evidence the NIST SP 800-171 Rev 2 requirements the platform owns. Accordingly:

- **Design target: NIST SP 800-171 Rev 2 (all 110 requirements), CMMC Level 2.** Level 1 (the FAR 52.204-21 subset) is implied by Level 2 alignment and is not separately engineered. **Level 3 (NIST SP 800-172) is out of scope for v1** and is not claimed anywhere.
- **Responsibility is mapped, not asserted.** Spec 005 §13 carries a control responsibility matrix over every 800-171 family: requirements the platform satisfies by construction, requirements it supports (the operator/IdP owns the remainder), and requirements that are organizational and out of product scope. No family is silently dropped.
- **FIPS honesty.** §3.13.11 requires FIPS-validated cryptography for protecting CUI. The platform's current cryptographic modules (Axiomere core: RustCrypto `sha2` / `ed25519-dalek`; the E1 service layer) are **not** FIPS-validated, and nothing in this program may claim they are. The amendment records the gap, a crypto inventory obligation (Spec 005 T549), the realistic validated-module routes, and the cross-repo dependency on the Axiomere roadmap — which this note does not commit; the migration decision returns to the owner when the CMMC track reaches it.
- **Hosted-shape flag (open owner/legal decision).** DFARS 252.204-7012 expects a cloud service provider that stores, processes, or transmits CUI to meet FedRAMP Moderate baseline equivalency. Whether and how the Axiovex-hosted shape seeks that equivalency is a legal/business decision engineering does not resolve; Spec 005 §13 records it as an open flag on the hosted shape, not a settled property.

## Gate

Spec 005 is drafted claims-first (AEE bundle assessed at `after_specify`). **No enterprise implementation code before the owner's G1-style go-ahead on Spec 005**, mirroring the Spec 002 precedent (G1, DN-002/DN-003 era). Hosted-infrastructure choices that cost money return to the owner as their own decision (DN-003's rule, unchanged).

**G-ENT-1 GIVEN — 2026-10-12.** The owner gave the go-ahead on Spec 005 in the Glossa-Lab chat (*"Give Spec 005 the G-ENT-1 go-ahead — start E1 identity core"*), following the delivered spec package (branch `enterprise-spec` @ `d29eb0e`; 22 claims assessed `gather_evidence`). E1 (identity core) is authorized. Phases E2–E6 proceed per the plan's per-phase exits; the remaining gates in Spec 005 §12 (Article XIV wireframe gate, pilot gate, spend gate) are unaffected. A second owner directive the same day (*"also make this tool CMMC compliant"*) is absorbed as a claims-first amendment to Spec 005 (Spec 005 §13, plus the CMMC section added to this note by that amendment) **before** E1 code, so the E1 build carries the CMMC requirements that touch it.

## Falsifier for this decision

If the E1 prototype shows the identity↔key binding unusable in practice — enrollment friction such that real adjudicators cannot complete a signed verdict flow — or if a target institution segment demonstrably authenticates exclusively through a channel neither OIDC nor SAML reaches (so both-protocols still excludes them), the direction in §1–§2 must be revisited before further enterprise build.
