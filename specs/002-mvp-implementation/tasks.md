# Spec 002 — Tasks (Draft)

**Date:** 2026-10-11 · All build tasks are gated on **G1 (owner go-ahead)**. Status: `[ ]` open · `[!]` gated

## Gates

- [!] G1 Owner go-ahead on Spec 002 before any code.
- [!] G3 OD-5 thresholds (K3 audit-time budget, K5 cost ceiling) recorded before the evaluation freeze.
- [!] G4 Any spend — none planned; free API keys on owner accounts only.

## Phase 0 — Setup

- [ ] T201 Record DN-004 (language/runtime/store decision with reasons).
- [ ] T202 Repo engineering setup: CI, test harness supporting seeded-defect cases.

## Phase 1 — Record service

- [ ] T203 Event store: append-only log, single sequencing point, hash chain.
- [ ] T204 Projections + replay; divergence reporting.
- [ ] T205 Standalone bundle verifier (skeleton → full in Phase 5).

## Phase 2 — Connectors

- [ ] T206 Connector contract implementation + query log events.
- [ ] T207 Crossref connector (polite pool, resolution source of record).
- [ ] T208 OpenAlex connector (key auth, credit budget + freeze-time reservation).
- [ ] T209 `license_basis` capture + rights-per-deployment-shape enforcement.

## Phase 3 — Claims, freeze, verdicts

- [ ] T210 Claim register (schema per WS2) + dependency graph + cycle check.
- [ ] T211 Freeze workflow + freeze checks (falsifiers, margins, controls, budget).
- [ ] T212 Verdict service: taxonomy mechanics, intervals, sufficiency floors.
- [ ] T213 Controls via production verification path (RT-1); exploratory/confirmation wall + disclosure (RT-3).

## Phase 4 — Verification

- [ ] T214 Citation pipeline stages 1–3 (resolution, agreement, content check).
- [ ] T215 Origin grouping + adjudication queue + second-review sampling (RT-4); metadata-only cap mechanized (RT-5).

## Phase 5 — Export + anchor

- [ ] T216 Audit bundle generator (WS4 §4 format) + manifest + HUMAN-README.
- [ ] T217 OSF/Zenodo deposit actions (adjudicator-approved).
- [ ] T218 **AR-1 anchor demonstrated end-to-end (G2)** — hard gate before any pilot.

## Phase 6 — UI

- [ ] T219 Register-first study workspace; role views (researcher/reviewer/adjudicator/integrity).

## Phase 7 — Evaluation

- [ ] T220 Evaluation corpus assembled + frozen (known-answer claims, seeded defects).
- [ ] T221 Evaluation registration frozen inside the engine (after G3).
- [ ] T222 Run + verdicts vs K1–K5; report published in-repo, negatives included.
