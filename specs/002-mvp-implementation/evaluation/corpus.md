# Spec 002 Phase 7 — Evaluation corpus (registration companion)

**Status**: pre-freeze design record, 2026-10-12. This document is the
evaluation study's registration companion: the corpus design, the seeded
defects, the adjudication decisions, and the **predicted outcomes —
recorded before the freeze** — that the run is scored against in
`EVALUATION-REPORT.md`. If the run disagrees with a prediction, the
report says so and names the mechanism; predictions are not edited
after the freeze.

The study is executed by `run_evaluation.py` in this directory through
the production machinery only (connectors, verification pipeline,
freeze, verdict engine, exporter, deposit). One operator plays all
four actors — `researcher`, `adjudicator`, `second-reviewer`,
`verdict-service` — as in the Phase 5 demonstration; the report states
this plainly wherever independence matters (RT-4 especially).

## Pipeline configuration (decided at assembly, with evidence)

- **Connector order for resolution: OpenAlex first, Crossref second.**
  Assembly probes (2026-10-12, throwaway stores) showed Crossref
  resolves these records but carries no abstracts for them (its
  licence screen drops abstracts it cannot assert rights over), so
  with Crossref first every citation lands `metadata_only` and
  stage 3 (content check) never runs on real data. OpenAlex carries
  licence-screened abstracts for the same records. Crossref remains a
  full participant: every question is queried on both connectors
  (logged), and Crossref is the resolution fallback. This ordering is
  a property of this study's registration, not a code change.
- **Deployment shape: hosted.** Every retrieved record in the final
  corpus reports `hosted_ok` (no licence in the corpus asserts an
  NC-style restriction), so the freeze's hosted check has nothing to
  block; the check still runs.
- **Freeze mode: confirmation**, `linked_exploratory=[]` stated
  explicitly (G1 hygiene: an argued empty, not a default).
- **Adjudication sample**: RT-4 fraction 0.10, seed 7.

## The five evidence questions and claims

Margins 0.1 throughout (the register default the phases have used).

| Claim | Statement | Falsifier (as registered) | Floor |
|---|---|---|---|
| CLM-E-001 | Cognitive behavioral therapy for insomnia (CBT-I) is an effective treatment for adults with chronic insomnia | A source-of-record synthesis of CBT-I trials finds no clinically meaningful improvement in sleep outcomes, or the cited records do not exist or do not say this | 1 |
| CLM-E-002 | Meditation programs produce small-to-moderate reductions in anxiety and depression symptoms | The cited synthesis finds no improvement in anxiety or depression, or the cited records do not exist or do not say this | 1 |
| CLM-E-003 | Exercise reduces symptoms of depression in adults | The cited syntheses find no reduction in depressive symptoms, or the cited records do not exist or do not say this | 1 |
| CLM-E-004 | Glucosamine reduces joint pain in patients with osteoarthritis of the hip or knee | A large-scale synthesis finds glucosamine does not reduce joint pain versus placebo — the registered falsifying observation is the Wandel 2010 network meta-analysis's conclusion | 1 |
| CLM-E-005 | Risk-factor models derived from the Framingham Heart Study predict coronary heart disease risk | The Framingham records do not exist, or do not describe predictive risk-factor models | **2** |

CLM-E-005's floor of 2 is deliberate: its two citations share one
dataset (below), so if derivative folding works the claim has exactly
**one** independent origin group and the floor must bite — K4 made
visible in a verdict, not only in a count.

## Citations (11) — fields as the sources of record state them

Assembly rule: clean citations carry the bibliographic fields exactly
as the resolving source of record states them (titles without added
subtitles — a subtitle the record does not carry fails the agreement
check, as an early probe demonstrated). Propositions are the findings
attributed to each source, written from the sources' own conclusion
sentences (stage 3 checks the proposition against the abstract).

| ID | Claim | Citation | Proposition | Dataset |
|---|---|---|---|---|
| CIT-E-101 | E-001 | Trauer et al. 2015, *Ann Intern Med*, DOI 10.7326/M14-2841 | "CBT-i is an effective treatment for adults with chronic insomnia, with clinically meaningful effect sizes" | — |
| CIT-E-102 | E-001 | Trauer et al. 2015, *Ann Intern Med*, **no DOI** (title/author/year/venue only) | same as CIT-E-101 | — |
| CIT-E-103 | E-001 | Trauer et al. 2015, *Ann Intern Med*, DOI **10.7326/M14-9999** | same as CIT-E-101 | — |
| CIT-E-201 | E-002 | Goyal et al. 2014, *JAMA Intern Med*, DOI 10.1001/jamainternmed.2013.13018 | "Meditation programs improve anxiety and depression symptoms" | — |
| CIT-E-202 | E-002 | "Khouri" et al. **2019**, *Clin Psychol Rev*, DOI 10.1016/j.cpr.2013.05.005 | "Mindfulness-based therapy reduces symptoms of anxiety and depression" | — |
| CIT-E-301 | E-003 | Cooney et al. 2013, *Cochrane Database Syst Rev*, DOI 10.1002/14651858.CD004366.pub6 | "Exercise reduces symptoms of depression" | — |
| CIT-E-302 | E-003 | Schuch et al. 2016, *J Psychiatr Res*, DOI 10.1016/j.jpsychires.2016.02.023 | "Exercise is an effective treatment for reducing depressive symptoms" | — |
| CIT-E-401 | E-004 | Wandel et al. 2010, *BMJ*, DOI 10.1136/bmj.c4675 | "Glucosamine reduces joint pain compared with placebo" | — |
| CIT-E-501 | E-005 | Wilson et al. 1998, *Circulation*, DOI 10.1161/01.CIR.97.18.1837 | "Risk factor models from the Framingham Heart Study predict coronary heart disease risk" | framingham-heart-study |
| CIT-E-502 | E-005 | D'Agostino et al. 2008, *Circulation*, DOI 10.1161/CIRCULATIONAHA.107.699579 | "A general cardiovascular risk profile from the Framingham Heart Study predicts cardiovascular disease" | framingham-heart-study |

## Seeded defects (the evaluation's teeth)

1. **Fabricated citation** — CIT-E-103's DOI (10.7326/M14-9999) does
   not exist. Assembly probes confirmed both connectors return
   not-found for it. It tests K1's catch-and-exclude path: it must be
   accounted `not_found`, quarantined, adjudicated out, and contribute
   **zero** evidence.
2. **Corrupted citation** — CIT-E-202 names a real paper (Khoury et
   al.) through its real DOI but misstates the first author's surname
   ("Khouri") and the year (2019 vs the record's 2013). Stage 2 must
   flag the disagreement, quarantine it, and the adjudicator excludes
   it *as cited*: the citation as registered is not a faithful
   reference, even though the underlying work is real.
3. **Duplicate citation** — CIT-E-102 cites the Trauer paper without
   a DOI. It must resolve (by search) to the same work as CIT-E-101
   and fold into the same origin group by grouping key 1 (shared
   source identity), so Q1's evidence count is 1 group with 2 items —
   derivative inflation contained (K4).
4. **Shared dataset** — CIT-E-501/502 are two distinct Framingham
   papers sharing `dataset_id="framingham-heart-study"`: grouping
   key 2 must fold them into one origin group (K4, and CLM-E-005's
   floor interaction above).

## Controls (registered with the study; RT-6 rationales)

- **Positive control** (claim CLM-E-CTL-POS): "control: CBT-I improves
  sleep efficiency in chronic insomnia (known-answer: Trauer 2015's
  conclusion)". Synthetic supporting groups (2 groups, support 0.9).
  *Rationale*: a known-answer control in the evaluation's own lead
  domain (sleep interventions), with the evidence shape Q1's claim
  was expected to have — if the engine cannot affirm this, Q1's
  verdict means nothing.
- **Negative control** (claim CLM-E-CTL-NEG): "control: glucosamine
  reduces joint pain versus placebo (known-answer: Wandel 2010 found
  it does not)". Synthetic contradicting groups with a registered
  falsifier observation. *Rationale*: mirrors CLM-E-004's exact shape
  (a popular remedy claim a decisive synthesis refutes) — if the
  engine cannot contradict this, Q4's CONTRADICTED is suspect.
- **Swap control** (RT-1): the standard ledger actor-swap tamper, in
  its Phase 7 fixed form (first distinct-actor pair). *Rationale*:
  provenance forgery is this study's realistic tamper — a multi-actor
  ledger whose signatures bind actors to events.

## Pre-registered adjudication decisions

- CIT-E-103 (fabricated) → **exclude**: "DOI does not resolve at any
  source of record — fabricated; excluded from the evidence basis."
- CIT-E-202 (corrupted) → **exclude**: "As cited, the authorship and
  year misstate the record of the work the DOI identifies — a
  corrupted citation; excluded as cited."
- RT-4 second review: whichever decided item the seeded sample draws
  is reviewed on its merits (both decisions are verifiable from the
  bundle alone: the DOI's non-resolution and the record's true
  fields).

## Predicted outcomes (registered before the freeze)

From assembly probes through the production stages (throwaway
stores, 2026-10-12):

| Claim | Predicted pipeline facts | Predicted verdict (mechanism) |
|---|---|---|
| CLM-E-001 | 101 resolved/agree/supports; 102 resolved by search, folds into 101's group; 103 not_found → excluded | **supported** (1 group, support 0.8, interval (0.6, 1.0) clears margin) |
| CLM-E-002 | 201 resolved/agree/supports; 202 resolved but disagreement (authors, year) → excluded | **supported** (Goyal's group alone) |
| CLM-E-003 | 301 resolved/agree/supports; 302 resolved/agree/**metadata_only** (OpenAlex carries no abstract for Schuch 2016) | **inconclusive** (interval dilution: averaging a checked supporting group with an unchecked group straddles the margin — RT-5's ignorance mass made visible) |
| CLM-E-004 | 401 resolved/agree/**contradicts** (Wandel's conclusion sentence negates the proposition with full key-term overlap) | **contradicted** (interval (−1.0, −0.6) clears −margin) |
| CLM-E-005 | 501 supports, 502 contextual; both fold into ONE group (dataset key) | **inconclusive — below sufficiency floor** (1 group < floor 2; K4's fold is what makes the floor bite) |

Run predicted **valid**: no unverified evidence (both quarantined
citations excluded before evidence construction), chain intact,
controls pass (swap control exchanges 'researcher'/'adjudicator' —
the ledger's first distinct pair — and is detected).

**K predictions**: K1 pass (11/11 citations accounted; fabricated
caught and excluded, zero evidence contribution). K2 pass (bundle
replays to identical verdicts; tamper cases detected). K3 pass
expected (bundle carries claims, evidence, groups, verdicts, and —
new in Phase 7 — the run outcome in-bundle). K4 pass (no artifact
counts the Trauer pair or the Framingham pair as two groups). K5 pass
by orders of magnitude (below).

## K measurement protocols (as executed)

- **K1**: from the study ledger + bundle: every registered citation
  has exactly one `citation.checked` event; resolution outcomes
  tallied; the fabricated citation's evidence contribution is
  verified to be zero in `evidence/items.json`; CLM-002-10 is then
  assessed on this frozen evidence.
- **K2**: `replay_check.py` rebuilds the register from the exported
  bundle alone (claims, evidence items, groups), replays
  `evaluate_claim` per claim, and compares verdict, interval, and
  point estimate against `verdicts.json`; then three tamper cases on
  bundle copies (verdict-payload edit, ledger payload edit, outcome
  forgery — each with a rehashed manifest so only the semantic checks
  can catch them) must all be detected by `verify_bundle`.
- **K3**: a fresh-context reviewer (subagent) receives **only** the
  exported bundle directory and the standalone verifier command. For
  every claim it must reach: the claim + falsifier, the verdict, the
  evidence items and their origin groups, and each cited source's
  pipeline outcome. Budget: 2 hours per question × 5 questions =
  10 hours (G3). Elapsed wall-clock, per-claim completeness, and
  friction points are recorded in the report.
- **K4**: group counts compared across the register fold,
  `evidence/groups.json`, and the HUMAN-README: the Trauer pair = 1
  group (2 items), the Framingham pair = 1 group (2 items); no
  artifact states a larger independent-evidence count for any claim
  than its group count.
- **K5**: marginal cost per question = (OpenAlex calls priced at the
  provider's published rates — help.openalex.org "Example costs",
  updated 2026-10-09: singleton lookup $0, list/filter $0.0001,
  search $0.001 — with the connector's `search()` priced at the
  search rate because it issues a `title_and_abstract.search` filter)
  + Crossref ($0; polite pool, no charge) + compute ($0 marginal; the
  run executes on the existing local VM, no paid infrastructure, G4),
  divided by 5 questions, against the $25 ceiling (G3). The
  connector's internal budget units are reported alongside (they are
  budget units, not dollars).

## Assembly findings worth the record (pre-freeze)

- The lexical stance checker's sentence scan is brittle in a
  specific way: Trauer's abstract contains a background sentence
  ("…benefits **without** the risk for tolerance…") whose key-term
  overlap with a short proposition clears the hit bar, and its
  negation token flips the whole check to *contradicts* even though
  the conclusion sentence supports. Propositions written as the
  sources' own conclusion sentences (this corpus's rule) avoid the
  trap; the brittleness itself is recorded here as a machinery
  finding for the report (checker precision limit — a stage-3
  *checked* tool, not an oracle).
- Two candidate records carry no abstract at either connector in a
  usable form (Schuch 2016 via OpenAlex; Khoury 2013) — the corpus
  keeps Schuch deliberately: a real systematic-review corpus
  contains records whose content cannot be checked, and RT-5 exists
  precisely to keep them from counting as checked support.
