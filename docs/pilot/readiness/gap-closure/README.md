# Gap Closure — Status Board for the HECVAT NOT YET ANSWERABLE Register

**Date:** 2026-10-12 · **Register:** `../HECVAT-SELF-ASSESSMENT-DRAFT.md` §9 (15
items) · **Rule:** this board maps each register item to what closes it. A
"draft-closed" item means an honest document now exists **as a draft for
owner/counsel review** — adoption, execution, or submission is a separate act,
and nothing in this folder has been sent anywhere. The HECVAT draft itself is
unchanged by this package.

**Adoption (2026-10-12):** the owner has ratified adoption of this folder's seven
documents (`PRIVACY-NOTICE-DRAFT.md`, `DPA-TEMPLATE-DRAFT.md`,
`INCIDENT-RESPONSE-PLAN-DRAFT.md`, `BCP-DR-DRAFT.md`,
`SUBPROCESSOR-INVENTORY-DRAFT.md`, `AI-GOVERNANCE-STATEMENT-DRAFT.md`,
`HOSTING-FACTS-MEMO.md`) as **Axiovex working documents**, effective 2026-10-12.
Adoption is recorded with one condition, stated here and in each document's dated
adoption line: **counsel review is required before execution with any partner.**
Adoption changes no document's substance; each draft's original "not yet adopted"
header stands as its drafting provenance, with the dated adoption line appended.
Nothing in this folder has been sent anywhere.

## The board

| # | Register item | Status | Closed by / gated on |
|---|---|---|---|
| 1 | Company profile facts (headcount, founding, HQ, financials) | **OWNER-SUPPLIED** | Only the owner can state these; no repo record contains them. Referenced as outstanding in `PRIVACY-NOTICE-DRAFT.md` §1. **Note (2026-10-12):** a **drafted** entry now exists in the HECVAT register §9, built from the repo record with every non-record field flagged — it is a draft **pending owner confirmation**, not an owner-supplied fact; this item's status is unchanged |
| 2 | Named security/privacy contacts | **OWNER-SUPPLIED** | Owner names; every draft in this folder carries `[OWNER-TO-NAME]` markers where the names land. **Note (2026-10-12):** a **drafted** entry now exists in the HECVAT register §9, flagged **pending owner confirmation**; this item's status is unchanged |
| 3 | Hosting provider, regions, host certifications | **HOSTING-DECISION-GATED** | `HOSTING-FACTS-MEMO.md` §2 — no provider exists to name today. **Decision note (2026-10-12):** the owner has decided the pilot deployment shape — **partner-workstation installs under the Spec 009 shape**; the Axiovex-hosted decision is deferred until a partner requirement names it (DESIGN §5.1 decision note). This item concerns the *hosted* offering: it **remains not-yet-answerable** for any future hosted deployment and is not closed by the pilot decision |
| 4 | Subprocessor inventory + change-notification process | **DRAFT-CLOSED** | `SUBPROCESSOR-INVENTORY-DRAFT.md` — five actual subprocessors from the shipped code/process; CORE and the other designed-only channels explicitly excluded as not-shipped (§4 of that doc). Notice period remains `[OWNER TO CONFIRM]` inside the draft. **Correction (2026-10-12):** the inventory now lists **six** subprocessors — Spec 012 landed the same day and CORE was entered as #6 in §1 of that document (its §4 entry carries the dated status line). CORE is no longer an excluded designed-only channel; the other designed-only channels remain excluded as not-shipped. **Adoption (2026-10-12):** adopted as a working document (counsel review before partner execution) |
| 5 | Backup schedule/retention + restore tests (hosted) | **HOSTING-DECISION-GATED** | `BCP-DR-DRAFT.md` §5 states today's truth (record-layer recoverability exists; deployment backups do not) and names the trigger: first hosted deployment, before first partner tenant. **Decision note (2026-10-12):** pilot shape decided as workstation installs (see item 3 note) — this hosted item **remains not-yet-answerable** for any future hosted offering; not closed |
| 6 | BCP/DR plan + exercise records | **DRAFT-CLOSED** (current reality) | `BCP-DR-DRAFT.md` — plan for the deployment reality that exists (repos + anchors + bundle recovery). Residue: hosted-service DR *exercises* are hosting-gated (memo §2). **Notes (2026-10-12):** adopted as a working document (see Adoption note above; counsel review before partner execution). The hosted residue stays gated on a future hosted decision — the pilot proceeds on workstation installs |
| 7 | Independent penetration test of the hosted deployment | **COMMISSIONED-WORK** | Not commissioned by this package. Sequencing note in the memo §2: its meaningful target is the hosted deployment, so it follows the hosting decision. **Disposition (2026-10-12):** owner-ratified — **commission when a pilot target engages**. No spend is authorized now |
| 8 | Hosted vulnerability scanning (tooling, cadence) | **HOSTING-DECISION-GATED** | Memo §2 — a deployment record, created when a deployment exists. **Decision note (2026-10-12):** pilot shape decided as workstation installs (see item 3 note) — this hosted item **remains not-yet-answerable** for any future hosted offering; not closed |
| 9 | Hosted network controls + monitoring / security-event monitoring (SIEM) records | **HOSTING-DECISION-GATED** | Memo §2 — properties of a deployment network that does not yet exist. **Decision note (2026-10-12):** pilot shape decided as workstation installs (see item 3 note) — this hosted item **remains not-yet-answerable** for any future hosted offering; not closed |
| 10 | IR plan with contractual notification timelines | **DRAFT-CLOSED** | `INCIDENT-RESPONSE-PLAN-DRAFT.md` — roles (owner-to-name), severity classes, detection sources as they actually exist (T554 egress named as specified-not-built), timelines as bracketed commitments-to-be-confirmed. **Correction (2026-10-12):** T554 signed incident-response event egress has since been **built** (Spec 005 E4, merged 2026-10-12) — on that one point the IR draft's detection premise is superseded. The draft itself is unchanged here; it takes the update at adoption. **Adoption (2026-10-12):** the plan is adopted as a working document (counsel review before partner execution); the T554 update above is taken at that review — the plan's text is not edited by adoption |
| 11 | Personnel security program records (screening, training) | **OWNER-SUPPLIED** | Organizational facts (CMMC matrix: 3.2/3.9 families are Organizational). The DPA template (§5) refuses to finalize its personnel section until these are true. **Note (2026-10-12):** a **drafted** entry now exists in the HECVAT register §9 — it records only what the repo record supports and flags the program facts as an open gap; this item's status is unchanged |
| 12 | Accessibility conformance (WCAG audit / VPAT) | **COMMISSIONED-WORK** | Not commissioned by this package; no conformance level is claimed anywhere until an audit exists. **Disposition (2026-10-12):** owner-ratified — **commission when a pilot target engages**. No spend is authorized now, and no conformance level is claimed in the meantime |
| 13 | Privacy notice + DPA template | **DRAFT-CLOSED** | `PRIVACY-NOTICE-DRAFT.md` + `DPA-TEMPLATE-DRAFT.md` — both carry the counsel-review label; the DPA's deletion clause states the append-only reality and the erasure-certificate mechanism's specified-but-not-executable status (Axiomere T112) verbatim. **Adoption (2026-10-12):** both adopted as working documents (counsel review before partner execution) |
| 14 | AI commitments as contract terms (no-training; governance policy) | **DRAFT-CLOSED** | Contract term: `DPA-TEMPLATE-DRAFT.md` §12. Policy document: `AI-GOVERNANCE-STATEMENT-DRAFT.md` (two-lane rule, no model in the verdict path, total attribution). **Adoption (2026-10-12):** adopted as working documents (counsel review before partner execution) |
| 15 | SCIM provisioning / automated deprovisioning as capabilities | **IN-FLIGHT ELSEWHERE** | Spec 005 phase E3 (build in flight). Answerable only when the phase lands and CLM-005-05/-06 move on evidence; this package claims nothing about it. **Correction (2026-10-12): LANDED.** Phase E3 merged the same day (PR #9); CLM-005-05, CLM-005-06, and CLM-005-07 moved to supported on evidence. Item 15 is now answerable from the claims record — and the answer claims nothing beyond what those claims support |

## The count

- **Draft-closed by this package: 5** — items 4, 6, 10, 13, 14.
- **Owner-supplied: 3** — items 1, 2, 11 (facts and names only the owner holds).
- **Commissioned work: 2** — items 7, 12 (pen test, WCAG audit; neither
  commissioned here).
- **Hosting-decision-gated: 4** — items 3, 5, 8, 9 — plus the hosted residues of
  items 6 and 7 noted in the board.
- **In-flight elsewhere: 1** — item 15 (E3).

Total: 15. Every item is accounted for, and no item is marked closed by anything
other than the thing that actually closes it.

*Correction (2026-10-12): item 15 has landed since this board was written — see
its row above. The in-flight count is now **0**; item 15's disposition is
closed-by-landing (E3, on claims evidence), not by this package. Items 4 and 10
carry same-day corrections on their rows (CORE's subprocessor entry; T554's
build). All other counts and statuses stand as written.*

*Owner decisions (2026-10-12), recorded on the rows above:* the seven documents
in this folder are **adopted as Axiovex working documents** (counsel review
required before execution with any partner); items 7 and 12 are dispositioned
**commission when a pilot target engages** (no spend authorized now); the pilot
deployment shape is decided (workstation installs — DESIGN §5.1 decision note), and
items 3, 5, 8, 9 and the hosted residues **remain hosting-gated for any future
hosted offering** — the count above is unchanged: the hosted items are answered
for the pilot by the absence of a hosted deployment, not closed. Items 1, 2, 11
remain owner-supplied; drafted entries for them exist in the HECVAT register §9,
pending owner confirmation.

## What adoption requires (not done here)

1. Owner supplies items 1, 2, 11 and confirms the bracketed periods/roles inside
   the drafts (subprocessor notice period, IR timelines, off-ledger retention,
   DR-exercise cadence).
2. Counsel reviews and completes the privacy notice and DPA template (all
   `[COUNSEL]` brackets, transfer mechanisms after the hosting decision).
3. Owner answers the single question at the end of `HOSTING-FACTS-MEMO.md`.
4. Only then are the HECVAT draft's answers re-issued against the adopted
   documents — by the coordinator's normal process, not by this package.

**Status of this list (2026-10-12):** step 3 is **answered** — the pilot
deployment shape is partner-workstation installs (DESIGN §5.1 decision note; the
hosted question returns only when a partner requirement names a hosted offering).
Adoption itself has been **ratified by the owner** (see the Adoption note at the
top of this board) with step 2's counsel review standing as a condition before
any partner execution, and step 1 partially advanced: drafted entries for items
1, 2, 11 exist in the HECVAT register §9, pending the owner's confirmation —
they are not yet owner-supplied facts. Step 4 has not been performed.

---

*Status board prepared from repo records only, 2026-10-12.*
