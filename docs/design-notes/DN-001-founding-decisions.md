# Design Note 001 — Founding Decisions

**Date:** 2026-10-11 · **Status:** Founding record · **Owner:** Tristen Pierson, Axiovex Systems, LLC
**Rule for this series:** design notes are append-only. A later note may supersede a decision here; this note is never edited to pretend the earlier decision did not happen.

## 1. What is being built

An AI-based research engine for research and analysis whose differentiator is **defensibility**. Consumer deep-research tools compete on speed and summary quality. This product competes on whether the result can be *inspected, reproduced, and stood behind*: every claim carries its evidence and its falsifier, verdicts are pre-registered, evidence is provenance-tracked and hash-verified, and the record is append-only.

## 2. Name — `research-engine` (AXIOVEX/research-engine)

**Decision:** keep the recommended name, `research-engine`.

**Reasoning.** Alternatives considered: `veritas-*` / Latinate coinages (evocative but opaque, and they promise truth rather than process), `dossier` / `audit-*` names (accurate but narrow — they name the output, not the system), and `axiovex-research` (redundant inside the AXIOVEX org). `research-engine` wins because it is plain, immediately legible to the institutional audience, and names the category the product intends to define: an *engine* — a system with a method — rather than an assistant, a chatbot, or a report generator. It also pairs cleanly with the theory sibling: `epistemic-ledger` is the theory, `research-engine` is the tool. The defensibility wedge lives in the description and the method, not in a clever name.

## 3. Positioning

- **One line:** Defensible AI research for universities: every claim carries its falsifier, every verdict is pre-registered, every result ships with an audit trail.
- **The wedge:** auditability over speed. Where incumbents optimize time-to-summary, this product optimizes *time-to-trust*: how quickly a reviewer, integrity officer, or replicator can verify how a conclusion was reached.
- **Voice:** Axiovex house voice — direct, evidence-first, no invented metrics, no customer claims that do not exist, no performance figures that have not been measured under a frozen protocol.

## 4. Audience (primary, in order)

1. University **research integrity offices** — inspection and adjudication of AI-assisted work.
2. **Systematic-review and meta-analysis teams** — reproducible search, auditable screening, honest evidence counting.
3. **Graduate research programs** — teaching and enforcing defensible AI use.
4. **Libraries and labs** — durable, depositable research records.

Individual consumers are explicitly *not* the primary audience for v1; the design optimizes for institutional review workflows, not chat UX.

## 5. Relationship to AXIOVEX/epistemic-ledger

`epistemic-ledger` is the **theory sibling** and remains the home of the framing paper, the scoring research, and the measured results (including negatives — they are part of the method's credibility). This repository is the **tool**. The engine *adopts* the ledger's measured mechanisms where the transfer is justified, *adapts* them where a product context differs from a research prototype, and *supersedes* them only with a recorded reason in a design note (see `docs/architecture/02-claim-evidence-model.md` §Ledger relationship). No content is duplicated between the repos; each links to the other.

## 6. Method commitments (inherited from the epistemic framework)

These are founding constraints, not features to be traded away:

1. Stable claim IDs, claim kinds, and an explicit falsifier per claim.
2. Claim dependency graphs — a verdict knows what it rests on.
3. Evidence counted by **origin group**; derivatives never double-counted.
4. Discriminating positive **and** negative controls; a gate that cannot differentially fail renders a run **INVALID**, not passed.
5. Verdict taxonomy: **INVALID / INCONCLUSIVE / CONTRADICTED / SUPPORTED** — applied claim by claim.
6. Freeze + replay: designs are frozen and timestamped before outcomes are seen; a frozen run can be replayed and checked.
7. Practical margins reported with intervals, never bare point scores.
8. Exploratory work and confirmation work are separate modes, labeled as such, and never blended in one headline result.
9. Historical assessments are appended; originals are never rewritten.

## 7. License

**Decision:** All rights reserved, © 2026 Axiovex Systems, LLC — matching the `epistemic-ledger` precedent.

**Reasoning.** The theory repo established the posture for Axiovex research IP; consistency keeps the org's IP position unambiguous while the product's commercial shape (hosted service vs. licensed deployment) is undecided. Revisit only by a later design note if a deployment model requires it.

## 8. Non-goals (v1)

- Not a general chatbot or writing assistant.
- Not a replacement for peer review, and never marketed as one.
- No autonomous publication: a human adjudicator signs every institutional verdict (see architecture workstream 5).
- No fabricated or "representative" citations, ever — an unverifiable reference is a defect that fails the run, not a rounding error.
- No performance, accuracy, or adoption claims until measured under a frozen protocol in this repo.
- No content from any other company's projects; the method is described on its own terms.

## 9. Process

Spec-first, per the project constitution: constitution → spec → plan → tasks, with AEE claims on the spec. **No implementation until the architecture has been genuinely iterated** — including a red-team pass against this repo's own design (a control that cannot fail is a defect, in the product and in the process). Milestones are reported to the owner as verified states only.

## 10. Open decisions carried forward

| # | Decision | Where it will be settled |
|---|----------|--------------------------|
| OD-1 | MVP slice (which audience workflow first) | `docs/architecture/06-product-shape.md`, then spec 001 amendment |
| OD-2 | Deployment shape (hosted, local, hybrid) | `docs/architecture/06-product-shape.md` |
| OD-3 | Ledger scoring: adopt / adapt / supersede, per mechanism | `docs/architecture/02-claim-evidence-model.md` |
| OD-4 | Storage/redistribution rights per source | `docs/architecture/01-source-layer.md` + workstream 5 |
| OD-5 | Kill criteria for the MVP slice | Spec 001 |
