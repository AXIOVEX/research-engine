# Tekmerion Pilot — Named-Target Shortlist (DRAFT)

**Date:** 2026-10-12 · **Status:** DRAFT for owner review — gate §7 step 4 of
`docs/pilot/DESIGN.md` (DN-012). **This document authorizes no outreach.** Approval of this
shortlist is not approval of contact (DESIGN §7 step 5): each named target requires the
owner's separate per-target approval before any communication with it. No institution named
here has been contacted, and nothing here is a claim about any institution's willingness to
participate.

---

## 1. Method note

- **Evidence rule.** Every fit judgment below rests only on public pages actually read on
  2026-10-12 (the unit's own service pages first; federation/registry and institutional IT
  pages second; scholarly literature about the unit third, and flagged as such). Each
  criterion carries a one-line citation: URL + what the page shows. A criterion that public
  evidence cannot settle is marked **UNKNOWN** — never inferred. Where a judgment is
  **PARTIAL**, the citation shows exactly which part is evidenced and which part is not.
- **Verdict vocabulary.** EVIDENCED = a public page read in this pass states it. PARTIAL =
  public evidence covers part of the criterion; the remainder is conversation-only.
  UNKNOWN = not settled by any public page read; the searches run are noted where the
  absence itself is informative.
- **Structural fact about F5 and F6.** F5 (accepts the append-only, no-delete posture before
  data moves) and F6 (agrees the pilot is measured, kill criteria shared in advance) are
  *agreements*, not observable properties. No public page can evidence them for any
  institution; both are UNKNOWN for every candidate below, by construction, and are
  first-conversation items (§6). They are listed in every table anyway so the gap is
  visible per candidate rather than averaged away.
- **Capability baseline used (Spec 005, main @ 17e01c4, 2026-10-12).** OIDC sign-in:
  supported (CLM-005-01). **SAML 2.0 service provider with per-tenant IdP configuration:
  supported (CLM-005-02 — E2 has landed since DESIGN.md was written).** IdP-bound Ed25519
  key enrollment: supported (CLM-005-03). MFA required at the tenant IdP, enforced
  platform-side: supported (CLM-005-27). SCIM provisioning: **draft** (CLM-005-06; E3 in
  flight separately — not claimed anywhere in this document). Deprovisioning: draft
  (CLM-005-05). SOC 2: readiness and evidence mapping only, never certification (DESIGN §6;
  CLM-005-16) — the evidence pack cannot satisfy a hard SOC 2 requirement today.
- **Consequence for F3.** DESIGN §2.2 F3 was written while SAML was "in flight, not
  shipped." That is no longer true. As assessed below, F3 reads: the partner's IdP speaks
  OIDC (Entra ID / Google Workspace) **or SAML 2.0** (including Shibboleth federation IdPs,
  the archetype's dominant shape). A Shibboleth institution is therefore a *current* pilot
  candidate on identity, not a later one. DESIGN §8's open question — whether the
  archetype's IdPs are Entra/Google or Shibboleth-first — is answered by this pass for the
  candidates below: **Shibboleth-first, almost everywhere** (see §5).

---

## 2. Candidates

### 2.1 Duke University — Medical Center Library & Archives, Evidence Synthesis Service

**What the unit publicly does.** A formal, tiered evidence-synthesis service for Duke Health
(School of Medicine / School of Nursing): systematic reviews, scoping reviews, evidence
maps. Librarians join as co-authors (Tier 2), design and run searches across multiple
databases, document strategies, and deliver de-duplicated results in a Covidence workspace.
Demand visibly exceeds supply: the service states that at any given time multiple reviews
are in the queue and that most reviews require 12 to 18 months to complete.

| # | Verdict | Evidence (page read → what it shows) |
|---|---------|------|
| F1 | EVIDENCED | https://mclibrary.duke.edu/news/evidence-synthesis-service → standing service with a queue of concurrent reviews, 1–2 week average search development, 12–18 month typical review completion; https://guides.mclibrary.duke.edu/sysreview/service → formal intake form and two-tier service model |
| F2 | PARTIAL | https://guides.mclibrary.duke.edu/sysreview/service → policy requires a named Duke Health faculty member or trainee as project leader and primary contact, and librarian co-authorship per ICMJE; whether named individuals can fill the adjudicator + reviewer roles for a pilot window is conversation-only |
| F3 | EVIDENCED (SAML) | https://security.duke.edu/vendor-risk-assessment/ → Duke's own vendor process requires vendors to return a **Shibboleth Readiness Profile** alongside the HECVAT, i.e. Duke's vendor SSO expectation is Shibboleth/SAML — within Spec 005 E2's supported shape |
| F4 | EVIDENCED | https://mclibrary.duke.edu/news/evidence-synthesis-service → the service's evidence base is the published literature, searched across multiple bibliographic databases with documented strategies — the Crossref/OpenAlex-reachable class DESIGN §2.2 names |
| F5 | UNKNOWN | Agreement-only criterion (see §1); no public page can evidence it |
| F6 | UNKNOWN | Agreement-only criterion (see §1) |

**§8 flags visible from public info.**
- **Hard, published vendor gate.** https://security.duke.edu/vendor-risk-assessment/ → a
  completed HECVAT is a stated non-negotiable requirement, scored by the IT Security
  Office; the vendor contractually warrants conformity with its HECVAT answers. Whether
  the HECVAT review treats absence of SOC 2 as disqualifying for a no-PHI hosted pilot is
  **not stated on the page — the single largest UNKNOWN in this shortlist (§5)**.
- **Retention anchor for the F5 conversation.** The service policy states the Library
  maintains records related to a systematic review for 7 years
  (https://guides.mclibrary.duke.edu/sysreview/service) — Duke already works to a
  fixed retention schedule; how it meets a no-delete posture is a concrete, evidence-based
  conversation, not an abstraction.
- Private institution: no state public-records exposure of the §8 kind.

### 2.2 University of Pittsburgh — Health Sciences Library System (HSLS), Systematic Review Program

**What the unit publicly does.** HSLS runs a named Systematic Review Program for Pitt's six
health-sciences schools: librarians join systematic-review research teams, run comprehensive
database searches, and document methodology to current reporting standards, generally as
co-authors. Annual reports list multiple completed SR collaborations per year.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED | https://info.hsls.pitt.edu/annual-report-development/ → HSLS lists "systematic review search expertise and methodology documentation" as a standing research-support service; http://files.hsls.pitt.edu/files/annual-reports/ar-14-15.pdf → librarians participate in SR teams with multiple named completed collaborations in a single year (recurrence; the report is dated — volume today is not published in what was read) |
| F2 | PARTIAL | https://www.hsls.pitt.edu/staff/helena-vonville → a named Research and Instruction Librarian whose profile lists systematic reviews and "systematic review searching, methods and data tracking" as her work; pilot-window adjudicator/reviewer naming is conversation-only |
| F3 | EVIDENCED (SAML) | https://services.pitt.edu/TDClient/33/Portal/KB/PrintArticle?ID=275 → Pitt's own KB: "Single Sign-On: Pitt Passport (InCommon Federation / Shibboleth)… made possible by the University's membership in the InCommon Federation"; the companion KB article states the University of Pittsburgh IdP is run by Pitt Digital and can be configured per service |
| F4 | EVIDENCED | https://info.hsls.pitt.edu/annual-report-development/ → SR work is comprehensive searching of the published biomedical literature with methodology documentation |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- **Published vendor security-review standard.**
  https://services.pitt.edu/TDClient/33/Portal/KB/PrintArticle?ID=46 → under Pitt's Vendor
  Security Risk Assessment Operating Standard, any unit engaging a vendor must complete an
  onboarding questionnaire and assessment by Pitt Digital Information Security; the page
  advises starting early "to avoid delaying engagement." SOC 2 / HECVAT hard-requirement:
  not stated on the pages read — UNKNOWN.
- Public (state-related) university: Pennsylvania Right-to-Know / records-retention
  exposure is the §8 append-only conversation; no institution-specific page on point was
  read in this pass — flagged as a category, not a finding.

### 2.3 University of York (UK) — Centre for Reviews and Dissemination (CRD)

**What the unit publicly does.** A research centre whose product is evidence verdicts:
systematic reviews and health technology assessments commissioned by the UK National
Institute for Health and Care Research (NIHR), including one of NIHR's Technology
Assessment Review teams and the York Evidence Synthesis Group, with "rapid commissioning
of HTAs including systematic reviews and economic evaluations" for NICE and NHS England.
CRD also produces PROSPERO, the international prospective register of systematic reviews —
protocol pre-registration is this unit's native discipline. This is the methods-group
archetype in DESIGN §2.1, not a library service.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED | https://www.york.ac.uk/crd/research/health-technology-assessment/ → HTA is CRD's largest programme of work; two standing NIHR-funded synthesis programmes with rapid commissioning; https://www.york.ac.uk/crd/knowledge-centre/publications/reports-books/ → continuing review output listed through 2025–2026 |
| F2 | PARTIAL (strongest public bench in this list) | https://www.york.ac.uk/crd/about/staffprofiles/ → a full named staff directory of evidence-synthesis researchers with research interests (risk-of-bias assessment, living systematic reviews, scientific misconduct identification, among others); whether CRD staff would serve as pilot adjudicators on an external platform is conversation-only |
| F3 | EVIDENCED (SAML) | https://www.york.ac.uk/it-services/tools/single-sign-on/ → "The University uses an SSO system called Shibboleth"; a supplier or service "must implement SAML 2.0 or support Shibboleth" — Spec 005 E2's exact shape |
| F4 | EVIDENCED | https://www.york.ac.uk/crd/research/health-technology-assessment/ → CRD reviews evaluate published evidence on healthcare interventions for national decision-makers; PROSPERO's register is of published-literature review protocols (https://documentation.cochrane.org/pages/diffpagesbyversion.action?pageId=107971619&originalVersion=1&revisedVersion=6 → "PROSPERO… Led by the Centre for Reviews and Dissemination, University of York") |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- **Published SSO lead time.** York IT requires **at least three months' notice** to
  implement SSO for a new service (same IT Services page) — a schedule fact, plannable,
  but it sets a floor under any York pilot start date.
- **Commissioned-programme fit is untested.** CRD's volume is funder-commissioned (NIHR);
  whether a commissioned TAR/YES workflow can take one question through an external
  vendor's platform — funder terms, NICE confidentiality on in-progress appraisals — is
  not publicly determinable. This is York's version of the F-fit question and it can only
  be answered in conversation.
- UK jurisdiction: GDPR / UK data-protection review and cross-border hosting posture are
  §8 legal-review items the US candidates do not raise in the same form. Not evidenced
  further in this pass.

### 2.4 Emory University — Woodruff Health Sciences Center (WHSC) Library, Systematic Review Service

**What the unit publicly does.** A named Systematic Review Service inside the WHSC Library:
the team assesses feasibility of each request before collaborating, designs reproducible
searches, and collaborates on data management and manuscript preparation. The service has a
named coordinator, and library news reports informationists co-authoring evidence-synthesis
publications at a steady rate (13 authored publications in one year, four more in the
pipeline, per the library's own news index).

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED (volume indicative, not counted) | https://guides.libraries.emory.edu/SRs → a standing SR Service with per-request feasibility assessment and a request form; https://scholarblogs.emory.edu/whscl-news/2017/05/22/keep-current-with-journals-using-browzine/?paged=6 → WHSC news index reporting 13 informationist-authored publications in a year, most from weeks-to-months evidence-synthesis collaborations |
| F2 | PARTIAL | Same WHSC news index → names a sitting **Systematic Review Service coordinator** (Shenita Peterson, Public Health Informationist) — a single named accountable person, the cleanest such evidence among the library candidates; pilot-window adjudicator + reviewer naming is still conversation-only |
| F3 | UNKNOWN | Searched Emory + InCommon/Shibboleth (this pass): results returned only generic InCommon material, no Emory IdP page read. Emory's IdP technology is not evidenced here — resolve in discovery before any reliance |
| F4 | EVIDENCED | https://guides.libraries.emory.edu/SRs → the service designs reproducible searches of the published literature for systematic reviews |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- No vendor security-review or HECVAT requirement surfaced in this pass — that is an
  absence of evidence, not evidence of a light gate; Emory's actual vendor review is
  UNKNOWN and is the first discovery question if Emory advances.
- Private institution: no state public-records exposure of the §8 kind.

### 2.5 University of Alberta — John W. Scott Health Sciences Library, systematic review service

**What the unit publicly does.** A long-running systematic-review searching service whose
demand-management history is itself published (the library documented eight strategies for
coping with SR request volume). Institution-level volume is quantified in the peer-reviewed
bibliometric literature: 640 University of Alberta systematic reviews (2016–2020) were
identified in one analysis, 152 with a librarian as co-author. The library also built and
teaches an SR-searching curriculum used by other institutions.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED (with currency caveat) | https://journals.library.ualberta.ca/jchla/index.php/jchla/article/view/29696 → bibliometric analysis: 640 U Alberta SRs 2016–2020, 152 librarian-co-authored; https://journals.library.ualberta.ca/jchla/index.php/jchla/article/download/24353/18021/ → the Scott Library's published account of restructuring its SR service under sustained demand. Caveat: the quantified window ends 2020; current request volume is not published in what was read |
| F2 | PARTIAL | Same literature names the service's librarians (e.g. Campbell, Dennett, Kung) as SR-searching leads and instructors (also https://journals.library.ualberta.ca/jchla/index.php/jchla/article/view/25595); currency of named individuals and pilot-window naming are conversation-only |
| F3 | EVIDENCED (SAML) | https://www.canarie.ca/wp-content/uploads/2021/03/TAD_University_of_Alberta.pdf → U Alberta's Canadian Access Federation Trust Assertion Document: it operates an IdP making SAML identity assertions to CAF service providers (authentication technologies listed: Kerberos, SAML, RADIUS) — Spec 005 E2's shape |
| F4 | EVIDENCED | The bibliometric and curriculum papers above → the service's evidence base is the published literature, searched comprehensively across databases |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- Public university in Alberta: provincial FOIP / records-retention exposure is the §8
  append-only conversation — category flagged, no institution-specific page read.
- Evidence currency: the service's public footprint in this pass is scholarly literature
  rather than a current service page; F1/F2 should be re-verified against a live service
  page in discovery before reliance.

### 2.6 University of Michigan — Taubman Health Sciences Library (informationist model)

**What the unit publicly does.** Health-sciences librarians ("informationists") partner on
evidence syntheses across Michigan Medicine and the health-sciences schools: expert-search
consultation, grant collaboration, and a maintained Evidence Syntheses guide whose
methodology pages describe dual independent screening with third-party conflict resolution
as the norm — i.e. the adjudication pattern Tekmerion instruments. Michigan's librarians
also co-developed SR data-management-planning teaching used across institutions.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED (qualitative; volume not published in pages read) | https://www.lib.umich.edu/locations-and-hours/taubman-health-sciences-library/research-and-clinical-support/ → standing informationist partnership service for evidence syntheses across seven schools plus the academic medical center |
| F2 | PARTIAL | https://guides.lib.umich.edu/TaubmanTalks/DMPFES → names Taubman informationists (MacEachern, Saylor, Townsend) presenting the library's SR data-management work; pilot-window naming is conversation-only |
| F3 | EVIDENCED (federation participation) | https://incommon.org/services/participating-organizations → InCommon's own page features the University of Michigan as a participating organization (TIER Campus Success case study, IAM team named); the IdP's protocol configuration for a new SP is a discovery detail |
| F4 | EVIDENCED | https://guides.lib.umich.edu/c.php?g=283340&p=9133328 → THSL's evidence-synthesis methodology is comprehensive searching of the published literature across many databases, with replicable documented strategies |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- **Published third-party security & compliance regime.**
  https://safecomputing.umich.edu/protect-the-u/protect-your-unit/third-party-vendor-security-compliance
  → U-M requires security screening of vendors (certifications, CSA STAR, prior
  questionnaires) under its Third Party Vendor Security and Compliance Standard (DS-20),
  with requirements scaled by data classification. A no-PHI literature pilot plausibly sits
  in a low data class — plausible, not evidenced; the classification conversation is a
  discovery item.
- **Coordination scale.** InCommon's case study describes ~650,000 active accounts in
  U-M's identity population — a large-institution IAM change process should be assumed
  until discovery says otherwise. (Not a defect; a timeline input.)
- Public university: Michigan FOIA / retention exposure is the §8 conversation — category
  flagged, no institution-specific page read.

### 2.7 UNC-Chapel Hill — Health Sciences Library (HSL), with the RTI-UNC Evidence-based Practice Center

**What the unit publicly does.** HSL librarians partner on systematic reviews across the
health fields, run an institutional Covidence subscription for screening/extraction, and
maintain the campus SR guide programme. Adjacent at the Cecil G. Sheps Center, librarians
are key staff for the RTI-UNC Evidence-based Practice Center's research contracts — "from
topic refinements and white papers to full systematic reviews" — i.e. contract-produced
evidence verdicts for external sponsors, the closest US analogue here to a verdicts-as-a-
product workflow.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED | https://guides.lib.unc.edu/c.php?g=8365&p=9849679 → HSL: "We can partner on high-quality systematic reviews across all health fields and specialties"; https://guides.lib.unc.edu/qual/help-at-unc → Sheps Center librarians are key staff for RTI-UNC EPC contracts producing full systematic reviews; https://asklib.hsl.unc.edu/faq/214394 → institution-wide Covidence subscription administered by HSL |
| F2 | PARTIAL | https://guides.lib.unc.edu/c.php?g=9160&p=45560 → named HSL librarian profiles with Systematic Reviews as a listed specialty (e.g. Moreton); the Sheps page names its Acting Associate Director for Information Services (Voisin) as the SR-project contact; pilot-window naming is conversation-only |
| F3 | PARTIAL | https://incommon.org/community/catalyst/incommon-catalyst-program-community-case-studies/ → InCommon's case-study page lists UNC Chapel Hill among organizations that have streamlined researcher onboarding "leveraging Cirrus Identity's cloud based identity management tools" with the InCommon Federation — federation participation via a hosted IdP is evidenced secondhand; UNC's own IdP documentation was not read in this pass |
| F4 | EVIDENCED | https://guides.lib.unc.edu/systematic-reviews → HSL's SR work is searching and screening the published literature (guide programme, Covidence workflow) |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- The EPC's sponsor-contract workflow (federal evidence reports) operates under sponsor
  terms; whether an EPC-adjacent pilot question can run on an external platform is a
  terms question for conversation, not publicly determinable.
- Public university: North Carolina public-records / retention exposure is the §8
  conversation — category flagged, no institution-specific page read.
- No UNC vendor security-review specifics surfaced in this pass — UNKNOWN.

### 2.8 Johns Hopkins University — Welch Medical Library, informationist systematic-review collaboration

**What the unit publicly does.** Welch informationists join systematic-review teams as
members: refining the question, identifying databases, developing and executing searches,
documenting strategies, updating searches before submission, and reviewing manuscripts —
with authorship expected. Welch administers Hopkins' Covidence access and teaches the SR
process. (Johns Hopkins also hosts an AHRQ Evidence-based Practice Center; its pages were
not read in this pass and it is not counted in the fit evidence.)

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED (qualitative) | https://browse.welch.jhmi.edu/sr-methods → the Welch Systematic Review Collaboration page describes a standing team-based SR service with defined informationist tasks across the review lifecycle |
| F2 | PARTIAL | https://welch.jhmi.edu/about/staff/elizabeth-c_whipple → named library leadership profile describing growth of the informationist service and evidence-synthesis guideline work; pilot-window adjudicator/reviewer naming is conversation-only |
| F3 | UNKNOWN | Searched Johns Hopkins + InCommon/Shibboleth/JHED (this pass): no Hopkins IdP or federation page was read; identity path is a discovery item, not an assumption |
| F4 | EVIDENCED | https://browse.welch.jhmi.edu/sr-methods/covidence → Welch's SR production is screening and appraising the published literature in Covidence |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- Thinnest public evidence base in this list relative to the institution's reputation:
  F1 is qualitative only and F3 is unevidenced. Neither is a negative finding; both mean
  Hopkins' ranking is the most discovery-sensitive in the set (§5).

### 2.9 University of Ottawa — Health Sciences Library, Knowledge Synthesis collaboration service

**What the unit publicly does.** A formally specified collaboration service for faculty and
researchers: tiered (acknowledgement vs co-authorship), protocol-first eligibility (the
team must arrive with a protocol and 3–5 target articles), a structured intake form, and a
published update policy (max three search updates). The page states requests have increased
significantly over several years, are first-come-first-served, and may be waitlisted.

| # | Verdict | Evidence |
|---|---------|------|
| F1 | EVIDENCED (qualitative) | https://www.uottawa.ca/library/health-sciences-library/knowledge-synthesis-services-health → standing collaboration service with published eligibility, tiers, and waitlist — recurrence and excess demand are stated on the page; counts are not published |
| F2 | PARTIAL (weak) | Same page → consultations are delivered by "the Research Librarian for your discipline," but no individuals are named on the page read; and the service **expressly excludes** screening, data extraction, and verification from librarian scope — the adjudication bench for a pilot must come from the partner's research teams, which the page does not evidence |
| F3 | UNKNOWN | Searched uOttawa + Canadian Access Federation Trust Assertion Documents on canarie.ca (this pass): TADs surfaced for Alberta, Toronto, Carleton, OCAD, Western — none for uOttawa was read. (Its intake form is hosted on the university's SharePoint, noted but not treated as IdP evidence.) |
| F4 | EVIDENCED | Same service page → knowledge-synthesis work is comprehensive searching of the published literature and grey literature with documented, reproducible strategies |
| F5 | UNKNOWN | Agreement-only (see §1) |
| F6 | UNKNOWN | Agreement-only (see §1) |

**§8 flags.**
- **Capacity / calendar risk is published, not hypothetical.** First-come-first-served with
  waitlists and a three-update cap signal a saturated service — directly relevant to
  DESIGN §8's adjudicator-availability question and the P-K3 two-hour audit budget.
- Public university in Ontario: FIPPA / retention exposure is the §8 conversation —
  category flagged, no institution-specific page read.

---

## 3. Recommended first three

1. **Duke — Medical Center Library Evidence Synthesis Service.** The strongest documented
   F-fit among the library services: a standing queue of concurrent reviews (F1 beyond
   argument), a policy that already names a project leader per review (F2's shape), and a
   Shibboleth/SAML identity path evidenced by Duke's own vendor requirements (F3). Its
   vendor gate is the heaviest in the set — a non-negotiable, scored HECVAT — but it is
   *completely published*, which makes the gate a plannable work item rather than a
   discovery risk.
2. **Pittsburgh — HSLS Systematic Review Program.** A named programme with named SR
   librarians, an IdP Pitt itself documents as configurable per service (F3 with the
   institution's own words), and a published vendor-assessment standard whose process is
   questionnaire-based and explicitly meant to be started early. The most procedurally
   legible US candidate after Duke.
3. **York — Centre for Reviews and Dissemination.** Archetype purity: CRD's product *is*
   defended evidence verdicts for a national decision-maker, its staff bench is publicly
   named, it runs the field's protocol register (PROSPERO), and its SAML path is
   documented down to the lead time (≥3 months for new-service SSO). Ranked third, not
   first, because its two open questions (commissioned-programme fit; UK legal/hosting
   review) are structural rather than procedural.

**First alternate: Emory (§2.4)** — the only candidate with a publicly named service
coordinator, and no published vendor gate found; it is also the candidate whose file is
thinnest (F3 unevidenced, volume indicative). Emory's position is the most sensitive to a
single discovery conversation in either direction.

**What would change this ranking.**
- If Duke's or Pitt's security review treats absence of SOC 2 as disqualifying for any
  hosted vendor (rather than only for PHI-class data), both drop below Emory and York —
  the evidence pack (DESIGN §6) expressly cannot claim SOC 2 today, and E6 is specified,
  not built.
- If Emory's actual vendor review proves light *and* its IdP proves to be SAML/OIDC in
  discovery, Emory takes the #1 slot on gate risk alone.
- If CRD's NIHR commissioning terms do not permit a question to run on an external
  platform, York exits the list and Emory (then Michigan) promotes.
- Any candidate whose data-governance office requires deletion-on-demand fails F5 and
  exits regardless of rank; any candidate that cannot protect two adjudicator-hours for
  the audit exercise fails the P-K3 premise and should be sequenced later, not first.

---

## 4. Not candidates (excluded categories, and why)

- **Pure clinical-trial units and trial-operations groups.** Their evidence is primary,
  human-subjects data — out of scope by DESIGN §2.3, and their "verdicts" are trial
  conduct, not literature-evidence adjudication. (The checker-honesty fit is also wrong:
  there is no published-literature evidence base for our machinery to check.)
- **Care-delivery clinical-effectiveness / guideline shops embedded in hospital
  operations**, where questions are inseparable from patient-level data (PHI) — §2.3
  excludes the data class, so the pilot question could not be scoped cleanly.
- **University research-integrity / research-misconduct offices as the named unit.** The
  archetype names the function, but its published caseload is investigations, not
  recurring evidence questions: F1 fails on public evidence for every such office
  examined in framing this pass, and its adjudication is disciplinary, not
  evidence-verdict adjudication. (An integrity office remains a plausible *second*
  stakeholder inside a library-led pilot; it is not a first target on this evidence.)
- **Commercial systematic-review producers / CROs.** Not the university archetype DN-012
  names; verdicts are client-confidential (F6's shared-measurement premise fails), and
  there is no institutional IdP/tenancy relationship of the Spec 005 shape.
- **Individual high-output labs / single-PI review groups.** No service recurrence (F1:
  no guaranteed second question), an adjudicator bench of one, and no institutional party
  able to make the F5/F6 agreements.

---

## 5. Cross-cutting findings from this pass

- **DESIGN §8's SAML question is answered for this archetype sample: Shibboleth-first.**
  Of nine candidates, five evidence a SAML/Shibboleth federation IdP from public pages
  (Duke, Pitt, York, Alberta, Michigan-by-federation), one evidences federation
  participation secondhand (UNC), and three are unevidenced (Emory, Hopkins, uOttawa).
  None evidenced Entra ID or Google Workspace as its institutional IdP. Had E2 (SAML) not
  landed, F3 would have excluded most of the best-fit partners — DN-012 caveat 1's risk
  was real and is now retired. SCIM (E3) remains draft; nothing in this shortlist relies
  on it.
- **The visible gates are security reviews, and they are published at the top of the
  list.** Duke (HECVAT, non-negotiable), Pitt (Vendor Security Risk Assessment Operating
  Standard), Michigan (DS-20) all publish their vendor-review machinery. **The biggest
  UNKNOWN gating the first three: whether those reviews hard-require SOC 2 Type II for a
  hosted, no-PHI literature pilot, or accept an evidence-based review of the DESIGN §6
  kind.** No page read in this pass answers it; it is DESIGN §8's SOC 2/HECVAT question,
  still open, and it is the first discovery question for Duke and Pitt.
- **OSF acceptance (DESIGN §8) has a native-speaker data point.** York CRD produces
  PROSPERO; protocol registration is its home discipline. Whether that makes OSF
  registration a requirement, a preference, or redundant beside PROSPERO for a York pilot
  is a genuinely open question — for the US library services, UNC's own FAQ already
  lists OSF among protocol-deposit options
  (https://asklib.hsl.unc.edu/faq/366920), which suggests familiarity, not requirement.

---

## 6. Open questions only a first conversation can resolve

Mapped to DESIGN §8. None of these can be closed with public evidence; all are written
here so the owner's per-target approval (DESIGN §7 step 5) is taken with the gaps named.

| # | Question | DESIGN §8 item | Applies to |
|---|----------|----------------|-----------|
| Q1 | Does your vendor security review hard-require SOC 2 Type II (or a completed HECVAT at a threshold score) for a hosted pilot holding no PHI — or does an evidence-based review (live bundles, independent verification, published failure records) satisfy it? | SOC 2 / HECVAT expectations | Duke, Pitt, Michigan (published regimes); Emory, UNC, Hopkins (regimes UNKNOWN) |
| Q2 | What is your measured security-review timeline for a low-data-class pilot, and does review start before or after a pilot agreement? | Procurement & security-review timelines | All; York adds a published ≥3-month SSO implementation lead on top |
| Q3 | Will your data-governance office accept the append-only posture (export + anchor + access restriction; no deletion workflow) for pilot records — and how do your retention schedule and, for public institutions, records law interact with it? Duke's published 7-year SR-record retention is the concrete starting point there. | Append-only vs institutional retention policy | All (F5 everywhere); public-records dimension at Pitt, UNC, Michigan, Alberta, uOttawa |
| Q4 | Identity specifics: which attributes will your IdP release to a new SP, is per-tenant SAML configuration (Spec 005 E2) acceptable as-is, and (Emory, Hopkins, uOttawa) what is your IdP in the first place? | SAML at pilot start (reframed post-E2) | All; F3 discovery at Emory, Hopkins, uOttawa |
| Q5 | Can a named adjudicator protect roughly two focused hours for the bundle-alone audit exercise (P-K3) inside the pilot window — given that Duke publishes a queue, uOttawa publishes a waitlist, and reviews run 12–18 months at Duke? | Adjudicator availability | All, sharpest at Duke and uOttawa |
| Q6 | Is OSF registration of the pilot study a requirement, a preference, or irrelevant beside the Zenodo DOI — and (York) beside PROSPERO? | OSF: requirement or preference? | All; York natively |
| Q7 | (York only) Do NIHR commissioning terms for TAR/YES work permit one question to run through an external vendor platform, and under what confidentiality terms for in-progress appraisals? | (Archetype-fit; §8 procurement analogue) | York CRD |
| Q8 | (UNC only) Do RTI-UNC EPC sponsor terms permit an EPC-adjacent question on an external platform, or is the pilot better scoped to HSL's campus service? | (Archetype-fit) | UNC |
| Q9 | At your question volume, does the ≤$25/question cost shape (P-K5) hold — what does your current per-review tooling cost baseline look like? | Cost reality at partner scale | All (Phase 7 informs, partner data decides) |

---

*End of draft. Prepared 2026-10-12 from public sources only; no institution was contacted.
Next step is the owner's: approve, amend, or reject this shortlist (§7 step 4), then
approve targets individually before any outreach (§7 step 5).*
