# Worked study: the 2026 AI-mathematics claims

Spec 003's worked study applied the engine — and the stage-model
doctrine (design note DN-010) — to the public AI-mathematics claims
of 2026. Each headline was registered as a parent theorem claim with
five sub-claims (faithful statement, verified proof, genuinely open,
clean attribution, significance), each with its own falsifier.

The verdict words below mean what they say: **contested** — a live
dispute blocks the claim; **inconclusive** — the evidence settled
nothing either way; **supported** — the evidence carried every part
of the claim.

**Run:** VALID. 93 ledger events; freeze (run 2) Merkle root
`5b497655…ad4`. Anchored on Zenodo:
[DOI 10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259).

!!! note "Disclosed in the record"
    Run 1's verdicts were superseded in-ledger by run 2: the run-1
    driver omitted the Lean runner. The supersession is an append, not
    a rewrite — both runs remain on the record.

## Verdicts as issued

| Case | Verdict | Why |
|---|---|---|
| **(a) OpenAI Navier–Stokes** (CLM-M-110) | **CONTESTED** | The Buckmaster/Alpöge attribution dispute is registered with both sides' evidence; a live attribution dispute caps the parent. |
| **(b1) Astra sphere-packing** (CLM-M-210) | **CONTESTED** | The Miller attribution dispute; the certificate was also not independently compiled by us (see honesty states below). |
| **(b2) Astra non-sofic groups** (CLM-M-310) | **INCONCLUSIVE** | The evidence did not settle the claim either way. |
| **(c) Quasi-Riemann case** (CLM-M-410) | **INCONCLUSIVE** | An abstention case from the October claims — the machinery declined to decide. |
| **(d) AlphaProof Nexus — nine Erdős results** (CLM-M-510) | **SUPPORTED** | All five sub-claims supported; the one case with lane-2 movement: explained **and** accepted, by named-human records. The positive control. |
| **(e) Reliability seed** — "OpenAI (Kevin Weil via X, Oct 2025): GPT-5 solved an Erdős problem" | **resolved false** | The calibration case: a public claim that had already been retracted/resolved false in the record, seeded to check the machinery resolves it as such. |

## What the checking could not do here

Every real-world Lean artifact in this study was `not_runnable_here`:
claimants pin Lean v4.27.0 / v4.32.0 / v4.34.0-rc2 with full Mathlib
builds; the local toolchain is v4.33.1 with no Mathlib build. Lane-1
evidence therefore rested on reading the artifacts, counting
unfinished steps (Lean's `sorry`/`admit` markers, where a proof is
left incomplete on purpose), and claimants' own compile claims — each
labelled with its honesty state (`run_by_us`, `recorded_output`,
`not_runnable_here`, `claimed_by_source`, `not_attempted` — in plain
terms: whether we ran it ourselves, only recorded someone else's
run, could not run it here, took the source's word for it, or never
tried), never upgraded in prose. The
full Lean verification service that closes this gap is specified
(Spec 004) and deliberately not yet built; its trigger is the first
study whose verdicts are actually capped by it.

No claim in this study is *digested*. Lane 2 holds only the AlphaProof
Nexus explanation/acceptance records and the project's own gate acts.
