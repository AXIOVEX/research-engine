# Spec 005 — Plan: Enterprise Platform

**Date:** 2026-10-12 · Companion to `spec.md`. Authority: DN-011 (adopted); DN-003; DN-005; Constitution Articles IV, XII, XIII, XIV.
**Gate:** owner G-ENT-1 go-ahead on Spec 005 before E1 code. Claims assessed first (`aee-claims.json` v0.1.0 → `aee-assessment.json`, outcome **gather_evidence**, 2026-10-12). **G-ENT-1 GIVEN by the owner 2026-10-12** (Glossa-Lab chat) — E1 authorized. The same day's CMMC directive is absorbed as a claims-first amendment (claims v0.2.0, Spec 005 §13) before E1 code.

## Build order

```
E1  Identity core — OIDC (code + PKCE) per-tenant IdP config; internal
    identity model; key enrollment (proof of possession) + rotation /
    revocation; custody modes; authorization service on the WS6 matrix
    + disjoint admin planes; platform audit ledger core; scoped API
    keys. CMMC absorbed (§13): AU event classes, MFA-evidence
    enforcement, crypto inventory.
                                       [CLM-005-01, 03, 04*, 08, 09, 14*, 18, 25(inv), 26*, 27]
E2  SAML — SP for Web Browser SSO; per-tenant metadata + attribute
    mapping (Shibboleth / InCommon class).       [CLM-005-02]
E3  Provisioning & lifecycle — SCIM 2.0; JIT (no-role default);
    deprovisioning pipeline (sessions + keys close; history intact);
    PII-off-ledger directory.                    [CLM-005-05, 06, 07, 04†]
E4  Tenancy hardening — tenant context at the data-access layer;
    isolation battery; break-glass (+ alarming, review); session /
    transport baseline battery; signed webhook egress + reference
    receiver; platform↔study reconciliation join; CMMC IR egress
    event classes.                    [CLM-005-09†, 10, 11, 14†, 19, 21, 22, 26†, 30*]
E5  Admin console — FUNCTIONAL build only, behind the Article XIV
    wireframe gate (T534-WF): tenant / IdP / user / role / key /
    audit surfaces as clients of the service APIs. [CLM-005-13]
E6  Compliance evidence + self-hosted shape — residency pin +
    migration; platform audit export + anchored demonstration;
    SOC 2 readiness mapping document; retention / legal-hold
    markers; self-hosted packaging + upgrade path. CMMC (§13.7):
    SPRS support, POA&M register, CUI marking.
                                       [CLM-005-12, 15, 16, 17, 23, 24, 28, 29, 30†, 31]

Every phase exit: (a) the phase's claims re-assessed at after_implement
with build evidence; (b) the full Spec 002 battery re-run unchanged
(CLM-005-20 — the regression obligation is per-phase, not final).
* = core lands here, † = completed/hardened here.
```

## Claim → phase map

| Claim | Phase | Exit evidence |
|-------|-------|---------------|
| CLM-005-01 OIDC, no local passwords | E1 | flow tests vs. a test IdP; schema/API audit for credential paths (F-005-01) |
| CLM-005-02 SAML SP | E2 | signed-assertion acceptance + unsigned/wrong-IdP rejection tests vs. a Shibboleth-class test IdP |
| CLM-005-03 key binding enforced | E1 | unenrolled/revoked-key append rejection tests through the service |
| CLM-005-04 key lifecycle as events | E1 core, E3 completion | rotation-keeps-history-verifying test; revocation event chain |
| CLM-005-05 deprovisioning semantics | E3 | both-halves test: next-request append denied; history verifies (F-005-05) |
| CLM-005-06 SCIM 2.0 | E3 | SCIM conformance-style create/update/deactivate cycle tests |
| CLM-005-07 JIT least privilege | E3 | JIT identity holds no role until a grant event (test) |
| CLM-005-08 service-layer RBAC | E1 | matrix battery: direct-API forbidden-action calls denied per role |
| CLM-005-09 disjoint planes | E1 model, E4 battery | cross-plane denial tests (platform admin cannot sign; tenant admin cannot cross) |
| CLM-005-10 break-glass | E4 | use-without-audit-event impossible (test); dual-auth + time-box denial tests |
| CLM-005-11 tenant isolation | E4 | the canonical cross-tenant battery across endpoint classes |
| CLM-005-12 shapes + residency | E6 | same-battery-both-shapes run; self-hosted payload absence check in hosted plane |
| CLM-005-13 Article XIV console gate | E5 | wireframe approval record precedes console code in git history |
| CLM-005-14 platform audit ledger | E1 core, E4 completion | admin-action-without-event audit sweep test |
| CLM-005-15 platform audit export | E6 | tampered-export (incl. rehashed manifest) fails standalone verification |
| CLM-005-16 readiness, not certification | E6 | wording sweep over product surfaces; mapping entries all resolvable |
| CLM-005-17 hold = export + anchor | E6 | hold flow produces marker + bundle + anchor; zero deletion paths in audit |
| CLM-005-18 scoped API keys | E1 | unscoped/non-expiring key unrepresentable (schema test); service appends attributed |
| CLM-005-19 session/transport baseline | E4 | header/cookie/lifetime/429 battery (F-005-19's enumeration) |
| CLM-005-20 no Spec 002 weakening | every exit | Spec 002 battery green unchanged, CI-recorded per phase |
| CLM-005-21 signed webhooks | E4 | reference receiver rejects unsigned/bad/replayed deliveries |
| CLM-005-22 platform↔study join | E4 | join walk for a bound actor; no cross-identity pairing (test) |
| CLM-005-23 CMMC framing honesty (L2 alignment, never product certification) | amendment; swept at E6 (T544) | wording sweep over product surfaces finds no unqualified CMMC claim |
| CLM-005-24 responsibility matrix complete (110/110) | amendment; maintained per exit | matrix coverage check; classifications match shipped machinery at each exit |
| CLM-005-25 FIPS position: inventory + open gap, no false claim | E1 (inventory, T549); migration = owner decision | crypto inventory delivered with E1; gap + routes recorded; zero FIPS claims in surfaces |
| CLM-005-26 AU event-class completeness | E1 core, E4 completion | T550 sweep: every E1 mutation/auth path emits its event with the AU content set |
| CLM-005-27 MFA at the IdP, platform-enforced | E1 | session without MFA evidence cannot mutate or step up (test) |
| CLM-005-28 CUI marking in artifacts | E6 (T551) | bundle for a marked study/tenant carries markings in manifest + HUMAN-README |
| CLM-005-29 SPRS self-assessment support | E6 (T552) | control states export in SPRS-input form; matrix↔state agreement check |
| CLM-005-30 IR hooks + POA&M register | E4 (hooks, T554) + E6 (register, T553) | IR event classes egress signed; POA&M status changes are appended events only |
| CLM-005-31 DFARS/FedRAMP hosted-shape flag stays visible | standing | hosted-shape materials carry the open-decision flag (spot-check per exit) |

## Key decisions recorded in the spec (argued there, indexed here)

- **One identity model behind both protocols** (spec §2): authorization and audit never branch on OIDC vs SAML after the boundary.
- **Two custody modes, honestly labeled on the record** (§3): self-custody signs client-side; delegated custody (KMS/HSM) signs server-side inside an authorized session and the append metadata says so — the signature attests what is true in each mode, never more.
- **PII lives off-ledger** (§4): ledgers carry random actor IDs + key fingerprints (DN-005 ingest discipline), so directory erasure never pressures the chain.
- **Tenant context from the session, never from request parameters** (§6): the isolation claim is a mechanism, not a coding guideline.
- **Platform audit = two ledger scopes** (§8): one deployment ledger (platform plane) + per-tenant ledgers (tenant plane), so tenant exports are complete without cross-tenant disclosure.
- **Erasure honesty** (§8): DN-005's certificate protocol remains *specified, not executable* until Spec 002 T223 (payload encryption) lands; Spec 005 inherits the dependency rather than papering over it.

## Composition (spec §10, summarized)

Phase 6 UI's actor-header/SSO-hook seam is the E1 integration point; the study UI and its wireframes are untouched by this spec. Specs 003/004 are unaffected (their actors bind keys once E1 exists; historical ledgers join by assertion — CLM-005-22's boundary). Enterprise branch merges after `phase-6-ui`; the coordinator sequences merges, and no enterprise phase starts on an unmerged base.
