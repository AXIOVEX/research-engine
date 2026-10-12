# Spec 005 — Plan: Enterprise Platform

**Date:** 2026-10-12 · Companion to `spec.md`. Authority: DN-011 (adopted); DN-003; DN-005; Constitution Articles IV, XII, XIII, XIV.
**Gate:** owner G-ENT-1 go-ahead on Spec 005 before E1 code. Claims assessed first (`aee-claims.json` v0.1.0 → `aee-assessment.json`, outcome **gather_evidence**, 2026-10-12). **G-ENT-1 GIVEN by the owner 2026-10-12** (Glossa-Lab chat) — E1 authorized. The same day's CMMC directive is absorbed as a claims-first amendment (claims v0.2.0, Spec 005 §13) before E1 code.

**Owner decisions 2026-10-12 (block ratification, Glossa-Lab chat):** (1) **E2 (SAML) starts now**, on the merged E1 foundation (E1 stack merged to main at `85c6210`; branch `enterprise/e2-saml`). (2) **The FIPS-validated crypto migration (Axiomere core, §13.3) waits for a named CUI/defense requirement** — the CMMC open-gap posture stands meanwhile: the crypto inventory (T549) and the seeded POA&M item carry the position, §3.13.11 stays "Supports — OPEN GAP", and no FIPS work starts under this spec until that requirement exists. This ratifies CLM-005-25's recorded route ("migration = owner decision") with the decision taken: *not now, on a named trigger*.

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

## Phase exits

**E1 — identity core: EXITED 2026-10-12** (branch `enterprise/e1-identity`,
commit `2c4afbd`; PR #2 opened for CI, run 38253126192 success; merging is the
coordinator's). Delivered: internal identity model + per-tenant IdP
configuration with secrets by reference (T501/T502); OIDC RP — discovery,
authorization code + PKCE (S256 only), JWKS rotation, RS256 validation — with
the no-local-credential audit test (T503); key enrollment with proof of
possession, rotation, revocation, closure (T504/T505); both custody modes with
the mode recorded on every append — delegated custody's signer is a labeled
**software development signer**, not KMS/HSM (T506); the append gate (T507);
WS6 authorization service + disjoint admin planes (T508/T509); the platform
audit ledger in two scopes (T510); scoped API keys (T511); the crypto
inventory (T549); the AU completeness sweep (T550). Tests: 122 passed locally
and in CI (82 prior + 40 new), including every seeded negative in the phase
brief. Claims at exit (bundle v0.3.0, re-assessed `after_implement`, outcome
`gather_evidence` — 14 claims remain below threshold, all unbuilt E2–E6 scope):
supported — CLM-005-01, 03, 08, 18, 25, 27; partially_supported — CLM-005-04
(E3 completion), 09 (E4 battery), 14 (SCIM/break-glass events), 26 (E4
review/retention half). Recorded finding for the record layer: high-precision
float payload values can fail Axiomere hash verification on reopen; platform
payloads carry whole-second timestamps only (see `platform/ledger.py`).
What remains not understood at this exit: real-IdP interoperability (the E1
evidence is an in-process mock IdP enforcing real PKCE/RS256 — no external
IdP has been exercised), delegated-custody behavior under a real KMS/HSM
(E2+ integration, interface only here), and platform-ledger behavior at
institutional event volumes.

**E2 — SAML 2.0 SP: EXITED 2026-10-12** (branch `enterprise/e2-saml`,
commit `bb5a985`; PR #4 opened for CI, run 38257747324 success; merging
is the coordinator's). Delivered: per-tenant SAML IdP configuration from
imported metadata (platform provisioning + tenant-admin self-service;
certificates by reference, fingerprints ledgered) (T513); the
signed-assertion-only validation battery — issuer/audience/recipient/
conditions/InResponseTo/replay, every refusal an `auth.login_failed`
event before the raise (T514); attribute mapping incl.
`eduPersonPrincipalName` (subject under `subject_source=eppn`) and
`eduPersonScopedAffiliation` into the §2 identity model (T515); the
Shibboleth-class test IdP harness in CI (T516); step-up parity — SAML
sessions reach the same §2 step-up state via ForceAuthn + REFEDS MFA
context, and no-MFA SAML sessions are refused at the append gate
exactly as OIDC ones (T517). Tests: 210 passed locally and in CI (173
prior + 37 new), Spec 002 battery unchanged. Claims at exit (bundle
v0.4.0, re-assessed `after_implement`, outcome `gather_evidence` — 13
claims remain below threshold, all unbuilt E3–E6 scope): CLM-005-02 →
**supported** (1.00); CLM-005-14 stays partially_supported with SAML
events added to its evidence (residue: E3 SCIM outcomes, E4
break-glass); CLM-005-27 stays supported with SAML MFA-parity
evidence. The responsibility matrix was reviewed — no classification
changes (IA rows are protocol-neutral; E2 makes their SAML half true);
the crypto inventory gains row 12 (XML-DSig verification, not
FIPS-validated — §3.13.11 gap unchanged under the owner's recorded
FIPS timing decision). What remains not understood at this exit: real
Shibboleth/Entra SAML interoperability (fixtures only — the harness's
signatures are real, its message shapes are ours), the in-repo
exclusive canonicalizer against production namespace-heavy
assertions, and SP request-signing / encrypted-assertion support
(both refused-or-absent by recorded v1 scope, not by oversight).

**E3 — SCIM + identity lifecycle: EXITED 2026-10-12** (branch
`enterprise/e3-scim`, commit `a1a0f3a`; PR #9 opened for CI, run
38276407663 success; merging is the coordinator's). Delivered: the
SCIM 2.0 provisioning surface — Users and Groups in RFC 7643/7644
shapes with per-tenant bearer provisioning credentials (hash-only
storage; cross-tenant presentation refused and ledgered in the
addressed tenant before any state change) (T518); group→role
mappings only as recorded tenant-admin-approved records, with
grant-source tracking so roles survive exactly while a source
justifies them (T519); JIT least privilege marked on both login
doors (T520); the deprovisioning pipeline through one shared
lifecycle core — SCIM deactivate/Delete and admin deactivation are
the same act (T521); adjudicator re-enrollment by tenant-admin
countersign plus the deprovisioned-identity key sweep (T522);
off-ledger directory PII with an erasure path that never touches a
chain (T523); the lifecycle admin API (T524); phase exit with
re-assessment (T525). Tests: 288 passed locally and in CI (249 prior
+ 39 new), including F-005-05 in both halves and the refusal battery.
Claims at exit (bundle v0.5.0, re-assessed `after_implement`, outcome
`gather_evidence` — 10 claims remain below threshold, all unbuilt
E4–E6 scope): supported — CLM-005-04 (E3 completion), 05, 06, 07
(joining the E1/E2 set); partially_supported — CLM-005-14 (SCIM half
discharged; residue is E4 break-glass only — completion at E4 per
the claim map), 09, 26 unchanged. CMMC maintenance: matrix reviewed,
no classification changes (rows 3.5.5/3.9.2's E3 bases now exist);
crypto inventory gains no row (SCIM credentials reuse the row-8
hashing operation and row-10 generation). What remains not
understood at this exit: live SCIM-client interoperability (no
Entra/Okta tenant exercised — fixtures only), SCIM↔login account
linking (unspecced; the dual-door fact now has a third door), and
provisioning behavior at institutional directory volumes.

**E4 — Tenancy hardening + break-glass: EXITED 2026-10-12** (branch
`enterprise/e4-tenancy`; PR opened for CI; merging is the
coordinator's). Delivered: tenant scoping audited and enforced at
every service surface — tenant context is taken from the resolved
session / addressed resource, never from a caller's tenant parameter
(T526); the isolation battery across OIDC, SAML, SCIM, keys, API
keys, lifecycle, break-glass, webhooks, and audit reads — every
cross-tenant attempt refused with zero of the other tenant's bytes,
target state unmoved, both chains verifying afterwards (T527,
F-005-11); the cross-plane battery in both directions (T528,
F-005-09); break-glass as the declared mechanism of §5 — per-tenant
declaration (tenant-admin act naming invoker roles, a
second-authorizer plane, scopes restricted to what the mechanism
can exercise, and a time box under the hard 4h ceiling), dual
authorization (never the invoker), every step a marked event in
BOTH the tenant ledger and the deployment security log, expiry that
closes the session and auto-creates the post-use review item, no
extension path (T529, F-005-10); the session/transport baseline —
real idle/absolute session-lifetime enforcement, the header/cookie/
TLS contract as asserted data, per-tenant per-endpoint-class rate
limits answering 429 with the trip ledgered (T530, F-005-19);
webhook egress — HMAC-SHA256 or Ed25519 signed deliveries, 300s
replay window, retry/backoff with every attempt a platform audit
event, and the reference receiver rejecting unsigned, badly-signed,
stale, and replayed deliveries by name (T531, F-005-21); the T554
IR security-event classes as first-class signed egress (auth-failure
bursts, revocation storms, break-glass use, audit-verification
failures) (T554, CLM-005-30 IR half); audit read + chain-verification
surfaces and the reconciliation join on the identity↔key binding
(T532, F-005-22). Tests: 318 passed, 2 skipped locally (288 prior +
30 new); the E1 AU completeness sweep was extended a third time to
exercise the E4 vocabulary. Claims at exit (bundle v0.6.0,
re-assessed `after_implement`, outcome `gather_evidence` — 4 claims
remain below threshold, all E6 scope or the standing DFARS flag:
005-12, 17, 28, 31): supported — CLM-005-09† (cross-plane battery),
10 (break-glass), 11 (isolation), 14† (audit enumeration complete,
incl. break-glass use), 19 (baseline), 21 (egress), 22
(reconciliation), 26† (review half: audit reads, honest
verification, the join; retention is the ledger's append-only
construction); partially_supported — CLM-005-30 (IR half delivered
at E4 per tasks.md — one phase earlier than the claim's boundary
text contemplated; the POA&M register half is E6/T553). CMMC
maintenance: the responsibility matrix was reviewed — no
classification changes (rows 3.3.4/3.3.5/3.6.1/3.6.2 already name
T554/CLM-005-22 mechanisms as their basis; E4 makes the basis
true); the crypto inventory gains row 13 (webhook HMAC-SHA256, not
FIPS-validated — the §3.13.11 gap is unchanged under the owner's
recorded FIPS timing decision). Pilot gate (T533): the isolation
battery is green; the platform audit export demonstration remains
scheduled in E6 (T542/T543) — the gate's second half is an E6
deliverable, recorded here as evaluated-not-yet-discharged. Two
defects were caught by the batteries and fixed in-phase: a
break-glass record helper collided a caller-named target with the
ledger record's own target field (found by the extended AU sweep),
and the AU sweep itself initially tripped the new rate limiter on
the test's own earlier traffic (battery construction, fixed by
window hygiene). One behavior the tamper battery exposed and the
record states plainly: effective roles replay from the tenant
ledger (the ledger is the record of truth), so tampering with a
role.granted event changes what the replay computes — detection is
the verification surface's job, and it fires (hash-mismatch,
security event, signed egress). What remains not understood at this
exit: no live external webhook receiver or IdP/SCIM client has been
exercised (the receiver is the shipped reference implementation;
customer receivers will differ); rate-limit and detector behavior
at institutional event volumes; break-glass under a real incident's
human process (the mechanism is built and batteried; the drill is
an E6/pilot activity); SCIM↔login account linking remains
unspecced (carried from E3).
