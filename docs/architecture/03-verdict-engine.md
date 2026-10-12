# WS3 — Verdict Engine

**Status:** Draft v0.1, 2026-10-11 · Governs: FR-001, FR-006, FR-007, FR-011 · Constitution: Articles III, VI, VII

## 1. The taxonomy, mechanically

A verdict is a function of: the frozen registration, the evidence groups, the falsifier test, and the controls. Exactly four outcomes per claim:

| Verdict | Meaning | Entry condition |
|---------|---------|-----------------|
| **INVALID** | The *run* was defective; no claim verdict is issued | Any control failure, any unverified citation in the evidence set, any deviation from the frozen registration, broken hash chain on replay |
| **INCONCLUSIVE** | The run was valid; the evidence does not decide the claim | Evidence groups below the registered sufficiency floor, or intervals straddle the margin, or origin groups conflict with no registered entrenchment rule resolving them |
| **CONTRADICTED** | The falsifier test fired | The registered falsifying observation is present in the evidence, within margin |
| **SUPPORTED** | The falsifier test was run, could have fired, and did not; support exceeds the registered margin | Support from ≥ the registered minimum of independent origin groups, interval clears the margin |

Two properties are load-bearing. First, **INVALID attaches to the run, not the claim** — a defective run issues no claim verdicts at all, so a broken process can never launder itself into weak-but-present "inconclusive" results. Second, **SUPPORTED requires the falsifier test to have been capable of firing**: if the evidence set contains nothing that *could* have contradicted the claim, the verdict is INCONCLUSIVE ("untested"), never SUPPORTED. Support without exposure to refutation is not support.

## 2. Controls that can fail (Article VI)

Every run registers, at freeze time, at minimum:

- **Positive control** — a claim with a known answer the pipeline must get right (e.g., a well-established finding inside the search scope). Failure → the retrieval/extraction path is broken → INVALID.
- **Negative control** — a claim known to be false, or a fabricated-but-plausible citation seeded *into the control channel only*, which the verification step must reject. A pipeline that accepts it → INVALID. (The seeded fabrication never enters the evidence store; it exists only as a test probe, is labeled as one in the record, and its presence is disclosed in the bundle.)
- **Swap control** — two evidence items' provenance stubs are exchanged in a test copy of the run; the replay/verification step must detect the mismatch by hash. Non-detection → the integrity machinery is decorative → INVALID.

Design rule: **a control is specified by its failure mode first.** When writing a control, the first sentence states what defect it exists to catch; a control whose author cannot name the defect is deleted, not kept for reassurance.

## 3. Freeze & pre-registration workflow

1. **Draft** — question, claims, falsifiers, sources, criteria, margins, controls assembled. Editable.
2. **Freeze check** — automated: every claim has a falsifier; graph is acyclic; controls have named failure modes; margins and sufficiency floors are set; source rights permit the planned storage (WS1). Any failure blocks the freeze.
3. **Freeze** — the registration is hashed, timestamped, and appended to the record. From here, the design is immutable.
4. **Run** — retrieval, grouping, weighing, verdicts, all as appended events referencing the registration hash.
5. **Amendment** (if needed) — a new dated record stating the change and reason, producing a *new* registration version. Verdicts already issued stay attached to the version that produced them. Re-running under v2 never rewrites v1's outcomes.

## 4. Exploratory vs. confirmation (FR-011)

Two modes, one hard wall:

- **EXPLORATORY** — no freeze required; the register is labeled exploratory at every level (study, claim, export watermark). Purpose: question-finding, scope discovery, hypothesis generation.
- **CONFIRMATION** — requires a frozen registration created *before* the confirmatory evidence is gathered.

The wall: exploratory results cannot be promoted. If exploration suggests a claim is true, confirmation starts from a fresh registration and fresh evidence-gathering under it. The bundle records which mode produced every verdict; a bundle that mixes modes without labels is an INVALID artifact. This is the product-level form of a rule the field already accepts for studies — the engine simply refuses to let software quietly violate it.

## 5. Replay

A frozen run can be replayed from its event record: same registration hash, same evidence content hashes, same verdict rules. Replay has two legitimate outcomes — verdicts reproduce exactly, or the divergence is surfaced as a finding (nondeterminism in extraction is expected with LLM components; the replay protocol therefore compares *verdicts and their evidence basis*, and records extraction variance rather than pretending bit-identical reproduction — see WS4 §3 for what is hashed and what is compared).

## 6. Scoring inside the engine

Where weighing needs numbers (WS2 §4), the engine keeps interval-valued support per claim: support mass, contradiction mass, and explicit ignorance mass, per origin group, combined under the registered rule. The interval — not a point — is what the margin test consumes, and the interval is what the export shows. Point scores exist only as a display convenience derived from the interval, always shown with it.

## 7. Open questions

- OQ-3.1 LLM extraction nondeterminism budget: how much verdict-level variance across replays is tolerable before a study class is declared unsuitable for automated extraction and routed to human extraction? To be settled by a frozen measurement in the MVP evaluation, not by intuition here.
- OQ-3.2 Sufficiency floors: are minimum origin-group counts set per claim kind by a house default, or always per-study? Leaning per-study with house defaults as starting values, because a floor tuned after seeing evidence is not a floor.
