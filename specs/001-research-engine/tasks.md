# Spec 001 — Tasks (Design Phase)

**Date:** 2026-10-11 · Status key: `[ ]` open · `[x]` done · `[!]` blocked on owner decision

## Founding

- [x] T001 Create repo `AXIOVEX/research-engine` (public, main, issues on) with description, homepage, topics — verified by API read-back.
- [x] T002 LICENSE (all rights reserved, © Axiovex Systems, LLC, per epistemic-ledger precedent).
- [x] T003 README as home page (house style; no unmeasured claims).
- [x] T004 DN-001 founding design note (name, positioning, audience, license, non-goals).
- [x] T005 Constitution v1.0.0 ratified into `.specify/memory/constitution.md`; spec-kit + AEE scaffold installed.

## Architecture workstreams

- [x] T006 WS1 Source layer — connector contract + source registry with verified API/licensing facts.
- [x] T007 WS2 Claim & evidence model — schema + ledger adopt/adapt/supersede map (OD-3).
- [x] T008 WS3 Verdict engine — taxonomy mechanics, control patterns, freeze/replay.
- [x] T009 WS4 Records & export — event store, hash chain, audit bundle, OSF/Zenodo paths.
- [x] T010 WS5 Trust & safety — citation verification, adjudication points, licensing boundaries.
- [x] T011 WS6 Product shape — roles, deployment shapes (OD-2), MVP slice (OD-1), competitor gap appendix.

## Review gates

- [x] T012 Cross-reference + consistency check (SC-3, SC-4) — pass 01 done with RED-TEAM-01; re-run required after WS1 registry facts + WS6 appendix finalize.
- [x] T013 Red-team pass over the full architecture set; findings logged.
- [x] T014 Revision pass resolving critical red-team findings.
- [x] T015 AEE assessment of spec 001 claims recorded (`assessment-2026-10-11.md`): outcome ITERATE / gather-evidence, all design claims honestly at asserted-design, CLM-001-07 pending OD-1.
- [x] T019 RED-TEAM pass 02 after WS1/WS6 research finalization — 4 findings (BASE eligibility per deployment shape; freeze-time budget reservation; support-check coverage reporting; retraction surveillance promoted to requirement candidate). SC-1 satisfied.
- [ ] T020 (Gate on any implementation spec, per RED-TEAM-01 AR-1) At least one external hash anchor implemented (deposit or institutional timestamp) before any institutional pilot.

## Owner gates (one at a time, never bundled)

- [!] T016 OD-1 — approve MVP slice + kill criteria (spec §6).
- [!] T017 OD-2 — deployment shape direction (hosted / local / hybrid).
- [!] T018 Any spend or external signup beyond free API keys — none requested in this phase.

## Explicitly not in this phase

- [ ] Implementation of any engine component — separate spec after T016/T017 and owner go-ahead.
