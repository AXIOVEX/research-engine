# Spec 003 — Tasks

**Date:** 2026-10-12 · Status: `[ ]` open · `[!]` gated. All build tasks follow the claims-first assessment of 2026-10-12 (`aee-assessment.json`, outcome gather_evidence).

## Gates

- [x] Claims first: CLM-003-01…12 authored + assessed at after_specify before code.
- [!] No spend, no new accounts (owner boundary); Zenodo deposit rides the existing owner token.
- [!] Untouched by this spec: Phase 6 wireframe gate (T219-WF), AEE repos, axiomere repos; no outreach drafted or sent.

## Phase A — Math layer core

- [x] T301 Theorem schema: parent + five sub-claims registered in the production register (Spec 003 §2 id scheme, parent depends on all five).
- [x] T302 Composition: parent verdict from sub-verdicts + dispute state, §2 precedence; refuses without `remains_not_understood`; lane fields on every record.
- [x] T303 Digestion records + UNEXPLAINED risk state; lane-2 acceptance events (human-evidence only).
- [x] T304 Dispute registration + attribution-state projection (both sides' evidence required to register a dispute as evidenced).
- [x] T305 Reliability events + per-source projection; seeding discipline (identified claim + identified resolution or nothing).

## Phase B — Lean ingestion

- [x] T306 Ingestion: fetch by URL, SHA-256 content hash, sorry/admit counts, statement extraction; ingestion appended to the ledger.
- [x] T307 Compile runner over the local Lean toolchain: version + exit code + output hash; `#print axioms` probe where runnable; the three honesty states (`run_by_us` / `not_runnable_here` / `claimed_by_source`) as record vocabulary.

## Phase C — Checks

- [x] T308 Openness check (mathclaims.openness_check): primary status source fetch + Crossref/OpenAlex searches via `run_query` (queries ledgered); emits evidence only.
- [x] T309 Attribution check (openness_check literature pass + mathclaims.register_dispute): connector literature search; dispute registration wired to T304.

## Phase D — Worked study

- [x] T310 Research pass over cases (a)–(e): primary sources first; every source logged with URL + retrieval date; gaps recorded as gaps.
- [x] T311 Study driver: multi-actor study on production paths (register → evidence → checks → freeze → evaluate_run → composition → issue verdicts).
- [x] T312 Case (e) resolution: reliability seed entered, or the identification failure recorded with the searches that failed.

## Phase E — Export, anchor, re-assessment

- [x] T313 Audit bundle export + standalone verification; theorem report projection included.
- [x] T314 Zenodo deposit (adjudicator approval = owner directive for this study, recorded verbatim) + receipt ledgered + `verify_anchor` against the independently fetched public record.
- [x] T315 Re-assessment at after_implement: CLM-003 claims updated on shipped evidence only; assessment record addendum written.

## Completion record (2026-10-12)

- T310: 13 sources logged in the study ledger (math.source_logged), incl. one recorded gap (OpenAI's announcement page returned HTTP 403; headline wording scored from the secondary record).
- T311: study driver `~/workspace/math-study/run_study.py` (+ append-only correction drivers run_study2/3). Actors: registrar / archivist / adjudicator from the first ledger lines. Run 1 froze at root b179057b… and was VALID; its verdicts were superseded in-ledger by run 2 (freeze root 5b497655dd6ae50d0ca39328b674bc528ad1f03d4a1febca70077ad514a49ad4) after a disclosed driver defect (LeanRunner omitted in run 1, so ingestions recorded not_attempted). Run 2 VALID, no invalid reasons.
- T312: reliability seed recorded — source "OpenAI (Kevin Weil, via X, Oct 2025)", outcome resolved_false, resolution TechCrunch 2025-10-19 + Bloom's refutation.
- T313: bundle exported (`~/workspace/math-study/bundle-v1`), standalone verify OK; theorem records in `~/workspace/math-study/theorem-records.json`.
- T314: deposited — DOI 10.5281/zenodo.23317259; bundle hash abb856aa5b5d5f57725b088399f2276e6ac712c6896b3c3ed1fb47c91a353de4; anchor verified against the independently fetched public record (bundle-v2, hash ee4ea147…).
- T315: re-assessment at after_implement recorded in assessment-2026-10-12.md (addendum 2).
