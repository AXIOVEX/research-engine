# Spec 002 — MVP Implementation (Draft)

**Status:** G1 APPROVED by owner 2026-10-11 — implementation in progress (Phase 0/1 done) · **Date:** 2026-10-11 · **Constitution:** v1.0.0
**Authority:** Spec 001 (ratified design) · DN-002 (OD-1: MVP slice) · DN-003 (OD-2: hybrid, hosted-first)
**Scope:** build the smallest working engine that runs the ratified U2 workflow end-to-end and can host its own evaluation. Nothing beyond the slice.

## 1. What gets built

The ratified loop (Spec 001 §6): registration → retrieval (Crossref + OpenAlex) → claim register → origin-grouped evidence → per-claim verdicts with controls → adjudicator sign-off → audit-bundle export.

## 2. Components (boundaries per DN-003)

1. **Record service** (institution-custody deployable): append-only event store, single sequencing point per study log (RT-2), hash chain, projections (claim register, verdict tables), replay. *This component holds the record; everything else is replaceable around it.*
2. **Connector service** (shared deployable): Crossref + OpenAlex connectors per the WS1 contract — query logging, credit budgeting + freeze-time reservation (RT2-2), `mailto` polite pool, per-record `license_basis` capture, rights-per-deployment-shape enforcement (RT2-1).
3. **Verification service**: citation pipeline (WS5 §1 stages 1–3), origin grouping with adjudication queue + second-review sampling (RT-4), control execution through the production verification path (RT-1).
4. **Verdict service**: taxonomy mechanics (WS3), freeze checks, budget reservation check, exploratory/confirmation wall + exploration disclosure (RT-3).
5. **Export service**: audit bundle per WS4 §4, standalone bundle verifier (OQ-4.2), OSF/Zenodo deposit actions (adjudicator-approved only).
6. **Anchor (AR-1 gate)**: bundle chain-head anchoring via deposit (OSF/Zenodo DOI) — **must land before any institutional pilot**, not after.
7. **Minimal UI**: register-first study workspace (WS6 §1 roles) — draft claims/falsifiers, freeze, run, adjudicate, export. No chat-first surface.

## 3. Non-goals for this spec

Additional connectors beyond Crossref/OpenAlex · cross-study dependencies (OQ-2.2) · retraction surveillance (RT2-4, post-MVP candidate) · automated extraction beyond stance classification with recorded model identity · any marketing surface.

## 4. Evaluation (the product's first study)

The MVP is evaluated by a frozen registration *inside the engine* against Spec 001 K1–K5:
- K1 citation resolution = 100% on the evaluation corpus.
- K2 replay integrity: tamper cases (seeded alterations) all detected.
- K3 adjudicator audit-time budget — OD-5 threshold set at evaluation freeze.
- K4 origin honesty: seeded derivative-inflation cases all counted once.
- K5 cost per question — OD-5 threshold set with the owner before the freeze.
Plus the control suite's own seeded-defect cases (F-001-D3): swapped provenance, corrupted evidence, fabricated citation — each must produce INVALID.

Evaluation corpus: a set of evidence questions with known-answer claims (positive controls drawn from the questions' own domains, RT-6), assembled and frozen before the run.

## 5. Gates

- **G1 (owner):** go-ahead on this spec before code.
- **G2 (AR-1):** anchor implemented + demonstrated before any institutional pilot. **RATIFIED 2026-10-12 (DN-008)** on the live Zenodo anchor evidence (DOI 10.5281/zenodo.23311479).
- **G3 (OD-5):** K3/K5 thresholds recorded by amendment before the evaluation freeze.
- **G4 (spend):** any paid infrastructure, API tier, or service returns to the owner as its own decision. Free keys on owner accounts (OpenAlex, OSF, Zenodo) are within standing authorization per the founding brief.
