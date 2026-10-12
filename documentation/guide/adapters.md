# Domain adapters

An **adapter** = an artifact type + an independent checker + a
**registered scope claim** stating what the check cannot establish.
Adapters supply **lane-1 evidence only**: an adapter result can never
settle a claim alone, never skips adjudication, and never moves lane 2.
Every adapter run is refused by the shared evidence seam if it lacks a
scope claim, if the checker is unavailable with no recorded output, or
if its provenance is incomplete — an unavailable checker is recorded
as `not_runnable_here`, never as a pass.

## checkCIF / PLATON — crystallography (Spec 006)

Validates CIF structure files against IUCr checkCIF reports and PLATON
`.chk` output. The mapping is deliberately asymmetric:

- An **A-level alert** contradicts (and sets a falsifier observation).
- A **B-level** alert partially contradicts.
- **C/G alerts and clean reports are context only. A clean checkCIF is
  never support** — the scope claim (CLM-006-02) states what the check
  cannot see.

**Stated limit:** live PLATON verification has never been performed in
this environment. PLATON is author-distributed under its own terms and
no binary is installed; the adapter runs on recorded real outputs
(provenance-pinned fixtures) or via the IUCr service output, and
records `not_runnable_here` with the reason when neither exists.

## CODECHECK — computational reproducibility (Spec 007)

Ingests certificates from the CODECHECK register: a certificate
attests that an independent codechecker re-executed named outputs of a
computational artifact. The evidence is **capped by the certificate's
own stated scope** — exercised in the build: the register's real
certificate 2020-001 is partial on its own text, so its evidence caps
at 0.40 with the uncertified outputs named. A certificate never
certifies correctness; it attests scoped re-execution.

## statcheck / GRIM — statistical reporting (Spec 008)

- **GRIM/GRIMMER** (native, exact rational arithmetic): tests whether
  reported means/SDs are arithmetically possible for integer data at
  the reported *n*. A GRIM impossibility is a contradiction with a
  falsifier observation — against a *reporting-consistency* claim
  ("the reported means are arithmetically possible"), never a claim
  that a paper is fraudulent. Validated against the scrutiny manual's
  published examples and a brute-force enumeration of >1,000 achieved
  datasets with zero false flags. Where granularity makes the test
  inapplicable, the run records `not_applicable` and emits no
  evidence.
- **statcheck**: recalculates p-values from reported test statistics.
  Extraction coverage is recorded on every run — "no statistics
  extracted" is a number in the record, not a clean bill.

**Stated limit:** live statcheck verification has never been performed
here — no R runtime exists in this environment. The Rscript seam is
implemented; the build's statcheck evidence comes from recorded
outputs whose classifications are the statcheck project's own
assertions. GRIMMER parity with the full reference implementation is
not claimed, and SPRITE is not implemented.

## Lean / math claims (Spec 003; service in Spec 004)

The math layer ingests Lean artifacts directly: fetch + SHA-256,
sorry/admit counts over comment-stripped bytes, an axiom audit via
`#print axioms` where the artifact is runnable (any axiom beyond the
standard three is named; `sorryAx` is a falsifying observation for
proof claims), and the formal statement pinned beside the claim it
supports. Compile honesty states are first-class: `run_by_us`,
`recorded_output`, `not_runnable_here`, `claimed_by_source`,
`not_attempted`.

**Stated limit:** in the worked study every real-world artifact was
`not_runnable_here` (claimants' pinned toolchains + Mathlib builds vs
a local bare toolchain) — see
[the math study](../evidence/math-study.md). The persistent Lean
verification service (pinned toolchains + Mathlib, whole-project
builds) is specified in Spec 004 and not yet built.

## The wider survey

The adapter program is organized by a nine-pattern verification
taxonomy (machine-checked proof, automated validation suites,
independent re-execution, curated benchmarks, model intercomparison,
institutional replication verification, reporting-consistency
checkers, credibility frameworks, standards with validators) surveyed
across all engineering disciplines, natural and social sciences,
philosophy/humanities, and law — with honest "no machine checker
exists" verdicts where true (systems engineering, archaeology/history,
and interpretive humanities among them). Survey:
`docs/surveys/2026-10-12-domain-evidence-adapters.md` in the
repository.
