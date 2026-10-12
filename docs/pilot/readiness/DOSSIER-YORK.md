# Pilot Readiness Dossier — University of York, Centre for Reviews and Dissemination (DRAFT)

**Target unit:** Centre for Reviews and Dissemination (CRD)
**Status:** DRAFT — internal preparation only. Prepared 2026-10-12 from public pages
actually read on that date and from Tekmerion's own repo records. **No contact has been
made with York or CRD, and this document authorizes none** (DESIGN §7 step 5). Every
York fact carries its source; anything public evidence cannot settle is marked
**UNKNOWN**. Shortlist context: `docs/pilot/SHORTLIST-DRAFT.md` §2.3 (ranked #3).
Discovery questions Q1–Q9 are the shortlist's §6 list.

---

## 1. The unit and its operating model

CRD is a research centre, not a library service — the methods-group archetype of
DESIGN §2.1 in its purest form in this set. Its own description: it "specialises in
evidence synthesis, assembling and evaluating data from multiple research studies to
generate robust evidence to inform health policy and practice," with research "ranked
6th in the UK for research power" in the REF-based THE ranking and over 92% rated
world-leading (4*) for impact. The Director (and Head of Department) is Professor
Lesley Stewart. (https://www.york.ac.uk/crd/)

- **Commissioned production.** CRD's largest programme is health technology
  assessment for the National Institute for Health and Care Research (NIHR):
  it hosts one of NIHR's Technology Assessment Review (TAR) teams and the York
  Evidence Synthesis Group, with "rapid commissioning of HTAs including systematic
  reviews and economic evaluations" for NICE and NHS England, and a continuing
  reports output listed through 2025–2026.
  (https://www.york.ac.uk/crd/research/health-technology-assessment/ and
  publications index, per the shortlist pass.)
- **PROSPERO.** CRD produces PROSPERO, the international prospective register of
  systematic reviews — "Led by the Centre for Reviews and Dissemination, University
  of York" (Cochrane's PROSPERO documentation page, cited in the shortlist pass).
  Protocol pre-registration is this unit's native discipline, which is why the OSF
  question (Q6) takes a different form here than anywhere else in the set.
- **Staff bench (published).** CRD's staff directory names its evidence-synthesis
  researchers with research interests — among them risk-of-bias assessment, living
  systematic reviews, and scientific misconduct identification
  (https://www.york.ac.uk/crd/about/staffprofiles/, shortlist pass). It is the
  strongest publicly evidenced adjudicator bench in the shortlist; whether CRD staff
  would adjudicate on an external platform is conversation-only.
- **No published queue, fee schedule, or service intake** of the Duke/HSLS kind was
  read: CRD's intake is funder commissioning, not a request form. Timelines and
  capacity are **UNKNOWN** from public evidence.

## 2. Vendor / third-party route — in detail

York has no HECVAT-style vendor questionnaire. The governing machinery is the
University's **IT Outsourcing and Cloud Computing Policy** and its method statements,
which form part of the University Information Security Policy — and it applies
"whether the University will pay for the service or use it free of charge," i.e. a
no-fee pilot does not route around it.
(https://www.york.ac.uk/staff/policies/information-policy/index/it-outsourcing-and-cloud-computing-policy/)

1. **Lead contact and risk assessment.** The service or department introducing the
   system appoints a lead contact. Working with the supplier (or using supplier
   materials), a **Computing Risk Assessment** must be completed for review and
   sign-off by the **Director of Infrastructure and Faculty IT**; the service owner
   owns implementation of, and ongoing adherence to, any resulting controls.
   (Method statement: risk assessment for selection of outsourcing/cloud computing,
   same policy index.)
2. **Data Protection screening is mandatory and early.** "Data Protection Screening
   Questions must be completed and returned to the Data Protection Officer for all
   new systems that process personal data. Where appropriate, a Data Protection
   Impact Assessment will be conducted." A Tekmerion pilot processes personal data
   at least in the platform directory (partner reviewer identities) — the screening
   is therefore not optional, and the pilot's data-minimal design (identities in the
   directory, never in ledger payloads — DESIGN §2.3) is the substantive answer it
   will examine.
3. **Contract machinery.** Draft contracts are prepared and reviewed by a University
   team covering information and contract law, data protection, procurement
   regulations, information security, and IT technical knowledge, following current
   Jisc Legal guidance on outsourcing/cloud contracts; contracts are signed off by
   the Head of Procurement (or nominee), and final contracts are agreed by the
   senior manager responsible for the service — for a University-level service, the
   Director of Technology, Estates and Facilities or nominee. The contract "must
   specify the information security and other standards the supplier is required to
   meet" and include remedies for breach and an SLA specifying working practices.
   **Which standards a York contract would name for this pilot is UNKNOWN** — that
   is York's form of the Q1 question (§6): if the named standard is an ISO 27001
   certification (the international information-security management standard) we
   do not hold, the honesty position is the same as for SOC 2 and
   must be stated, not negotiated around.
   (Policy page + contractual-requirements method statement, same index.)
4. **Personal-data terms.** Where a contract involves personal-data or
   special-category data, appropriate data-protection clauses are required, and
   "due diligence may also be required in relation to a third party's information
   security protocols" (University Contract Approval and Signature Framework).
   Processor terms follow UK GDPR Article 28 (University Data Protection Policy).
5. **International transfer.** Legal advice must be taken if a contract involves
   data transfer outside the European Economic Area; the University's Data
   Protection Policy requires all transfers outside the UK to follow UK GDPR. A
   US-hosted pilot is an international transfer on its face: expect a transfer risk
   assessment and transfer clauses, and treat the hosting-location question as a
   first-order agenda item, not a detail. (The platform's self-hosted shape —
   DN-003 — exists architecturally, but DESIGN §5.1 promises no date for it; the
   pilot as designed is hosted.)
6. **Third-party access terms.** For any third-party access, York requires a code
   of practice, a data sharing arrangement, and a non-disclosure agreement agreed
   **in advance** (Third Party Access to University Information and IT Services
   Policy, same index). Oversight sits with the Information Security Board.
7. **Breach posture on their side.** York's Data Protection Policy maintains a
   breach procedure reporting qualifying breaches to the ICO (the UK
   data-protection regulator) within 72 hours. Our
   side's commitment (DESIGN §5.3: every record-touching incident disclosed to the
   partner with evidence) is compatible in spirit; contractual notification
   timelines on our side are **not yet answerable** — see the HECVAT draft's list.

## 3. Federation and identity facts

- **SSO system:** "The University uses an SSO system called Shibboleth." External
  services (externally hosted library journals are York's own example) use it.
- **Supplier requirement, verbatim in substance:** "The supplier or service must
  implement SAML 2.0 or support Shibboleth." Spec 005 E2 (SAML 2.0 SP, supported)
  is this shape exactly.
- **Lead time, published:** "we require **at least three months' notice** to
  implement SSO for a new service," because configuration and testing depend on the
  provider's experience. This sets a hard floor under any York pilot start and
  stacks with the §2 contract process.
  (All three: https://www.york.ac.uk/it-services/tools/single-sign-on/ — page last
  reviewed 23 December 2025.)
- **IdP entityID: UNKNOWN.** No York page read in this pass publishes the IdP
  entityID, and the UK Access Management Federation listing for York's IdP was not
  read. The entityID and attribute-release set are exchanged during the SSO
  implementation the page describes; nothing in the readiness package depends on
  knowing them earlier.
- **Attribute release: UNKNOWN** (same basis). Spec 005 E2's mapping covers ePPN,
  scoped affiliation, mail, displayName; what York releases to a new SP is a
  configuration-time fact.

## 4. Data-handling and retention postures York publishes

- **UK GDPR framework throughout:** data minimisation ("the minimum amount of data
  necessary"), Article 28 processor contracts, 72-hour ICO breach reporting,
  UK-only-by-default transfer posture (Data Protection Policy). The pilot's
  data-minimal scope is designed for exactly this examination.
- **CRD- or University-level retention schedule for review records: UNKNOWN** — no
  retention figure was read in this pass (contrast Duke's published 7 years). Q3 at
  York is therefore argued from principles (below), not from a number.
- **The append-only question in its sharpest legal form.** UK GDPR carries erasure
  rights that US candidates' retention conversations do not raise in the same way.
  The pilot's honest position, from DESIGN §2.3/§5.4 and CLM-005-17: identities live
  in the platform directory (mutable, deprovisionable — access ends, the directory
  record is the institution's to govern); ledger payloads carry no PII (personally
  identifying information) beyond what
  the record requires, and there is no deletion workflow for the record itself —
  retention is export + anchor + access restriction. Whether that division satisfies
  York's data-protection review for a literature-only pilot is Q3 here, and it is a
  legal review, not a sales conversation.

## 5. Instruments enumerated

| Instrument | Who completes it | Publicly enumerable? |
|---|---|---|
| Data Protection Screening Questions (→ DPO; DPIA where appropriate) | Introducing service, with supplier input | Process published; the form's item text was not reproduced in pages read — obtain at first contact |
| Computing Risk Assessment (sign-off: Director of Infrastructure and Faculty IT) | Lead contact, "working with the supplier (or using materials that the supplier makes available)" | Process published; item text not public. **Our vendor packet + HECVAT draft are written to be usable as the "materials the supplier makes available" for this step.** |
| Contract standards + SLA + breach remedies (Head of Procurement sign-off) | University team drafts; supplier accepts/negotiates | Standards to be named are UNKNOWN until drafted |
| Code of practice + data sharing arrangement + NDA (Third Party Access Policy) | Both parties, in advance | Requirement published; templates not public |
| SSO implementation request (≥3 months' notice) | Service, with IT Services | Requirement and lead time published |

## 6. First-conversation agenda — Q1–Q9 mapped

| Q | Status from this file | What remains to ask |
|---|---|---|
| Q1 SOC 2 / HECVAT | **Reframed, process answered.** York's gate is not a SOC 2/HECVAT gate: it is the Computing Risk Assessment + DP screening + contract standards, all published process. | Which information-security standards would the contract name for this pilot — and does our evidence posture (live bundles, independent verification, claims records, no certifications) satisfy the risk assessment without a named certification? Also the transfer assessment for US hosting. |
| Q2 Timeline | **Partially answered.** SSO floor: ≥3 months. | CRA + contract cycle duration; whether assessment precedes any pilot agreement; stacking order. |
| Q3 Append-only vs retention/erasure | **Open, sharpest form.** UK GDPR erasure vs no-delete record; directory/payload division is our answer's shape. | York DP review's read on that division for literature-only content; retention period the contract would set. |
| Q4 Identity specifics | **Answered at protocol level.** SAML 2.0/Shibboleth mandatory; lead time known. | EntityID, attribute release set, test process. |
| Q5 Adjudicator hours (P-K3) | **Unanswered, culturally promising.** CRD's product is defended verdicts and its bench is named; the two-hour bundle-alone audit is native to its discipline. | Whether commissioned workflow calendars admit it in the window. |
| Q6 OSF requirement/preference | **Native-speaker question.** CRD produces PROSPERO. | Is OSF registration a requirement, a preference, or redundant beside PROSPERO for a study CRD adjudicates? |
| Q7 NIHR commissioning terms | **Fully open — the structural question.** | Do TAR/YES commissioning terms permit one question to run on an external vendor platform? What confidentiality attaches to in-progress appraisals, and does a *non*-appraisal question (outside the NICE pipeline) sidestep the terms question? |
| Q8 (UNC) | N/A | — |
| Q9 Cost shape | **Orthogonal, framed.** CRD's economics are funder-commissioned; our ≤$25/question is a marginal-cost claim about our machinery, not their budget line. | Whether any charge/cost-recovery expectation attaches to CRD staff time on an external pilot, and under what instrument. |

## 7. York-specific risks

- **Jurisdiction is a first-order cost, not a footnote:** transfer assessment,
  Article 28 terms, possible UK/EU hosting expectations. If York is the first pilot,
  its timeline includes legal work the US candidates' does not.
- **Commissioning terms may simply prohibit the pilot shape** (Q7) — if so, York
  exits per the shortlist's ranking logic and the dossier's value is having learned
  it from one conversation instead of a procurement cycle.
- **Contract standards risk mirrors Q1:** a contract naming ISO 27001 (or a Cyber
  Essentials requirement for UK public-sector-adjacent work) would meet the same
  honest answer as SOC 2 — we hold no certifications; readiness mappings and
  evidence are what exist. Stated early, it is a scoping fact; discovered late, it
  is a failed procurement.

---

*Prepared from public sources and repo records, 2026-10-12. DRAFT — not sent anywhere.*
