# Phase 6 (T219) — wireframe conformance record

How the shipped UI was verified against the approved wireframe
package (`docs/wireframes/`, DN-009, constitution Article XIV), and
every place the production rendering interprets the wireframes'
sample content. Screenshots are the evidence: the production
screens were captured with Playwright at 1440×900 and 390×844
against the running app (localhost), seeded with a **copy** of the
Phase 5 demo study (the original in the Phase 5 demo workspace was
never mutated), and compared screen-by-screen with
`docs/wireframes/screens/`. The capture workspace and screenshots
are retained with the work records.

Seed: study `ar1-demo-1905` — demo ledger copy (20 events, incl. the
stage-model audit stage assignments and the v3 re-anchor), meta title as in
the wireframes, freeze sidecar = the frozen registration document
from bundle-v2 (`registration_hash` re-verified against the
ledger's `study.frozen` event), retrieved/citation sidecars from
the demo record, bundle-v1 held as an export, the v1 public record
held for anchor verification, RT-4 seed chosen so the deterministic
draw reproduces the demo's own sampling outcome (ADQ-001 sampled
and reviewed; ADQ-002 not sampled). Before capture, one **fresh
export was produced through the UI itself**, so screen (f) shows a
UI-produced current bundle.

The production stylesheet is the wireframes' `style.css` adopted
byte-identical (`src/tekmerion/ui/style.css`); no CSS was added.
Wireframe `.note` footers (documentation *about* the wireframes)
are correctly absent in production.

## Per-screen verdicts

### (a) Claim register — MATCH
Same shell, banner, stats, table, chips. Differences, all in text
the wireframes carry as illustration: the INVALID banner's reason
is the engine's verbatim replayed reason (`swap control failed:
provenance swap NOT detected by production verification`, mono,
per WIREFRAMES.md §4) instead of the wireframe's sample sentence;
the falsifier renders **ledger-verbatim** (lowercase, as registered)
instead of the wireframe's capitalized rendering; the sidebar
actor note is the production SSO wording. The INVALID state itself
is not seeded data: it is replayed from the record by
`evaluate_run` (see "Run presentation" below).

### (b) Register a claim, refused state — MATCH
Captured by actually submitting the form with the falsifier empty:
the engine's `RegistrationError` verbatim in the refusal banner,
submitted values intact, the falsifier field in its
`required-missing` state, and nothing appended to the ledger
(asserted in tests). The identity survives the POST via the
identity cookie (the browser stand-in for the SSO header), so the
form still acts as `researcher`.

### (c) Claim detail — MATCH, with one documented extension
Header, falsifier card, evidence-group card, citations table, and
retrieved-record card match; disposition chips use the wireframe's
own labels (`variant`, `excluded`). Below the wireframe's fold, the
production screen carries the **working forms** the wireframe's two
buttons (`Attach a citation`, `Withdraw claim (marks it dead)`)
anchor to — the wireframe depicts the buttons, not the forms; the
forms are built only from depicted field components. CIT-2's
cited-as line omits an author surname the wireframe shows, because
the citation as actually registered carries no authors; the record
governs.

### (d) Adjudication queue — MATCH
Stats, decided cards (verbatim rationales from the ledger),
second-review line, and the RT-4 sampling card all render from
`queue_state` / `second_review_report`. The wireframe's
trailing full stop inside quoted rationales is the wireframe's;
the ledger's text has none and is shown verbatim.

### (e) Freeze & verdicts — MATCH
Two-card layout (Registration / Controls) as rendered in the
approved screenshots, `study.frozen · seq 10`, full hashes,
"none — disclosed explicitly (RT-3)", the INVALID block with the
engine's reason on the **Why:** line, the empty verdict table with
the wireframe's own text, and the taxonomy legend with inline
chips. The block's second paragraph is the generic Article VI text
(the wireframe's is the demo study's defect narrative — sample
content, not template). An adjudicator-only **Run evaluation**
button appears under the block: a functional control the wireframe
does not depict, built from the depicted primary-button component;
without it a frozen study could never be run from the UI at all.

### (f) Export & anchor — MATCH, with value drift (record moved on)
Card structure, PASS rows, deposit card, and verify card match.
Values differ from the wireframe **because the record advanced**:
the current export is a fresh UI export of the 20-event ledger
(bundle-002; 20 events, head root `8d1e09f2…aa1cb`, post-anchor),
and **two** anchor receipts are shown — the AR-1 v1 receipt
(10.5281/zenodo.23311479, with its verify-vs-public-record PASS,
computed live by `verify_anchor` from the held bundle-v2-successor
export that carries the receipt) and the stage-model audit v3 re-anchor
(10.5281/zenodo.23317023, for which the workspace holds no public
record, so no verify row is shown). The v1 verify row pairs the
receipt with a bundle that *contains* it: the anchored bundle
itself predates its own receipt, per the wireframe's own note.

### (g) Component specimens — MATCH
Rendered at `/specimens` from the same production components,
labeled "Design specimens — component states, not study data":
badge legend, dead-row specimen, valid-run banner, pending
decision control (non-functional by construction — it renders the
control only), 40% coverage meter, WS6 §1 role table.

## Documented interpretations (no appearance invented)

- **Run presentation.** Verdicts, once issued, are events and are
  shown from them. Before any run is issued, the workspace replays
  the run through `evaluate_run` itself — chain state from the
  production verifier, the WS3 structural checks, the swap control.
  An INVALID replay renders as INVALID with the engine's reasons;
  this reproduces the demo study's recorded INVALID from the
  record alone. **Limitation:** positive/negative known-answer
  controls execute in a replay only when the workspace holds
  their evaluation fixture (the registration document persists
  only the four registered control fields); the swap control
  always executes. Verdict *issuance* (the Run button) uses the
  same path.
- **Deposit approval** lives inside the anchor receipt
  (`approved_by`, the existing event vocabulary — no new event
  type). The wireframe's "three separate ledger events" phrasing
  is honored in substance: approval, deposit, and receipt are
  separate acts by named identities; the approval is recorded in
  the receipt event rather than as a distinct event type, because
  the engine's vocabulary has none and inventing one at the UI
  layer would fork the record format.
- **"Request deposit approval"** (researcher view) is a role-view
  link to the adjudicator view of the same page, where approval
  and deposit happen — the only non-mutating reading of the
  wireframe's button in a workspace with no notification channel.
- **Study index** at `/` (study list + create) precedes any study;
  CLM-002-31 governs opening a *study* (register first), and the
  index is a workspace surface reusing shell/card components.
- **Dead-claim rows** in the 6-column register table carry the
  specimen's four elements across the table's columns: DEAD chip +
  struck statement + `dead · reason: "…"` in the status cell, and
  score `0.0` in the verdict cell.
- **Freeze form** (unfrozen studies) and the **attach/withdraw
  forms** extend depicted components only (fields, cards, buttons
  as specified); no new visual element was introduced anywhere.
  Had one been needed, Article XIV would have required stopping
  for a wireframe change — none was.

## Behavioral evidence

`tests/test_phase6_ui.py` — 15 tests through the real HTTP surface
against the production services, keyed to CLM-002-31…40 (refusals
append nothing; the full flow's event sequence equals the API
path's; INVALID and dead states from real fixtures; role matrix
enforced server-side; tampered bundle fails verification; the
demo study's receipts render from the record). Full suite:
97 passed locally at capture time.
