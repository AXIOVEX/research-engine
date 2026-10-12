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

---

## Amendment — CMMC (2026-10-12, after gate G-ENT-1, before E1 code)

**Trigger:** owner directives the same day — G-ENT-1 given (*"start E1 identity core"*), then *"also make this tool CMMC compliant."* The amendment was assessed **before any E1 code**, so E1 absorbs the CMMC deltas that touch it (Spec 005 §13; DN-011 CMMC section).

**Framing (Article X discipline, not optional):** CMMC (32 CFR Part 170) certifies organizations and assessment boundaries, not products. The amendment therefore claims **CMMC Level 2 alignment / compliance support** against NIST SP 800-171 Rev 2 (110 requirements); Level 1 is implied; Level 3 (SP 800-172) is out of scope (§11). The responsibility matrix (`cmmc-responsibility-matrix.md`) classifies all 110 requirements — Platform / Supports / Organizational — and records that SP 800-171 Rev 2 has no SA family (acquisition is organizational/contractual; platform support is provenance evidence only), so the 15-code list in the owner's brief is fully accounted: 14 families in the standard + SA recorded as absent-from-standard.

**New claims (bundle v0.2.0, 31 total), re-assessed at `after_specify`, outcome `gather_evidence` (11 ≥ 0.70, 20 below):**

| Claim | Score | Reading |
|-------|-------|---------|
| CLM-005-23 CMMC framing honesty | 0.756 | Rests on DN-011 + §13.1 records; discharged continuously, swept at E6 (T544) |
| CLM-005-24 matrix complete, 110/110 | 0.958 | The matrix artifact exists and was verified complete at authoring; classifications re-checked per phase exit |
| CLM-005-25 FIPS position + inventory obligation | 0.968 | Scores the *position* (gap + routes + dependency recorded; zero FIPS claims). The inventory itself is an E1 deliverable (T549); §3.13.11 satisfaction is an owner-decision-gated migration, **not** claimed |
| CLM-005-26 AU event-class completeness | 0.68 | **draft** — E1 core (T550 sweep is its instrument), E4 completion |
| CLM-005-27 MFA at IdP, platform-enforced | 0.68 | **draft** — E1 (joins T503) |
| CLM-005-28 CUI marking in artifacts | 0.68 | **draft** — E6 (T551); specced now so payloads never re-shape |
| CLM-005-29 SPRS self-assessment support | 0.958 | **Score flagged as ahead of its machinery:** the evidence is the matrix artifact (its data source) + §13.7. The matrix does not yet carry per-requirement SPRS deduction classes — that is T552 (E6). Recorded here so the 0.958 is never quoted as the feature existing; re-examined at E6 exit |
| CLM-005-30 IR hooks + append-only POA&M | 0.68 | **draft** — E4 hooks (T554) + E6 register (T553), seeded with the FIPS gap |
| CLM-005-31 DFARS/FedRAMP hosted-shape flag | 0.68 | **draft** — standing flag; an open owner/legal decision engineering does not resolve |

The original 22 claims' scores are unchanged by the amendment run (same evidence; the seven above-threshold claims stand as recorded in the first section). Tasks absorbed the deltas in place: [CMMC] flags on T503, T507, T510, T529, T531, T542, T544; new tasks T549 (crypto inventory, E1), T550 (AU completeness, E1), T551 (CUI marking, E6), T552 (SPRS support, E6), T553 (POA&M register, E6), T554 (IR event classes, E4). E6 is retitled "Compliance evidence (SOC 2 readiness + CMMC Level 2 support) + self-hosted shape" in plan and tasks.
