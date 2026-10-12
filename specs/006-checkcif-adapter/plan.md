# Spec 006 — checkCIF Adapter (P2: automated validation suite) — plan

1. Claims + assessment (this spec). 2. Build gated on owner shortlist approval. 3. Seeded-defect tests through production paths before any study use.

## Build exit (2026-10-12)

Owner shortlist gate passed 2026-10-12; built the same day on branch adapters/build-006-008. The shared adapter seam (`tekmerion.adapters.core`) was defined by this build and is reused by Specs 007–008: one `adapter.run` ledger event per invocation (artifact hash, checker identity + version, invocation honesty state, raw-output hash, scope-claim id) and evidence emission only through a seam that refuses scope-claim-less, unavailable, or provenance-incomplete runs.

Invocation reality: no live PLATON run is claimed. PLATON is author-distributed and not OSI-licensed; the IUCr web service is a submission service the adapter does not automate. The parser and recorded-output path are validated against recorded real outputs (IUCr service HTML report; two PLATON .chk files) with provenance in tests/fixtures/adapters/checkcif/PROVENANCE.json. Live-binary verification is open task T4.

Claims at exit: bundle v0.2.0, assessed at after_implement — CLM-006-01…04 all at 1.00 / supported, lifecycle stage *checked* (author's own tests; DN-010 convention). Fixture limitation recorded in the test module: no public matched (CIF, A-bearing output) pair exists, so the A-alert row is tested at parser + mapping + evidence-builder level and the run path end-to-end on matched C/G pairs; pairing unrelated bytes would fabricate provenance.
