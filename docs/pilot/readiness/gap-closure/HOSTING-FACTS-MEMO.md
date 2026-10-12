# Hosting Facts — Decision Memo for the Owner

**MEMO — not a draft policy.** This document states facts from the records, names
what they block, and ends with the one question whose answer unblocks it.
**Date:** 2026-10-12 · **To:** the owner · **From:** the pilot readiness work ·
**Sources:** DN-003, DN-011, `specs/005-enterprise-platform/spec.md` (§6 shapes,
§13.8), `docs/pilot/DESIGN.md` (§5.1), `docs/install.md`, Spec 009 records, HECVAT
register §9.

---

## 1. The facts

1. **No production Axiovex-operated cloud hosting of Tekmerion exists today.** No
   cloud provider, region, or hosting account is named in any platform record.
   Nothing in the records describes a running hosted service, because there isn't
   one.
2. **The hosted-first pilot shape was decided; the hosting was not.** DN-003
   (2026-10-11) chose a hosted-first pilot for speed of learning and said, in the
   same paragraph, that hosted-pilot infrastructure choices that cost money return
   to the owner as their own decision. That decision has not been taken yet.
   DESIGN §5.1 inherits the posture: "Axiovex operates the deployment" is the
   pilot's *design*, not a description of an operating service.
3. **What operates today instead:** three public GitHub repositories with CI;
   installable packages (wheels built from those repos) that run on operator or
   institution machines — the Spec 009 install path, executed verbatim in
   clean-room acceptance; a local stdio MCP server as the agent surface; and live
   public anchors on Zenodo and OSF. Spec 009 states its own scope plainly: "no
   hosted/remote transport" — streamable-HTTP/hosted MCP is designed-for, not
   built.
4. **Spec 005's platform claims are written against a deployment that the hosting
   decision will instantiate.** The identity/authorization core (E1/E2) is built
   and claim-supported as code; the tenancy/residency claims it hangs on
   (CLM-005-12, residency pin) are draft, because a residency pin is a fact about
   a deployment, and there is no deployment.
5. **The self-hosted shape is not a fallback in the records; it is a first-class
   target** (DN-003 hybrid architecture), and DN-011/Spec 005 §13.8 record it as
   the *capable* path for CUI-bearing tenants while the hosted shape's DFARS
   252.204-7012 FedRAMP-equivalency question stands open. For the pilot's
   no-CUI/no-PHI scope, that flag does not bite — but the same section is why
   "just stand it up somewhere" is not a records-supported move.

## 2. Which register items this blocks

From the HECVAT register (`HECVAT-SELF-ASSESSMENT-DRAFT.md` §9):

| Item | Why it is blocked |
|---|---|
| **3 — Hosting provider, regions, host certifications** | There is no provider to name. Certifications (the host's own SOC 2 / ISO / FedRAMP posture) attach to a named provider's service and region. |
| **5 — Backup schedule/retention and restore tests** | A schedule is a property of operating deployment storage. The record layer's recoverability exists today (see `BCP-DR-DRAFT.md`); deployment backups do not, because there is no deployment storage. |
| **8 — Hosted vulnerability scanning (tooling, cadence)** | Scanning targets a running deployment. Code-plane hygiene exists (CI on every change); hosted scanning tooling/cadence is a deployment record. |
| **9 — Hosted network controls and monitoring/SIEM** | Network rules and SIEM are properties of the deployment's network, which does not exist. Application-layer deny-by-default is built and answered separately in the HECVAT draft. |
| **6 (hosted half) — DR exercises of a hosted service** | The record-plane recovery procedure is drafted and its pieces exercised; an exercise *of the hosted service* requires the service. |
| **7 (target) — Penetration test** | Commissioned work (not this memo's gate), but its meaningful target is the hosted deployment; a pen test commissioned before the deployment exists tests the wrong thing. Sequencing note, recorded for the owner's planning. |

## 3. The options the records support

**A. Axiovex-hosted on a named cloud (the DESIGN §5.1 / DN-003 pilot shape).**
Stand up the Spec 005 platform as a multi-tenant hosted service on one named
provider in named region(s). Makes answerable: item 3 directly (provider, regions,
inheritable host certifications for the infrastructure scope); items 5, 8, 9 as
deployment records created when the service stands up (backup schedule + first
restore test, scanning tooling + cadence, network controls + monitoring) — i.e.
the hosting decision converts them from *unanswerable* to *scheduled work with an
owner*. Costs money (DN-003's spend gate is exactly this). Also creates the pen
test's real target (item 7).

**B. Partner-self-hosted (the institution operates the deployment).**
The institution runs the deployment inside its own boundary; hosting facts become
the institution's own records (its provider, its regions, its backup regime).
Makes answerable: item 3 by substitution (the answer is the institution's
deployment record), and items 5/8/9 similarly become institution-side facts the
vendor review can cite. **But:** DESIGN §5.1 and success criterion S2 are written
against Axiovex-operated hosting, and pilot kill criterion P-K6 measures whether
*partner staff can operate the product* — under B the operability question changes
meaning. Choosing B is a design amendment (a new design note that says it is
revising the design), not a silent substitution.

**C. Partner-workstation installs (the Spec 009 shape, operating today).**
Partners install the packages and run the study plane + MCP surface on their own
machines now; no new deployment is created. Makes answerable: items 3/5/8/9
largely *dissolve* into the institution's endpoint estate rather than being
answered — a vendor review would assess an installed-software posture, not a
hosted one. Weakest fit to Spec 005's platform claims (the identity plane assumes
a service deployment), and the pilot's hosted-tenancy evidence (E1/E2 in their
designed shape) goes unexercised. Strongest on one axis: it is the only option
that exists today with an acceptance-proven install record.

## 4. What each option does NOT do

None of A/B/C closes the owner-supplied items (company facts, named contacts,
personnel program — register 1, 2, 11), the commissioned items (pen test, WCAG
audit — 7, 12), or the in-flight item (SCIM, 15). The hosting decision is
necessary for §2's items and sufficient for none of the rest; the rest already
have owners or drafts (see `README.md` in this folder).

## 5. The question

> **Which deployment operates the pilot: (A) Axiovex-hosted — and if so, on which
> named cloud provider, in which region(s)? (B) partner-self-hosted, accepting
> the design amendment that requires? Or (C) partner-workstation installs under
> the Spec 009 shape?**

Until that is answered, register items 3, 5, 8, 9 (and the hosted halves of 6
and 7) stay exactly as the HECVAT draft states them: **not yet answerable** — and
at Duke, per its published process, that gap statement is a warranty we can keep,
while any invented answer would be a breach we wrote ourselves.

---

*Memo prepared from repo records only, 2026-10-12. No decision is recorded by this
document; it exists to make the decision statable in one sitting.*

**Decision recorded (2026-10-12):** the owner has answered §5's question,
ratifying the coordinator's recommendation: the pilot operates as **(C)
partner-workstation installs under the Spec 009 shape**. The Axiovex-hosted
option (A) is **deferred until a partner requirement names it**; no cloud provider
or region is named, because none was decided. Register items 3, 5, 8, 9 (and the
hosted halves of 6 and 7) therefore remain exactly as §5's closing paragraph
states them — not yet answerable for any future hosted offering. This memo is
adopted as an Axiovex working document with the rest of the gap-closure folder
(2026-10-12; counsel review required before execution with any partner). The
footer above stands as written on the day the memo was prepared.
