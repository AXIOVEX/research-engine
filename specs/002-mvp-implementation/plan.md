# Spec 002 — Plan (Draft)

**Date:** 2026-10-11 · Companion to `spec.md` (DRAFT — awaiting owner go-ahead, gate G1).

## Build order (dependency-driven)

```
Phase 0  Repo engineering setup (language/toolchain decision recorded as DN-004
         candidate; CI; test harness that can express seeded-defect cases)
Phase 1  Record service — event store, sequencing, hash chain, replay,
         standalone verifier skeleton        [WS4; RT-2]
Phase 2  Connectors — Crossref, OpenAlex: contract, query log, license_basis,
         credit budget + reservation          [WS1; RT2-2]
Phase 3  Claim register + freeze workflow + verdict service
         (taxonomy, controls via production path)  [WS2, WS3; RT-1, RT-3, RT-6]
Phase 4  Verification pipeline — resolution, agreement, content check,
         origin grouping + adjudication queue      [WS5; RT-4, RT-5]
Phase 5  Export + anchor — bundle, verifier, OSF/Zenodo deposit  [WS4; AR-1 = G2]
Phase 6  Minimal UI (register-first) + roles/SSO hooks           [WS6]
Phase 7  Evaluation — corpus assembly, OD-5 thresholds (G3), freeze,
         run, verdicts against K1–K5, report (negatives included)
```

Each phase ends with its seeded-defect tests green *and able to fail* (a test that cannot fail is deleted or fixed, Article VI) plus a short phase record appended to this plan's history in git.

## Key technical decisions to record as design notes during the build

- DN-004 candidate: implementation language/runtime + store technology for the event log (candidates judged on: boring durability, single-writer simplicity, 20-year bundle readability — WS4's format rules bind exports regardless).
- DN-005 candidate: extractor model policy (identity/version recording is mandatory per WS2; which models, hosted vs local, and the OQ-3.1 variance budget).

## Risks carried visibly

- OpenAlex credit economics at evaluation scale (mitigated by reservation, RT2-2; measured in Phase 7 under K5).
- Full-text availability for support checks varies by field (RT2-3; coverage reported, not hidden).
- LLM extraction nondeterminism in replay (WS3 §5/WS4 §3: verdict-level comparison + variance log; OQ-3.1 budget set by Phase 7 measurement).

## Phase records

- 2026-10-11 — Phase 0/1 complete (record service live, 8/8 tests, CI green). **DN-005 adopted** (absolute append-only; redaction removed). **DN-006:** framework renamed **Tekmerion**. **DN-007:** record layer is **Axiomere** (AXIOVEX/axiomere + axiomere-python); Phase 1 EventStore is the prototype/reference, `tekmerion.store.StudyStore` is the live surface. Phase 2 begins on Axiomere.
- 2026-10-11 — Phase 2 connectors landed: Crossref live-verified; OpenAlex fixture-verified behind its key gate (owner signup is the one external action). 17/17 tests green locally.
- 2026-10-12 — Phase 3 complete: claim register, freeze workflow, verdict service, controls-through-production-path, exploratory/confirmation wall (T210–T213). 31/31 tests green locally. One test fixture corrected during the build (a "straddle" case that did not straddle — the engine was right per WS3 §1).
- 2026-10-12 — Phase 4 complete (T214–T215), claims first: CLM-002-14…20 authored and assessed (after_specify, drafts at 0.48–0.68) before code; all seven at 1.00 after. Verification service (`tekmerion.verification`): 3-stage citation pipeline with K1 accounting ledgered per citation, WS2 origin grouping (pairwise union-find — the first single-key implementation failed its own test on the two-papers-one-dataset case), ledger-backed adjudication queue, RT-4 seeded second-review sampling with the rubber-stamp anomaly, RT-5 cap mechanized in the fold + verdict path. 50/50 tests green locally; live Crossref smoke recorded under T214.
- 2026-10-12 — Phase 5 complete (T216–T218), claims first: CLM-002-11/13 decomposed into CLM-002-21…30, assessed at after_specify (0.675–0.756) before code; all ten + both parents at 1.00 after. Export service (`tekmerion.export`: WS4 §4 bundle, manifest + bundle hash, WS5 §2 coverage, WS5 §4 rights gate, standalone verifier on the production Axiomere verifier) and deposit service (`tekmerion.deposit`: adjudicator-approved Zenodo transport, deterministic packaging, OSF metadata mapping). **AR-1 demonstrated live**: demo bundle deposited to Zenodo (DOI 10.5281/zenodo.23311479), receipt ledgered, re-exported bundle verified against the public record — G2 evidence complete, ratification is the owner's. 68/68 tests green locally. The demo also surfaced a real defect: the swap control's fixed line-1/2 actor swap is a no-op on single-actor ledgers, so the demo run was INVALID (correctly) and issued no verdicts; the fix is Phase 7 preparation, recorded in the assessment + T218.
