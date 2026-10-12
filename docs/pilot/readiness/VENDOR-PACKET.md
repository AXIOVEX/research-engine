# Tekmerion — Vendor Review Packet (Pilot)

**Issued by:** Axiovex Systems, LLC · **Status: DRAFT for owner approval — this packet
is assembled for a future vendor review and has not been sent to any institution.**
**Rule of this document:** every statement below is a verified state from our own
records (specifications, claim assessments, public anchors), fetchable or runnable by
the reviewer. Where something does not exist yet, this packet says so in place rather
than omitting it. A statement a reviewer cannot check is not included.

---

## 1. What Tekmerion is

Tekmerion is a research engine for evidence questions whose differentiator is
**defensibility**: every claim is registered with the observation that would falsify
it; evidence is provenance-tracked and hash-verified; verdicts are issued only
against frozen, pre-registered study state; and every study exports an **audit
bundle** that a third party can verify standalone — without our systems, our staff,
or our say-so. Records are append-only: corrections are new records, never edits.

The pilot offers one institution one real systematic-review evidence question run
end-to-end through this machinery, operated by the partner's own staff, measured
against criteria registered before the partner was named (§7 of this packet).

## 2. The pilot — what it is and is not

**Shape.** Hosted by Axiovex (multi-tenant platform; the partner is a tenant with
its own IdP configuration — IdP, the institution's sign-in service). One real evidence question from the partner's pipeline,
scoped small enough to audit completely. The partner's adjudicator personally
performs the freeze approval and the deposit approval; Axiovex staff assist but do
not drive. A pilot only we can operate demonstrates a consultancy, not a product —
the criteria in §7 are written to catch exactly that.

**Data in scope:** published-literature metadata and full text where the recorded
licence basis permits storage (per-source rights — query / store / redistribute —
recorded separately before use); partner-authored claim statements, falsifiers, and
adjudication rationales; partner reviewer identities in the platform directory
(never in ledger payloads).

**Out of scope, by design:** controlled unclassified information (CUI); protected
health information (PHI) and human-subjects raw data; unpublished or
access-restricted corpora; any content whose licence basis cannot be recorded.
Partner data never enters a public bundle or registry deposit without a recorded
licence basis; partner deposits default to the least-public anchored form until the
partner directs otherwise in writing.

## 3. Identity and tenancy posture

Built and claim-supported today (Spec 005, bundle v0.4.0, assessed 2026-10-12):

- **OIDC sign-in** (the modern sign-in standard) through the tenant's own IdP, using
  the flow where the app proves itself with a one-time code challenge
  (authorization code + PKCE, S256 variant) —
  supported. There are no local passwords.
- **SAML 2.0 service provider** with per-tenant IdP configuration (metadata import,
  attribute mapping incl. eduPersonPrincipalName and scoped affiliation) —
  supported. This is the Shibboleth shape the research-library archetype uses.
- **Signed appends:** every accepted record write is signed by an Ed25519 key
  enrolled to an IdP identity through a recorded enrollment; key rotation and
  revocation are ledger events.
- **Authorization:** a role matrix (researcher / reviewer / adjudicator / integrity)
  enforced in the service layer, deny-by-default; platform-admin, tenant-admin, and
  study planes are disjoint.
- **Multi-factor authentication (MFA):** required at the tenant IdP and enforced
  platform-side (the platform
  requires MFA evidence and refuses step-up actions without it).

Specified, **not yet built, and not claimed**: SCIM provisioning and automated
deprovisioning (build phase in flight), break-glass mechanism, tenancy-hardening
phase, the admin console (which ships only after owner-approved wireframes), and
the compliance-evidence phase. A draft HECVAT self-assessment accompanies this
packet in our readiness file and states our position item by item, including its
own gaps.

**Correction (2026-10-12, appended the same day):** the list above and this
section's bundle reference (v0.4.0) predate three landings. Spec 005 phases E3,
E4, and E6 have since merged, and the bundle now stands at **v0.7.0 — 29 of 31
claims supported**. Of the items listed above as not yet built: **SCIM
provisioning and automated deprovisioning** are built and claim-supported (E3;
CLM-005-05, CLM-005-06, CLM-005-07); the **break-glass mechanism** and the
**tenancy-hardening phase** are built and claim-supported (E4; CLM-005-10,
CLM-005-11); and the **compliance-evidence phase** is built (E6; SPRS self-score
machinery CLM-005-29, POA&M register and incident-response support CLM-005-30).
The **admin console** alone remains unbuilt and unclaimed: its wireframes are
delivered and awaiting owner approval — the gate described above — and
CLM-005-13 stands draft. The one other open claim, CLM-005-31, is the DFARS flag
of §5: an owner/legal decision, not an engineering phase.

## 4. Record integrity

- **Append-only ledgers** (Axiomere): hash-chained, Ed25519-signed, with Merkle
  checkpoints. No update or delete operation exists in any plane; a tampered record
  fails verification from the exported bundle alone.
- **The audit bundle is the exit.** At any point — end of pilot, failed criterion,
  or the partner's unilateral decision — the partner receives the complete bundle
  (ledger, registration, claims, evidence, verdicts, manifest) plus the standalone
  verifier. Anchored roots on Zenodo/OSF are independently fetchable. A partner who
  leaves keeps everything they created and the ability to prove what the record
  said.
- **Retention posture, stated before any data moves:** retention is export +
  anchor + access restriction. There is no deletion workflow. Institutions whose
  governance requires deletion-on-demand should treat this as a gating fact, not a
  negotiable feature (pilot fit criterion F5).

## 5. Compliance posture

- **CMMC.** CMMC (32 CFR Part 170) certifies organizations and assessment
  boundaries, not products. Tekmerion claims **CMMC Level 2 alignment / compliance
  support** only. All 110 NIST SP 800-171 Rev 2 requirements are classified in a
  maintained responsibility matrix: **17 Platform** (satisfied by the product's
  construction), **51 Supports** (the platform provides the mechanism or evidence;
  the operator owns the remainder), **42 Organizational** (outside product scope,
  listed so nothing is silently dropped).
- **FIPS — open gap, stated plainly.** No cryptographic operation in the platform
  uses a FIPS 140-3 validated module today (§3.13.11: Supports — OPEN GAP). A
  twelve-operation cryptographic inventory is maintained; the gap is the seeded
  item in our POA&M planning (POA&M — plan of action and milestones, the formal
  gap register); the validated-module migration is a recorded owner
  decision awaiting a named CUI requirement. **Correction (2026-10-12):** the
  inventory now carries **thirteen** operations — row 13 (webhook egress payload
  signing, HMAC-SHA256) was added when signed incident-response event egress
  landed at Spec 005 E4. The §3.13.11 gap itself is unchanged, and the seeded
  POA&M item now exists as register item POAM-0001 (E6). The sentence above is
  retained as written, with this note, per the correction discipline.
  CUI is out of pilot scope for this
  reason. The hosted shape's DFARS 252.204-7012 question — whether it needs
  equivalency with FedRAMP (the federal cloud-security authorization program) — is a
  recorded open owner/legal decision; the self-hosted shape inside an existing
  compliant boundary is the capable CUI path meanwhile.
- **SOC 2.** We hold **no SOC 2 report**. Our claim is readiness and evidence
  mapping only — never certification — and the readiness-evidence build is
  specified, not yet built. The same honesty applies to FERPA and GDPR, which
  appear in product language only as design constraints, never as certifications.
  **Correction (2026-10-12):** the readiness-evidence build has since landed
  (Spec 005 E6, task T544): the SOC 2 readiness mapping
  (`specs/005-enterprise-platform/soc2-readiness-mapping.md`), the SPRS
  self-score machinery, and the POA&M register now exist as built artifacts.
  What has not changed: no SOC 2 report exists, and the claim remains readiness
  and evidence mapping only — never certification.

## 6. Public anchors — check these yourself

Each item is fetchable or runnable by the reviewer; none requires trusting our
summary of it.

| Anchor | What it evidences |
|---|---|
| Phase 7 evaluation bundle — Zenodo DOI [10.5281/zenodo.23319126](https://doi.org/10.5281/zenodo.23319126) | The pre-registered evaluation of the production pipeline (§7 below): five evidence questions, seeded defects, controls, verdicts as issued, standalone verification |
| OSF registration of the same study — project [dvrew](https://osf.io/dvrew/), registration [84dk7](https://osf.io/84dk7/), DOI [10.17605/OSF.IO/84DK7](https://doi.org/10.17605/OSF.IO/84DK7) | The registry-side anchor: the registration record itself states the bundle's anchor values (checkpoint root, bundle hash, registration hash); receipt and passed public verification are in our repo (`specs/010-osf-registration/records/`). Disclosed in place: the first submitted registration died in OSF's own archive step (provider-confirmed by OSF's failure notice) and the deposit resumed — no second project, no re-upload — to this registration. The failure semantics worked as specified, on a real provider failure |
| Worked study of contested public AI-mathematics claims — Zenodo DOI [10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259) | The decomposition discipline on real, contested claims. Verdicts as issued include **CONTESTED** (twice — both on attribution disputes, which cap the parent claim by doctrine), **INCONCLUSIVE** (twice), and one SUPPORTED. This study is the packet's evidence that the machinery reports "no" |
| First demo bundle — Zenodo DOI [10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479) | End-to-end export, standalone verification, and external anchoring. **Disclosed: this study's evaluation run was INVALID** — a control in the run was a no-op on its single-actor ledger, so no verdicts stand on it. The correction is carried on the public record itself, and the corrected bundle is anchored as version 2, DOI [10.5281/zenodo.23317023](https://doi.org/10.5281/zenodo.23317023), under the append-only correction discipline. We lead with this because it is the strongest evidence in the packet: the failure was found by our own controls, published by us, and corrected without editing history |
| Repository — github.com/AXIOVEX/tekmerion | Specifications, claims with falsifiers, assessments, audit reports (including the stage-model audit re-staging all prior work: checked vs. accepted vs. digested), and the records behind every statement above |

## 7. Measured results and the pilot's kill criteria

**Phase 7 evaluation (pre-registered; corpus and predictions frozen before the
run).** Five evidence questions; ten citations including a seeded fabricated DOI, a
seeded corrupted citation, a duplicate, and a shared-dataset pair. The run was
**VALID**; verdicts as issued: **supported, supported, inconclusive, contradicted,
inconclusive** — each by a distinct mechanism fixed in advance (pre-registered), all
five matching the pre-freeze predictions. Kill criteria measured: **K1 citation
reality — pass** (the
fabricated DOI was caught, set aside (quarantined), and excluded; zero fabricated
citations in the evidence basis); **K2 replay integrity — pass** (bundle-alone replay reproduces
the verdicts exactly; tamper cases detected — including one the evaluation itself
found in our verifier and that was fixed in-phase, disclosed in the report);
**K3 audit burden — pass** (a fresh-context auditor retraced all five verdicts from
the bundle alone in ~18 minutes against a 2-hour budget); **K4 origin honesty —
pass**; **K5 cost — pass** ($0.0012 per question against a $25 ceiling).
Stated caveat, from the report itself: one operator played all four actors, and
the second-review sample (one review) cannot acquit under the ≥5 rule.

**The pilot is measured by the same discipline.** These criteria were registered
before any partner was named; any one firing ends the pilot as a **published
failure**, recorded with its evidence — not renegotiated after the fact:

| # | Criterion | Threshold |
|---|---|---|
| P-K1 | Citation reality — exported citations resolving to real records | 100% |
| P-K2 | Replay integrity — independent replay vs. recorded verdicts | Any undetected divergence kills |
| P-K3 | Adjudicator burden — partner adjudicator, bundle alone, reaches every verdict's evidence + falsifier test | ≤ 2 hours |
| P-K4 | Origin honesty — derivative sources must not inflate evidence counts | Any inflation kills |
| P-K5 | Cost shape — marginal cost per pilot question | ≤ $25 |
| P-K6 | Operability — any load-bearing step the partner's staff cannot complete without our engineering intervention | Kills the pilot as a product test |

Success requires all of: the full loop completed with verdicts from a valid run;
the run **partner-operated** (the partner's adjudicator performs the freeze and
deposit approvals); an independent bundle-alone audit by the partner within the
P-K3 budget; and the partner's written close-out assessment — positive, negative,
or mixed — appended to the pilot record **unedited**. A declined assessment is
recorded as itself, not chased into a testimonial.

## 8. Support — what we promise and what we do not

One named Axiovex contact; business-hours response; issues logged into the pilot
record. **No SLA numbers are promised** — none can be evidenced at this scale, and
we do not claim service levels we have not operated. What is promised is narrower
and true: every pilot incident that touches the record — integrity, ledger
availability, deposit failures — is disclosed to the partner with its evidence,
whether or not it flatters us.

## 9. What we do not claim

Not in this packet, and not claimed in any pilot material: SOC 2 certification;
CMMC certification or compliance (alignment language only, §5); FIPS-validated
cryptography (§5); SCIM or automated deprovisioning availability; admin-console
availability; SLA figures; customer references (there are none yet — this pilot
would be the first); and any count of verdicts presented as a quality score. Our
doctrine forbids volume tallies standing in for understanding; every verdict we
issue states what remains not understood.

**Correction (2026-10-12):** one item in the list above has changed state since
this packet was assembled. **SCIM and automated deprovisioning** landed at Spec
005 E3 and are claim-supported (CLM-005-05, CLM-005-06, CLM-005-07); they are no
longer non-claims, and §3 as corrected states them as built. **Admin-console
availability** remains a true non-claim (unbuilt; owner wireframe gate).
Everything else in this section stands as written.

---

*Assembled 2026-10-12 from DESIGN §6 and the records it cites, updated to the
claims state of the same date (Spec 005 E2 SAML has landed since §6's identity row
was drafted; this packet follows the claims records). DRAFT — not sent anywhere.*
*Corrections appended 2026-10-12 after the Spec 005 E3/E4/E6 and Spec 012
landings (§3, §5, §9); the original statements are preserved in place with their
corrections, per this program's append-only correction discipline.*
