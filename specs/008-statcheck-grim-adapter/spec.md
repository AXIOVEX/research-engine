# Spec 008 — statcheck + GRIM-family Adapter (P7: reporting-consistency)

- **Date:** 2026-10-12 · **Status:** Draft (claims first; assessed before code) · **Build: NOT started — gated on the owner's shortlist approval.**
- **Pattern:** P7 (reporting-consistency checkers). **Survey record:** docs/surveys/2026-10-12-domain-evidence-adapters.md §3/P7.
- **Adapter triple:** artifact = a manuscript (statcheck) or reported summary statistics + N (GRIM/GRIMMER/SPRITE) · independent checkers = the statcheck R package and the GRIM-family implementations (`scrutiny`) · scope claim = CLM-008-02 (blind spots).
- **Function:** extract APA-style NHST results and recompute p-values (statcheck); test reported means/SDs for arithmetic possibility given N and scale granularity (GRIM/GRIMMER); optionally reconstruct candidate datasets (SPRITE, plausibility display only). Findings attach as evidence to the claim that a paper's *reported statistics are internally consistent* — a decomposition sub-claim, never the paper's headline claim directly.

## Requirements

- **CLM-008-01** (requirement): The adapter's evidence item records the checker + version, the extraction coverage (how many results were extractable vs present), and every flagged result with its recomputed values; an item without the coverage record is not evidence.
- **CLM-008-02** (requirement): BLIND SPOT (scope claim): these checkers establish internal arithmetic consistency of reported statistics only. They do NOT establish that the underlying data exist, that the analysis was appropriate, or that conclusions follow. statcheck is silent on everything it cannot parse (non-APA formats, tables, model-based/Bayesian results) — no flags is not a clean paper. A GRIM fail proves inconsistency, not its cause (typo, wrong N, exclusions all produce fails). SPRITE reconstructions are candidate datasets, never the real data.
- **CLM-008-03** (requirement): A GRIM/GRIMMER impossibility (a mathematical impossibility given the reported N and granularity) attaches contradiction mass to the reporting-consistency sub-claim with falsifier_observation set — it is the registered falsifying observation for that sub-claim — while a statcheck decision_error attaches partial contradiction, and mere inconsistencies attach context.
- **CLM-008-04** (requirement): Applicability is checked before mass is assigned: GRIM-family checks run only where data are integer-granular and N/decimals give the test power; where the test is uninformative (large N, continuous data), the adapter records not_applicable rather than a pass.

## Non-goals

No verdicts (lane-1 only, Spec 004 §2); no per-study tuning of mappings or applicability tables; no build before owner shortlist approval.
