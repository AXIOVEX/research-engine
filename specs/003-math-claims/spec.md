# Spec 003 — The Math Layer: theorem claims under the stage model

**Status:** DRAFT — claims first (this spec's `aee-claims.json` is assessed before code, per Article XII) · **Date:** 2026-10-12 · **Constitution:** v1.1.0
**Authority:** DN-010 (stage model, adopted 2026-10-12) · Spec 002 machinery (register, freeze, verdicts, verification, export, deposit) · Owner directive 2026-10-12 (worked study on the 2026 public AI-mathematics claims).
**Scope:** a math layer over the Spec 002 engine that takes a public headline result ("X solved Y") and returns a decomposed, evidenced, lane-separated verdict — plus its first worked study. Nothing beyond that slice.

## 1. Purpose

Public AI-mathematics announcements arrive as single undifferentiated claims,
graded by counts. DN-010 adopts the contrary doctrine: a headline result is
five claims, in two lanes, with digestion tracked and attribution adjudicated.
This spec builds the machinery for that treatment and runs it once, in
public, on the hardest current cases.

## 2. Theorem claim schema (DN-010 point 2)

A **theorem claim** is a parent claim in the ordinary register plus five
first-class sub-claims, each independently registered with its own
falsifier, evidence, and verdict:

| Sub-claim | Question it answers |
|-----------|---------------------|
| `faithful` | Is the formal statement faithful to the original problem (same hypotheses, same scope, same conclusion)? |
| `proof_verified` | Is the proof artifact verified — sorry-free, axiom-clean, compiled — and by whom? |
| `genuinely_open` | Was the problem genuinely open at announcement (primary status source + literature)? |
| `attribution` | Is attribution clean — prior literature cited, no live dispute? |
| `significance` | Is the result significant and explained (the community-facing claim)? |

Claim ids: parent `CLM-<study>-<case>10`; sub-claims `…<case>11`
(faithful), `…12` (proof), `…13` (open), `…14` (attribution), `…15`
(significance). The parent depends on all five (register DAG); the parent
is never evaluated from evidence of its own.

**Composition (the parent verdict).** Computed from the five sub-verdicts
(WS3 taxonomy, issued by the production verdict path) plus the attribution
dispute state, in this precedence — the order *is* the doctrine:

1. A **live attribution dispute** caps the parent at **contested**
   (point 4: contested attribution keeps the parent contested). The
   sub-verdicts stand beside it in the same record; nothing is hidden.
2. Else, any sub-claim **contradicted** makes the parent **contradicted**:
   the headline, as stated, fails.
3. Else, all five sub-claims **supported** makes the parent **supported**.
4. Else the parent is **inconclusive**, with the weakest sub-claim(s)
   named in the reason.

A theorem verdict is a record, not a label: it carries the five
sub-verdicts, the lane fields (§5), the digestion state (§5), and
`remains_not_understood` (§6). Composition **refuses** to issue a parent
verdict without `remains_not_understood` — the field is mandatory the way
a falsifier is mandatory (Article II discipline, applied to verdicts).

## 3. Lean artifact ingestion (point 2ii, point 8)

Given a Lean artifact (repo file or standalone file, by URL):

- **Fetch + hash.** The artifact bytes are fetched and SHA-256
  content-hashed; the ingestion record (URL, retrieval date, hash, byte
  length) is appended to the study ledger. Evidence about an artifact is
  evidence about *those bytes*, never about a claimant's description.
- **Parse.** `sorry`/`admit` occurrences are counted from the bytes;
  theorem/lemma declarations and their statement text are extracted.
- **Faithfulness pinning.** The extracted formal statement is pinned
  beside the **original problem statement, verbatim, with its source** —
  the gap between them, if any, is itself the `faithful` sub-claim's
  subject matter, adjudicable from the pinned pair.
- **Compile check — honesty states.** Compile status is one of:
  - `run_by_us`: we ran the pinned toolchain (version recorded) on the
    fetched bytes; exit code and full-output hash are in the record.
    Where feasible, a probe appends `#print axioms <theorem>` so axiom
    dependence (incl. `sorryAx`) is read from the kernel, not inferred.
  - `not_runnable_here`: a run was attempted or assessed and the
    environment cannot carry it (e.g., the artifact needs a Mathlib
    build that is not present); the reason is recorded. This is **not**
    a proof failure and never scored as one.
  - `claimed_by_source`: no run by us; the record cites the claimant's
    own CI/artifact evidence as asserted evidence, labeled as such.
  A compile we did not run is never recorded as run. A `sorry` found in
  the bytes is a falsifying observation for `proof_verified` regardless
  of compile state.

## 4. Openness and attribution checks (points 2iii, 2iv, 4)

- **Openness.** The primary status source for Erdős problems is the
  Erdős Problems status listing (erdosproblems.com); for other problems,
  the closest primary status listing. A connector literature search
  (Crossref/OpenAlex, queries ledgered per the WS1 contract) looks for
  prior solutions. The check's output is **evidence on the sub-claim**,
  never a verdict by itself.
- **Attribution.** A connector literature search for prior/related work,
  plus dispute registration: a dispute is a ledger record naming the
  parties, each side's position, and each side's retrieved evidence
  (URL + date). Attribution state is a replay of those records:
  `undisputed` until a dispute record exists, `contested` while one
  stands unresolved. Resolutions are further appends, never edits.

## 5. Digestion and the two lanes (points 1, 3, 6)

- **Digestion record** per theorem claim: a named human explainer and an
  explanation artifact (link or pinned quotation), recorded as a ledger
  event — or the explicit state `UNEXPLAINED`, which raises a
  **risk flag** carried on the parent record and in every export.
  Verified-but-unexplained is a flagged state, never a silent one.
- **Lane 1 — verification (machine-speed):** ingestion, parsing, compile
  checks, citation pipeline outcomes. **Lane 2 — acceptance
  (human-paced):** digestion, adjudication decisions, acceptance stages
  (explained → accepted → digested). Lane 2 advances **only** on human
  evidence events (a named explainer's artifact; a named adjudicator's
  decision). Every theorem verdict record carries `lane1_verification`
  and `lane2_acceptance` as separate fields; no rendering of lane 1 may
  stand in for lane 2 (point 6).

## 6. Verdict shape and anti-gradability (point 5)

Every theorem verdict record carries: parent verdict, the five
sub-verdicts with reasons, `remains_not_understood` (mandatory,
adjudicator-written prose: what is not understood even if everything
checks), lane fields, digestion state + risk flag, and the evidence
trail references. **No Tekmerion math-layer output or export publishes
an aggregate count of "solved" results** — counts of verdicts are
tallies, not verdicts, and this layer does not issue them.

## 7. Per-source reliability record (point 8; calibration)

Resolved claims calibrate their sources. A **reliability record** is a
replayable projection of ledger events of the form: *source S asserted
claim C; C resolved true / resolved false / contested*, each with the
resolution's evidence reference. A resolved-false assertion stays on
its source's record permanently (append-only, Article IV), so future
assessments of that source carry the calibration. Seeding a record
requires an identified claim and an identified resolution, both from
retrieved sources; an unidentifiable case seeds nothing.

## 8. The worked study (first application)

One study on the production machinery, registered and frozen in the
engine, verdicts issued through the verdict service, exported as an
audit bundle, and anchored on Zenodo (AR-1 path, gate G2 machinery).
Multi-actor by design — registration, evidence, adjudication, and
control-relevant events carry distinct actors, because the Phase 5 demo
taught that a control which cannot bite invalidates the run (and a
single-actor ledger makes the swap control a no-op). If a control
fails, the run is INVALID, issues no verdicts, and is reported as such.

Cases (each a theorem claim per §2):

- **(a) OpenAI Navier–Stokes (Sept 8, 2026 announcement)** — the
  contested showcase: headline vs forced-case scope lives in `faithful`;
  Lean-check provenance (claimant-run vs independently run) lives in
  `proof_verified`; outstanding human verification lives in lane 2; the
  Buckmaster/Alpöge attribution dispute is registered with **both**
  sides' retrieved evidence.
- **(b) The Astra ten proofs** — the fairness case: `proof_verified`
  rests on the public Lean certificates (fetched, hashed,
  sorry-counted, compiled where feasible); novelty/citation concerns
  from the Scientific American reporting are evidenced on `genuinely_open`
  / `attribution`, naming the results the reporting concerns.
- **(c) The October manuscript dump (the quasi-Riemann manuscript)** —
  the abstention case: provenance is the question; the honest outcome
  is whatever the retrievable evidence supports, expected to be
  abstention/INCONCLUSIVE with the unestablishable facts named.
- **(d) DeepMind AlphaProof Nexus, nine Erdős results** — the positive
  control: openness from the Erdős status source, proof verification
  from the public Lean artifacts; expected strongest case, evidence
  decides.
- **(e) The resolved October 2025 Erdős retraction** — calibration:
  identify the retracted claim and its resolution from public sources
  and seed the §7 reliability record for its source. If the retraction
  cannot be identified with confidence from retrieved sources, seed
  nothing and say so.

**Research method.** Public web only; primary sources first (claimants'
posts/papers/repos, Lean artifacts, the Erdős status listing), reputable
reporting second (Scientific American, New Scientist, Quanta). Every
source enters the study ledger as evidence with URL + retrieval date.
Sources that cannot be retrieved or resolved are recorded as gaps and
score INCONCLUSIVE — the expected narrative is never borrowed.

## 9. Gates and non-goals

- **No spend; no new accounts.** Zenodo deposit uses the existing owner
  token via the Phase 5 transport; adjudicator approval for the study's
  deposit is the owner's directive for this study, recorded as such.
- **Untouched:** the Phase 6 wireframe package and its gate
  (DN-009/T219-WF), the AEE repos, the axiomere repos. The study runs
  through code/API on existing machinery; there is no UI work in this
  spec, and no outreach of any kind is drafted or sent.
- **Non-goals:** re-verifying claimant mathematics beyond the artifact
  checks defined here; a general theorem-proving service; aggregate
  leaderboards (forbidden by §6, not merely deferred).
