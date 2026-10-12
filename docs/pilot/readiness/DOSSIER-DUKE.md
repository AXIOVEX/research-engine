# Pilot Readiness Dossier — Duke University (DRAFT)

**Target unit:** Medical Center Library & Archives — Evidence Synthesis Service
**Status:** DRAFT — internal preparation only. Prepared 2026-10-12 from public pages
actually read on that date and from Tekmerion's own repo records. **No contact has been
made with Duke, and this document authorizes none** (DESIGN §7 step 5: per-target owner
approval precedes any outreach). Every Duke fact carries its source; anything public
evidence cannot settle is marked **UNKNOWN**. Shortlist context: `docs/pilot/SHORTLIST-DRAFT.md`
§2.1 (ranked #1). Discovery questions Q1–Q9 referenced below are the shortlist's §6 list.

---

## 1. The unit and its operating model

The Evidence Synthesis Service is the Medical Center Library's formal service for Duke
Health — School of Medicine (SOM) and School of Nursing (SON) faculty, staff, trainees,
and students — covering systematic reviews, scoping reviews, evidence maps, and other
formal review methodologies.

- **Intake.** All teams start with the Evidence Synthesis Literature Review Request Form
  (Qualtrics). The service page enumerates what it asks: requester name, email, mentor
  (if applicable), Duke Health status, school/program/center, research question, PICO
  elements (population, intervention, comparison, outcome — the parts of a clinical
  question) or variables of interest, inclusion and exclusion criteria, 5–10 relevant
  article references meeting the criteria, and whether reviews already exist on the
  topic. (https://guides.mclibrary.duke.edu/sysreview/service — "This form will ask for
  your name, email, mentor… research question, PICO elements…")
- **Eligibility and leadership.** Projects are considered only with a Duke Health author
  as project leader; a Duke Health faculty member or trainee must serve as project
  leader and primary contact, "responsible for all communication, project decisions,
  and co-leading meetings with the librarian." Multi-institution projects are considered
  if the Duke Health author leads; society/guideline projects case-by-case.
  (Same policy page.)
- **Tiers.** Tier 1 (Consultative): guidance on process, topic and eligibility
  refinement, protocol-registration guidance, screening-methods guidance, Covidence
  guidance — librarians do not run searches. Tier 2 (Research Partner / Co-author):
  librarians additionally develop and execute searches, download results to citation
  software, upload results to screening software (Covidence workspace with
  de-duplicated results is the stated deliverable), document strategies, manage
  results, draft the Methods search description and appendix, and review the
  manuscript. (Tier table, same guide page.)
- **Screening is the team's work, not the librarians'.** In both tiers, "Screening
  abstracts for inclusion" is marked No for librarian performance. For a Tekmerion
  pilot this matters directly: the adjudication bench (DESIGN F2) is the research team,
  and the library's role maps to the evidence-production side of the workflow.
- **Authorship norm.** Co-authorship for librarians when ICMJE criteria / CRediT
  taxonomy are met is stated policy, not a courtesy. (Policy page.)
- **Timelines (published).** Contact the service a minimum of 3–4 weeks before hoped-for
  screening start; average search development 1–2 weeks; at any given time multiple
  reviews are in the queue and a first consultation may take 1–2 weeks to schedule;
  "most reviews require 12 to 18 months to complete."
  (https://mclibrary.duke.edu/news/evidence-synthesis-service)
- **Costs.** Fees are waived for individual Duke Health faculty/staff/trainees/students
  without external grant funding. For grant-funded projects, investigators are
  expected to include library effort in the grant; costs are based on librarian effort,
  coverable as a percentage of effort, estimated by Library Administration with the
  Associate Director for Research & Education. (Policy page.) No published rate card.

## 2. Vendor / third-party security review — in detail

**Two tracks exist, and which one governs this engagement is itself an open question
(see §6).** Duke's published vendor page states that where university data is shared
with a service provider, a security assessment is required — and, in the same breath:
"Duke Health requires a separate review process. Initiating a DHTS Demand review is
done through ServiceNow in the Service Request Catalog."
(https://security.duke.edu/vendor-risk-assessment/) The Medical Center Library serves
Duke Health (SOM/SON) — the shortlist's analysis rests on the university IT Security
Office (ITSO) track described below; whether a library-service engagement is reviewed
by ITSO or routed to Duke Health Technology Services (DHTS) is **not determinable from
public pages** and is a first-conversation item.

### 2.1 The university ITSO track (as published)

1. **Trigger.** A security assessment is required in all instances where university
   data is shared with a service provider, or a provider captures data for subsequent
   university use.
2. **Instruments the vendor must submit** (page heading: "Required forms… vendors must
   submit each of the following items"):
   - **HECVAT, most up-to-date version — "Only version 4 of the HECVAT will be
     accepted"** — returned as an Excel spreadsheet with all tabs intact; no other
     format. The vendor is instructed to read the HECVAT Instruction Worksheet first
     and to make the Additional Information entry "fully answer what is noted as
     Guidance for each question." Several HECVAT questions request additional
     documentation, which must be returned with the forms.
   - **SOC 2 Type 2 report — "If available,"** performed within the past two years,
     and it must be the vendor's own report, "not one for a cloud service provider such
     as Amazon Web Services or Microsoft Azure." Note the textual tension: the list is
     introduced as items vendors *must* submit, and the SOC 2 item is qualified *if
     available*. The page nowhere states that absence of a SOC 2 report is
     disqualifying. Q1 therefore survives, sharpened: see §6.
   - **Shibboleth Readiness Profile** (Duke-hosted form): Duke requires SAML 2.0
     authentication to integrate with its Shibboleth service; vendors complete the
     profile "to determine the level of effort required to integrate." The page calls
     this "a non-negotiable requirement for any platform where Duke students will be
     users" — the published non-negotiability is scoped to student-user platforms;
     whether the profile is demanded identically for a faculty/staff/trainee-only
     pilot is a confirmation item, not an assumption either way.
3. **Flow.** The vendor returns completed forms to its Duke unit contact; the unit
   submits everything to the IT Security Office via a Kuali Build intake form (a
   preview is public on SharePoint) together with an explanation of what Duke data
   the platform will process and which users will have access (external users named,
   with reasons). Review results go to the requesting unit, the Office of General
   Counsel, and Procurement Services. **Published duration: "this process can take up
   to two weeks"** — that is the ITSO review step once a complete submission is in;
   it is not an end-to-end procurement timeline.
4. **Additional reviews that may be required** depending on the data: Duke Privacy,
   E-Commerce, Web Accessibility, and the service owner of any existing Duke service
   the platform integrates with. A Tekmerion pilot should expect at least the Privacy
   and Web Accessibility questions to be asked.
5. **Data classification drives depth.** Where a provider holds Duke "Sensitive"
   and/or "Restricted" data (per Duke's Data Classification Standard, linked from the
   page), additional contractual documentation is required; classification determines
   what accompanies the contract. The pilot's data (published literature + partner-
   authored records) is the lowest-sensitivity class in substance, but the
   classification is Duke's to assign.
6. **Contractual consequences (published, and unusually explicit).** At contract
   negotiation Duke expects the vendor to (i) warrant that services will be in
   substantial conformity with the HECVAT responses; (ii) promptly notify Duke of any
   material variation in operations from those responses; and (iii) accept that any
   material deficiency from the described operations is a material breach. Our HECVAT
   self-assessment draft (`HECVAT-SELF-ASSESSMENT-DRAFT.md`) is written against this
   warranty: an over-claim is not a sales risk, it is a breach term.
7. **Third-party hosting.** If the provider uses a third-party host (AWS/Azure named
   as examples), the provider must work with that host to answer hosting-specific
   HECVAT questions; "N/A" is not appropriate for questions affected by the hosting
   arrangement. Our current records do not name the hosted deployment's underlying
   infrastructure provider — see the HECVAT draft's NOT YET ANSWERABLE list.

### 2.2 The Duke Health (DHTS) track

Public pages establish only that it exists, is separate, and is initiated as a DHTS
Demand in ServiceNow's Service Request Catalog. Its instruments, timeline, and
thresholds are **UNKNOWN** from public evidence. Because the counterparty unit sits
inside Duke Health, the first conversation must establish which track governs before
any HECVAT work is aimed. This is the dossier's main sharpening of the shortlist's
Duke analysis (see Readiness package report: source-record divergences).

## 3. Federation and identity facts

- **IdP:** Duke Shibboleth, SAML 2.0. Duke OIT's Authentication Manager documentation
  instructs service providers to configure the IdP entityID
  **`https://shib.oit.duke.edu/shibboleth-idp`**, with SSO endpoints
  `https://shib.oit.duke.edu/idp/profile/SAML2/POST/SSO` (HTTP-POST) and
  `…/Redirect/SSO` (HTTP-Redirect); Duke's signed metadata file is published at
  `https://shib.oit.duke.edu/duke-metadata-3-signed.xml`.
  (https://authentication.oit.duke.edu/manager — SP configuration documentation.)
- **InCommon:** Duke's Authentication Manager FAQ states "Our InCommon Entity ID is:
  **urn:mace:incommon:duke.edu**" and instructs vendors to use the InCommon entity ID.
  (https://authentication-test.oit.duke.edu/manager/user/faq) The two identifiers
  coexist in Duke's own documentation (URL-form entityID in SP configuration,
  URN-form as the InCommon-registered ID); per-tenant configuration under Spec 005 E2
  imports IdP metadata, so the operative value is whichever the metadata carries at
  configuration time — a detail to confirm, not a blocker.
- **SP onboarding is self-service:** vendors register their service provider through
  the Duke Authentication Manager ("Register Service Provider"), supplying SP
  EntityID, ACS URL, and certificate; attribute release is requested via Duke's help
  form, stating the SP entity ID and needed attributes. The standard attributes named
  in Duke's SP documentation are eduPersonPrincipalName and
  eduPersonScopedAffiliation — both are inside Spec 005 E2's supported attribute
  mapping (eduPersonPrincipalName incl. `subject_source="eppn"`, scoped affiliation,
  mail, displayName; repo records, Spec 005 E2 exit).
- **MFA:** Duke's IdP login operates with MFA in production use (Duke's own IAM
  writing describes IdP login "with MFA turned on for everything" in the author's
  case; https://spaces.at.internet2.edu — Duke, Consent and OAuth). Platform-side,
  CLM-005-27 (supported) requires MFA evidence at the tenant IdP — the shapes are
  compatible; the exact acr/amr values (the codes stating how strongly a login was
  authenticated) Duke asserts are a configuration-time item.

## 4. Data-handling and retention postures Duke publishes

- **Library record retention:** "The Library will maintain records related to a
  systematic review for 7 years. Research teams are responsible for complying with
  any data sharing or archiving policies." (Service policy page.) This is the
  concrete anchor for the F5 conversation (Q3): Duke's library already operates a
  fixed, multi-year retention schedule for review records. What public evidence does
  not show is how Duke's data-governance side treats a *no-delete* posture inside
  that schedule — export + anchor + access restriction (our CLM-005-17 shape) vs.
  scheduled destruction at year 7. That is the substance of Q3 at Duke.
- **Classification-first data handling:** Duke's vendor process is organized around
  its Data Classification Standard; additional documentation scales with the
  Sensitive/Restricted classes (vendor page, §2.1 item 5 above).
- Duke is a private institution: no state public-records exposure of the kind the
  public-university candidates carry (shortlist §2.1 flag).

## 5. Instruments enumerated

| Instrument | Who completes it | Publicly enumerable? |
|---|---|---|
| HECVAT v4 (Excel, all tabs) | Vendor | Structure yes (EDUCAUSE published category set); workbook itself is distributed by EDUCAUSE — our pre-draft is `HECVAT-SELF-ASSESSMENT-DRAFT.md` |
| SOC 2 Type 2 report (if available, ≤2 years old, vendor's own) | Vendor | N/A — we have none; posture stated in the HECVAT draft and vendor packet |
| Shibboleth Readiness Profile | Vendor | Form is Duke-hosted (Box link from the vendor page); its questions are not reproduced in pages read — enumerate at first contact |
| ITSO intake form (Kuali Build) | Duke unit contact | Preview public on SharePoint; it is the unit's submission, not ours |
| Evidence Synthesis Literature Review Request Form (Qualtrics) | Review teams | Fields enumerated in §1 — this is the service's intake, and its shape (protocol elements, named leader, existing-review check) is the closest public analogue to our register discipline |

## 6. First-conversation agenda — Q1–Q9 mapped

| Q | Status from this file | What remains to ask |
|---|---|---|
| Q1 SOC 2 / HECVAT hard requirement | **Partially answered.** HECVAT v4 completion is a stated requirement; SOC 2 is requested "if available" and the page states no disqualification for its absence. | Confirm in the room: for a hosted pilot holding no PHI and no Duke Sensitive/Restricted data, is a complete HECVAT + evidence-based review (live bundles, independent verification) sufficient without a SOC 2 report? And which track — ITSO or DHTS — asks the question? |
| Q2 Timeline | **Partially answered.** ITSO review step: up to two weeks after complete submission. | End-to-end: DHTS-vs-ITSO routing, Privacy/Accessibility review sequencing, contract cycle after a passed review. |
| Q3 Append-only vs retention | **Anchored.** Library retains SR records 7 years (published). | Does a no-delete record with export + anchor + access restriction fit Duke's governance inside that 7-year schedule — and what happens at year 7? |
| Q4 Identity specifics | **Mostly answered.** SAML 2.0/Shibboleth; entityIDs and endpoints published; ePPN + scoped affiliation standard. | Attribute-release approval for our SP; confirmation of the operative entityID form; required acr/amr for MFA evidence. |
| Q5 Adjudicator hours (P-K3) | **Unanswered; risk visible.** Published queue + 12–18-month review durations say the service is saturated; the audit exercise's two hours would come from a research team, not librarians (screening/adjudication is team work). | Whether a project leader can protect ~2 hours in the pilot window — ask the service, expect the answer to be team-dependent. |
| Q6 OSF requirement/preference | **Unanswered.** The service's protocol-registration guidance is published (Tier table: guidance on protocol registration in both tiers) but names no registry preference in pages read. | Requirement, preference, or indifferent beside the Zenodo DOI? |
| Q7 (York) | N/A | — |
| Q8 (UNC) | N/A | — |
| Q9 Cost shape | **Partially framed.** Duke's own cost model is effort-based (waived unfunded; % of effort when grant-funded) — a library-side cost baseline exists in those terms. | Their per-review tooling baseline (screening software, database licences are institutional) vs. our ≤$25/question marginal-cost shape (P-K5) — largely non-overlapping cost categories; the conversation is about what the pilot may and may not be charged for. |

## 7. Duke-specific risks

- **Track ambiguity (ITSO vs DHTS)** is the largest procedural unknown; resolving it
  is agenda item zero, before any document is sent anywhere.
- **The HECVAT warranty clause** converts every answer into a contractual
  representation. Our draft's NOT YET ANSWERABLE items must be resolved as answers
  (or stated as gaps) before submission, never smoothed over.
- **Queue reality:** even a willing service runs a 12–18-month review culture with a
  standing queue. A pilot question must be chosen to fit the pilot window, not the
  service's median timeline (DESIGN §3.1 scoping is the mechanism).
- **Students:** if any pilot user were a student, the Shibboleth Readiness Profile's
  non-negotiability applies by the page's own terms, and FERPA-adjacent questions
  follow. Scoping pilot users to faculty/staff/trainees does not remove the question;
  it is asked, not assumed.

---

*Prepared from public sources and repo records, 2026-10-12. DRAFT — not sent anywhere.*
