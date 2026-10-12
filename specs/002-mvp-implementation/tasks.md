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

- [x] T206 Connector contract implemented (`tekmerion.connectors`): `RetrievedItem` + `run_query` logs every query into the study's Axiomere ledger before results are used.
- [x] T207 Crossref connector done (polite pool w/ mailto; resolution source of record) — **verified live** 2026-10-11 (search + DOI resolve roundtrip against api.crossref.org).
- [x] T208 OpenAlex connector done: key auth (env `OPENALEX_API_KEY`), filter-first (~10× cheaper than search), `CreditBudget` reserve/settle with exhaustion as a stop (RT2-2). **Verified live 2026-10-11** with the owner's key (registered earlier the same day under his "approve it all"; stored in `~/workspace/glossa-run/research-api-keys.env`, never in the repo): filter search + resolve by DOI and by W-id all return real records; a DOI-routing bug in `resolve` was caught by that live run and fixed with a pinning test.
- [x] T209 `license_basis` captured per record on both connectors; abstracts dropped when no licence is asserted (Crossref abstracts are not CC0); NC-licensed items flagged `hosted_ok=False` (rights per deployment shape, RT2-1).

## Phase 3 — Claims, freeze, verdicts

- [x] T210 Claim register done (`tekmerion.claims`): WS2 schema, falsifier mandatory (Article II), statement immutability + supersede links, dependency DAG with cycle detection (circular support rejected), evidence folded to origin groups (Article V).
- [x] T211 Freeze workflow done (`tekmerion.freeze`): automated freeze check fails closed (falsifiers, acyclicity, margins, floors, control failure modes + RT-6 rationales, hosted-shape rights, RT-3 disclosure); freeze commits the registration hash as a `study.frozen` event + Axiomere Merkle checkpoint.
- [x] T212 Verdict service done (`tekmerion.verdicts`): WS3 taxonomy mechanically — INVALID attaches to the run and issues no claim verdicts; SUPPORTED requires a capable falsifier test + interval clearing the margin; interval-valued masses per WS3 §6; sufficiency floors enforced.
- [x] T213 Controls + wall done: positive/negative controls evaluate through the same `evaluate_claim` production path; the swap control tampers a copy of the study ledger and requires the production Axiomere verifier to catch it (RT-1). Confirmation mode without a frozen registration is INVALID; linked-exploratory disclosure is a freeze-check requirement (RT-3).

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
