# Data Processing Addendum — Tekmerion Pilot (TEMPLATE DRAFT)

**DRAFT TEMPLATE — for owner/counsel review — not yet adopted, not offered to any
institution, and not legal advice.** Prepared by a non-lawyer from the program's own
records, 2026-10-12. **Closes:** HECVAT register item 13 (with
`PRIVACY-NOTICE-DRAFT.md`); carries the no-training contract term for register
item 14 (§12). **Sources:** `docs/pilot/DESIGN.md` (§2.3, §5.4, §5.5),
`specs/005-enterprise-platform/spec.md` (§§3–4, §8), DN-005, Axiomere DESIGN §6.
Every bracket is a fact, name, period, or legal choice only the owner/counsel can
supply. Nothing bracketed has been invented.

---

This Addendum is between **[INSTITUTION — COUNSEL TO COMPLETE]** ("Controller") and
Axiovex Systems, LLC ("Processor") and forms part of the Tekmerion pilot agreement
(the "Agreement").

## 1. Subject matter and duration

The Processor processes personal data solely to operate the Tekmerion pilot: one
evidence question run end-to-end (register claims with falsifiers → retrieve
published-literature evidence → freeze → evaluation → verdicts → audit bundle →
external anchor), plus tenant identity administration and audit-record keeping.
Duration: the pilot term, plus the retention outcomes in §10.

## 2. Nature and purpose of processing

Hosting/operation of the platform plane (identity, authorization, tenancy, audit
ledger) and the study plane (claim register, evidence retrieval from scholarly
sources, verdict issuance, bundle export, registry anchoring) as specified in the
pilot design. No other purpose is authorized; §12 states the prohibitions
expressly.

## 3. Types of personal data and data subjects

- **Data subjects:** the Controller's staff and named collaborators who hold
  platform identities (researcher / reviewer / adjudicator / integrity roles).
- **Data:** directory identity data (name, email, IdP subject, affiliation as
  asserted by the Controller's IdP); key enrollment records (public-key
  fingerprints); content those persons author for the record (claim statements,
  falsifiers, adjudication rationales); audit events keyed by a random actor ID.
- **Scope exclusions (obligations, not aspirations).** The pilot takes **no** PHI or
  human-subjects raw data, **no** CUI, **no** student education records, **no**
  payment-card data, and no content whose licence basis cannot be recorded. If
  out-of-scope data is transmitted to the Processor, the Processor will notify the
  Controller, quarantine it from the study record, and follow the Controller's
  instructions — it will not be appended to a ledger.

## 4. Documented instructions

The Processor processes personal data only on documented instructions from the
Controller (including this Addendum and the pilot design's operating procedures),
unless required by law to do otherwise, in which case the Processor informs the
Controller before processing where lawful. Configuration acts by the Controller's
tenant administrators through the platform's recorded admin actions are documented
instructions.

## 5. Confidentiality and personnel

Persons authorized to process personal data are bound by confidentiality duties
and act under role-based authorization (deny-by-default; platform-admin,
tenant-admin, and study planes are disjoint). **[OWNER TO CONFIRM: personnel
program facts — screening and training are organizational facts (HECVAT register
item 11, owner-supplied) and must be true before this section is finalized.]**

## 6. Security measures (summary; Annex II controls detail)

- Authentication only via the Controller's IdP (OIDC authorization code + PKCE
  S256, or SAML 2.0 with signed assertions); **no local passwords**; MFA performed
  at the IdP and enforced platform-side, with step-up for verdict-signing and
  admin actions.
- Every record append is signed with an Ed25519 key enrolled to an IdP identity
  (proof of possession at enrollment); enrollment, rotation, and revocation are
  appended ledger events; deprovisioning closes keys to new appends at the next
  authenticated request.
- Append-only, hash-chained, Merkle-checkpointed ledgers for study and platform
  audit records; **no update or delete operation exists in any plane**; tampering
  fails verification from an exported bundle alone.
- Secrets (IdP credentials, API keys) held in a secrets store / by reference;
  API-key secrets hashed at rest; only fingerprints appear in records.
- Disclosure carried into this contract deliberately: **the Processor holds no
  SOC 2 report**, and **no cryptographic operation uses a FIPS 140-3 validated
  module** today (inventory: `specs/005-enterprise-platform/crypto-inventory.md`;
  the gap is a seeded POA&M item). The Controller accepts these stated facts as the
  security posture for a pilot whose scope excludes CUI and PHI.

## 7. Subprocessors

The Processor uses the subprocessors in Annex III (`SUBPROCESSOR-INVENTORY-DRAFT.md`,
incorporated by reference and versioned). The Controller gives general
authorization for that list. The Processor will give **[30 days' — OWNER TO
CONFIRM]** notice of any addition or replacement touching Controller data, during
which the Controller may object on reasonable data-protection grounds; if the
objection cannot be resolved, the Controller may terminate the pilot under §10's
exit terms. Flow-down: each subprocessor is bound to data-protection terms no less
protective than this Addendum, to the extent of its function.

## 8. International transfers

**[PENDING HOSTING DECISION + COUNSEL: the operating deployment is not yet named
(see `HOSTING-FACTS-MEMO.md`); transfer mechanisms (SCCs / UK IDTA / adequacy) to be
completed once it is. Registry anchoring (Zenodo/CERN; OSF/Center for Open Science)
occurs only for content with a recorded licence basis and, for Controller content,
in the least-public anchored form absent written Controller direction.]**

## 9. Assistance

The Processor will, taking into account the nature of the processing: (a) assist
with data-subject requests affecting directory data (access, rectification,
erasure of off-ledger data); (b) assist with the Controller's security, breach, and
assessment duties by producing the platform's own records — exported audit bundles
and platform audit exports are standalone-verifiable and are the primary audit
evidence; (c) make available the records cited in the pilot evidence pack. Audit
access beyond those records is **[COUNSEL TO COMPLETE: scope/frequency]**.

## 10. Return, exit, and the deletion clause — stated precisely

- **Exit is the bundle.** At any time, and at termination for any reason, the
  Processor will deliver the complete audit bundle (byte-for-byte ledger,
  registration, claims, evidence, verdicts, manifest, standalone verifier).
  Anchored roots remain independently fetchable.
- **Off-ledger personal data** (identity directory, session stores) will be deleted
  within **[OWNER TO CONFIRM]** days after termination, except where retention is
  legally required; deletion of the directory identity does not require touching
  any ledger.
- **On-ledger content is not deletable — by design, and the Controller accepts
  this as a pilot precondition** (pilot fit criterion F5, confirmed before any data
  moves). Ledgers contain no names or emails; attribution persists via random
  actor IDs and key fingerprints.
- **Erasure-certificate mechanism — status disclosure.** The record layer's design
  specifies one erasure path, for documented legal compulsion only: an
  owner-signed erasure certificate appended to the chain plus destruction of the
  affected record's per-record encryption key, leaving the chain verifiable
  (Axiomere DESIGN §6; DN-005). **That mechanism is specified but not yet
  executable**: it awaits per-record payload encryption at ingest (record-layer
  task Axiomere T112, open). The Processor does not warrant its availability
  during the pilot term; if it becomes executable, the Processor will notify the
  Controller. If a legal erasure duty reaches ledger content before then, the
  Processor will apply every measure that exists (directory erasure, access and
  key closure, export restriction), disclose the residual limit plainly, and
  record the request and response as appended records.

## 11. Personal-data breach notification

The Processor will notify the Controller without undue delay, and in any case
within **[72 hours — OWNER TO CONFIRM; align with
`INCIDENT-RESPONSE-PLAN-DRAFT.md`]**, after confirming a personal-data breach
affecting Controller data, with the facts then known, the evidence (the platform's
events are ledgered and exportable), measures taken, and updates as assessment
continues. Incidents touching the record are disclosed with their evidence whether
or not they meet a regulatory threshold — that is the product's standing posture.

## 12. AI and secondary-use prohibitions (contract term)

- The verdict machinery is deterministic production code, not a trained model.
- The Processor will **not** use Controller data (including study content and
  directory data) to train, fine-tune, or evaluate any model; will not perform
  cross-tenant analytics over study content; and will not use Controller data for
  any purpose other than §2. (Platform posture: Spec 005 §8.)
- Where the Controller operates agent tooling (e.g. the MCP surface) under its own
  named roles, those acts are the Controller's documented instructions; every such
  action is attributed and ledgered like a human's. The Processor's AI governance
  statement is `AI-GOVERNANCE-STATEMENT-DRAFT.md`.

## 13. Precedence, liability, governing law

**[COUNSEL TO COMPLETE.]** In conflict, this Addendum prevails over the Agreement
for personal-data processing.

## Annexes

- **Annex I** — Details of processing: §§1–3 of this Addendum.
- **Annex II** — Technical and organizational measures: §6 of this Addendum, plus
  the platform records it cites (Spec 005 claims/assessments; crypto inventory).
- **Annex III** — Subprocessors: `SUBPROCESSOR-INVENTORY-DRAFT.md` (versioned).

---

*Template draft prepared from repo records only, 2026-10-12. Not legal advice; no
legal effect until reviewed by counsel, completed, and executed.*
