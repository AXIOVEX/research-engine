# Business Continuity & Disaster Recovery — Tekmerion (DRAFT)

**DRAFT — for owner review — not yet adopted.**
**Adoption (2026-10-12):** adopted as an Axiovex working document by owner
ratification, 2026-10-12. **Counsel review is required before execution with any
partner.** The header above stands as this document's drafting provenance;
adoption changes nothing substantive in the text. The hosted residues named
below remain gated on a future hosted decision (the pilot proceeds on
workstation installs — DESIGN §5.1 decision note, 2026-10-12).
**Date:** 2026-10-12 · **Closes:** HECVAT register item 6 for the deployment
reality that exists today; item 5 (backup schedule / restore tests) and the
hosted-exercise half of item 6 remain gated on the hosting decision — see §5 and
`HOSTING-FACTS-MEMO.md` · **Sources:** `docs/install.md`, `docs/pilot/DESIGN.md`
(§5.5, §6), Spec 009 acceptance records, Spec 010 records, DN-003, DN-005.

---

## 1. The distinction this plan is built on

Continuity of the **record** and continuity of the **service** are different
problems, and Tekmerion's architecture makes the first one strong today and the
second one not yet a thing that exists:

- **The record** — study ledgers, bundles, registrations, verdicts — is
  content-addressed, hash-chained, and anchored outside our control plane. It is
  recoverable from public artifacts without trusting us.
- **The service** — an Axiovex-operated hosted deployment — **does not operate in
  production today**. Tekmerion is delivered as installable packages (wheels built
  from three public repositories) run on operator or institution machines. There is
  therefore no hosted service whose continuity this plan could honestly describe
  yet; §5 states what comes into existence when one does.

## 2. Source of truth, as it exists today

| Layer | Location | Why it is a source of truth |
|---|---|---|
| Code + specs + records | Public GitHub repositories `AXIOVEX/tekmerion`, `AXIOVEX/axiomere`, `AXIOVEX/axiomere-python` | Every claim, assessment, and study record of the program is committed history; CLM-level states are re-derivable from the repo |
| Study artifacts (Axiovex's own) | Zenodo deposits: DOIs 10.5281/zenodo.23311479, 23317023, 23317259, 23319126 | Published, effectively immutable; changes are new versions by registry rule |
| Registration anchor (Phase 7 study) | OSF registration 84dk7, DOI 10.17605/OSF.IO/84DK7 | Public registration record states the bundle's anchor values; receipt + passed public verification on file in `specs/010-osf-registration/records/` |

Loss of any single copy — including every Axiovex machine — does not lose the
record: the anchors are held by registries we do not operate, and any bundle copy
can be checked byte-for-byte against them.

## 3. Recovery procedure (record plane — the procedure that exists)

1. Clone the three repositories (above).
2. Build the wheel set and install, following `docs/install.md` verbatim (maturin
   build of the Axiomere bindings; `pip install` of the three wheels + the MCP
   SDK). This path was executed verbatim from a clean environment in the Spec 009
   clean-room acceptance — twice (21/21 steps, both runs).
3. Restore study state from the exported audit bundle: the bundle is the complete,
   byte-for-byte record (ledger, registration, claims, evidence, verdicts,
   manifest). The standalone verifier checks it without any Axiovex system.
4. Re-anchor or re-verify against Zenodo/OSF: compare checkpoint root, bundle
   hash, and registration hash against the registry records' stated anchor values
   (Spec 010's `verify_osf_anchor` and the Zenodo equivalent exist and have been
   run against live records).
5. Resume operation: new appends continue the chain from the restored checkpoint;
   the recovery itself is recorded as appended events, never as a rewritten past.

**Stated limit:** this procedure has been exercised in its pieces (clean-room
install; standalone bundle verification; live anchor verification) but has **not**
been run as a single timed disaster-recovery exercise, and no recovery-time
objective (RTO) is claimed for
it. **[OWNER TO CONFIRM: whether a timed end-to-end exercise is run before the
first pilot onboarding — recommended.]**

## 4. Continuity of current operations

- Development and program records are committed and pushed continuously; the loss
  of the operator workstation loses only uncommitted work. Long-running work is
  checkpointed in the repo by program discipline.
- Registry-side failure is a handled case, not a theory: when OSF's archive step
  destroyed a submitted registration, the deposit machinery detected it on
  read-back, recorded the state honestly, and resumed safely, without duplicating
  anything (idempotently), to a completed
  registration (Spec 010 records). Zenodo versioning gives the same property on
  the deposit side.
- No single person's machine is a system of record for anything already anchored
  or committed.

## 5. What does NOT exist yet — and the trigger that creates it

Until an Axiovex-operated hosted deployment exists, the following **do not exist**
and are not claimed anywhere:

- a backup schedule or retention policy for deployment storage;
- restore tests of deployment backups;
- disaster-recovery exercises of a hosted service;
- commitments on how much data could be lost or how fast service returns
  (RPO/RTO commitments) of any kind.

**Trigger:** the owner's hosting decision (`HOSTING-FACTS-MEMO.md`) and the
creation of the first hosted deployment. Before the first partner tenant onboards
onto that deployment, the deployment record must add: the backup schedule and
retention, the first restore test with its result, and the recovery-exercise
cadence. Those become HECVAT-answerable deployment records at that point (register
items 5 and 6 close fully), not before.

For the **self-hosted shape** (institution operates the deployment), the
institution's storage and backup regime governs the service layer; the record
layer's guarantees above (bundle exit, external anchors, standalone verification)
apply unchanged, and the partner's exit bundle is itself a complete recovery
artifact for the study record.

## 6. Roles and review

- Plan owner: **[OWNER-TO-NAME]** · Recovery executor: **[OWNER-TO-NAME]**.
- Review triggers: the hosting decision; any Spec 005 phase exit that changes the
  deployment shape; any SEV-1/SEV-3 incident (per
  `INCIDENT-RESPONSE-PLAN-DRAFT.md`).

---

*Draft prepared from repo records only, 2026-10-12. Not adopted; the §5 items are
named absences, and this document's honesty about them is its content.*
