<h1 align="center">Tekmerion</h1>

<p align="center">
  <strong>Defensible AI research — built for universities that have to stand behind the result.</strong>
</p>

<p align="center">
  🌐 <a href="https://axiovexsystems.com"><strong>axiovexsystems.com</strong></a>
  &nbsp;·&nbsp; Theory sibling: <a href="https://github.com/AXIOVEX/epistemic-ledger">AXIOVEX/epistemic-ledger</a>
  &nbsp;·&nbsp; Record layer: <a href="https://github.com/AXIOVEX/axiomere">AXIOVEX/axiomere</a>
</p>

**Tekmerion** (τεκμήριον — *conclusive evidence by which a thing is proved*; renamed from the Axiovex Research Engine, 2026-10-11, DN-006) is Axiovex's defensible-research framework. Its records live in [Axiomere](https://github.com/AXIOVEX/axiomere), a truth ledger where records are revised by new snapshots and never deleted.

Most AI research tools sell speed and summaries. This one sells something different: **an audit trail a university can rely on.** Every claim the engine makes carries the evidence it rests on and the test that would falsify it. Verdicts are registered before outcomes are seen. Records are append-only — a correction is a new entry, never a quiet rewrite of the old one. When the engine cannot support a claim, it says so, in a verdict designed for exactly that: *inconclusive* is an answer, not a failure.

## The problem

AI-assisted research is fast, fluent — and hard to defend. Citations are generated as easily as they are retrieved, and some are fabricated outright. Methods shift mid-run without a record. A summary arrives with no way to ask *what does this rest on, what would change it, and who checked?* For a student paper that is an inconvenience. For a research integrity office, a systematic-review team, or a lab whose work will be replicated, challenged, or published, it is disqualifying.

The missing piece is not a better summary. It is a research process whose every step leaves evidence.

## What it will do

- **Register the question before answering it.** Research questions, inclusion criteria, and verdict rules are frozen and timestamped before evidence is gathered — the same discipline as a pre-registered study.
- **Retrieve from scholarly infrastructure, with provenance.** Sources are real scholarly systems (OpenAlex, Semantic Scholar, Crossref, CORE, and peers — see the [source registry](docs/architecture/01-source-layer.md)), every query is logged, and every retrieved item carries its origin. Nothing enters the record without a source that can be re-checked.
- **Build a claim register, not a prose answer.** Findings are decomposed into claims with stable IDs, each carrying its evidence, its dependencies, and an explicit **falsifier** — the observation that would overturn it.
- **Count evidence honestly.** Derivative sources that repeat one origin are counted once, by origin group. Ten echoes of a single study are one piece of evidence, not ten.
- **Render verdicts that can fail.** Each claim resolves to a verdict from a fixed taxonomy — **Supported, Contradicted, Inconclusive,** or **Invalid** (the run itself was defective). Controls are designed so they *can* fail: a check that cannot differentially fail marks the run invalid rather than passing it.
- **Keep the record append-only and hash-verified.** The full history of what was believed, when, and why stays queryable. Exports are dossiers and audit bundles a university can keep, deposit (OSF, Zenodo), and hand to a reviewer or an integrity board.

## How it works

1. **Frame.** State the question, the claims it implies, and what would falsify each one.
2. **Freeze.** Register the design — sources, criteria, verdict rules — before outcomes are seen.
3. **Gather.** Retrieve from scholarly sources; log every query; deduplicate by DOI and identity; attach provenance to every item.
4. **Weigh.** Group evidence by origin, test it against the falsifiers, run the controls.
5. **Decide.** Issue verdicts claim by claim, with intervals and margins — never a single blended score that hides a weak link.
6. **Deposit.** Export the registration, the claim register, and the audit bundle. The record stands on its own, without the engine.

The method is not new decoration. It is the epistemic engineering framework Axiovex has developed and measured in the open — claim registers with falsifiers, origin-group evidence counting, discriminating controls, freeze-and-replay integrity, and an append-only ledger whose scoring machinery is published, with its negative results, in the theory sibling repository, [AXIOVEX/epistemic-ledger](https://github.com/AXIOVEX/epistemic-ledger). This repository is the **tool** built on that theory.

## Who it is for

- **Research integrity offices** that must inspect how an AI-assisted conclusion was reached.
- **Systematic-review and meta-analysis teams** that need reproducible searches and auditable screening.
- **Graduate research programs** teaching — and enforcing — defensible AI use.
- **Libraries and labs** that need research records they can keep, deposit, and re-run.

## Status

**Implemented through Spec 002 Phase 5 (October 2026); lifecycle stages per DN-010.** The MVP engine (Specs 001–002) is built and CI-verified: study store on the Axiomere record layer, live Crossref/OpenAlex connectors, claims/freeze/verdicts, the citation pipeline, and the audit bundle with a standalone verifier and Zenodo anchoring — demonstrated live in Phase 5 (gate G2 ratified by the owner, DN-008; the demonstration run itself was INVALID and is recorded as such). Spec 003 (math-claims layer, stage model per DN-010) is implemented; its worked study is in progress. Phase 6 (UI) is claims-first only: its wireframe package awaits owner approval (gate T219-WF). Under the DN-010 stage model, the engineering claims stand at **checked** (one gate demonstration **accepted**); none is presented as explained or digested. The founding decisions are recorded in [Design Note 001](docs/design-notes/DN-001-founding-decisions.md), the architecture in [`docs/architecture/`](docs/architecture/), and the governing specifications in [`specs/`](specs/) under the project [constitution](.specify/memory/constitution.md). A status in this repository is a claim, and claims here carry evidence. (This section previously read "Design phase… No implementation yet" — stale since Phase 0/1; corrected 2026-10-12 by the stage-model audit, docs/audits/2026-10-12-stage-model-audit.md.)

## Repository layout

```
.
├── README.md                  # This page
├── LICENSE                    # All rights reserved, © 2026 Axiovex Systems, LLC
├── .specify/memory/           # Project constitution
├── specs/001-research-engine/ # Spec, plan, tasks, AEE claims
└── docs/
    ├── architecture/          # The six architecture workstreams
    └── design-notes/          # Numbered, append-only design decisions
```

## License

All rights reserved. © 2026 Axiovex Systems, LLC. See [LICENSE](LICENSE).

<p align="center">
  <strong>Claims with falsifiers. Verdicts with receipts.</strong>
</p>
