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
