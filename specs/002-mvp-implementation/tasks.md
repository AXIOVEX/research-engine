# Spec 002 — Tasks (Draft)

**Date:** 2026-10-11 · All build tasks are gated on **G1 (owner go-ahead)**. Status: `[ ]` open · `[!]` gated

## Gates

- [x] G1 Owner go-ahead on Spec 002 — given 2026-10-11.
- [!] G3 OD-5 thresholds (K3 audit-time budget, K5 cost ceiling) recorded before the evaluation freeze.
- [!] G4 Any spend — none planned; free API keys on owner accounts only.

## Phase 0 — Setup

- [x] T201 DN-004 recorded (Python 3.12 stdlib core, JSONL log, SHA-256 chain).
- [x] T202 Repo setup done: pyproject, GitHub Actions CI, pytest harness with seeded-defect cases.

## Phase 1 — Record service

- [x] T203 Event store done: append-only JSONL, single sequencing point (lock + monotonic seq), SHA-256 hash chain, fsync appends.
- [x] T204 Projections + replay done: invalid log replays INVALID with no verdicts surfaced.
- [x] T205 Standalone verifier core done (`verify_log` needs only the log file); bundle-level manifest verification lands in Phase 5.
- [x] T223 DN-005 code alignment done (2026-10-11): tombstone redaction removed from the record service; no-redaction test in place. (Payload encryption at ingest + erasure-certificate protocol moved to the Axiomere layer — tracked in AXIOVEX/axiomere DESIGN §6, still open.)
- [x] T224 Record layer adopted: **Axiomere** (DN-007) — `tekmerion.store.StudyStore` over the `axiomere` Python package; Phase 1 EventStore retained as prototype/reference. Migration of remaining Phase 3+ services proceeds on Axiomere from the start.

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
