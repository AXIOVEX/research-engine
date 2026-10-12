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

- [ ] T310 Research pass over cases (a)–(e): primary sources first; every source logged with URL + retrieval date; gaps recorded as gaps.
- [ ] T311 Study driver: multi-actor study on production paths (register → evidence → checks → freeze → evaluate_run → composition → issue verdicts).
- [ ] T312 Case (e) resolution: reliability seed entered, or the identification failure recorded with the searches that failed.

## Phase E — Export, anchor, re-assessment

- [ ] T313 Audit bundle export + standalone verification; theorem report projection included.
- [ ] T314 Zenodo deposit (adjudicator approval = owner directive for this study, recorded verbatim) + receipt ledgered + `verify_anchor` against the independently fetched public record.
- [ ] T315 Re-assessment at after_implement: CLM-003 claims updated on shipped evidence only; assessment record addendum written.
