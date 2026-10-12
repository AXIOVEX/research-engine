# Verdicts

Each claim in a valid run resolves to exactly one verdict from a fixed
taxonomy:

| Verdict | Meaning |
|---|---|
| **Supported** | The evidence interval clears the claim's registered margin, on at least the registered sufficiency floor of independent origin groups. |
| **Contradicted** | The evidence interval clears the margin in the negative direction — or the claim's falsifier was observed. |
| **Inconclusive** | The evidence does not clear the margin either way: too little of it, too diluted (e.g. metadata-only records priced as ignorance), or below the sufficiency floor. A result, not a failure. |
| **Contested** | (Theorem claims) a load-bearing sub-claim — classically attribution — is under a live, evidenced dispute. The parent cannot stand above it. |
| **Invalid** | Not a claim verdict: the *run itself* was defective (a control failed, the chain broke, adjudication items were left undecided, no frozen registration). An invalid run issues no claim verdicts at all. |

## Verdicts are issued, not opined

A verdict exists only if a `verdict.issued` event exists in the study
ledger, produced by the production verdict machinery against a frozen
registration. "The evidence looks strong" is not a verdict. Verdicts
are claim-by-claim, each with its interval and margin — never a single
blended score that hides a weak link.

## Controls that can fail

Every frozen study carries three controls, each designed to catch a
named failure mode:

- **Positive** — a fixture claim backed by strong agreeing evidence
  must reach *supported*.
- **Negative** — a fixture claim its own evidence contradicts must
  reach *contradicted*.
- **Swap** — a provenance swap between early ledger lines must be
  detected by the verifier.

A check that cannot differentially fail marks the run **invalid**
rather than passing it. This is not hypothetical: the project's own
Phase 5 demonstration run was INVALID because its swap control was a
no-op on a single-actor ledger (see
[the demo study](../evidence/demo-study.md)).

## What a verdict does not say

A verdict is the *checking* stage of a claim's life — lane 1. It says
nothing about whether any human has explained, accepted, or digested
the result; that is [lane 2](stages-and-lanes.md), tracked separately,
and every theorem verdict carries a `remains_not_understood` field
written by the adjudicator.
