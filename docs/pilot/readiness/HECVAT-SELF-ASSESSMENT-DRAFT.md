# HECVAT Self-Assessment — Tekmerion, Hosted Shape (DRAFT)

**Status: DRAFT — internal preparation only; not submitted to any institution.**
Prepared 2026-10-12. Purpose: when a partner's vendor review runs on the HECVAT (Duke's
does — `DOSSIER-DUKE.md` §2), our answers exist in advance, drafted against the
instrument rather than improvised under a deadline.

**Basis and its limits — read first.**

- The instrument is the **HECVAT 4** (Higher Education Community Vendor Assessment
  Toolkit, © EDUCAUSE). HECVAT 4 unified the former Full / Lite / On-Prem versions
  into a single workbook; a "Lite" evaluation reviews the questions marked with an
  asterisk (Critical importance) in the Institution Evaluation and Privacy Analyst
  Evaluation tabs, with scores aggregated in the High Risk Evaluation tab
  (EDUCAUSE, *HECVAT FAQs for Higher Education* and *How to Use the HECVAT*,
  educause.edu). Duke accepts **only version 4**, as an Excel workbook with all tabs
  intact.
- The workbook itself is distributed by EDUCAUSE and was not reproduced here. This
  draft is therefore structured on the **published category set**: the HECVAT 4
  section structure (Start Here · Organization · Product · Infrastructure ·
  IT Accessibility · Case-Specific · AI · Privacy, per the public v4 form
  structure) and the published critical-question category codes (AAAI, APPL, DATA,
  etc.). **Item wordings below are topic paraphrases, not verbatim HECVAT
  questions.** When the actual workbook is completed for a submission, answers are
  transcribed item-by-item and re-verified against the records cited.
- **Answer rule.** Every answer below derives from Tekmerion's own records: Spec 005
  claims and assessments (`specs/005-enterprise-platform/`), the CMMC responsibility
  matrix, the cryptographic inventory, and the pilot design (`docs/pilot/DESIGN.md`).
  Where the records cannot answer, the item is marked **NOT YET ANSWERABLE** with
  what would close it. Nothing is answered from intention.
- **Why accuracy is the whole game at Duke:** Duke's published process has the
  vendor *warrant* that services conform to its HECVAT responses, with material
  deficiency deemed a material breach (`DOSSIER-DUKE.md` §2.1). An optimistic answer
  in this draft is a future breach term, not a sales asset. The same discipline is
  applied for every institution.

**Scope of this draft:** the hosted shape (Axiovex-operated multi-tenant deployment,
DESIGN §5.1 / DN-003) and the pilot data scope only (DESIGN §2.3): published
literature and its metadata under recorded licence basis, partner-authored claim
statements / falsifiers / adjudication rationales, and partner reviewer identities in
the platform directory. **Out of scope by design: PHI, CUI, student education
records, payment-card data, unpublished or access-restricted corpora.**

---

## 1. Start Here — vendor and product identification

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| Vendor legal name | Axiovex Systems, LLC | Repo licence/identity records (LICENSE, © 2026 Axiovex Systems, LLC) | Answered |
| Product | Tekmerion — an evidence-claims research engine: claims are registered with falsifiers, evidence is provenance-tracked and hash-verified, verdicts are issued against frozen registrations, and every study exports a standalone-verifiable audit bundle anchored to public registries (Zenodo, OSF) | Specs 001/002; DESIGN §6 anchors | Answered |
| Deployment model assessed | Hosted SaaS, multi-tenant, one codebase shared with the self-hosted shape | DN-003; CLM-005-12 (draft) | Answered |
| Data processed in this scope | As scoped above; **no PHI, no CUI, no FERPA records, no cardholder data** | DESIGN §2.3 | Answered |
| Company profile (headcount, founding date, HQ, ownership, financial-stability evidence) | — | Not present in repo records | **NOT YET ANSWERABLE** — owner supplies company facts |
| Named security/privacy contacts | — | Not present in repo records | **NOT YET ANSWERABLE** — owner names contacts |

## 2. Organization — security program, assessments, documentation (PPPR · DOCU · THRD)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| Documented security governance | Development is governed by a written constitution and a claims-first specification process: every material claim carries a falsifier and is assessed before and after implementation; UI changes are gated on approved wireframes. This dossier's answers cite those records item by item | Program constitution; Specs 001–010 assessment records | Answered (as process evidence) |
| SOC 2 report | **We do not hold a SOC 2 report of any type.** The product claims SOC 2 *readiness and evidence mapping only — never certification*; the readiness-evidence build is specified (Spec 005 E6) and not yet built. We will not represent otherwise, to any institution, at any stage | CLM-005-16 (posture); DESIGN §6 ("Explicitly not in the pack… SOC 2 certification") | Answered — the answer is No, stated |
| ISO 27001 / other certifications | None held; none claimed | Same posture | Answered — No, stated |
| Independent penetration test | No infrastructure penetration-test record exists. Design-level red teams of the assessment methodology exist in the program record (RED-TEAM-01/02, cited in the matrix at 3.13.2) — those are methodology red teams, **not** penetration tests, and are not offered as substitutes | Matrix 3.13.2 basis | **NOT YET ANSWERABLE** — closes with a scoped pen test of the hosted deployment + report |
| Vulnerability management | The codebase is continuously test-built in CI; vendor patch releases are signed, anchored records. Hosted-deployment vulnerability scanning (tooling, cadence) is not recorded | Matrix 3.11.2/3.11.3 (Supports) | Partial |
| Business continuity / disaster recovery | No BCP/DR plan or test record exists in the platform records. The record layer is content-addressed and exportable (the audit bundle is the exit, DESIGN §5.5), which bounds data-loss semantics for study records, but that is not a DR plan | DESIGN §5.5 | **NOT YET ANSWERABLE** — closes with a documented BCP/DR + recovery exercise for the hosted deployment |
| Incident response | Every pilot incident touching the record (integrity, ledger availability, deposit failures) is disclosed to the partner with its evidence; no SLA numbers are promised, because none can be evidenced at this scale. Platform security events are ledgered and exportable; signed IR event egress is specified (E4) and the POA&M register is E6 — neither is built yet. A contractual notification *timeline* cannot be stated from current records | DESIGN §5.3; CLM-005-30 (draft) | Partial — disclosure commitment answered; **timeline NOT YET ANSWERABLE** |
| Personnel security (screening, role-based training) | Classified Organizational across the matrix (3.2, 3.9 families): role records evidence who held which role when; no vendor personnel-program record exists in the repo | Matrix 3.2/3.9 | **NOT YET ANSWERABLE** — owner supplies HR-side facts |
| Subprocessors | No subprocessor inventory exists in the records | — | **NOT YET ANSWERABLE** — closes with a maintained subprocessor list for the hosted deployment |
| Hosting provider and regions | The hosted shape is operated by Axiovex (DN-003); the underlying infrastructure provider and regions are **not named in the platform records**, and per-tenant residency is a configuration concept (residency pin) in a draft claim | DN-003; CLM-005-12 (draft) | **NOT YET ANSWERABLE** — closes with the deployment record naming provider/regions; note Duke's process requires working *with* the host on hosting-specific answers |

## 3. Product — application and service security (APPL · AAAI · CHNG · VULN)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| User authentication | Human users authenticate **only** through the tenant's own external IdP. OIDC (authorization code + PKCE S256): supported. SAML 2.0 service provider with per-tenant IdP configuration (metadata import, attribute mapping): supported. **There are no local passwords; the platform stores none** | CLM-005-01, CLM-005-02 (supported); matrix 3.5.7–3.5.10 | Answered |
| MFA | Interactive access requires MFA performed at the tenant IdP, enforced platform-side: the platform requires MFA evidence (`acr`/`amr`, incl. REFEDS MFA profile on the SAML path) and refuses step-up-sensitive actions without it | CLM-005-27 (supported) | Answered |
| Authorization | Every read and mutation is authorized in the service layer against a role matrix (researcher / reviewer / adjudicator / integrity, plus disjoint platform-admin and tenant-admin planes); deny-by-default; no anonymous mutation path | CLM-005-08 (supported); CLM-005-09 (partially_supported) | Answered / plane-separation Partial |
| Record integrity & signing | Every accepted append is **signed by an Ed25519 key enrolled to an IdP identity** (issuer + subject) through a recorded enrollment with proof of possession. Enrollment, rotation, and revocation are appended events; rotation supersedes without breaking verification of history | CLM-005-03 (supported); CLM-005-04 (partially_supported) | Answered / lifecycle Partial |
| Sessions | Idle (30 min) and absolute (12 h) session lifetimes, tenant-configurable downward; TLS-only transport | Spec 005 §9; matrix 3.1.11 (Platform). Session-baseline claim CLM-005-19 is draft | Partial |
| Programmatic access | Scoped, expiring, revocable API keys/service accounts; scopes cannot exceed the role matrix; secrets are hashed at rest (SHA-256) and never written to ledgers (fingerprints/references only) | CLM-005-18 (supported); crypto inventory #8 | Answered |
| Provisioning / deprovisioning automation | **Not yet a supported capability.** SCIM 2.0 provisioning and the automated deprovisioning pipeline are draft claims with a build phase in flight (E3); today, lifecycle is IdP-driven plus platform administration. Deactivation, once effected, is refused at the next authenticated request by the E1 gate | CLM-005-05, CLM-005-06 (draft); matrix 3.1.8/3.5.6 | **NOT YET ANSWERABLE** as a capability — stated as in-flight, not claimed |
| Change management | Claims-first change process: falsifiers and assessments per change; wireframe gate for UI (constitution Article XIV); CI-gated merges; signed release history is the vendor-side change evidence | Matrix 3.4.3/3.4.4 (Supports) | Answered (as process) |
| Audit logging | A platform audit ledger — append-only, hash-chained, Ed25519-signed, Merkle-checkpointed — records the SP 800-171 §3.3.1/§3.3.2 event classes (account creation/modification, authentication incl. failures, authorization decisions incl. denials, admin actions, key lifecycle), each with actor, type, timestamp, target, outcome. **No update or delete operation exists in any plane**; tampering fails verification from an exported bundle alone. Event-class completeness is partially_supported (E6 completes the set); audit export follows the audit-bundle pattern (draft claim) | CLM-005-26 (partially_supported); CLM-005-15 (draft); matrix 3.3 family | Answered in core; completeness Partial |

## 4. Infrastructure and data (DATA · DCTR · FIDP)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| Encryption in transit | TLS is required on every service path; HTTP is refused or redirected | Spec 005 §9; matrix 3.13.4 (Supports — termination point is deployment-owned) | Answered (requirement); deployment termination detail Partial |
| Encryption at rest | Study-ledger files are operator storage; at-rest encryption is the deployment's storage layer. Content-level (payload) encryption of ledger records is a **recorded dependency that has not landed** (Spec 002 T223); it is not claimed | Matrix 3.13.16 (Supports) | Partial — gap stated |
| Cryptographic validation (FIPS 140-3) | **No cryptographic operation in the platform uses a FIPS 140-3 validated module.** All twelve inventoried operations (SHA-256 hash chains and Merkle checkpoints, Ed25519 signatures, RS256/XML-DSig verification, PKCE, secret hashing, key fingerprints) are implemented in non-validated modules (Rust `sha2`/`ed25519-dalek`; pure-Python service-layer implementations, prototype-grade). A full inventory is maintained (`specs/005-enterprise-platform/crypto-inventory.md`); the gap is the seeded item in the platform's POA&M planning, and the validated-module migration is recorded as an owner decision awaiting a named CUI/defense requirement | Crypto inventory (all rows "No"); matrix 3.13.11 "Supports — OPEN GAP"; CLM-005-25 (supported — the no-false-claim claim) | Answered — the answer is a disclosed No |
| Data scope controls | Per-source licence basis is recorded before content is stored (query / store / redistribute recorded separately); content a source does not permit redistributing is replaced by its provenance stub in any export, visibly | DESIGN §2.3/§5.4 (WS5 discipline) | Answered |
| Data return at exit | **The audit bundle is the exit:** at any point the partner receives the complete bundle — byte-for-byte ledger, registration, claims, evidence, verdicts, manifest, and a standalone verifier that checks it without us. Anchored roots remain independently fetchable | DESIGN §5.5 | Answered |
| Data deletion | **There is no deletion workflow.** Retention is export + anchor + access restriction only; the record is append-only by constitutional design, and this is disclosed to partners *before* any data moves (pilot fit criterion F5) | CLM-005-17 (draft); DESIGN §2.2 F5, §5.4 | Answered — the answer is No, with the posture stated |
| Backups | No backup schedule, retention, or restore-test record exists for the hosted deployment in the platform records | — | **NOT YET ANSWERABLE** |
| Network controls of the hosted deployment | The application layer is deny-by-default; deployment network rules are the operator's layer and are not recorded in the platform records | Matrix 3.13.6 (Supports) | **NOT YET ANSWERABLE** for the hosted deployment record |
| Infrastructure monitoring | Platform-plane security events are ledgered and exportable; hosted-infrastructure monitoring / security-event monitoring (SIEM) is not recorded | Matrix 3.14.6/3.14.7 (Supports) | **NOT YET ANSWERABLE** |

## 5. IT Accessibility (ITAC)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| WCAG conformance / VPAT | The partner-facing UI is server-rendered and wireframe-governed, but **no accessibility audit or VPAT (the standard accessibility conformance report) exists in the records, and no conformance level is claimed.** Duke's process names Web Accessibility as a possible additional review; we would enter it with this gap stated, not papered over | Phase 6 records (UI built; no accessibility assessment recorded) | **NOT YET ANSWERABLE** — closes with a WCAG audit of the shipped UI |

## 6. Case-specific (HIPA · PCID · FERPA · CMMC)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| HIPAA | Not applicable to the pilot scope: no PHI is accepted, by design; no BAA (business associate agreement) is offered for the pilot. If a future scope required PHI, it would be a different engagement with its own assessment | DESIGN §2.3 | Answered (scope exclusion) |
| PCI DSS | Not applicable: no payment-card data is processed | DESIGN §2.3 | Answered (scope exclusion) |
| FERPA | FERPA appears only as a design constraint in product language; no student education records are in pilot scope. The product never claims "FERPA compliance" as a certification | CLM-005-16 | Answered |
| CMMC / DFARS | CMMC (32 CFR Part 170) certifies organizations and assessment boundaries, **not products**; Tekmerion claims **CMMC Level 2 alignment / compliance support** only. All 110 NIST SP 800-171 Rev 2 requirements are classified in a maintained responsibility matrix (Platform / Supports / Organizational). §3.13.11 (FIPS) is an open gap (§4 above); CUI is out of pilot scope for exactly this reason; the hosted shape's DFARS 252.204-7012 FedRAMP-equivalency question is a recorded open owner/legal decision | CLM-005-23/24 (draft — the matrix exists and is maintained; the claims' own status is draft and is reported as such); CLM-005-31 (draft) | Answered as posture |

## 7. AI (AIGN · AIPL · AISC · AIML · AILM · DPAI)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| Where AI sits in the product | The verdict machinery is deterministic production code: registered claims, rule-based evaluation, recorded controls. LLM-based agents may *operate* the platform through its MCP surface and agent skill (Spec 009) under named human roles; the governing doctrine keeps two lanes separate — machine-speed verification never displays as human-paced acceptance, and adjudication acts (freeze, deposit approval) are named-human acts in the record | Specs 002/009; DN-010 two-lane doctrine | Answered (architecture) |
| Training on partner data | No model-training pipeline exists in the specced architecture, and no partner data is needed to train anything for the pilot. A contractual no-training commitment, however, is not recorded in the platform records | — | **NOT YET ANSWERABLE** as a commitment — closes with an explicit platform statement/contract term |
| AI governance policy | No standalone AI governance policy document exists in the records; the operative controls are the two-lane doctrine and the human-act gates above | DN-010 | **NOT YET ANSWERABLE** as a policy document |

## 8. Privacy (PCOM · PTHP · PDAT · PRPO)

| Item (topic) | Draft answer | Basis | State |
|---|---|---|---|
| Personal data processed | Partner reviewer identities in the platform directory (name/IdP subject as the tenant provides); ledger payloads carry no PII beyond what the record requires — identities live in the directory, never in ledger payloads; deprovisioning ends access without touching the record | DESIGN §2.3, §5.4 | Answered |
| Privacy notice / DPA | No published privacy notice or DPA template exists in the repo records | — | **NOT YET ANSWERABLE** — closes with executed privacy notice + DPA template |
| Breach notification | Record-touching incidents are disclosed to the partner with evidence (DESIGN §5.3); a contractual notification timeline is not recorded | DESIGN §5.3 | Partial (see §2, incident response) |
| Data residency | Per-tenant residency is a design concept (residency pin, draft claim); the hosted deployment's actual regions are not recorded (§2, hosting) | CLM-005-12 (draft) | **NOT YET ANSWERABLE** |

---

## 9. The NOT YET ANSWERABLE register (consolidated work product)

Each item names what closes it. Until closed, the honest submission answer is the
gap statement in the tables above — at Duke, that is a warranty we can keep.

1. **Company profile facts** (headcount, founding, HQ, financials) — owner supplies.
   (A drafted entry exists below, 2026-10-12 — pending owner confirmation; until
   confirmed, this item remains not yet answerable as stated.)
2. **Named security/privacy contacts** — owner names. (A drafted entry exists
   below, 2026-10-12 — pending owner confirmation.)
3. **Hosting provider, regions, and host certifications** — deployment record.
4. **Subprocessor inventory** (and change-notification process) — maintained list.
5. **Backup schedule/retention and restore tests** for the hosted deployment.
6. **Business continuity / disaster recovery plan** and exercise records.
7. **Independent penetration test** of the hosted deployment (design red teams do
   not substitute).
8. **Hosted-deployment vulnerability scanning** tooling and cadence.
9. **Hosted network controls and infrastructure monitoring/SIEM** records.
10. **Incident-response plan with contractual notification timelines** (the
    disclosure commitment exists; timelines do not).
11. **Personnel security program records** (screening, training) on the vendor side.
    (A drafted entry exists below, 2026-10-12 — it records only what the repo
    record supports and flags the program facts as an open gap.)
12. **Accessibility conformance** (WCAG audit / VPAT) for the shipped UI.
13. **Privacy notice and DPA template.**
14. **AI commitments as contract terms** (no-training statement; AI governance
    policy document).
15. **SCIM provisioning / automated deprovisioning as capabilities** — draft
    claims, build in flight (E3); answerable only when the phase lands and the
    claims move on evidence.

### Drafted entries for items 1, 2, and 11 (2026-10-12) — DRAFTED, pending owner confirmation

The owner directed (2026-10-12) that these three items be drafted from what we
have, with the gaps flagged. **Everything in this subsection is a coordinator
draft, not an owner-supplied fact.** Each entry separates what this repo's
records state (with the citation) from what they do not. Until the owner
confirms or corrects an entry, items 1, 2, and 11 remain **NOT YET ANSWERABLE**
in the tables above, and no line below may be quoted as the owner's statement.

- **Item 1 — company profile (DRAFTED).** *From the record:* vendor legal name
  **Axiovex Systems, LLC** (§1 table above; LICENSE, © 2026 Axiovex Systems,
  LLC). Owner: **Tristen Pierson** (DN-001 founding record: "Owner: Tristen
  Pierson, Axiovex Systems, LLC"). *Drafted — NOT in this repo's records, owner
  to confirm or correct:* state of organization (drafted: Michigan), membership
  (drafted: two-member LLC), officers (drafted: Tristen Pierson, President;
  Rockson Arnold, Chief of Strategy). *Open gaps, not drafted:* headcount,
  founding date, HQ address, financial-stability evidence — no record states
  them; the owner supplies.
- **Item 2 — named contacts (DRAFTED).** Security contact and privacy contact
  are both drafted as **Tristen Pierson** — basis: DN-001 names him the owner,
  and DESIGN §5.3 promises partners "one named Axiovex contact." *Pending owner
  confirmation:* that he holds both roles for vendor-review purposes, and the
  contact details (no email address or phone for this purpose exists in the
  records; none is drafted).
- **Item 11 — personnel security (DRAFTED, mostly a flagged gap).** *From the
  record:* the CMMC responsibility matrix classifies the personnel families
  (3.2, 3.9) as Organizational, and the platform's role records evidence who
  held which role when (§2 table above). *Open gap, flagged:* **no record in
  this repo states a personnel security program** — nothing on screening,
  training, the vendor's membership/employment structure, or who holds
  production access. This entry claims none of those things; the owner supplies
  the program facts, and the DPA template's personnel section stays unfinalized
  until they are true (gap-closure board, item 11).

*Not on this list, deliberately:* SOC 2 (answered — none exists, readiness only) and
FIPS validation (answered — none, gap disclosed with inventory and POA&M seed). A
"No, stated" is an answer; this register is only for questions the records cannot
yet answer at all.

---

*Prepared from repo records only, 2026-10-12. DRAFT — not submitted anywhere.*
