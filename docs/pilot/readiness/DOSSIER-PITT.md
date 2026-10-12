# Pilot Readiness Dossier — University of Pittsburgh (DRAFT)

**Target unit:** Health Sciences Library System (HSLS) — Systematic Review Program
**Status:** DRAFT — internal preparation only. Prepared 2026-10-12 from public pages
actually read on that date and from Tekmerion's own repo records. **No contact has been
made with Pitt, and this document authorizes none** (DESIGN §7 step 5). Every Pitt fact
carries its source; anything public evidence cannot settle is marked **UNKNOWN**.
Shortlist context: `docs/pilot/SHORTLIST-DRAFT.md` §2.2 (ranked #2). Discovery
questions Q1–Q9 are the shortlist's §6 list.

---

## 1. The unit and its operating model

HSLS runs a named **Systematic Review Program** for the health-sciences schools:
librarians design and conduct the comprehensive searches systematic reviews require,
produce the documentation the final manuscript needs, and are embedded from protocol
stage. HSLS's own annual-report material lists systematic-review search expertise and
methodology documentation as a standing research-support service
(https://info.hsls.pitt.edu/annual-report-development/, per the shortlist pass).

- **Protocol-first intake.** HSLS's published intake document, "Getting ready for a
  systematic review — things to consider," sets the expectation that a review "will
  begin with creation of a protocol," that the literature search will not begin before
  a written protocol is available, and that investigators are encouraged to register
  protocols (the document names PROSPERO). This is the closest published analogue to
  Tekmerion's register discipline among the three dossiers.
  (https://hsls.libguides.com/ld.php?content_id=1265534 — HSLS's own intake document,
  dated 2014 and still the live linked version; flagged here for currency.)
- **Team-based conduct.** The same document: screening is performed "systematically
  and independently" by research-team members and must be thoroughly documented; a
  results-management/screening system must be in place before the search process
  begins; librarians design and conduct searches and advise on grey literature;
  meta-analysis teams are advised to include a biostatistician. As at Duke, the
  adjudication bench for a pilot is the research team; the library supplies search
  and methodology.
- **Co-authorship and effort norms.** "A librarian who has designed and conducted
  comprehensive literature searches… should be included as a co-author on the primary
  manuscript," writing the literature-search methodology section; for grant proposals,
  the librarian is included as co-investigator or consultant with an allocation of
  effort discussed in advance. (Same intake document.)
- **Service model in the literature (flagged as such).** A JMLA account of HSLS's
  programme describes a two-tiered service model (advisory consultation vs.
  collaboration), a work-plan document guiding the initial meeting, workload
  distribution across health-sciences librarians, and formal peer review of each
  other's searches using the PRESS checklist (https://jmla.pitt.edu/ojs/jmla — HSLS
  programme article; scholarly literature about the unit, not a current service page).
- **Named people (public evidence).** The shortlist pass read a named HSLS Research
  and Instruction Librarian profile listing systematic reviews and "systematic review
  searching, methods and data tracking" as her work
  (https://www.hsls.pitt.edu/staff/helena-vonville). Historical HSLS publications name
  further SR librarians (2016-era; currency conversation-only). No published queue
  length, timeline, or cost-recovery schedule was read for HSLS in either pass —
  **UNKNOWN**, and a deliberate contrast with Duke's published numbers.

## 2. Vendor / third-party security review — in detail

Pitt's machinery is published at the level of process and policy, not instrument
text:

1. **The governing instrument** is Pitt Digital's **Vendor Security Risk Assessment
   Operating Standard**. Per Pitt's own KB: "any unit that wishes to engage with a
   vendor must complete the onboarding questionnaire" under that standard; units are
   told to "initiate the risk assessment early to avoid delaying engagement with the
   vendor." (https://services.pitt.edu/TDClient/33/Portal/KB/PrintArticle?ID=46)
2. **The questionnaire is the engaging unit's submission, not a vendor form.** It is
   completed by the Pitt unit and submitted through the "Request an Assessment" path
   (the form itself runs on Qualtrics); a preview is hosted on Pitt SharePoint. Its
   stated functions: give Pitt Digital Information Security the information to
   understand the product or service, define the assessment scope, identify the
   university's potential risk, and collect the vendor's contact information. (Same
   KB article.)
3. **The item-level content of the questionnaire is not publicly enumerable.** The
   preview sits behind Pitt SharePoint access; no page read in this pass reproduces
   its sections. This dossier therefore enumerates the instrument's *function* (§5)
   and lists obtaining the questionnaire itself as a first-conversation deliverable.
   Any claim about what Pitt's questionnaire asks, beyond the KB's own description,
   would be invention.
4. **Policy stack the KB itself links** — the review does not float free; it sits
   under: Data Risk Classification and Compliance (Pitt Digital); University
   Administrative Computer Data (UACD) Security and Privacy, policy AO 35; HIPAA
   policy CS 30; Access to and Release of Education Records (FERPA), AC 04; Payment
   Card Handling FN 16; Social Security / University Primary ID policy CS 23;
   Computer Data Administration AO 10. For a no-PHI, no-student-records literature
   pilot, the operative members of the stack are the data-risk classification and
   AO 35; the others are named here so the packet is never surprised by them.
5. **SOC 2 / HECVAT posture: not stated on any page read.** Neither the KB article
   nor the shortlist pass found Pitt publishing a SOC 2 requirement or a HECVAT
   mandate. That is an absence of evidence, recorded as such: Q1 at Pitt is fully
   open, in both directions.
6. **Timeline: not published.** The only published temporal guidance is the advice to
   start early. Q2 at Pitt is fully open.

## 3. Federation and identity facts

- **SSO service:** Pitt Passport, the university's single sign-on, operated by Pitt
  Digital; Pitt's KB describes it as "InCommon Federation / Shibboleth," made
  possible by the university's InCommon membership, and configurable per service
  (shortlist pass: https://services.pitt.edu/TDClient/33/Portal/KB/PrintArticle?ID=275).
- **IdP entityIDs (Pitt's own published SP-onboarding documentation):**
  production **`https://passport.pitt.edu/idp/shibboleth`**; development
  **`https://passport-dev.pitt.edu/idp/shibboleth`**, with production and development
  IdP certificates published for metadata exchange.
  (https://www.technology.pitt.edu/security/leverage-pitt-passport-for-your-application)
- **Onboarding flow (published):** the SP onboarding form is completed by the
  department IT administrator, application owner, or vendor; the ticket routes to
  Pitt Digital's Identity & Access Management (IAM) team, which confirms metadata
  needs, attribute release, and test plans; configuration and verification happen
  **first in the Development IdP**, and production cutover follows successful testing
  and approval. **All integrations must pass dev testing before production.**
- **SAML 2.0 is a hard protocol requirement:** "The application cannot use Pitt
  Passport without SAML 2.0 support." (Same page, FAQ.) Spec 005 E2 (SAML SP,
  supported) is exactly this shape; attribute mapping (ePPN, scoped affiliation,
  mail, displayName) is within E2's recorded support.
- **MFA:** Pitt Passport is the university's MFA-backed SSO (Pitt IT's own writing
  describes the transition to Passport logins as strengthening security "by utilizing
  multifactor authentication"; https://www.technology.pitt.edu — Atlassian/Pitt
  Passport article). Platform-side MFA-evidence enforcement is CLM-005-27
  (supported); the specific acr/amr Pitt asserts is a configuration-time item.

## 4. Data-handling and retention postures Pitt publishes

- **Classification-led:** Pitt Digital's Data Risk Classification and Compliance
  framework is the linked companion to the vendor standard — the pilot's data class
  under that framework is the assessment's scoping act (KB ID=46, related policies).
- **Institutional exposure:** Pitt is a state-related public university; Pennsylvania
  Right-to-Know and records-retention exposure are the §8 dimension of the F5
  conversation (category flagged in the shortlist; no institution-specific page on
  point was read in either pass — **UNKNOWN** in its specifics).
- **HSLS-level retention:** no HSLS retention schedule for review records was read in
  either pass — **UNKNOWN** (contrast Duke's published 7 years). Q3 at Pitt therefore
  starts from the university policy layer, not a library number.

## 5. Instruments enumerated

| Instrument | Who completes it | Publicly enumerable? |
|---|---|---|
| Vendor Security Risk Assessment onboarding questionnaire (Qualtrics; preview on SharePoint) | The engaging Pitt unit | **No** — functions established from the KB (product understanding, scope definition, risk identification, vendor contacts); item list is a first-conversation deliverable |
| Vendor Security Risk Assessment Operating Standard | Pitt Digital (governs the unit) | Referenced and linked from the KB; its text was not reproduced in pages read |
| Pitt Passport SP onboarding form | Dept IT admin / application owner / vendor | Flow published (IAM routing, dev-first testing); form fields not enumerated in pages read |
| HSLS "Getting ready for a systematic review" intake document | Review teams, with HSLS | **Yes** — its questions: research question & rationale; existing reviews/protocols checked (with librarian help); protocol in place (search does not begin before a written protocol); protocol registration encouraged (PROSPERO named); team composition (independent duplicate screening, documentation duties, biostatistician for meta-analysis); multi-database searching; results-management/screening system in place before searching; screening time available; timetable; publication target; search-update plan (incl. post-publication); standards awareness (IOM Standards, PRISMA); grant status → librarian as co-investigator/consultant with effort allocation; librarian co-authorship incl. writing the search-methods section |

## 6. First-conversation agenda — Q1–Q9 mapped

| Q | Status from this file | What remains to ask |
|---|---|---|
| Q1 SOC 2 / HECVAT hard requirement | **Fully open.** No published SOC 2 or HECVAT position found in either pass. | The whole question: does the Operating Standard's assessment hard-require SOC 2 Type II or a HECVAT for a hosted, no-PHI literature pilot — or does the questionnaire-based assessment plus an evidence pack of the DESIGN §6 kind satisfy it? Also: obtain the questionnaire itself. |
| Q2 Timeline | **Fully open** (only "start early" is published). | Measured timeline for a low-data-class assessment; whether review precedes or follows a pilot agreement. |
| Q3 Append-only vs retention | **Open at policy level.** Classification framework and public-records exposure identified; no HSLS number. | Data-governance read on export + anchor + access restriction (no deletion workflow) against Pitt's classification and Pennsylvania retention/Right-to-Know posture. |
| Q4 Identity specifics | **Mostly answered.** SAML 2.0 mandatory; prod/dev entityIDs published; IAM confirms attribute release; dev-first testing is process, plannable. | Which attributes IAM will release to our SP; test-plan expectations; MFA acr/amr values. |
| Q5 Adjudicator hours (P-K3) | **Unanswered.** No published queue/timeline data for HSLS; the intake document's own framing (team screens independently; substantial time) is the only signal. | Whether a partner team's adjudicator can protect ~2 hours in the window. |
| Q6 OSF requirement/preference | **Partially framed.** HSLS's intake document encourages protocol registration and names PROSPERO; UNC's FAQ (shortlist §5) shows OSF familiarity in the archetype, not Pitt's position. | OSF: requirement, preference, or indifferent beside PROSPERO/Zenodo? |
| Q7 (York) | N/A | — |
| Q8 (UNC) | N/A | — |
| Q9 Cost shape | **Framed, unanswered.** HSLS's norm is effort allocation on grants (co-investigator/consultant) rather than fees in pages read. | Their per-review tooling/effort baseline vs. our ≤$25/question marginal shape (P-K5). |

## 7. Pitt-specific risks

- **Instrument opacity:** the gating questionnaire cannot be pre-answered the way
  Duke's HECVAT can — our preparation for Pitt is the vendor packet plus the HECVAT
  draft as evidence of posture, and the first conversation's job is to obtain the
  instrument. Plan the Pitt conversation as a document request, not a document
  delivery.
- **Currency:** HSLS's most detailed public intake document is dated 2014 (still
  live-linked). Its norms (protocol-first, PROSPERO) are consistent with the
  programme's current self-description, but every operational detail from it should
  be re-confirmed in conversation before reliance.
- **Public-records dimension:** as a state-related institution, Pitt's records
  posture may make the pilot's own records (including a failure record, DESIGN §3.4)
  a disclosure conversation, not only a retention one. F5/F6 wording must be agreed
  with that in view.

---

*Prepared from public sources and repo records, 2026-10-12. DRAFT — not sent anywhere.*
