# Incident Response Plan — Tekmerion Pilot (DRAFT)

**DRAFT — for owner review — not yet adopted.** Timelines in brackets are
commitments-to-be-confirmed, not commitments.
**Adoption (2026-10-12):** adopted as an Axiovex working document by owner
ratification, 2026-10-12. **Counsel review is required before execution with any
partner.** The header above stands as this document's drafting provenance;
adoption changes nothing substantive in the text. Cross-reference: the
gap-closure README board (item 10) records that T554 signed incident-response
egress was built at Spec 005 E4, superseding this plan's detection premise on
that one point; the plan's text takes that update at counsel review, not here.
**Date:** 2026-10-12 · **Closes:** HECVAT register item 10 (plan + notification
timelines in draft form) · **Sources:** `docs/pilot/DESIGN.md` (§5.3 support model),
`specs/005-enterprise-platform/spec.md` (§8 audit ledger, §13.4 AU event classes,
§13.7 T554 IR hooks), Spec 005 CMMC matrix rows 3.6.1–3.6.3,
`specs/010-osf-registration/records/` (a worked provider-side incident).

---

## 1. Scope and posture

This plan covers security and record-integrity incidents affecting the Tekmerion
pilot service: the platform plane (identity, authorization, tenancy, platform audit
ledger) and the study plane (claim registers, evidence, verdicts, bundles,
registry anchors).

Two standing postures govern everything below, and are not negotiable in an
incident:

- **Disclosure with evidence.** Every incident that touches the record — integrity,
  availability of the ledger, deposit failures — is disclosed to the affected
  partner with its evidence, whether or not it flatters us (DESIGN §5.3). No SLA
  numbers (service-level agreement figures) are promised anywhere in this plan:
  none can be evidenced at this scale.
- **Append-only correction.** Incident findings and remediations are appended
  records. Nothing in any ledger is edited or deleted in the course of an incident;
  a correction is a new record that supersedes, exactly like any other correction
  in this program.

## 2. Roles

Role titles are real; the people are the owner's to name. At current scale one
person may hold several roles — that fact is stated, and the owner confirms the
assignments on adoption.

| Role | Responsibility | Held by |
|---|---|---|
| Incident Commander | Declares the incident and severity; owns the timeline, decisions, and closure | **[OWNER-TO-NAME]** |
| Engineering Lead | Containment and remediation in the platform/study code and deployment | **[OWNER-TO-NAME]** |
| Records & Integrity Lead | Evidence preservation: ledger checkpoints, bundle exports, verification runs | **[OWNER-TO-NAME]** |
| Partner Communications | All partner notification under §5; single channel, no side channels | **[OWNER-TO-NAME]** |
| Counsel | Legal duties, regulatory clocks, privilege calls | **[OWNER-TO-NAME: external counsel]** |

Detection, triage support, and the program's operational work sit with the
platform operator on duty: **[OWNER-TO-NAME: rota or named individual]**.

## 3. Severity classes

| Class | Definition (any one suffices) | Examples from the actual machinery |
|---|---|---|
| **SEV-1** | Record integrity compromised or credibly threatened; unauthorized access to partner data; a live ledger or bundle **fails verification** | Tampered ledger detected on verification; a cross-tenant read that returned another tenant's bytes (the E4 isolation battery exists to prove this cannot happen — if it ever does, it is SEV-1 by definition) |
| **SEV-2** | Security event with contained impact; a named-human control bypassed or a key compromised | Single identity's key compromised; authentication-failure burst against one tenant; break-glass session used outside its declared policy; revocation storm |
| **SEV-3** | Record-path function failed without integrity loss | Deposit/anchor failure (precedent: OSF's archive step destroyed a submitted registration while the project and its files were unharmed — detected by receipt/verification read-back, recovered by idempotent resume); prolonged ledger unavailability |
| **SEV-4** | Minor; no record impact | Single failed deposit retry recovered by the machinery; cosmetic/UI defects; a connector outage (Crossref/OpenAlex) that delays retrieval but touches nothing recorded |

## 4. Detection sources — as they actually exist today

Listed by what is real, with the specified-but-not-built parts named as such:

- **Platform audit ledger (built, E1/E2).** The ledger emits the SP 800-171
  §3.3.1/§3.3.2 event classes: account creation/modification, authentication
  successes **and failures**, authorization decisions including denials, admin
  actions, the full key lifecycle, session and API-key lifecycle. Review and
  export of these events is available today.
- **Signed IR event egress (specified, NOT built).** Spec 005 T554 specifies
  security-significant events (auth-failure bursts, break-glass use, revocation
  storms — bursts of key revocations — audit-verification failures) as
  first-class signed outbound messages (webhook egress, E4).
  Until E4 lands, detection of those patterns is by ledger review/export, and this
  plan does not pretend otherwise.
- **Verification machinery (built).** Standalone bundle/ledger verification runs
  offline and fails loudly on tampering; receipt + `verify_anchor` read-backs on
  Zenodo/OSF deposits detect registry-side failures (this is how the SEV-3
  precedent above was caught — the deposit was *not* reported complete until its
  receipt verified).
- **GitHub (code plane).** CI failures, Dependabot/security alerts, and the repo
  audit log for the public codebase. The codebase is public; a code-plane event is
  assessed for whether it can touch any record plane before severity is set.
- **Partner and user reports.** Via **[OWNER-TO-NAME: support channel]** (DESIGN
  §5.3: one named Axiovex contact; business-hours response; issues logged into the
  pilot record).

## 5. Notification timelines — COMMITMENTS-TO-BE-CONFIRMED

These numbers are drafted to be confirmed or changed by the owner on adoption;
until then they are placeholders with a shape, not promises. Regulatory
notification duties rest with the partner institution as controller; Axiovex's
duty is to give the partner the facts and evidence in time for theirs.

| Trigger | Notify | Timeline (draft) |
|---|---|---|
| SEV-1 confirmed | Affected partner institution (named contact) | Initial notice within **[72h — OWNER TO CONFIRM]** of confirmation; updates at least **[daily — OWNER TO CONFIRM]** until closure |
| SEV-2 confirmed, partner data or partner-tenant controls affected | Affected partner | Within **[5 business days — OWNER TO CONFIRM]** |
| SEV-3 affecting a partner study's anchors or availability | Affected partner | In the pilot record and by notice within **[5 business days — OWNER TO CONFIRM]** |
| Any incident touching the record | The pilot record itself | Disclosure with evidence appended at closure, regardless of severity or notification path (DESIGN §5.3) |

An initial notice may be partial; saying what is known, what is not yet understood,
and when the next update arrives is the required shape — a complete-but-late
notice fails this plan.

## 6. Response procedure

1. **Declare.** Incident Commander assigns severity (§3) and opens the incident
   record. The declaration is itself an appended record where the platform ledger
   is the system of record for the affected tenant.
2. **Preserve evidence.** Export the affected ledger(s) and bundle(s); record
   checkpoint roots and bundle hashes at declaration time; run standalone
   verification and record the result. (Append-only ledgers preserve themselves;
   preservation here means *pinning the state at declaration* so later appends
   cannot be confused with it.) Off-ledger material (deployment logs) is
   snapshotted where a deployment exists — see `HOSTING-FACTS-MEMO.md` for the
   current limits of that clause.
3. **Contain with the machinery that exists.** Key revocation (an appended event,
   effective at the next authenticated request), session revocation via
   deprovisioning, API-key revocation, tenant access restriction. There is no
   delete step and no step that rewrites history to look cleaner.
4. **Assess.** Scope from the ledger: which identities, keys, studies, and anchors
   are implicated is answerable from the record; where the record cannot answer,
   the assessment says so.
5. **Notify** per §5.
6. **Remediate.** Code/process fixes land through the normal claims-first, CI-gated
   change process; record-level corrections are appended superseding records.
7. **Close with a post-incident record.** What happened, the measured impact, the
   evidence, what remains not understood, and the remediation — appended to the
   pilot/platform record and shared with affected partners unedited. The SEV-3
   OSF precedent in `specs/010-osf-registration/records/` is the shape of a
   closed incident record in this program.

## 7. Testing and maintenance

- Tabletop exercise against §3 scenarios: **[OWNER TO CONFIRM: cadence — proposed
  once before the first pilot onboarding, then annually]**; exercise records are
  appended like any other record. (CMMC 3.6.3 classifies capability *testing* as
  Organizational — this plan's commitment is ours to set, and it is bracketed
  until the owner sets it.)
- This plan is reviewed on every Spec 005 phase exit and after every SEV-1/SEV-2.

---

*Draft prepared from repo records only, 2026-10-12. Not adopted; creates no
commitment until the owner confirms the bracketed roles and timelines.*
