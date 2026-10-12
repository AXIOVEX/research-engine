# Red-Team Pass 01 — Architecture Drafts v0.1

**Date:** 2026-10-11 · **Scope:** WS1–WS6 v0.1, spec 001, constitution v1.0.0
**Method:** adversarial self-review hunting the four defect classes the constitution exists to prevent: (a) controls that cannot fail, (b) derivative evidence inflation, (c) silent record rewriting, (d) unverified citations entering the record. Findings are claims; each carries the section that must change.

## Findings

### RT-1 (critical, class a) — Swap control can be vacuous
WS3's swap control runs on a *test copy* of a run. If the test copy's verification path differs from the production replay path (different code, different build), the control passes while production verification is broken — a control that cannot fail where it matters.
**Fix:** WS3 amended — controls must execute through the *same* verification code path as production replay, on the production build; the control record names the build/version it exercised.

### RT-2 (critical, class c) — Hash chain forks under concurrent writers
WS4 specifies a per-study hash chain but no sequencing authority. Institutional use is multi-user; two adjudicators appending concurrently can fork the chain, and "the log wins" (WS4 §1) is undefined for two logs.
**Fix:** WS4 amended — each study log has a single sequencing point (all appends serialize through it); a detected fork renders the study record INVALID until resolved by an appended adjudication event that selects the surviving chain and preserves the forked branch in the record. Forking is never silently merged.

### RT-3 (high, class a/d) — Exploration can launder HARKing
WS3's exploratory/confirmation wall stops *relabeling*, but a researcher can explore until a design yields the wanted answer, then register exactly that design as "confirmation." The freeze is honest; the selection is not.
**Fix:** WS3/WS5 amended — a confirmation registration must disclose linked exploratory studies on the same question (they exist in the record anyway); the bundle carries the disclosure. Reviewers can then judge selection effects with the exploration history in front of them. The engine cannot prevent motivated design choice; it can — and must — refuse to hide it.

### RT-4 (high, class b) — DOI-less evidence has a weak dedup path
WS1 dedups by DOI first; books, reports, preprints, and archival items often lack DOIs, and WS2's grouping key 4 (near-duplicate + fingerprint) routes to human adjudication — but at review scale, adjudication queues become rubber stamps, re-opening derivative inflation through the manual path.
**Fix:** WS1/WS2 amended — grouping adjudications are sampled for second review (a registered fraction, default 10%), and the sample's disagreement rate is reported in the bundle. A rubber-stamp queue then shows up as a measured ~0% disagreement, which is itself a flagged anomaly (a check that never disagrees is treated like a control that never fails).

### RT-5 (medium, class d) — Metadata-only cap is stated but not mechanized
WS5 §1.3 caps the weight of `metadata-only` items "by rule" without stating the rule.
**Fix:** WS5 amended — the rule: a claim whose entire supporting basis is metadata-only caps at INCONCLUSIVE, and any single metadata-only item contributes no support mass, only context. Mechanized in the verdict function, not left as guidance.

### RT-6 (medium, class a) — Positive control can be gamed by scope
A positive control chosen inside an easy region of the search space passes while retrieval fails on the study's actual, harder region.
**Fix:** WS3 amended — positive controls are drawn from the study's own domain and difficulty class, and the freeze check requires the control's selection rationale to name why it is representative. Controls the author picked *because* they pass are a named abuse case in WS5.

## Accepted risks (recorded, not fixed)

- **AR-1** Hash-chain head authenticity depends on external anchoring (WS4 §2 states this). Accepted for design phase; MVP must implement at least one anchor (deposit or institutional timestamp) before any institutional pilot — added to spec 001 tasks as a gate on the implementation spec.
- **AR-2** Entrenchment orders declared at registration (WS2 §4) can themselves be gamed at design time. Accepted: the order is frozen, disclosed, and adjudicated — visibility is the mitigation the product can honestly offer.

## Outcome

6 findings: 2 critical, 2 high, 2 medium — all fixed by amendment in the same pass (amendments are visible in git history, per Article IV's spirit: drafts evolve in the open, frozen records never do). 2 accepted risks recorded with a hard gate on AR-1. Spec 001 SC-1 is satisfied for pass 01; a second red-team pass is required after the WS1 registry facts and WS6 competitor appendix are finalized, because those sections were still in draft-research state during this pass.
