# Assessment addendum — build exit (2026-10-12, after_implement)

Claims bundle v0.2.0 (4 claims), assessed at after_implement with AEE engine 1.0.4, threshold 0.70. Outcome: iterate (the assessor's standard signal at this phase); per-claim propagated scores: CLM-007-01 1.00, CLM-007-02 1.00, CLM-007-03 1.00, CLM-007-04 1.00. All four claims moved draft → supported on shipped-test evidence only; lifecycle stage *checked* per the DN-010 audit convention. Full record in aee-assessment.json (this run replaced the after_specify record, which remains in git history).

## What the evidence is

- The production ingestion path ran against recorded real register material (full register snapshot, certificate 2020-001's codecheck.yml and certificate PDF; provenance in tests/fixtures/adapters/codecheck/PROVENANCE.json) and replayed from the ledger with checker identity (Stephen J. Eglen, ORCID), certificate date, register DOI 10.5281/zenodo.3674056, certified scope, and all three SHA-256 pins intact.
- Falsifiers exercised: F-007-1 (real yml with the codechecker block stripped → context, no evidence, missing fields named), F-007-3 (the real certificate is partial on its own text → capped at 0.40 with uncertified outputs named when the study supplies the full list; 0.70 only when the manifest covers the supplied list), F-007-4 (lane2_effect asserted as "none" on the replayed record).
- Register-absent and register-unreachable ingestions are ledgered states with reasons, and emit no evidence.

## Open items (not smoothed over)

- None for the adapter as specced. (Live fetching is the same code path as the fixture-injected path; no account or service dependency exists to verify.)
