# Stages & lanes

Tekmerion's doctrine for any claim — above all a headline result —
follows the five-stage model adopted in design note **DN-010**
(adopted 2026-10-12).

## The five stages

A claim passes through:

1. **Created** — registered, with its falsifier.
2. **Checked** — machine verification ran against it (citation checks,
   adapter checks, Lean compiles, a verdict).
3. **Explained** — a named human has explained the result.
4. **Accepted** — a named human or body has accepted it, on evidence.
5. **Digested** — the explanation has been absorbed and re-stated by
   the community that relies on it.

**Creation + checking alone never settle a claim.** Most of Tekmerion's
own engineering claims stand at *checked*; lane 2 holds only explicit
human acts recorded on the ledger (an owner's gate ratification, a
named explainer's digestion record). Verified-but-unexplained is a
flagged risk state, not a footnote.

## The two lanes

| Lane | Contents | Pace |
|---|---|---|
| **Lane 1** | Machine verification: resolution, stance checks, adapters, compiles, verdict computation | Machine speed |
| **Lane 2** | Explanation, acceptance, digestion — by named humans, on recorded evidence | Human pace |

The lanes are tracked in separate fields on every verdict record
(`lane1_verification`, `lane2_acceptance`). Lane 2 advances only on
human evidence — a named explainer, an adjudicator's decision — never
as a side effect of lane 1. No code path promotes a lane-1 state into
a settled result.

## The rest of the doctrine

The remaining DN-010 points, each carried by a named mechanism:

- **Digestion is first-class tracked work** — a digestion record per
  theorem claim: named explainer + explanation artifact, or the
  explicit state `UNEXPLAINED`, which raises a risk flag on the parent
  record wherever it is displayed or exported.
- **Attribution is a claim** — disputes are registered with both
  sides' evidence; a live dispute holds the parent at *contested*.
  Disputes are appends, never edits.
- **Anti-gradability** — easily graded metrics (counts, scores) never
  stand in for understanding. No Tekmerion output publishes aggregate
  "solved" counts; every theorem verdict carries
  `remains_not_understood`.
- **Openness is protected** — registration is hash-chained and
  checkpointed at registration time, and audit bundles are publishable
  and externally anchored, so a claimant's priority is provable from
  the public record.
- **Inspectable records** — every verdict ships an auditable evidence
  trail: the audit bundle plus an external anchor (Zenodo / OSF) is
  the standard output of a study. Verdicts without a bundle and an
  anchor are drafts, whatever they say.
