# SOC 2 Readiness Mapping — Spec 005 (T544)

**Status: READINESS MAPPING ONLY.** This document maps the AICPA
Trust Services Criteria (2017 TSC, CC series) to the platform
mechanisms and records that would serve as evidence inputs to a
future SOC 2 examination. **Axiovex holds no SOC 2 report, has
engaged no CPA firm, and claims no SOC 2 certification or
attestation of any kind.** SOC 2 is an attestation over an
*organization's* controls operated over time; a product document
cannot be one. Every entry below is labeled what it is: machinery
that exists, a record the platform produces, or an organizational
obligation the platform does not discharge. (CLM-005-16: readiness
only, never certification; CLM-005-23: the same honesty rule as the
CMMC framing.)

How to read an entry: **Mechanism / record** names code or a
maintained record — each is resolvable (the E6 test battery parses
this document and asserts every cited claim exists in
`specs/005-enterprise-platform/aee-claims.json` and every cited
code path exists in the repository). **Status** says which of
three honest things the entry is: *machinery* (built and tested),
*record* (a maintained document/ledger an auditor would consume),
or *organizational* (the operator's or vendor's own program —
named, never silently implied to be the platform's).

## CC1 — Organization and management

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC1.1 Integrity and ethical values | The claims-first development record itself: every material platform statement is a claim with a falsifier in `specs/005-enterprise-platform/aee-claims.json`, assessed by an independent evaluator; verdicts state what remains not understood | CLM-005-16, CLM-005-23 | record |
| CC1.2 Board oversight | Organizational — Axiovex governance; no platform mechanism is claimed | CLM-005-16 | organizational |
| CC1.3 Structure, authority, responsibility | Disjoint admin planes with a recorded role→action matrix: `src/tekmerion/platform/authz.py`; platform and tenant authority are separate by construction | CLM-005-09 | machinery |
| CC1.4 Competence | Organizational — hiring/training are the operator's and vendor's programs; role records evidence *who held which role when* (matrix row 3.2.1 basis) | CLM-005-24 | organizational |
| CC1.5 Accountability | Every privileged execution is an attributed ledger event (actor, action, outcome) in `src/tekmerion/platform/ledger.py`; the reconciliation join ties platform events to study appends per actor | CLM-005-22, CLM-005-26 | machinery |

## CC2 — Communication and information

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC2.1 Quality information | Append-only, hash-chained, signed audit ledgers are the platform's information substrate: `src/tekmerion/platform/ledger.py`; exports are standalone-verifiable (`src/tekmerion/platform/exports.py`) | CLM-005-15, CLM-005-26 | machinery |
| CC2.2 Internal communication | The spec/claims record is the internal channel of record for control changes: a phase exit updates claims, matrix, and assessments in the same commit (`specs/005-enterprise-platform/cmmc-responsibility-matrix.md` maintenance rule) | CLM-005-24 | record |
| CC2.3 External communication | Public surfaces are wording-swept against unqualified compliance claims (T547); readiness language only — this document is itself an instance | CLM-005-16, CLM-005-23 | record |

## CC3 — Risk assessment

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC3.1 Objectives | The enterprise spec's scope and non-goals are recorded (`specs/005-enterprise-platform/spec.md` §11); CUI/defense scope is explicitly gated on named requirements | CLM-005-31 | record |
| CC3.2 Risk identification | Per-phase red-team/assessment rhythm recorded in `specs/005-enterprise-platform/assessment-2026-10-12.md`; the crypto gap is a named, inventoried risk (`specs/005-enterprise-platform/crypto-inventory.md`) | CLM-005-25, CLM-005-30 | record |
| CC3.3 Fraud risk | Tamper-evidence is the fraud control: verification failures are first-class security events with signed egress (`src/tekmerion/platform/webhooks.py`) | CLM-005-26, CLM-005-30 | machinery |
| CC3.4 Change risk | Claims are re-assessed at every phase exit; a change that alters a control's basis re-opens its claim rather than inheriting its score | CLM-005-24 | record |

## CC4 — Monitoring activities

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC4.1 Ongoing/separate evaluations | Control states are maintained in SPRS-input form and recomputed deterministically (`src/tekmerion/platform/compliance.py`); per-phase AEE re-assessment is the separate evaluation | CLM-005-29 | machinery |
| CC4.2 Deficiency communication | The POA&M register (`src/tekmerion/platform/poam.py`) carries deficiencies as append-only items with milestones and status history; security-significant deficiencies egress as signed IR events | CLM-005-30 | machinery |

## CC5 — Control activities

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC5.1 Control selection | The CMMC responsibility matrix is the control-selection record for the 800-171 control set: 110 requirements, each classified with a stated basis | CLM-005-24 | record |
| CC5.2 Technology controls | Deny-by-default authorization, the append gate, and the session baseline are enforced in the service layer: `src/tekmerion/platform/authz.py`, `src/tekmerion/platform/gate.py`, `src/tekmerion/platform/baseline.py` | CLM-005-08, CLM-005-21 | machinery |
| CC5.3 Policies and procedures | Tenant security policy is recorded configuration (session lifetimes, custody, rate limits, detector thresholds), set by event, never by silent edit: `src/tekmerion/platform/directory.py` | CLM-005-21 | machinery |

## CC6 — Logical and physical access

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC6.1 Access restriction | Identity is IdP-asserted (OIDC + SAML) and bound to enrolled Ed25519 keys; no local passwords exist: `src/tekmerion/platform/oidc.py`, `src/tekmerion/platform/saml.py`, `src/tekmerion/platform/keys.py` | CLM-005-01, CLM-005-02, CLM-005-03 | machinery |
| CC6.2 Access provisioning | SCIM provisioning and the admin doors share one lifecycle core; provisioning never authenticates: `src/tekmerion/platform/scim.py`, `src/tekmerion/platform/service.py` | CLM-005-05, CLM-005-06 | machinery |
| CC6.3 Access removal | Deprovisioning ends new appends immediately while history stays verifiable; keys close with the identity | CLM-005-07 | machinery |
| CC6.4 Physical access | Organizational / hosting-provider — the residency pin records *where* a deployment runs (`src/tekmerion/platform/service.py`, T541); physical control is the provider's and is not claimed | CLM-005-12 | organizational |
| CC6.5 Media protection | Organizational; CUI marking on platform artifacts aids identification: `src/tekmerion/marking.py` | CLM-005-28 | organizational |
| CC6.6 Boundary protection | Webhook egress is allowlisted, signed, and replay-windowed; inbound surfaces are authenticated and rate-limited per tenant: `src/tekmerion/platform/webhooks.py`, `src/tekmerion/platform/baseline.py` | CLM-005-19, CLM-005-21 | machinery |
| CC6.7 Transmission protection | TLS-only transport posture is a recorded, enforced baseline; termination is deployment-owned and the matrix says so (row 3.13.4) | CLM-005-21, CLM-005-24 | machinery |
| CC6.8 Malicious-code prevention | Organizational (deployment endpoints/servers); the platform's contribution is a minimal, deny-by-default service surface | CLM-005-24 | organizational |

## CC7 — System operations

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC7.1 Vulnerability management | Vendor-side: the codebase is continuously test-built in CI and releases are signed, anchored records; deployment scanning is the operator's (matrix rows 3.11.2/3.11.3) | CLM-005-24 | record |
| CC7.2 Anomaly monitoring | Security-event detectors (auth-failure bursts, revocation storms, break-glass use, audit-verification failures) fire signed egress events: `src/tekmerion/platform/webhooks.py` | CLM-005-30 | machinery |
| CC7.3 Incident evaluation | Break-glass use auto-creates a post-use review item; every step of an invocation is a marked event in both ledgers: `src/tekmerion/platform/breakglass.py` | CLM-005-14, CLM-005-30 | machinery |
| CC7.4 Incident response | Organizational incident process; the platform's duty is evidence: complete, exportable, tamper-evident records (`src/tekmerion/platform/exports.py`) | CLM-005-15, CLM-005-30 | organizational |
| CC7.5 Recovery | Organizational / deployment — no backup or restore claim is made for the platform; the ledger format is forward-readable and exports are the recovery record | CLM-005-12 | organizational |

## CC8 — Change management

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC8.1 Change authorization | Spec-kit + AEE flow: claims precede code, wireframes gate UI change (constitution Article XIV), phase exits re-assess — the change record is `specs/005-enterprise-platform/` itself | CLM-005-24 | record |

## CC9 — Risk mitigation

| Criterion | Mechanism / record | Claims | Status |
|---|---|---|---|
| CC9.1 Business disruption mitigation | The self-hosted shape runs the same codebase inside the institution's own boundary — the recorded continuity answer while hosted-shape questions stand open: `src/tekmerion/platform/packaging.py` | CLM-005-12, CLM-005-31 | machinery |
| CC9.2 Vendor management | Organizational — subprocessor and vendor review are the operator's program; the platform's vendor-facing posture is the readiness packet discipline this document belongs to | CLM-005-16 | organizational |

## What this mapping does not do

- It does not assert that any criterion is *satisfied* — SOC 2
  conclusions belong to a CPA firm's examination over an operating
  period, and none has occurred.
- Availability (A), Confidentiality (C), Processing Integrity
  (PI), and Privacy (P) criteria beyond the CC series are not
  mapped here; the CC series is the common core, and extending
  the mapping is future readiness work, not an implied claim.
- FERPA and GDPR appear in platform language only as design
  constraints, never as certifications (CLM-005-16) — no entry
  above should be read as a FERPA/GDPR compliance statement.
