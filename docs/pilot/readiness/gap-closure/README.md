# Gap Closure — Status Board for the HECVAT NOT YET ANSWERABLE Register

**Date:** 2026-10-12 · **Register:** `../HECVAT-SELF-ASSESSMENT-DRAFT.md` §9 (15
items) · **Rule:** this board maps each register item to what closes it. A
"draft-closed" item means an honest document now exists **as a draft for
owner/counsel review** — adoption, execution, or submission is a separate act,
and nothing in this folder has been sent anywhere. The HECVAT draft itself is
unchanged by this package.

## The board

| # | Register item | Status | Closed by / gated on |
|---|---|---|---|
| 1 | Company profile facts (headcount, founding, HQ, financials) | **OWNER-SUPPLIED** | Only the owner can state these; no repo record contains them. Referenced as outstanding in `PRIVACY-NOTICE-DRAFT.md` §1 |
| 2 | Named security/privacy contacts | **OWNER-SUPPLIED** | Owner names; every draft in this folder carries `[OWNER-TO-NAME]` markers where the names land |
| 3 | Hosting provider, regions, host certifications | **HOSTING-DECISION-GATED** | `HOSTING-FACTS-MEMO.md` §2 — no provider exists to name today |
| 4 | Subprocessor inventory + change-notification process | **DRAFT-CLOSED** | `SUBPROCESSOR-INVENTORY-DRAFT.md` — five actual subprocessors from the shipped code/process; CORE and the other designed-only channels explicitly excluded as not-shipped (§4 of that doc). Notice period remains `[OWNER TO CONFIRM]` inside the draft |
| 5 | Backup schedule/retention + restore tests (hosted) | **HOSTING-DECISION-GATED** | `BCP-DR-DRAFT.md` §5 states today's truth (record-layer recoverability exists; deployment backups do not) and names the trigger: first hosted deployment, before first partner tenant |
| 6 | BCP/DR plan + exercise records | **DRAFT-CLOSED** (current reality) | `BCP-DR-DRAFT.md` — plan for the deployment reality that exists (repos + anchors + bundle recovery). Residue: hosted-service DR *exercises* are hosting-gated (memo §2) |
| 7 | Independent penetration test of the hosted deployment | **COMMISSIONED-WORK** | Not commissioned by this package. Sequencing note in the memo §2: its meaningful target is the hosted deployment, so it follows the hosting decision |
| 8 | Hosted vulnerability scanning (tooling, cadence) | **HOSTING-DECISION-GATED** | Memo §2 — a deployment record, created when a deployment exists |
| 9 | Hosted network controls + monitoring/SIEM records | **HOSTING-DECISION-GATED** | Memo §2 — properties of a deployment network that does not yet exist |
| 10 | IR plan with contractual notification timelines | **DRAFT-CLOSED** | `INCIDENT-RESPONSE-PLAN-DRAFT.md` — roles (owner-to-name), severity classes, detection sources as they actually exist (T554 egress named as specified-not-built), timelines as bracketed commitments-to-be-confirmed |
| 11 | Personnel security program records (screening, training) | **OWNER-SUPPLIED** | Organizational facts (CMMC matrix: 3.2/3.9 families are Organizational). The DPA template (§5) refuses to finalize its personnel section until these are true |
| 12 | Accessibility conformance (WCAG audit / VPAT) | **COMMISSIONED-WORK** | Not commissioned by this package; no conformance level is claimed anywhere until an audit exists |
| 13 | Privacy notice + DPA template | **DRAFT-CLOSED** | `PRIVACY-NOTICE-DRAFT.md` + `DPA-TEMPLATE-DRAFT.md` — both carry the counsel-review label; the DPA's deletion clause states the append-only reality and the erasure-certificate mechanism's specified-but-not-executable status (Axiomere T112) verbatim |
| 14 | AI commitments as contract terms (no-training; governance policy) | **DRAFT-CLOSED** | Contract term: `DPA-TEMPLATE-DRAFT.md` §12. Policy document: `AI-GOVERNANCE-STATEMENT-DRAFT.md` (two-lane rule, no model in the verdict path, total attribution) |
| 15 | SCIM provisioning / automated deprovisioning as capabilities | **IN-FLIGHT ELSEWHERE** | Spec 005 phase E3 (build in flight). Answerable only when the phase lands and CLM-005-05/-06 move on evidence; this package claims nothing about it |

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

## What adoption requires (not done here)

1. Owner supplies items 1, 2, 11 and confirms the bracketed periods/roles inside
   the drafts (subprocessor notice period, IR timelines, off-ledger retention,
   DR-exercise cadence).
2. Counsel reviews and completes the privacy notice and DPA template (all
   `[COUNSEL]` brackets, transfer mechanisms after the hosting decision).
3. Owner answers the single question at the end of `HOSTING-FACTS-MEMO.md`.
4. Only then are the HECVAT draft's answers re-issued against the adopted
   documents — by the coordinator's normal process, not by this package.

---

*Status board prepared from repo records only, 2026-10-12.*
