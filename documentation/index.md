# Tekmerion

**Defensible AI research — built for universities that have to stand behind the result.**

Tekmerion (τεκμήριον — *conclusive evidence by which a thing is proved*) is
Axiovex's defensible-research engine. Most AI research tools sell speed and
summaries. This one sells something different: **an audit trail a university
can rely on.**

- **Every claim carries its falsifier.** A claim cannot be registered
  without stating the observation that would overturn it. No falsifier, no
  registration — the engine refuses, and nothing is appended.
- **Verdicts are pre-registered.** Questions, inclusion criteria, verdict
  rules, and controls are frozen and timestamped *before* evidence is
  gathered, and verdicts are issued only by the machinery against a valid
  frozen run.
- **Evidence is provenance-tracked and hash-verified.** Sources are real
  scholarly systems (Crossref, OpenAlex, CORE); every query is logged,
  every retrieved item carries its origin and its licence basis, and
  sources that all repeat one original study are counted once, as one
  origin group.
- **Records are append-only.** Corrections are new entries, never quiet
  rewrites. The record layer is [Axiomere](https://github.com/AXIOVEX/axiomere),
  a hash-chained, signed ledger with no delete or update operation.

When the engine cannot support a claim, it says so with a verdict designed
for exactly that: *inconclusive* is an answer, not a failure.

## The two lanes

Tekmerion's doctrine (the stage model, design note DN-010) keeps two
kinds of work — two lanes — strictly separate:

- **Lane 1 — machine-speed verification:** citation checks, domain
  adapters, Lean compiles, verdict computation.
- **Lane 2 — human-paced acceptance:** explanation, acceptance, and
  digestion by named humans.

Lane-1 completion never displays as lane-2 completion: a *checked* claim
is not an *accepted* one, and every verdict states what remains not
understood. See [Stages & lanes](concepts/stages-and-lanes.md).

## Who it is for

- **Research integrity offices** that must inspect how an AI-assisted
  conclusion was reached.
- **Systematic-review and meta-analysis teams** that need reproducible
  searches and auditable screening.
- **Graduate research programs** teaching — and enforcing — defensible
  AI use.
- **Libraries and labs** that need research records they can keep,
  deposit, and re-run.

## Where to start

- [Installation](guide/installation.md) — install from PyPI and connect
  an MCP client.
- [Quickstart](guide/quickstart.md) — one study end to end: register,
  verify, adjudicate, freeze, evaluate, export.
- [Evidence base](evidence/index.md) — what the engine has actually done,
  including the runs that came back disputed (CONTESTED), not settled
  (INCONCLUSIVE), and defective (INVALID).

## Honest status

Statuses in this project are claims, and claims carry evidence. The
engineering claims behind the engine stand at the **checked** stage
(machine-verified by the project's own tests and evaluations); almost
none is presented as *explained* or *digested*, because lane 2 advances
only on named-human evidence. The worked studies, their verdicts, and
their disclosed defects are in the [evidence base](evidence/index.md).
The theory the tool is built on is published separately in the
[epistemic-ledger](https://github.com/AXIOVEX/epistemic-ledger)
repository.

## License

All rights reserved. © 2026 Axiovex Systems, LLC.
