# Spec 007 — CODECHECK Adapter (P3: independent re-execution) — plan

1. Claims + assessment (this spec). 2. Build gated on owner shortlist approval. 3. Seeded-defect tests through production paths before any study use.

## Build exit (2026-10-12)

Owner shortlist gate passed 2026-10-12; built the same day on branch adapters/build-006-008, on the shared seam defined by Spec 006. The adapter fetches the public register (no account), resolves the certificate's repository, and ingests `codecheck.yml` + the deposited certificate PDF, hash-pinning every byte stream in the run record. Completeness (CLM-007-01), scope assessment with the partial-scope cap (CLM-007-03), the certificate's own correctness disclaimer, and the lane-2 non-effect (CLM-007-04) are all recorded per ingestion.

Certificate 2020-001 served as the primary fixture and is a genuine partial-scope certificate on its own text (visualisation steps only; other output files not checked) — the cap and the uncertified-output naming are exercised on real material, recorded in tests/fixtures/adapters/codecheck/PROVENANCE.json. Note recorded there: 2020-001 predates the current certificate template, so the standing disclaimer text is carried in the record with `present_in_certificate_material: false` for this certificate — detected per certificate, never assumed.

Claims at exit: bundle v0.2.0, assessed at after_implement — CLM-007-01…04 all at 1.00 / supported, lifecycle stage *checked* (author's own tests; DN-010 convention).
