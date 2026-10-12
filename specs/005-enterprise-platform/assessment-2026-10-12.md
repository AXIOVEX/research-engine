# AEE Assessment — Spec 005 (after_specify)

**Date:** 2026-10-12 · **Tooling:** spec-kit 1.0.10, AEE extension v1.2.0, AEE engine 1.0.4 (glossa venv pin), threshold 0.70
**Claims assessed:** 22 (`aee-claims.json` v0.1.0) · **Machine record:** `aee-assessment.json`
**Outcome: gather_evidence** — 7 claims at/above threshold; 15 below, all of them build commitments whose evidence does not exist yet. That is the correct state for a spec whose implementation is gated (G-ENT-1): the assessment was run *before* the design prose was finalized and before any code, per Article XII and the standing claims-first rule.

## Per-claim state

| Claim | Score | State |
|-------|-------|-------|
| CLM-005-01 OIDC only via tenant IdP; PKCE; no local passwords | 0.75 | draft — rests on DN-011 + the wireframes' SSO-hook record |
| CLM-005-02 SAML 2.0 SP, signed assertions, per-tenant IdP | 0.68 | **draft** — E2 commitment |
| CLM-005-03 appends only under enrolled identity-bound keys | 0.75 | draft — Article XIII + StudyStore actor machinery exist; the gate does not |
| CLM-005-04 key lifecycle as events; history keeps verifying | 0.68 | **draft** — E1/E3 commitment |
| CLM-005-05 deprovisioning ends access, never history | 0.68 | **draft** — E3 commitment |
| CLM-005-06 SCIM 2.0 lifecycle honored | 0.68 | **draft** — E3 commitment |
| CLM-005-07 JIT = asserting tenant only, no role by default | 0.68 | **draft** — E3 commitment |
| CLM-005-08 service-layer RBAC on the WS6 matrix | 0.75 | draft — matrix + actor model exist (WS6 §1, store.py); enforcement service does not |
| CLM-005-09 admin planes disjoint from study powers | 0.68 | **draft** — E1 model, E4 battery |
| CLM-005-10 break-glass: named, dual, boxed, alarmed, ledgered | 0.68 | **draft** — E4 commitment |
| CLM-005-11 tenant isolation by construction + battery | 0.68 | **draft** — E4 commitment; highest-uncertainty claim in the bundle |
| CLM-005-12 one codebase/model across shapes; residency pin | 0.68 | **draft** — E6 commitment |
| CLM-005-13 console gated on rendered-wireframe approval | 0.90 | draft — the Article XIV process itself is observed operating (T219-WF discharged 2026-10-12) |
| CLM-005-14 platform audit ledger: every admin action an event | 0.68 | **draft** — E1 core, E4 completion |
| CLM-005-15 platform audit export verifies standalone | 1.00 | draft — the Phase 5 pattern it reuses is built and test-evidenced; the platform-plane instance is E6 |
| CLM-005-16 readiness, not certification; mapping entries real | 0.97 | draft — DN-011's non-claims + the observed DN-008 wording correction |
| CLM-005-17 hold = export + anchor; erasure only via DN-005 certificate | 0.68 | **draft** — E6 commitment |
| CLM-005-18 scoped, expiring, revocable, attributed API keys | 0.68 | **draft** — E1 commitment |
| CLM-005-19 session/transport baseline, enumerated | 0.68 | **draft** — E4 battery commitment |
| CLM-005-20 enterprise build weakens no Spec 002 guarantee | 1.00 | draft (prediction) — scored on the existing battery it must keep green (68/68, CI 38214358137); discharged per phase exit |
| CLM-005-21 signed webhooks; receiver rejects bad/replayed | 0.68 | **draft** — E4 commitment |
| CLM-005-22 platform ↔ study records join on the binding | 0.68 | **draft** — E4 commitment |

## Reading

`gather_evidence` is the honest verdict for this package today. The seven claims at/above threshold divide into two kinds, and the record should not blur them: CLM-005-15 and CLM-005-20 score on **observed test evidence that already exists** (the Phase 5 bundle/verifier machinery and the Spec 002 battery) — they are claims about reusing and not breaking real machinery. CLM-005-01/03/08/13/16 score on **primary decision records plus observed process** (DN-011, the constitution, the WS6 matrix, the discharged wireframe gate) — strong direction evidence, no build evidence. The fifteen at 0.68 are the build itself, stated as requirements with falsifiers; each maps to a phase exit in `plan.md`, where it either gains evidence or fails in the open.

The engine's challenges, dispositioned per house practice — recorded, answered where they were right, never gamed:

- **Irreducibility** fired on all 22. Two were genuinely compound and were split before this run was finalized: CLM-005-14 (audit completeness) → +CLM-005-22 (platform↔study joinability), and CLM-005-19 (session/transport baseline) → +CLM-005-21 (webhook signing). The rest are single propositions; the challenge stands on them as a record.
- **Negation-conflict** pairs (54) are the engine's pairwise heuristic. The substantively tense pairs are this spec's named design tensions, resolved in the prose rather than by weakening claims: deprovisioning vs. historical verifiability (CLM-005-04/05 — resolved by separating authentication state from the record, spec §4); tenant isolation vs. auditor export (CLM-005-11/15 — resolved by per-tenant platform ledgers, spec §8); break-glass existence vs. no-backdoor (CLM-005-10 — the mechanism is the audit trail, spec §5).
- **Authority** challenges remain on CLM-005-13/16 (compliance kind): their evidence is directive- and process-level until E5/E6 produce build evidence. Recorded as standing.
- **Precision** on CLM-005-19 stands after one tightening pass (the claim was rewritten into enumerable checks — named cookie attributes, named headers, the 429 behavior); the residual challenge is recorded.

*Process note:* claims preceded the spec prose (DN-011 and `aee-claims.json` were written and assessed before `spec.md`/`plan.md`/`tasks.md`), and this spec was authored on its own branch/worktree (`enterprise-spec`, `~/workspace/tekmerion-ent`) writing only new files, so the running Tao-audit and Phase 6 UI workstreams are untouched. No implementation exists for any claim above; statuses are drafts and will move only on build evidence at phase exits.
