# Spec 007 — CODECHECK Adapter (P3: independent re-execution) — tasks

- [x] T1 Spec + claims bundle v0.1.0 + assessor run at after_specify.
- [x] T2 Build (GATED: owner shortlist approval — PASSED 2026-10-12). Built 2026-10-12: `src/tekmerion/adapters/codecheck.py` (register consumption, codecheck.yml parsing, completeness demotion, scope assessment, disclaimer recording) on the shared seam from Spec 006.
- [x] T3 Seeded-defect tests (each claim's falsifier exercised by a fixture that must fail the naive implementation): tests/test_adapters_codecheck.py — 9 tests over recorded real register material, incl. an incomplete certificate record (real yml, codechecker block stripped) demoted to context (F-007-1), a partial-scope real certificate capped with uncertified outputs named (F-007-3), and register-absent / register-unreachable states ledgered with no evidence.
