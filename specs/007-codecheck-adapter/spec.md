# Spec 007 — CODECHECK Adapter (P3: independent re-execution)

- **Date:** 2026-10-12 · **Status:** Built 2026-10-12 (claims first; assessed before code; owner shortlist gate passed 2026-10-12).
- **Pattern:** P3 (independent re-execution). **Survey record:** docs/surveys/2026-10-12-domain-evidence-adapters.md §3/P3.
- **Adapter triple:** artifact = a CODECHECK certificate (timestamped, in the public register) + the codecheck.yml it certifies · independent checker = the named, unaffiliated codechecker who performed the re-execution · scope claim = CLM-007-02 (blind spots).
- **Function:** given a paper/work with a CODECHECK certificate, ingest the certificate as evidence: checker identity, date, scope (which figures/tables/outputs were recreated), register DOI, and the work's artifact hash. The engine does not re-execute anything itself under this adapter — it consumes institutional re-execution as evidence, which is exactly the P6-style consumption pattern, with CODECHECK as the certificate issuer.

## Requirements

- **CLM-007-01** (requirement): The adapter's evidence item records the certificate's named codechecker, certificate date, register DOI, certified scope (outputs recreated), and the certified work's identifier; a certificate record missing any of these is context, not evidence.
- **CLM-007-02** (requirement): BLIND SPOT (scope claim): a CODECHECK certificate establishes only that the named checker, at that time, in that environment, could run the supplied material and recreate the certified outputs. It does NOT establish correctness or scientific validity (the certificates state this themselves), does not cover outputs outside the certified scope, and does not establish that the code is free of bugs that produce plausible wrong outputs.
- **CLM-007-03** (requirement): Scope honesty: where the certified scope is partial (a subset of the paper's outputs), the evidence item's mass is capped as partial-scope, and the uncertified outputs are named in the item.
- **CLM-007-04** (requirement): Lane separation: the codechecker is a named human performing lane-1 re-execution; the adapter records the certificate as lane-1 evidence and never as explanation, acceptance, or digestion of the work.

## Non-goals

No verdicts (lane-1 only, Spec 004 §2); no per-study tuning of mappings or applicability tables; no build before owner shortlist approval.
