# Claims & falsifiers

A Tekmerion study does not produce a prose answer. It builds a **claim
register**: findings decomposed into claims with stable IDs, each
carrying its evidence, its dependencies, and an explicit **falsifier** —
the observation that would overturn it.

## The claim

A registered claim states:

- `statement` — the proposition, written so it can be wrong.
- `falsifier` — **mandatory.** The observation that would falsify the
  claim. Registration without one is refused before anything is
  appended; an empty falsifier is refused by the engine itself:
  `no falsifier — not registered (Article II)`.
- `margin` — how far the range of values the evidence supports (its
  interval) must clear zero before a verdict may be issued.
- `sufficiency_floor` — the minimum number of independent **origin
  groups** that must support the claim. Ten echoes of a single study
  are one origin group, not ten pieces of evidence.
- `kind` and `dependencies` — claims can rest on other claims; a claim
  can never stand stronger than the weakest claim it depends on.

## Headline results decompose

For theorem claims (Spec 003), a headline result — "X solved Y" — is
never one claim. It decomposes into a parent plus five first-class
sub-claims, each with its own falsifier, evidence, and verdict:

1. **Faithful** — the formal statement matches the original problem.
2. **Proof verified** — the proof artifact checks.
3. **Genuinely open** — the problem was actually open and novel.
4. **Attribution clean** — prior work credited; disputes registered
   with both sides' evidence.
5. **Significant** — the result matters, and is explained.

A contested attribution holds the parent at *contested* while the
dispute stands. Attribution is itself a claim.

## Corrections are appends

There is no edit and no delete. A claim is corrected by a superseding
claim (`supersedes`), an adjudication decision, or a withdrawal with a
reason — the claim stays on the record, marked dead, its history fully
readable.
