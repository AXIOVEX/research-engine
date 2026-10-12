# Design Note 012 — Pilot Authorized (Design-First); OSF Registration in Pilot Scope

**Date:** 2026-10-12 · **Status:** Ratified by the owner (Tristen Pierson) — block ratification of the coordinator's recommendations, 2026-10-12.
**Decided by:** Tristen Pierson · **Governs:** the Tekmerion institutional pilot (design in `docs/pilot/DESIGN.md`) · **Depends on:** DN-008 (G2 ratified), DN-003 (hosted-first), DN-005 (append-only), DN-011 (enterprise direction) · **Bound by:** Constitution Articles X, XI, XIII, XIV; gates G3 (thresholds, set 2026-10-12) and G4 (spend).

## Decision

1. **Pilot work is authorized to BEGIN — as design.** Gate G2 (DN-008) unblocked institutional pilot work but explicitly did not start a pilot ("ratification is not a pilot start: any pilot remains a separate owner decision"). This note is that decision, in its first stage: the pilot is designed first — partner archetype and fit criteria, a pre-registered pilot study with kill criteria, an operational shape, and an evidence pack — before any institution is named. **No outreach is authorized by this note.** A shortlist of named target institutions returns to the owner as its own gate, and contact with any named target requires the owner's approval of that target.

2. **The OSF registration workflow is IN pilot scope.** DN-008 recorded caveat 2: OSF support shipped in Phase 5 as deposit-ready metadata + component mapping only (`tekmerion.deposit.osf_metadata`), and "an OSF registration workflow is a separate owner decision, outstanding." The owner has now made that decision: the registration workflow is built as part of the pilot, **sequenced before partner onboarding** (see `docs/pilot/DESIGN.md` §4). No further decision is outstanding on OSF scope. Zenodo remains the demonstrated executable anchor (DOI 10.5281/zenodo.23311479); OSF is added because it is the systematic-review community's home registry, not because Zenodo anchoring is deficient.

3. **Design-first, claims-honest.** Everything the pilot will say to a partner is limited to verified states (Article X). The evidence pack (DESIGN.md §6) leads with the anchored public records and discloses the known negatives with them: the Phase 5 demo run was INVALID and issued no verdicts (DN-008 caveat 1); K1 stands open until the Phase 7 frozen evaluation discharges it; the enterprise platform is at E1 of six phases. A pilot sold on claims the record does not carry would falsify the product's premise.

4. **Spend: standing G4 only.** This note authorizes no spend. Free API keys on the owner's accounts — OpenAlex, OSF, Zenodo — are within standing authorization (Spec 002, G4); any paid infrastructure, API tier, or service the pilot design turns out to need returns to the owner as its own decision (DN-003's rule, unchanged).

5. **CUI is out of pilot scope.** Per DN-011's CMMC posture, the platform's cryptographic modules are not FIPS-validated and the FIPS gap is an open POA&M item; no pilot partner data class may include CUI, and the pilot makes no CMMC representation beyond the alignment language DN-011 permits.

## Basis

- **G2 evidence** (DN-008): audit-bundle export with independent verification and a live Zenodo anchor, verified by read-back at ratification.
- **Public demonstration:** the Spec 003 worked study (2026 AI-mathematics claims) — frozen, verdicted, and anchored at DOI [10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259) — plus the Tao realignment audit of all prior work (`docs/audits/2026-10-12-tao-realignment-audit.md`), including its corrections to the demo study's record (bundle v3, DOI [10.5281/zenodo.23317023](https://doi.org/10.5281/zenodo.23317023)).
- **G3 thresholds** (owner, 2026-10-12, same ratification): K3 adjudicator audit-time budget **2 hours per bundle**; K5 cost ceiling **$25 per question**. The pilot's pre-registered criteria adopt both values unchanged (DESIGN.md §3).
- **Product surface:** the Phase 6 register-first UI (constitution v1.2.0; wireframe-governed) and Spec 005 E1 identity core (OIDC, key enrollment, service-layer RBAC, platform audit ledger) are built and merged; E2 (SAML) is authorized and in flight.

## Recorded caveats (accepted with eyes open)

1. **Enterprise readiness is partial, and partner expectations may not be.** SAML (E2), SCIM (E3), tenancy hardening (E4), and the admin console (E5, wireframe-gated) are specified, not built. Research-federation institutions authenticate via Shibboleth (SAML); a pilot partner whose IdP is SAML-only cannot complete SSO onboarding until E2 lands. The design (§2) therefore treats IdP landscape as a fit criterion, not an assumption.
2. **No SOC 2 certification exists** (DN-011: readiness and evidence only). University security review may ask for SOC 2 or a HECVAT response; whether that is a pilot blocker is unknown until discovery and is recorded as such in the design (§8), not presumed away.
3. **Phase 7 has not reported at design time.** The pilot study's design consumes the Phase 7 evaluation's verdicts when they land (DESIGN.md §6 reserves the slot); if Phase 7 returns a kill (K1–K5 fired), the pilot does not proceed to the shortlist gate on a failed engine — the kill tradition binds the pilot exactly as it binds the evaluation.
4. **The append-only posture will meet institutional retention/erasure policy.** DN-005 admits no delete operation; the break-glass erasure certificate exists for legal compulsion. How a partner's data-governance review receives that posture is a discovery question (§8), and no pilot material may soften it into a deletion promise.

## Falsifier for this decision

If the pilot design's pre-registered criteria cannot be stated in a form a named partner could actually be measured against — or if discovery with the first owner-approved target shows the pilot's load-bearing assumptions (OSF registration wanted, OIDC acceptable at start, adjudicator time available) are all false at once — the pilot premise as scoped here is wrong, and this note must be revisited before any further pilot spend of effort.
