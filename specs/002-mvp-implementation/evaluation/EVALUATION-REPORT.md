# Spec 002 Phase 7 — Evaluation report (T220–T222)

**Date**: 2026-10-12. **Branch**: `phase-7-evaluation`. **Study**:
`evaluation/study/` (ledger + bundles in-repo). **Registration
companion**: `evaluation/corpus.md` (design, seeded defects, and
predictions recorded *before* the freeze — this report scores the run
against them and does not edit them). **Driver**:
`evaluation/run_evaluation.py` (+ `resume_deposit.py`, see §7);
**K2 replay**: `evaluation/replay_check.py`.

**The run in one paragraph.** Five evidence questions from the MVP
systematic-review workflow were registered as claims (CLM-E-001…005)
with ten citations — real records from Crossref/OpenAlex, among them
a seeded fabricated DOI, a seeded corrupted citation, a duplicate
citation, and a shared-dataset pair — plus positive/negative/swap
controls. The registration froze at Merkle checkpoint root
**`a4c798715c05ae151849ddf0e7c4a3dcb7b119620757b088686bd18d24e6c049`**
(registration hash `977c1db162e9ba06b3e34c633a5bbae96fe4779aa49c43356b564cc8c3b9ac9b`).
The frozen run evaluated **VALID** (chain intact, all controls
behaved, no unverified evidence) and verdicts were issued through
the production engine only: **supported, supported, inconclusive,
contradicted, inconclusive** — each by a distinct, pre-registered
mechanism (§3). The audit bundle verifies standalone, states its own
run outcome in-bundle (Phase 7's NC-6 projection), and is anchored on
Zenodo at **DOI 10.5281/zenodo.23319126**, verified against the
independently fetched public record. One operator played all four
actors (researcher, adjudicator, second-reviewer, verdict-service);
wherever independence matters, this report says so.

**Kill criteria at a glance** (mechanisms and numbers in §2):
K1 **pass**, K2 **pass** (after a verifier gap the evaluation itself
found and Phase 7 fixed, §2.2), K3 **pass** (§2.3), K4 **pass**,
K5 **pass** ($0.0012 per question against the $25 ceiling).

---

## 1. What was run

Pipeline configuration (registered in `corpus.md` before the freeze):
resolution order **OpenAlex first, Crossref fallback** — assembly
probes showed Crossref carries no abstracts for these records, so
Crossref-first would have made every citation metadata-only and
stage 3 would never have run on real data; both connectors were
queried for every question (10 `connector.query` events). Freeze:
confirmation mode, `linked_exploratory=[]` stated explicitly,
hosted shape (no corpus licence asserts an NC restriction; the
freeze's licence check ran and blocked nothing). Adjudication:
4 queue items decided (§3.3). RT-4 sample: 1 of 4 decided items
(seed 7) — ADQ-003, the grouping decision — second-reviewed
`agrees=True` by the second-reviewer actor. With one review, the
RT-4 anomaly rule (≥5 reviews) **cannot acquit anyone**, and this
report does not pretend otherwise; the sample is a workflow
exercise, and the single-operator caveat applies in full.

## 2. Kill criteria

### 2.1 K1 — citation resolution (CLM-002-10's frozen test)

From the bundle's own `verification.json` (identical to the ledger):

- **Accounting: 10 of 10 citations have exactly one
  `citation.checked` event.** (The corpus companion's prose says
  "eleven" in two places — a counting slip in the text; the
  registered table, the ledger, and the bundle all carry ten. The
  Zenodo deposit description repeats the slip; the anchored values
  — root and bundle hash — are exact, and the bundle itself is the
  ground truth.)
- **Outcomes: 9 resolved, 1 not_found, 0 error.** Of the resolved:
  8 agreement=agree, 1 agreement=disagree. Content checks:
  5 supports, 1 contradicts, 1 contextual, 2 metadata_only.
- **The fabricated citation (CIT-E-103, DOI 10.7326/M14-9999) was
  caught**: resolved by neither connector, quarantined (ADQ-001),
  adjudicated **exclude**, and contributes **zero** evidence —
  `evidence/items.json` contains no CIT-E-103 entry.
- **The corrupted citation (CIT-E-202)** — a real paper cited
  through its real DOI with a misstated author surname and year —
  was caught at stage 2 (mismatches: authors, year), quarantined
  (ADQ-002), and excluded *as cited*.
- No fabricated or unsupported citation stands in the evidence
  basis: the 8 evidence items are exactly the 8 citations that
  resolved and agreed (or folded, §2.4).

**CLM-002-10 disposition: status `supported`, lifecycle stage
`created` → `checked`.** The claim's falsifier (F-002-D10) is quoted
here because its wording deserves scrutiny: *"the Phase 7 evaluation
reports any fabricated or unresolvable citation in the frozen
corpus (K1 fails…)"*. Read with hostile literalism, the seeded
fabricated citation's mere presence would fire it — a reading that
would make the claim untestable, since a fabrication-catch claim can
only be tested on a corpus that contains a fabrication to catch.
The claim's operative definition — its own text ("drive fabricated
or unsupported citations **to zero**"), its boundary ("kill
criterion K1 (DN-002)"), and Spec 001's K1 — is the accounting
standard applied above: every citation accounted to an outcome,
fabrications caught and excluded, zero in the evidence basis. On
that standard the frozen evidence supports the claim. The stage is
**checked**, not accepted: the checking was done by the author's own
evaluation (Tao discipline — checking is not acceptance), and no
external party has yet accepted CLM-002-10. What remains not
understood: the pipeline's behaviour on corpora orders of magnitude
larger, and on fabrications subtler than a nonexistent DOI (a real
DOI attached to the wrong proposition is caught only as well as the
lexical stance checker performs — §4).

### 2.2 K2 — replay from the bundle alone

`replay_check.py`, run against bundle-v2 with no live store:

- The bundle verifies standalone (`verify_bundle` ok).
- **Honest replay is exact**: rebuilding the register from
  `claims.json` + `evidence/items.json` and re-running
  `evaluate_claim` reproduces all five issued verdicts with
  identical verdict, interval, and point estimate.
- **Tamper case B (ledger actor edit, manifest rehashed): detected**
  — "ledger fails production verification: hash-mismatch".
- **Tamper case A (verdict string flipped in verdicts.json,
  manifest rehashed): NOT detected on the first pass.** The
  verifier's projection cross-check compared only the *count* of
  verdict entries against the ledger's `verdict.issued` events.
  This is a real gap the evaluation existed to find, and it was in
  our code: Phase 7 fixed it in the same phase (the cross-check now
  compares projection entries to the ledger's events payload for
  payload, for verdicts and queries alike; regression test
  `test_verdict_flip_in_rehashed_bundle_is_detected`). After the
  fix, case A is detected ("verdicts.json does not match the
  ledger's verdict.issued events"), honest replay is unchanged,
  and all four pre-existing Phase 5 demo bundles still verify under
  the strengthened verifier. The deposited bundle is unaffected —
  the fix is verifier-side; bundle-v2 verifies under the new
  verifier exactly as exported.

**K2: pass** — with the sequence disclosed: found by the K2 tamper
case, fixed, regression-tested, re-verified.

### 2.3 K3 — fresh-context audit of the bundle alone

A fresh-context reviewer (a subagent with no prior exposure to this
program) received **only** the exported bundle-v2 directory and the
standalone verifier command — no live store, no repository, no
corpus document. It was asked to reach, per claim: statement +
falsifier, verdict + interval + reason, evidence items + origin
groups + sufficiency floor, each citation's identity and pipeline
outcome, exclusions and their reasons — and to run the verifier and
identify the bundle's external anchor.

- **Elapsed: ~18 minutes for all five questions** (the auditor's
  own timestamps span 1,085 seconds from first read to final
  report) — against the G3 budget of 2 hours per question
  (10 hours total), the audit consumed ~3% of budget.
- **Completeness: 5 of 5 claims fully retraced** — every element
  (falsifier, verdict, evidence, groups vs floor, citation
  outcomes, exclusions) reached from the bundle alone, nothing
  inferred. The run outcome was located in `verdicts.json`
  (`run_outcome`) and corroborated against the ledger, coverage,
  and README. The verifier returned **ok (exit 0)**. The anchor
  receipt (DOI 10.5281/zenodo.23319126, root, bundle hash) and the
  freeze root were cross-checked inside the bundle
  (receipt ↔ `registration.json` committed root ↔ the ledger's
  `study.frozen` → checkpoint chain).
- **Friction, reported by the auditor and confirmed on read-back**
  (the substantive items are also §4.7–4.9):
  (1) **No control outcomes exist in the bundle.** `controls.json`
  carries the three control *definitions*; `verdicts.json` states
  `controls_replayed: []`; no file records a control's result —
  yet the positive/negative control rationales say the Q1/Q4
  verdicts are meaningless if the controls fail. That a valid run
  *implies* the controls passed is true only via the engine's
  rules, which the bundle does not state: from the artifact alone,
  an auditor cannot determine whether any control ever ran.
  (2) **CLM-E-004's falsifier flag contradicts its registration.**
  The claim's falsifier names Wandel 2010's conclusion as *the*
  falsifying observation, and CIT-E-401 (that paper) contradicts —
  but its evidence item records `falsifier_observation: false`,
  and the verdict fired via the interval path, not the falsifier
  path. The registration's language overclaims the mechanism; the
  verdict itself is sound (§4.8).
  (3) **The anchor binds bundle-v1, not bundle-v2** (§6): v2 is
  checkable against the public record only through its carried
  receipt, registration hash, and pre-anchor checkpoint root —
  v2's own bundle hash is anchored nowhere.
  (4) **No retrieved content at all**: `evidence/content/` is
  empty and all nine retrieved records are provenance stubs
  (WS5 rights gate), so no stance can be re-derived from the
  bundle alone — stage 3's labels must be taken on the pipeline's
  word by an offline auditor.
  (5) **The as-cited forms of citations are absent** — only
  resolved records and mismatch field *names* are carried, so the
  fabricated DOI itself and CIT-E-202's corrupted fields cannot
  be re-inspected, only the adjudicators' rationales.
  (6) Excluded citations vanish from the evidence files without a
  marker (recoverable only by cross-referencing
  `verification.json`/`adjudication.json`); `claims.json` still
  shows every claim `status: "proposed"`; CIT-E-302's outcome is
  `metadata_only` in one file and stance `contextual` in another,
  with no stated mapping; the second-review aggregate does not
  name its target (it was the ADQ-003 grouping decision — no
  quarantine decision was second-reviewed).
  (7) The auditor **caught a corpus blemish the pipeline did
  not**: CIT-E-401's citation names the Wandel paper's first
  author as "Peter Wandel"; the record's author is Simon Wandel
  (the citation conflated him with co-author Peter Jüni).
  Identification was unaffected — DOI, surname, title, year, and
  venue all exact, and stage 2 compares surnames — but the
  registered citation's given name is wrong, and this report is
  the correction of record. A fresh pair of eyes on the bundle
  earned its keep.

**K3: pass** — a reviewer reached every verdict's evidence and
falsifier from the bundle alone, in ~18 minutes against a
10-hour budget. The pass is on reachability and completeness;
the friction above — controls, falsifier flag, anchor scope,
absent content — is the bundle's honest limit list, and items
(1)–(3) are machinery findings, not auditor error. (This executed
pass is also the K3 protocol whose existence Spec 001's NC-5 was
waiting for — §8.)

### 2.4 K4 — derivative-source inflation

Derivative folding, from `evidence/groups.json` and the register
fold (identical):

- The duplicate citation pair (CIT-E-101 by DOI + CIT-E-102 by
  search) forms **one** origin group (EVG-001, 2 items) — grouping
  key 1 (shared source identity).
- The Framingham pair (CIT-E-501/502, shared `dataset_id`) forms
  **one** origin group (EVG-008, 2 items) — grouping key 2.
- Totals: 8 evidence items in **6** origin groups; no artifact in
  the bundle states a larger independent-evidence count for any
  claim than its group count (the HUMAN-README directs auditors to
  `evidence/groups.json` for exactly this).
- The fold is visible in a verdict, as designed: CLM-E-005's
  sufficiency floor of 2 is **not met by its single folded group**,
  yielding inconclusive-by-floor (§3). Had folding failed, the
  claim would have shown 2 groups and (with support 0.8) cleared
  to supported — the inflation K4 exists to prevent.

**K4: pass.**

### 2.5 K5 — marginal cost per question

Priced from the frozen ledger's own records (queries.json +
citation outcomes), at the provider's published rates (OpenAlex
Help Center, "Example costs", updated 2026-10-09: singleton lookup
$0, list/filter $0.0001, search $0.001; the connector's `search()`
issues a `title_and_abstract.search` filter and is priced at the
search rate):

| Call | Count | Rate | Cost |
|---|---|---|---|
| OpenAlex searches (5 question queries + 1 duplicate-citation resolution search) | 6 | $0.001 | $0.0060 |
| OpenAlex singleton lookups (9 DOI resolutions, incl. the fabricated DOI's failed lookup) | 9 | $0 | $0 |
| Crossref (5 queries + 1 fallback resolution) | 6 | $0 (polite pool, no charge) | $0 |
| Compute | local VM, existing infrastructure (G4) | — | $0 marginal |

**Total marginal cost $0.006 for 5 questions = $0.0012 per
question, against the $25 ceiling (G3) — a pass by a factor of
~20,000.** Corroboration: the connector's internal CreditBudget
counted 14 units for the run (its units are budget units, not
dollars; the one-unit difference from the 15-call table is the
failed fabricated-DOI lookup, which the connector does not
charge). Even under the most hostile accounting — every OpenAlex
call priced at the search rate — the total is $0.015 ($0.003 per
question). Assembly probes and one aborted pre-freeze driver
attempt (§7) spent roughly another $0.01 of API calls in total;
they are corpus assembly, not the frozen run, and are disclosed
here for completeness.

**K5: pass.**

## 3. Verdicts vs the pre-registered predictions

All five verdicts match the predictions recorded in `corpus.md`
before the freeze, each by its pre-registered mechanism:

| Claim | Verdict | Mechanism (as it fired) |
|---|---|---|
| CLM-E-001 (CBT-I) | **supported** | 1 group (Trauer, duplicate folded in), support 0.8, interval (0.6, 1.0) clears margin 0.1; fabricated citation excluded pre-evidence |
| CLM-E-002 (meditation) | **supported** | Goyal's group alone (support 0.8, interval (0.6, 1.0)); corrupted citation excluded pre-evidence |
| CLM-E-003 (exercise) | **inconclusive** | Interval dilution: Cooney's checked supporting group (0.8) averaged with Schuch's metadata-only group (no abstract at either connector — ignorance mass) → interval (−0.2, 1.0) straddles the margin |
| CLM-E-004 (glucosamine) | **contradicted** | Wandel 2010's conclusion negates the proposition with full key-term overlap → contradiction 0.8, interval (−1.0, −0.6) clears −margin |
| CLM-E-005 (Framingham) | **inconclusive** | Below sufficiency floor: the dataset fold leaves 1 group against a registered floor of 2 |

Controls: positive (supported), negative (contradicted), swap
(actor exchange 'researcher'/'adjudicator' on the multi-actor
ledger, detected by the production verifier) — all behaved;
`evaluate_run` reported no control failures.

### 3.3 Adjudication record

ADQ-001 (CIT-E-103, resolution failed) → **exclude**;
ADQ-002 (CIT-E-202, disagreement authors/year) → **exclude**;
ADQ-003 (grouping suspect CIT-E-101+CIT-E-103) → **separate_origin**;
ADQ-004 (grouping suspect CIT-E-102+CIT-E-103) → **separate_origin**.
The grouping suspects were **not predicted** in `corpus.md` (the
companion expected none): the suspect rule pairs citations on
title/surname fingerprints across different origin groups without
filtering unresolved citations, so the fabricated citation was
paired with both of its real namesakes. The decisions are honest
(a nonexistent work shares an origin with nothing), but the rule's
behaviour is recorded here as a machinery observation: on a corpus
with many fabrications, the queue would fill with trivial
separate-origin pairs. Second review sampled ADQ-003 (§1).

## 4. Machinery findings (the negatives and the brittle parts)

1. **Verifier projection cross-check compared counts, not
   payloads** — found by K2 tamper case A, fixed in-phase (§2.2).
   The most consequential finding of the evaluation.
2. **The lexical stance checker is brittle at sentence level.**
   During assembly, Trauer's abstract scored *contradicts* for a
   short proposition because a background sentence ("…benefits
   without the risk for tolerance…") cleared the key-term bar and
   carried a negation token, outweighing the conclusion sentence.
   Propositions written as the sources' own conclusion sentences
   (this corpus's rule) avoid the trap, but the checker's
   precision limit is real: it is a *checked*-stage instrument,
   and a subtler fabrication (real DOI, mis-stated finding) would
   stress exactly this weakness.
3. **The grouping-suspect rule does not filter unresolved
   citations** (§3.3) — queue noise, honestly decidable, worth a
   future filter.
4. **Metadata-only records dilute intervals by design** (RT-5):
   CLM-E-003's inconclusive is the machinery working as ratified,
   but users should understand that attaching an unchecked record
   to a claim *lowers* its standing even when the record agrees
   bibliographically — ignorance is priced, visibly.
5. **Connector budget units ≠ provider dollars** (§2.5): the
   CreditBudget counts a failed lookup as free and a search as one
   unit; K5 accounting must price from the provider's published
   rates, as done here, not from the unit count.
6. **A registered citation carried a wrong author given name**
   (CIT-E-401, §2.3): stage 2's surname-level agreement cannot see
   given-name errors. The citation identified its paper exactly by
   every checked field; the blemish is the corpus author's, caught
   by the K3 auditor, and stands corrected here — the frozen
   registration itself is not rewritten (DN-005).
7. **Control outcomes are not recorded anywhere in the bundle**
   (K3 friction 1). Control evaluation is ephemeral in the engine:
   `run_controls` returns failures into the run evaluation, and a
   valid run silently implies success. For an artifact whose
   control rationales tell auditors the verdicts depend on the
   controls, the bundle should carry per-control outcomes (and the
   `run_outcome` projection should not state `controls_replayed:
   []` for a run whose controls were in fact executed at verdict
   time). Candidate fix for a future spec: record control results
   in the run projection from `evaluate_run`'s own execution.
8. **The falsifier-observation path is unreachable from real
   pipeline evidence** (K3 friction 2). `to_evidence_item` never
   sets `falsifier_observation`, so a corpus citation whose
   content *is* the registered falsifying observation still enters
   as ordinary contradicting mass and the verdict fires via the
   interval path. CLM-E-004's registration text ("the registered
   falsifying observation is the Wandel 2010 conclusion") was
   written as if the falsifier path would fire; it did not, and
   the CONTRADICTED verdict rests on the interval (−1.0, −0.6)
   alone. The outcome is unaffected; the mechanism attribution
   in the frozen registration is imprecise, and the gap between
   "the falsifier fired" and "the interval contradicted" should
   either be closed in the conversion (a contradicting content
   check against a claim whose falsifier names that observation)
   or the registration language should stop implying it.
9. **Bundle-v2's own hash is anchored nowhere** (K3 friction 3):
   the DN-005 pattern anchors the pre-anchor bundle (v1) and the
   post-anchor bundle (v2) carries the receipt. An auditor can
   verify v2's *contents* standalone and its *registration*
   against the public record, but v2 as an artifact is
   self-attested. Phase 6's records noted the same v1/v2 split;
   the evaluation confirms it from a fresh reader's side.

## 5. The Phase 7 preparation fixes (context for this run)

Two fixes landed before the freeze, as their own commits, and the
evaluation ran on top of them: **(a)** the swap control's event
selection (Phase 5's fixed lines-1/2 exchange was a no-op whenever
those actors matched — the demo study's INVALID): the control now
exchanges the first distinct-actor pair, or rewrites the first
event's actor to a probe actor on single-actor ledgers; regression
tests pin the defect mechanism itself, and the demo ledger
re-derives honestly (the fixed control detects on it; the
historical INVALID stands as issued). **(b)** The exporter
run-outcome projection (audit NC-6): `verdicts.json` now carries
`run_outcome`; this study's bundle states `valid` in-bundle, and
seeded forgeries of the outcome fail the standalone verifier. All
four Phase 5 demo bundles still verify unchanged.

## 6. Deposit

Bundle-v1 was deposited to Zenodo under the standing G4 pattern
after the run evaluated valid and the bundle verified standalone.
The approval is the study's own registered step: a
`deposit.approved` ledger event by the **adjudicator** actor,
naming the basis (valid run; standalone-verifying bundle; owner's
standing G4 authorization). Receipt: **DOI 10.5281/zenodo.23319126**
(concept DOI 10.5281/zenodo.23319125), bundle hash
`296786be0f31d212435b64c89f685a9c14b31cff6f36b6c603e41d05c21b10c2`,
anchoring the freeze root in §0. The anchor was recorded in the
ledger, the study re-checkpointed, bundle-v2 exported (it carries
the receipt), and `verify_anchor` confirms bundle-v2's carried
receipt and registration against the independently fetched public
record. Precisely (K3 friction 3, §4.9): the anchored values are
bundle-v1's hash and the freeze checkpoint root; bundle-v2's own
bundle hash is not itself anchored.

## 7. Execution honesty (driver history)

The frozen record was produced by `run_evaluation.py` on its fifth
execution. Attempts 1–3 died on driver API mismatches before or at
study creation (wrong import locations, a register method name) —
no study state. Attempt 4 completed the live pipeline and died on
the adjudication queue's payload shape (grouping items carry a
citation pair, not a single citation id) — pre-freeze, discarded;
its API spend is disclosed in §2.5. Attempt 5 ran the full study —
freeze, verdicts, export, standalone verification — and stopped in
the deposit leg on the same class of driver bug (a store method
that does not exist); `resume_deposit.py` performed only the
remaining post-run steps (approval, deposit, anchor, v2 export,
anchor verification), rebuilding its state from bundle-v1. No
attempt altered any frozen artifact, and the sequence is recorded
here rather than smoothed over.

## 8. Follow-ups named for the coordinator

- **NC-5 (Spec 001)**: F-001-D6's falsifier was inoperable "until a
  K3 protocol exists". This evaluation *is* a K3 protocol, executed
  (§2.3) — the Spec 001 claim set can now be re-assessed against it;
  that bundle is outside Phase 7's file scope and is left as a
  coordinator item.
- The grouping-suspect unresolved-filter (§4.3) and the stance
  checker's sentence-negation weighting (§4.2) are candidate
  machinery improvements for a future spec, not Phase 7 scope.
- CLM-002-10's stage is **checked**. Its path to *accepted* runs
  through an external party's hands (a pilot site's reviewers
  re-running K1 on their own corpus) — the pilot workstream owns
  that lane.
