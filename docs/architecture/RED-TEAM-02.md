# Red-Team Pass 02 — After WS1 Appendix A + WS6 Appendix Finalization

**Date:** 2026-10-11 · **Scope:** changes since pass 01 — verified source registry (WS1 App. A), competitor appendix (WS6), license_basis schema amendment (WS2). Same four defect classes, plus a fifth this pass: (e) *legal/operational assumptions that fail at deployment.*

## Findings

### RT2-1 (high, class e) — BASE may be legally unavailable to the hosted product
Appendix A records BASE access as framed for **non-commercial** projects, IP-whitelisted after application. Axiovex's hosted offering is commercial; the connector could be refused or, worse, used out of terms.
**Fix:** WS1 amended — BASE status is **conditional**: excluded from the hosted deployment's connector set until terms for commercial use are confirmed in writing; institution-local deployments evaluate eligibility on their own (non-commercial) status. The registry records eligibility *per deployment shape*, not per source alone — this generalizes: rights entries gain a deployment-shape dimension.

### RT2-2 (high, class a/c) — Credit exhaustion can silently truncate a run
OpenAlex is credit-metered (App. A). A run that exhausts its credit budget mid-retrieval returns a partial evidence set; if the run proceeds, verdicts rest on silently truncated evidence — the Elicit failure mode (incomplete retrieval presented as complete) entering through the billing layer.
**Fix:** WS1/WS3 amended — the freeze check includes a **budget reservation**: estimated connector cost for the registered query plan is computed and reserved at freeze; a run that hits a hard budget/rate ceiling **aborts to INVALID with reason `budget-exhausted`** rather than completing on partial evidence, unless the registration itself pre-declared a degraded-source contingency (in which case affected claims cap at INCONCLUSIVE, WS1 §5). Partial evidence is never silent.

### RT2-3 (medium, class d) — Support-check coverage is bounded by full-text access, unevenly across fields
WS5 stage 3 (support verification) needs content. CORE coverage and paywall patterns differ by discipline; a field with poor OA coverage gets systematically more `metadata-only` caps — honest, but it means verdict strength correlates with a field's publishing economics, not just its evidence.
**Fix:** no mechanism change (the ignorance reporting in WS5 §2 is the honest answer); WS5 amended to require the bundle to report support-check coverage per claim explicitly, so the correlation is visible to adjudicators rather than buried in per-item flags.

### RT2-4 (medium, opportunity recorded as requirement candidate) — Retraction surveillance of delivered bundles
The competitor pass found no incumbent monitors *already-delivered* verdicts for later retractions/corrections of their sources (Scite's Reference Check is manuscript-level, pre-publication). WS5 OQ-5.1 left the notification duty open. Given the gap, this is promoted from open question to a **recorded post-MVP requirement candidate**: delivered bundles register their evidence DOIs for periodic re-check against Crossref/retraction signals; a hit appends a `verdict.flagged` event and notifies the adjudicator of record. It does not change any verdict automatically — revisits remain human-adjudicated. Final scoping belongs to the implementation spec; the design records the intent and the reason (it is the "living review" the ledger theory already motivates).

## Checked and held

- **Non-repeatable search (Elicit's documented failure):** WS1 §4 already separates the reproducible query from the hash-pinned result set and reports drift. Held — this is a designed answer, and K-criteria for the MVP evaluation should include a repeat-run drift measurement (noted for the evaluation registration, not added as a new kill criterion without owner input).
- **Vote counting (Consensus Meter):** WS2 origin-group weighting + WS3 interval/margin verdicts are the structural opposite. Held.
- **Fabricated markers under empty retrieval (Perplexity):** FR-005 + WS5 stage 1 make an unresolvable citation run-failing, and INCONCLUSIVE exists precisely as the abstention incumbents lack. Held.

## Outcome

4 findings: 2 high fixed by amendment (BASE eligibility per deployment shape; freeze-time budget reservation with INVALID-on-exhaustion), 1 medium fixed by reporting requirement, 1 promoted to a recorded requirement candidate. With pass 01, Spec 001 **SC-1 is now satisfied for the design as a whole**: all six workstreams are final-draft, internally consistent, and red-teamed twice. Remaining gates are the owner's: OD-1 (MVP slice), OD-2 (deployment shape), OD-5 thresholds.
