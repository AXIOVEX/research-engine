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

- [x] T214 Citation pipeline stages 1–3 done (`tekmerion.verification`): stage 1 resolution gives every citation exactly one explicit outcome (resolved / not-found / error), each appended as a `citation.checked` ledger event (K1 accounting); stage 2 agreement compares title/authors/year/venue and quarantines material mismatches; stage 3 content check runs stance extraction (deterministic lexical baseline, extractor identity recorded) on licence-permitted retrieved content only — no content means `metadata_only`, never content-verified. Seeded defects green: fabricated DOI fails stage 1, tampered metadata fails stage 2, unsupported content fails stage 3. **Live smoke 2026-10-12** against Crossref: real DOI resolved, fabricated DOI not-found, translated-title citation correctly routed to adjudication as a variant case.
- [x] T215 Origin grouping + adjudication queue done: citations fold to origin groups by WS2 keys 1–3 as pairwise equivalence (union-find); key-4 near-duplicate suspects are flagged to the ledger-backed adjudication queue, never auto-merged. Queue state is a replay of `adjudication.*` events; decisions are named appends (re-decision refused). RT-4: deterministic seeded sampling at the registered fraction (default 10%) of decided items for second review; the report flags a zero-disagreement window at/above the minimum sample (5) as a rubber-stamp anomaly. RT-5 mechanized: metadata-only items fold to zero mass and no falsifier exposure in `group_masses`, and `evaluate_claim` caps an entire-metadata-only basis at INCONCLUSIVE — test proves the cap binds and that a mixed basis is not capped.

## Phase 5 — Export + anchor

- [x] T216 Audit bundle generator done (`tekmerion.export`): WS4 §4 layout (ledger copied byte-for-byte, registration bound by hash to the `study.frozen` commitment, claims/evidence/groups/coverage/verification/verdicts/adjudication/queries, manifest with per-file SHA-256 + bundle hash, HUMAN-README). WS5 §2 coverage per claim rides on the Phase 4 group records (`metadata_only` per group), as Phase 4 left it. WS5 §4 rights gate mechanized: content enters only under a redistribution-permitting licence basis, substitutions listed in the manifest. Standalone verifier consumes only the bundle and delegates chain/signature checks to the production Axiomere verifier. Seeded defects green (18 tests): flipped byte, unlisted file, altered manifest root, truncated ledger, tampered ledger payload, tampered registration — the last four with attacker-rehashed manifests, so the cross-checks (not just hashes) carry them. Exports are byte-deterministic.
- [x] T217 Deposit actions done (`tekmerion.deposit`): adjudicator-approval is mechanical (no named approver → refused; unverifiable bundle → refused). Zenodo is the executable transport (deposit API, DOI-minting); OSF is deposit-ready (metadata + component mapping per WS4 §4 in `osf_metadata`) — no OSF transport, because AR-1's DOI comes from the Zenodo deposit and an OSF registration workflow is a separate owner decision. Deposit metadata states the checkpoint root + bundle hash (the anchoring loop, WS4 §4). Packaging is a deterministic zip.
- [x] T218 **AR-1 anchor demonstrated end-to-end, live (G2 evidence)** — 2026-10-12: demo study (live Crossref; real 1905 citation adjudicated *variant*/metadata-only, fabricated citation *exclude*d; RT-4 second review logged) froze at checkpoint root `74342096…e317`; its bundle was deposited to **Zenodo, DOI 10.5281/zenodo.23311479** (record created 2026-10-12T06:46:48Z) under the owner's standing authorization (Spec §5 G4: free keys on owner accounts) with his Phase 5 go-order as the recorded adjudicator approval; the receipt was appended to the study ledger and the re-exported bundle passes `verify_anchor` against the public record fetched independently. **G2 ratification remains the owner's act.** Defect found by the demo (see assessment record): the study's run was INVALID — the swap control's fixed line-1/2 actor exchange is a no-op on single-actor ledgers, so the control failed and no verdicts issued; the deposited bundle records exactly that, and the Zenodo description was corrected in place to say so. Control event-selection fix is Phase 7 preparation, logged here so it is not lost.

## Phase 6 — UI

- [!] T219-WF **Wireframe approval gate (owner)** — added 2026-10-12 by owner ruling: wireframes first, and the wireframes are constitutional (DN-009; constitution Article XIV drafted for v1.2.0, taking effect on the same approval). The package in `docs/wireframes/` — screens (a)–(f) + component specimens, rendered at desktop + mobile — must be approved by the owner on the rendered screenshots before any UI implementation. **T219 does not start until this gate clears.**
- [ ] T219 Register-first study workspace; role views (researcher/reviewer/adjudicator/integrity). *(Blocked on T219-WF.)*

## Phase 7 — Evaluation

- [ ] T220 Evaluation corpus assembled + frozen (known-answer claims, seeded defects).
- [ ] T221 Evaluation registration frozen inside the engine (after G3).
- [ ] T222 Run + verdicts vs K1–K5; report published in-repo, negatives included.
