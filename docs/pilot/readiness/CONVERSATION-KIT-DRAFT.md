# Pilot Conversation Kit (DRAFT — NOT SENT)

**Status: HELD DRAFTS.** Nothing in this document has been sent to anyone, and no
part of it may be sent until the owner gives per-target approval for that target
(DESIGN §7 step 5). Prepared 2026-10-12 from `docs/pilot/DESIGN.md`,
`docs/pilot/SHORTLIST-DRAFT.md`, and the three dossiers in this folder. Bracketed
slots are filled per target from the dossier personalization blocks in §2.

---

## 1. First-contact letter template — library evidence-synthesis service archetype

> Subject: A measured pilot for [UNIT NAME] — one evidence question, verdicts you can
> defend from the record alone
>
> Dear [NAME / TEAM],
>
> I lead Axiovex Systems, where we build Tekmerion, a research engine for evidence
> questions whose point is defensibility: claims are registered with their
> falsifiers before evidence is gathered, every verdict is issued against a frozen
> registration, and the whole study exports an audit bundle your team can verify
> without us. We are looking for **one** university partner for a first pilot: one
> real question from your pipeline, run end-to-end by your staff, measured against
> criteria we registered before naming any partner — including kill criteria that
> end the pilot as a published failure if our machinery doesn't hold up (a citation
> that doesn't resolve, a replay that diverges, an audit that takes your
> adjudicator more than two hours from the bundle alone).
>
> [PERSONALIZATION BLOCK — see §2]
>
> Everything we would ask you to evaluate is already public: our evaluation study
> and its verdicts (including the inconclusive and contradicted ones), a worked
> study that returned CONTESTED verdicts on contested public claims, and our first
> demo — whose run was invalid, which we published ourselves. [ANCHOR LINKS SLOT:
> Phase 7 DOI 10.5281/zenodo.23319126 · OSF registration 10.17605/OSF.IO/84DK7 ·
> worked study DOI 10.5281/zenodo.23317259 · demo DOI 10.5281/zenodo.23311479]
>
> Would you be open to a 30-minute conversation? Not a sales call — the first
> questions are ours to answer about your review process, and the first is the one
> that may end this quickly: [Q1 SLOT — the security-review question from §3, in
> the target's own vocabulary]. If the answer is a hard requirement we cannot meet
> today, we would rather learn it in one conversation than in a procurement cycle,
> and we will tell you plainly which of our limits are current facts rather than
> roadmap items.
>
> [SIGN-OFF SLOT]

Template rules (binding on any send): no claim beyond the claims records; no SLA
(service-level agreement), certification, or timeline promises; the kill criteria
are named in the first
letter, not discovered later (F6 is an agreement, and this letter is where it
starts); the INVALID demo is linked in the first letter, not the third meeting.

## 2. Personalization blocks (from the dossiers)

**Duke — Medical Center Library, Evidence Synthesis Service.**
"We have read your service model closely — the tiered partnership, the project-leader
policy, and a queue of reviews that run 12 to 18 months. Tekmerion is aimed at the
half of that work your librarians deliberately don't do: the screening and
adjudication record, where a team must later defend why each verdict stands. We have
also done our homework on your vendor process: our HECVAT answers are pre-drafted
against your published requirements — including the places where our honest answer
today is a gap, such as the absence of a SOC 2 report. One routing question we
cannot answer from public pages: whether an engagement with the Medical Center
Library is reviewed through the university IT Security Office process or Duke
Health's DHTS demand process."

**Pitt — HSLS Systematic Review Program.**
"Your programme's intake discipline is the closest published analogue to how
Tekmerion works: a written protocol before searching begins, protocol registration
encouraged, independent duplicate screening, and the search documented to
manuscript standard. We would like to show you what that discipline looks like when
the adjudication record itself — not only the search — is registered, frozen, and
independently replayable. We know Pitt's vendor assessment runs on an onboarding
questionnaire your unit submits under the Vendor Security Risk Assessment Operating
Standard; if a conversation is useful, we would welcome receiving that
questionnaire so our answers are aimed at your instrument rather than a generic
one."

**York — Centre for Reviews and Dissemination.**
"CRD's product is defended evidence verdicts for a national decision-maker, and
PROSPERO makes protocol pre-registration your home discipline — which is why we are
writing to a methods group, not only to library services. Our machinery registers
claims and their falsifiers before evidence moves, freezes the registration, and
makes every verdict replayable from a standalone bundle. We recognise the threshold
question may not be interest but permission: whether NIHR commissioning terms for
TAR/YES work allow a question to run on an external platform at all, and what
confidentiality attaches. If the answer is no for commissioned work, a
non-commissioned question may still be in scope — that is the first thing we would
ask. We also flag, rather than bury, that we are US-hosted today, which makes your
data-protection transfer assessment a real agenda item."

## 3. Discovery-question script (in order; branch logic included)

Ask in this order. Record answers verbatim in the fit-confirmation record; a
conversation that produces no record did not happen.

**Q1 — the gate (ask first, in the target's vocabulary).** *Does your vendor
security review hard-require SOC 2 Type II (or a completed HECVAT at a threshold)
for a hosted pilot holding no PHI (protected health information) — or does an
evidence-based review satisfy it?*
(Duke form: is the HECVAT + evidence pack sufficient without a SOC 2 report, and
does ITSO or DHTS review us? Pitt form: what does the Operating Standard's
assessment require for a low-data-class vendor — and may we see the questionnaire?
York form: which information-security standards would the contract name after the
Computing Risk Assessment?)
- **Branch A — hard requirement we cannot meet.** Do not negotiate against a
  published standard. State our position once (readiness mapping, E6 specified not
  built, no date promised). Options, in order: (i) pause this target until the
  compliance-evidence phase lands; (ii) discuss the self-hosted shape inside their
  boundary (architecture exists; no date promised); (iii) close gracefully and
  record the discovery outcome — the shortlist's ranking logic already prices this
  in. Never offer to "start the SOC 2 process" as a pilot inducement.
- **Branch B — evidence-based review accepted.** Send the vendor packet
  (`VENDOR-PACKET.md`) and the HECVAT draft; agree the review's instrument and
  owner on their side; proceed to Q2.
- **Branch C — unclear / depends.** Ask what it depends on (data classification is
  the usual axis) and get the classification conversation scheduled; treat as
  Branch A for sequencing until resolved.

**Q2 — timeline.** *What is your measured security-review timeline for a
low-data-class pilot, and does review start before or after a pilot agreement?*
- If the review exceeds the pilot window, re-sequence the start date rather than
  compressing the review. York carries a published floor: ≥3 months for SSO
  implementation alone, before the contract process is counted.

**Q3 — append-only.** *Will your data-governance office accept export + anchor +
access restriction — no deletion workflow — for pilot records?* (Duke anchor:
their library's published 7-year SR-record retention. York form: the
directory/payload division under UK GDPR.)
- **Deletion-on-demand required → F5 fails → the target exits**, per the
  shortlist's rule, regardless of enthusiasm elsewhere. Record and close honestly.

**Q4 — identity.** *Which attributes will your IdP release to a new SP (service
provider — our side of the sign-in connection), and is
per-tenant SAML configuration acceptable as-is?* (Pitt: use the dev IdP first, per
their published flow. Duke: confirm the operative entityID form and attribute
release for our SP.)
- If their IdP cannot do OIDC or SAML 2.0 → F3 fails for now (not a judgment; a
  sequencing fact).

**Q5 — adjudicator hours.** *Can a named adjudicator protect roughly two focused
hours for the bundle-alone audit exercise inside the pilot window?*
- If not in this window, sequence the target later; do not shrink the exercise —
  P-K3 measured on a rushed audit measures nothing.

**Q6 — OSF.** *Is OSF registration of the pilot study a requirement, a preference,
or irrelevant beside the Zenodo DOI (York: beside PROSPERO)?*
- Any answer is workable: the OSF workflow is built and live-proven (Spec 010).
  Record the answer; it calibrates messaging, not feasibility.

**Q7 — York only.** *Do NIHR commissioning terms permit a question on an external
platform, under what confidentiality?* A no exits York and promotes the alternate;
a "non-commissioned only" answer scopes the pilot question accordingly.

**Q8 — UNC only.** Not applicable to the first three; retained in the script for
the alternate list.

**Q9 — cost shape.** *At your question volume, what does your per-review tooling
cost baseline look like?* Our commitment is ≤$25 marginal cost per question (P-K5);
theirs is context for whether the shape matters.

## 4. If they say yes — next-steps checklist

(In order; DESIGN §7 steps 5–6 and §5.2 govern. Per-target owner approval is
already given when this checklist starts.)

1. **Fit confirmation recorded** (§5.2 step 1): F1–F6 each evidenced or failed in
   writing, including the Q3 append-only conversation's outcome. A failed
   criterion ends onboarding honestly rather than waived.
2. **Vendor review initiated on the target's track** (per dossier: Duke —
   HECVAT v4 + Shibboleth Readiness Profile returned via the unit contact,
   ITSO/DHTS routing confirmed; Pitt — unit submits the onboarding questionnaire,
   instrument obtained and answered; York — Data Protection Screening Questions
   filed, Computing Risk Assessment scheduled, transfer assessment opened).
3. **Data & licence intake** (§5.2 step 2): partner content classes reviewed
   against the pilot scope; per-source rights recorded before the first retrieval.
4. **OSF registration of the pilot study** — protocol/registration created and
   anchored **before any partner data moves** (DN-012 sequencing; Spec 010
   machinery, partner-directed publicity per DESIGN §5.4: least-public form until
   the partner directs otherwise in writing).
5. **Tenant + identity setup** (§5.2 step 3): tenant created; IdP configured
   (their SAML/OIDC, per-tenant); partner actors enrolled with signing keys; role
   assignments named by the partner (researcher / reviewer / adjudicator /
   integrity).
6. **Training** (§5.2 step 4): register discipline (no claim without a falsifier),
   freeze semantics, adjudication and second review, reading a bundle — taught on
   the demo study's real record, including its INVALID run.
7. **Pilot question selection** (§5.2 step 5): one real question, jointly scoped
   small enough to audit completely.
8. **Run** (§5.2 step 6): partner-operated end-to-end; Axiovex assists, does not
   drive (success criterion S2).
9. **Audit exercise** (§5.2 step 7): partner adjudicator, bundle alone, timed
   against P-K3; recorded either way.
10. **Close-out** (§5.2 step 8): criteria scored against the registered §3.2/§3.3
    as written; partner's written assessment appended unedited (or its absence
    recorded as itself); pilot record anchored.

---

*HELD DRAFT — not sent. Prepared 2026-10-12.*
