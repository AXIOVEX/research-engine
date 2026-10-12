# Tekmerion Pilot — Design

**Date:** 2026-10-12 · **Authorized by:** DN-012 (owner ratification, 2026-10-12) · **Status:** design only.
**This package contains no named target institutions and authorizes no outreach.** The named-target
shortlist is the next owner gate (§7). Nothing in this document is a partner commitment, and no
statement here may be presented to a partner beyond what the evidence pack (§6) verifies.

---

## 1. Purpose and shape

The pilot exists to answer one question with evidence rather than assertion: **can an institution
run one real evidence question through Tekmerion — register → freeze → verdicts → audit bundle →
external anchor — and come out the other end able to defend every verdict from the bundle alone?**

Shape: one partner, one real systematic-review evidence question (the OD-1 MVP workflow), hosted
by Axiovex (DN-003 hosted-first), over a bounded window agreed with the partner, measured against
criteria pre-registered in §3 of this document — stated before any partner is named, and not
revisable after results are known except by a new design note that says it is revising them.

## 2. Partner archetype and fit criteria

### 2.1 Archetype

A university unit that produces systematic reviews or evidence syntheses as a service or a
research line — typically one of:

- a **health-sciences library evidence-synthesis service** (the highest-volume systematic-review
  producers in higher education; adjudication pain is their daily reality);
- a **university research-integrity / research-office function** that reviews evidence claims
  and wants an auditable record of how verdicts were reached;
- a **systematic-review methods group** (e.g. a Cochrane-affiliated or evidence-synthesis unit)
  with named adjudicators already on staff.

The common trait matters more than the unit's name: **recurring evidence questions, named human
adjudicators, and a professional obligation to defend verdicts to third parties** (funders,
journals, institutional review). A partner without named adjudicators cannot exercise the
machinery that makes Tekmerion different, and a partner with one question ever has nothing to
pilot.

### 2.2 Fit criteria (all must hold)

| # | Criterion | Why it is a criterion |
|---|-----------|------------------------|
| F1 | Runs systematic reviews / evidence syntheses recurrently (order: dozens of questions in flight or per year) | The pilot study is one question; the partner must have a second question waiting, or the pilot proves a demo, not a workflow. |
| F2 | Can name at least one adjudicator and one reviewer for the pilot window | WS6 roles are people, not settings; the K3 burden measure (§3) is taken on the partner's adjudicator, not ours. |
| F3 | IdP is Microsoft Entra ID or Google Workspace (OIDC), **or** the partner accepts that SSO completes when Spec 005 E2 (SAML) lands | E1 (OIDC + key enrollment) is built; SAML is in flight, not shipped (DN-011, DN-012 caveat 1). A Shibboleth-only partner is a *later* pilot, not a failed one. **Correction (2026-10-12): E2 SAML has landed and is claim-supported (CLM-005-02, merged 2026-10-12); the shortlist pass found the archetype Shibboleth-first, so F3 no longer defers Shibboleth partners and DN-012 caveat 1 is retired.** |
| F4 | The pilot question's evidence base is published literature reachable via Crossref/OpenAlex | The MVP connectors are Crossref + OpenAlex (OD-1). Questions whose sources live elsewhere are out of the MVP slice by decision, not by defect. **Correction (2026-10-12): the connector set is now Crossref + OpenAlex + CORE, per the owner's directive of 2026-10-12 ("Add CORE, this is still needed") and Spec 012 — CORE joins as the full-text content channel (third in resolution order, content enrichment only where the earlier connectors serve no licence-permitted content). F4's reachability test should now be read as Crossref/OpenAlex/CORE.** |
| F5 | Partner accepts the append-only record posture, including no-delete, before any data moves | DN-005 is constitutional. A partner whose data-governance office requires deletion-on-demand is a policy conversation that must happen before onboarding, not during it (§8). |
| F6 | Partner agrees the pilot is measured: criteria in §3 are shared with the partner in advance, and a fired kill criterion ends the pilot as a recorded failure | Pre-registration only disciplines us if the partner can see the registration. A partner who wants a sales demo instead is not a pilot partner. |

### 2.3 Data sensitivity — what the pilot will and will not take

**In scope:** published-literature metadata and full text where the recorded licence basis
permits storage (WS5 per-source rights: query / store / redistribute recorded separately);
partner-authored claim statements, falsifiers, and adjudication rationales; partner reviewer
identities in the platform directory (never in ledger payloads — DN-005 ingest discipline).

**Out of scope for the pilot, by design:**

- **CUI** — excluded per DN-011's CMMC posture (FIPS gap open; no CMMC representation beyond
  alignment language).
- **PHI / patient-level data and human-subjects raw data** — the MVP workflow is literature
  evidence, not primary data; nothing in the pilot needs it.
- **Unpublished or access-restricted corpora** (e.g. keyset-gated collections) — institution-local
  shapes for those exist in the architecture (DN-003) but are not the hosted pilot.
- **Any content whose licence basis cannot be recorded** — WS5's rule is mechanical: unknown
  rights answer = stub-only until researched and recorded. The pilot inherits it unchanged.

## 3. The pilot study — pre-registered criteria

### 3.1 The study

One real evidence question from the partner's own pipeline, chosen jointly at onboarding,
scoped to a single answerable question with a registered claim set small enough to audit
completely (the register discipline matters more than the count). Run end-to-end through
production paths only:

**register claims with falsifiers → retrieve (Crossref/OpenAlex, queries logged) → origin-grouped
evidence → freeze (registration hash committed, Merkle checkpoint) → evaluation run with
controls → verdicts → adjudication incl. second-review sampling → audit bundle → anchor
(Zenodo DOI + OSF registration, §4) → partner audit exercise (§3.3).**

No step may be performed by a mechanism the partner couldn't use themselves the following week.
A pilot that only Axiovex staff can operate has demonstrated a consultancy, not a product.

### 3.2 Success criteria (all must hold)

- **S1 — Full loop completed.** The study reaches anchored bundle + OSF registration with
  verdicts issued by a **valid** run (controls capable of firing and not fired adversely;
  an INVALID run salvaged by narrative is a failure, not a result).
- **S2 — Partner-operated.** The partner's adjudicator personally performs the freeze approval
  and the deposit approval through the production UI/services; Axiovex staff assist but do not
  drive.
- **S3 — Independent audit passed.** The partner adjudicator (or a partner-named reviewer who
  did not adjudicate) audits the completed bundle **from the bundle alone** and reaches every
  verdict's evidence and falsifier test within the K3 budget (P-K3 below).
- **S4 — Partner assessment recorded.** The partner provides a written close-out assessment —
  positive, negative, or mixed — which is appended to the pilot record unedited. Silence or a
  declined assessment is recorded as itself, not chased into a testimonial.

### 3.3 Kill criteria (any one firing ends the pilot as a failure)

In the K-tradition of Spec 001 (K1–K5): these are registered now, before any partner is named,
and a fired criterion is a **published negative**, internally and to the partner — it is not
renegotiated after the fact.

| # | Criterion | Measure | Threshold (source) |
|---|-----------|---------|--------------------|
| P-K1 | **Citation reality** (K1 shape) | % of exported citations in the pilot bundle resolving to real records | **100%**. Any miss ends it; the response is fixing verification before any further pilot work (Spec 001 K1, unchanged). |
| P-K2 | **Replay integrity** (K2 shape) | Independent replay of the frozen run vs recorded verdicts | Any divergence not detected and flagged by the machinery = kill. |
| P-K3 | **Adjudicator burden** (K3 shape) | Partner adjudicator, bundle alone, reaches every verdict's evidence + falsifier test | **≤ 2 hours** (G3 threshold, owner 2026-10-12). Over budget = kill: the bundle is not yet an audit instrument, whatever the verdicts say. |
| P-K4 | **Origin honesty** (K4 shape) | Origin-group accounting in every exported artifact of the pilot | Any derivative source inflating an evidence count = kill. |
| P-K5 | **Cost shape** (K5 shape) | Marginal cost of the pilot question: connector credits (CreditBudget ledger), anchor/deposit costs, attributable infrastructure | **≤ $25 per question** (G3 threshold, owner 2026-10-12). Over = kill: the cost shape is wrong at MVP scale. |
| P-K6 | **Operability** | Steps in §3.1 that partner staff cannot complete without Axiovex engineering intervention in the machinery (as opposed to training questions) | Any load-bearing step = kill for the pilot as a *product* test (it may still be a successful engagement; the record must say which). |

### 3.4 What "failure" produces

A fired kill criterion closes the pilot with a written failure record: which criterion, the
measured value, the evidence, and the remediation that would have to land before a second
pilot is proposed. That record is part of the program's evidence, in the same tradition as the
INVALID demo run and the Phase 7 negatives — the pilot is an instrument for learning whether
the claims hold at an institution, and an instrument that cannot report "no" is not one.

## 4. OSF registration workstream

**Decision status:** none outstanding. DN-008 reserved the OSF registration workflow as a
separate owner decision; DN-012 records that this ratification *was* the decision — OSF is in
pilot scope, sequenced before partner onboarding.

### 4.1 Starting point (what already exists)

`tekmerion.deposit.osf_metadata` already produces the deposit-ready OSF document from a bundle
manifest: title/description (the description is the anchor statement — checkpoint root, bundle
hash, registration hash), category `project`, tags, creators, and the **component mapping**
(WS4 §4): `registration` (registration.json, claims.json, controls.json), `evidence`
(items/groups/content + coverage), `verification`, `verdicts`, `record`
(ledger/study.axmr, manifest, HUMAN-README), plus `anchor_values`. What does not exist: any
OSF transport, any registration action, any OSF receipt or verification path. The executable
deposit in `tekmerion.deposit` targets Zenodo only.

### 4.2 What building it entails

1. **OSF transport** — a deposit transport alongside the Zenodo transport, same discipline:
   deterministic packaging; the mechanical adjudicator-approval gate applies identically
   (no named approver or an unverifiable bundle → refused, DepositError — approval is a
   property of the action, not of the destination). API access uses the owner's OSF account
   token (free key on an owner account — within standing G4 authorization, Spec 002).
2. **Project + component creation** from the `osf_metadata` mapping: one OSF project per
   anchored bundle, components per the mapping, files uploaded to OSF storage; the mapping is
   the contract — if the live structure diverges from it, the mapping is wrong and is fixed,
   not the other way round.
3. **Registration action** — an OSF registration (the registry snapshot) of the project at the
   study's frozen state, so the registration's content is the frozen registration + bundle,
   hash-bound by the anchor values stated in the registration itself. Embargo handling for
   partner content per §5.4: a registration that must not be public yet is created under
   embargo/private terms the OSF workflow actually supports — the build must demonstrate the
   embargo path on a test registration, not assert it.
4. **Receipt + verification** — the OSF identifiers (project GUID, registration DOI/GUID)
   recorded into the study ledger via `anchor.recorded`, ledger re-checkpointed, and a
   `verify_anchor` path for OSF equivalent to the Zenodo one: re-export, fetch the public
   (or embargoed, as applicable) OSF record independently, compare root + bundle hash +
   registration hash against the record's stated anchor values.
5. **Failure semantics** — partial OSF state (project created, registration failed) is a
   recorded, resumable deposit state, never presented as an anchor. The deposit is complete
   when the receipt verifies, and not before — the same rule the Zenodo path already obeys.
6. **UI surfacing** — any new UI for OSF actions goes through the Article XIV wireframe gate
   (wireframes updated + owner approval of renders before UI code). Service-level capability
   lands first; UI follows the constitution.
7. **Live demonstration before onboarding** — the completed workflow is demonstrated on an
   Axiovex-owned study (not partner data) with the same read-back standard as AR-1: public
   record fetched independently, receipt verified, evidence recorded. Only then is OSF part of
   onboarding. (This demonstration is a build deliverable, not a partner activity.)

### 4.3 Task sketch (for the build spec that follows this design)

| # | Task | Depends on |
|---|------|-----------|
| T-P1 | OSF transport (project/components/files) behind the adjudicator-approval gate; seeded failure tests | `osf_metadata` (exists) |
| T-P2 | Registration action incl. embargo path, demonstrated on test registrations | T-P1 |
| T-P3 | Receipt ledgering + OSF `verify_anchor` vs independently fetched record | T-P2 |
| T-P4 | Live demonstration on an Axiovex study; evidence record (AR-1 standard) | T-P3 |
| T-P5 | UI surfacing for deposit/anchor incl. OSF | T-P4 + Article XIV gate |

Claims for this workstream are authored claims-first under the program's standing spec-kit +
AEE rule when the build is specced; this design fixes scope and sequencing, not claim text.

## 5. Operational shape

### 5.1 Hosting

DN-003 hosted-first: Axiovex operates the deployment; the partner is a tenant (Spec 005
tenancy model) with its own IdP configuration (E1) and role assignments (WS6 matrix:
researcher / reviewer / adjudicator / integrity). The institution-local and hybrid shapes
remain available as later moves on the same architecture; the pilot does not promise them on
a date.

**Decision note (2026-10-12):** the owner has decided the **pilot** deployment shape
(ratifying the coordinator's recommendation, 2026-10-12): the pilot operates as
**partner-workstation installs under the Spec 009 shape** — the partner installs and runs
Tekmerion on its own workstations; no Axiovex-operated hosted deployment exists for the
pilot. The DN-003 hosted shape above is **deferred, not abandoned**: an Axiovex-hosted
offering is decided only when a partner requirement names it, and the §5.2 onboarding steps
written for the hosted shape apply at that point. Until then, the hosted-shape register
items (HECVAT §9 items 3, 5, 8, 9 and the hosted residues of 6 and 7) remain
**not yet answerable** — the workstation pilot creates no hosting facts. This note is
appended; the DN-003 text above stands as originally written.

### 5.2 Onboarding steps

1. **Fit confirmation** against §2.2 — including the F5 append-only conversation and F3 IdP
   check — recorded, with any failed criterion ending onboarding honestly rather than waived.
2. **Data & licence intake** — partner content classes reviewed against §2.3; per-source
   rights recorded (WS5) before the first retrieval.
3. **Tenant + identity setup** — tenant created, IdP configured, partner actors enrolled
   with signing keys (Spec 005 E1 enrollment); role assignments named by the partner.
4. **Training** — register discipline (no claim without a falsifier), freeze semantics,
   adjudication and second review, reading a bundle. Short, practical, on the demo study's
   real record (including its INVALID run — the failure is part of the training material).
5. **Pilot question selection** — one real question, jointly scoped (§3.1).
6. **Run** — §3.1 end-to-end, partner-operated (S2).
7. **Audit exercise** — §3.3 P-K3 measured with the partner's adjudicator, timed, recorded
   either way.
8. **Close-out** — criteria scored against §3.2/§3.3 as registered; partner assessment (S4)
   appended; pilot record anchored.

### 5.3 Support model (honest at MVP scale)

One named Axiovex contact; business-hours response; issues logged into the pilot record.
**No SLA numbers are promised** — none can be evidenced at MVP scale, and Article X forbids
claiming a service level we have not operated. What is promised is narrower and true: every
pilot incident that touches the record (integrity, availability of the ledger, deposit
failures) is disclosed to the partner with its evidence, whether or not it flatters us.
Uptime, response-time, and support-coverage commitments are commercial terms for a later,
post-pilot conversation — with operating data behind them by then, or not made.

### 5.4 Partner data handling

- WS5 §4 rights gate is mechanical, not advisory: content a source does not permit
  redistributing is replaced by its provenance stub in any bundle, substitution visible in
  the manifest; unknown = stub-only.
- **Partner data never enters a public bundle, Zenodo deposit, or OSF registration without a
  recorded licence basis for that content.** The AR-1 demo deposits were Axiovex's own study;
  partner deposits default to the least-public form the anchor allows (embargoed/private
  with public anchor values) until the partner directs otherwise in writing.
- Ledger payloads carry no PII beyond what the record requires (DN-005 ingest discipline);
  identities live in the platform directory, and deprovisioning ends access without touching
  the record (DN-011 §3).
- Retention is export + anchor + access restriction (DN-011); there is no deletion workflow
  to offer, and onboarding says so before data moves (F5).

### 5.5 Exit / egress

**The audit bundle is the exit** (DN-003): at any point — end of pilot, fired kill criterion,
or partner's unilateral decision — the partner receives the complete bundle: byte-for-byte
ledger, registration, claims, evidence, verdicts, manifest, and the standalone verifier that
checks it without us. The anchored roots on Zenodo/OSF are public (or embargoed per §5.4)
and independently fetchable. A partner who leaves loses nothing they created and keeps the
ability to prove what the record said. This is stated in partner-facing material because it
is true and because it is the pitch: lock-in would contradict the product's premise.

## 6. Evidence pack — what a partner is shown

Only verified states (Article X). Each item is fetchable or runnable by the partner
themselves; none requires trusting Axiovex's summary of it.

| Item | What it evidences | State |
|------|-------------------|-------|
| Phase 5 audit bundle, Zenodo DOI [10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479) | Export + standalone verification + external anchoring, end-to-end (G2, DN-008) | Live; description carries the INVALID-run correction on the record itself |
| Audit-corrected bundle v3, DOI [10.5281/zenodo.23317023](https://doi.org/10.5281/zenodo.23317023) | The append-only correction discipline applied to our own record | Live |
| Spec 003 worked study, DOI [10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259) | The five-sub-claim decomposition on real, contested public claims — incl. CONTESTED and INCONCLUSIVE verdicts, not only favorable ones | Live |
| Stage-model audit (`docs/audits/2026-10-12-stage-model-audit.md`) | Every prior claim re-staged honestly (checked vs accepted vs digested), nonconformances named | In repo |
| Phase 6 UI | The register-first product surface a partner's staff would actually use | Built; wireframe-governed (Article XIV) |
| **Phase 7 evaluation verdicts** | K1–K5 measured on the frozen evaluation corpus — incl. negatives, published by design | **Filled (2026-10-12): verdicts as issued — supported, supported, inconclusive, contradicted, inconclusive; K1–K5 all pass (K2 after the in-phase verifier fix the evaluation caught); run VALID; bundle anchored at Zenodo DOI [10.5281/zenodo.23319126](https://doi.org/10.5281/zenodo.23319126); full record in `specs/002-mvp-implementation/evaluation/EVALUATION-REPORT.md`** |
| OSF registration of the Phase 7 study (Spec 010, T-P4) | The registry-side anchor for the same evaluation bundle: OSF project [dvrew](https://osf.io/dvrew/), registration [84dk7](https://osf.io/84dk7/), DOI [10.17605/OSF.IO/84DK7](https://doi.org/10.17605/OSF.IO/84DK7) — the registration record states the bundle's anchor values; receipt + passed public verification in `specs/010-osf-registration/records/` (`demo-receipt.json`, `demo-verification.json`) | Live |
| Spec 005 E1 + E2 | OIDC + SAML identity, key enrollment, RBAC, platform audit ledger | Built and claim-supported (CLM-005-01, CLM-005-02); E3 (SCIM) in flight; E4–E6 specified, not claimed *(row corrected 2026-10-12 — as written it predated E2's landing)* *(second correction, 2026-10-12: E3 (SCIM provisioning + lifecycle), E4 (tenancy hardening, break-glass, signed incident-response egress), and E6 (compliance evidence — SPRS self-score machinery, POA&M register, SOC 2 readiness mapping, CUI marking, audit-export demonstration) have all since merged and are claim-supported; the bundle stands at v0.7.0 with 29 of 31 claims supported, and the T533 pilot gate is discharged. Still open, both by design: the E5 admin console (CLM-005-13, draft — unbuilt, gated on owner approval of the wireframes in PR #11) and CLM-005-31 (the DFARS owner/legal flag). The row's item text still names E1 + E2; read it as the enterprise build E1–E4 + E6)* |

Explicitly **not** in the pack, and not claimed anywhere in pilot material: SOC 2 certification,
CMMC compliance (DN-011 language governs), SAML/SCIM/admin-console availability, SLA figures,
customer references, and any count of verdicts presented as a quality score (DN-010: no volume
tallies standing in for understanding).

*Correction (2026-10-12): SAML (E2) and SCIM (E3) have landed and are claim-supported, so
their availability no longer belongs in the not-claimed list above — the Spec 005 row carries
them. Admin-console availability remains not claimed (E5 unbuilt; owner wireframe gate).
SOC 2 certification and CMMC compliance are not claimed, as written; neither are
SLA figures, customer references, or verdict tallies.*

## 7. Sequencing and gates

1. **This design** (DN-012 + this document) — done on owner ratification of DN-012.
2. **OSF workstream build** (§4) — claims-first spec, build, live demonstration (T-P4).
3. **Evidence pack finalized** — Phase 7 verdicts slotted into §6 as issued.
4. **Named-target shortlist** — institutions matched against §2, with the fit evidence for
   each — **returns to the owner as the next gate.**
5. **Per-target approval** — the owner approves (or doesn't) each named target before any
   contact with it. Approval of the shortlist is not approval of contact.
6. **Outreach, onboarding, run** — per §5.2, only for approved targets.

## 8. What remains not understood

Recorded as questions for discovery (with approved targets) and for the OSF build — not
assumptions baked into the design:

- **Procurement & security-review timelines.** University vendor review (security, privacy,
  accessibility, legal) can run weeks to many months and may gate any pilot start. We have no
  measured figure for our archetype, and whether the review starts before or after a pilot
  agreement is unknown.
- **SOC 2 / HECVAT expectations.** Whether the archetype's security review requires SOC 2, a
  HECVAT, or accepts an evidence-based review of the kind §6 offers (DN-012 caveat 2).
- **OSF: requirement or preference?** §4 builds OSF because it is the community's registry and
  the owner decided it — but whether partners treat OSF registration as a hard requirement, a
  nice-to-have beside the Zenodo DOI, or irrelevant is unlearned. Discovery answers it; the
  build does not depend on the answer, but pilot messaging should.
- **SAML at pilot start.** Whether the archetype's IdPs are Entra/Google in practice, or
  Shibboleth-first in a way that makes F3 exclude the best-fit partners until E2 lands.
  *Resolved (2026-10-12): the shortlist pass answered this — the sample is Shibboleth-first (5 of 9 SAML-evidenced, none Entra/Google) — and E2 has landed, so the exclusion does not bite; see `SHORTLIST-DRAFT.md` §5.*
- **Adjudicator availability.** P-K3 assumes a partner adjudicator can give the audit exercise
  two focused hours. Whether that time exists in a real evidence-synthesis service's week is
  an empirical question the pilot itself will answer — possibly by firing P-K3 for reasons
  that are about calendars, not bundles. The record will distinguish the two if it happens.
- **Append-only vs institutional retention policy.** F5 starts the conversation; the actual
  data-governance review (retention schedules, erasure requests, records law for public
  universities) has not happened anywhere yet, and its outcome could reshape onboarding.
- **Cost reality at partner scale.** P-K5 measures one question's marginal cost. Whether the
  $25 shape holds across a partner's full question volume (OpenAlex credit economics at
  scale) is Phase 7's question first and the pilot's second — neither has reported yet.
