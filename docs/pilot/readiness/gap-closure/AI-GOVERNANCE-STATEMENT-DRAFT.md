# AI Governance Statement — Tekmerion (DRAFT)

**DRAFT — for owner review — not yet adopted.** The contract-term half of this
statement is carried in `DPA-TEMPLATE-DRAFT.md` §12.
**Date:** 2026-10-12 · **Closes:** HECVAT register item 14 (with the DPA term) ·
**Sources:** DN-010 (Tao realignment doctrine), `specs/005-enterprise-platform/spec.md`
(§8: no secondary use), `specs/009-mcp-server/spec.md`, `docs/install.md`,
HECVAT draft §7.

---

## 1. Where AI sits in the product — the architecture, stated plainly

- The verdict machinery is **deterministic production code**: registered claims,
  rule-based evaluation against frozen registrations, recorded controls. No model
  produces a verdict, a score, or an adjudication.
- AI agents may **operate** the platform — through the MCP server surface and its
  agent skill (Spec 009) — only as named actors holding one of the platform's
  human roles (researcher / reviewer / adjudicator / integrity), with a signing
  key enrolled to an identity. Every action they take is attributed and ledgered
  exactly like a human's; there is no anonymous or unauthenticated agent path.
- **Adjudication acts are named-human acts.** Freeze approval and deposit approval
  are gated in the machinery on a named approver; an agent instance cannot supply
  that approval as configuration or by default (Spec 009/010 deposit discipline).

## 2. The two-lane rule (DN-010)

Machine-speed verification (lane 1) and human-paced acceptance (lane 2) are
tracked separately in the record, and lane-1 results are never displayed as lane-2
states. A claim that machinery has *checked* is labeled checked; it becomes
*accepted* only through a named human's recorded acceptance, and *digested* only
through a named human's explanation. This is doctrine, enforced in how records
and verdicts are worded — including in this program's own reporting.

## 3. Commitments (to be adopted; contract form in DPA §12)

1. **No training.** Partner data — study content, directory data, any of it — is
   never used to train, fine-tune, or evaluate any model, by us or by any
   subprocessor on our behalf.
2. **No secondary use.** No cross-tenant analytics over study content; no use of
   partner data for any purpose beyond operating the partner's own studies.
3. **No model in the verdict path.** Any future feature that would put a model
   inside evidence evaluation — as opposed to operating the surface under a named
   role — is a new capability requiring its own spec, claims with falsifiers, and
   assessment before it ships (the program's claims-first rule). It will not be
   introduced as a configuration change.
4. **Attribution is total.** If an agent instance takes an action in a study, the
   record shows the instance's actor identity and role. There is no "the system
   did it" state in the ledger.

## 4. Boundaries of this statement

- This statement governs **Axiovex's platform and Axiovex-operated agent
  instances**. Agent tooling a partner runs under its own control (its own MCP
  clients, its own actor names) is the partner's governance; the platform's
  contribution is that those acts are still role-bound, attributed, and ledgered.
- Model providers a partner's own agent stack may call are the partner's
  subprocessors, not ours; nothing in the platform's operation requires or makes
  such a call.
- This statement makes no claim about AI quality, accuracy, or suitability for any
  research purpose. It is a governance statement about where models may and may
  not sit, and about what partner data is never used for.

## 5. Review

Reviewed on: any Spec 009 (MCP/agent surface) change; any proposal that touches
the verdict path; and at adoption of the DPA template, so the statement and the
contract term cannot drift apart.

---

*Draft prepared from repo records only, 2026-10-12. Not adopted; the commitments
bind only on owner adoption and DPA execution.*
