# Privacy Notice — Tekmerion Pilot Service (DRAFT)

**DRAFT — for owner/counsel review — not yet adopted, not published, and not a
commitment to any institution.**
**Date:** 2026-10-12 · **Prepared by:** a non-lawyer, from the program's own
records · **Closes:** HECVAT register item 13 (with `DPA-TEMPLATE-DRAFT.md`) ·
**Sources:** `docs/pilot/DESIGN.md` (§2.3, §5.4), `specs/005-enterprise-platform/spec.md`
(§4 PII placement, §8 GDPR posture), `docs/install.md`, Spec 009 records. Bracketed
markers are facts or decisions only the owner/counsel can supply; nothing bracketed
has been invented.

---

## 1. Who we are

Axiovex Systems, LLC ("Axiovex", "we") provides Tekmerion, a research engine for
evidence questions. Privacy contact: **[OWNER-TO-NAME: named privacy contact and
email]**. (HECVAT register items 1–2 — company profile facts and named contacts —
are owner-supplied and outstanding; this notice cannot be finalized until they are.)

## 2. Deployment status — read this first

Tekmerion is today delivered as installable software packages (built from our public
repositories) that run on machines operated by the institution or the operator; there
is **no production Axiovex-operated cloud hosting of Tekmerion today**. An
Axiovex-hosted multi-tenant deployment is specified, and the pilot design prefers
the hosted shape, but the hosting decision has not been taken (see
`HOSTING-FACTS-MEMO.md`). This notice is drafted for the pilot service; the sections
on transfers and subprocessors will be re-issued in final form when the operating
deployment is named.

## 3. What personal data we process

- **Directory / account data.** Names, email addresses, IdP subject identifiers, and
  affiliation attributes exactly as asserted by the partner institution's identity
  provider at sign-in. There are no local passwords; we store none.
- **Key enrollment records.** Public-key fingerprints bound to an identity through a
  recorded enrollment. (Private keys are never transmitted to or stored by the
  platform in self-custody mode.)
- **Study content.** Claim statements, falsifiers, and adjudication rationales
  authored by partner staff, and published-literature metadata/content retrieved
  under a recorded licence basis. Study content is authored for the record; ledger
  payloads carry a stable random actor ID and key fingerprints — **never names or
  email addresses**.
- **Platform audit records.** Event type, actor ID, timestamp, target, and outcome
  for authentication, authorization, administrative, and key-lifecycle events.
- **Support communications.** Emails and issue reports sent to us.

**Out of scope by design:** we do not accept, and the pilot does not process, PHI or
patient-level data, human-subjects raw data, CUI, student education records, or
payment-card data. Content whose licence basis cannot be recorded is not stored.

## 4. Purposes and basis

We process the above only to operate the study workflow (register → freeze →
verdicts → audit bundle → external anchor), to authenticate and attribute record
actions, to maintain the audit record, and to provide support. Processing is
performed on the instructions of the partner institution under the pilot agreement
and the Data Processing Addendum (`DPA-TEMPLATE-DRAFT.md`); the institution directs
the processing of partner data. **[COUNSEL TO CONFIRM: legal-basis wording per
jurisdiction.]**

We do **not** sell personal data, use it for advertising, or use partner data —
including study content — to train or fine-tune any model. There is no cross-tenant
analytics over study content.

## 5. Sharing and public anchors

- **Subprocessors** are listed in `SUBPROCESSOR-INVENTORY-DRAFT.md` (code hosting/CI,
  public registries, scholarly-metadata APIs). Scholarly APIs receive only
  published-literature queries (DOIs and bibliographic search terms) — never partner
  personal data.
- **Public registries (Zenodo, OSF).** A study's audit bundle is deposited or
  registered only where a recorded licence basis covers that content. Partner
  content defaults to the least-public anchored form (embargoed/private with public
  anchor values) until the partner directs otherwise **in writing**.

## 6. Retention

The study record is **append-only by constitutional design and is not deleted**
(see §7). At any point the partner may obtain the complete audit bundle — the exit
is the bundle, not a summary. Directory and session data (off-ledger) are retained
per the tenant's policy and the pilot agreement and are deletable under ordinary
data controls. **[OWNER TO CONFIRM: off-ledger retention periods.]**

## 7. Your rights — including the honest erasure answer

You may request access to, and rectification of, your directory data at any time;
rectification of the identity directory never requires touching the study record.

**Erasure requires a precise answer, and we give it rather than a comfortable one.**
Off-ledger personal data (directory entries, session stores) can be erased on a
valid request, and deprovisioning ends a person's access and closes their keys to
new appends immediately. Content already appended to a study or platform ledger
**cannot be deleted or altered** — that immutability is the product's premise, is
disclosed to partners before any data moves (pilot fit criterion F5), and is why
personal data is kept out of ledger payloads in the first place.

The record design specifies exactly one exception, for documented legal compulsion
only: an owner-signed **erasure certificate** appended to the chain with destruction
of that record's encryption key (Axiomere DESIGN §6; DN-005). **That mechanism is
specified but not yet executable** — it depends on per-record payload encryption at
ingest, which is open work in the record layer (Axiomere task T112). We will not
promise it until it exists. If a legal erasure duty reaches ledger content in the
meantime, we will say so plainly, apply every measure that does exist (directory
erasure, access closure, export restriction), and record the request and our
response as an appended record.

## 8. Security (summary)

Identity only through the tenant's IdP (OIDC / SAML 2.0) with MFA enforced
platform-side; every record append signed (Ed25519) and hash-chained in append-only
ledgers with Merkle checkpoints; authorization deny-by-default against a role
matrix; secrets held by reference/fingerprint, never in ledgers. Two disclosures we
make everywhere, including here: **we hold no SOC 2 report**, and **no cryptographic
operation in the platform uses a FIPS 140-3 validated module** (full inventory in
`specs/005-enterprise-platform/crypto-inventory.md`; the gap is a recorded, seeded
POA&M item).

## 9. International transfers

Depends on the operating deployment, which is not yet decided
(`HOSTING-FACTS-MEMO.md`). Registry deposits (Zenodo/CERN, OSF) occur only under §5.
**[PENDING HOSTING DECISION + COUNSEL: transfer mechanisms.]**

## 10. Changes to this notice

This notice is versioned in our public repository. Material changes will be
announced to pilot partners **[OWNER TO CONFIRM: notice period]** before taking
effect.

---

*Draft prepared from repo records only, 2026-10-12. Not legal advice; no legal
effect until reviewed by counsel and adopted by the owner.*
