# Tao Realignment Audit — Tekmerion, all work through Phase 5

- **Date:** 2026-10-12
- **Standard:** DN-010 (Tao realignment doctrine: five lifecycle stages — created / checked / explained / accepted / digested; decomposition; digestion as tracked work; attribution as a claim; anti-gradability; two lanes; provenance; inspectable records).
- **Directive:** owner, 2026-10-12 (retroactive application; correct only by appending / reclassifying; label the unfixable as historical limitations).
- **Scope:** every AEE claims bundle (Specs 001, 002, 003), every study ledger the program produced, every anchored bundle, and every presentation surface (README, phase records, Zenodo record text).

## 1. Inventory

| Artifact | Contents | Location |
|---|---|---|
| Spec 001 claims bundle | 7 claims (CLM-001-01…07) | specs/001-research-engine/aee-claims.json |
| Spec 002 claims bundle | 40 claims (CLM-002-01…40) | specs/002-mvp-implementation/aee-claims.json |
| Spec 003 claims bundle | 12 claims (CLM-003-01…12) | specs/003-math-claims/aee-claims.json |
| Study ledgers | Exactly ONE production study ledger exists: the Phase 5 AR-1 demo (`~/workspace/phase5-demo/study.axmr`). An exhaustive find over ~/workspace found only ephemeral test artifacts besides (tmp*/live.axmr, demo.axmr, s.axmr, x.axmr — test fixtures, not studies) | phase5-demo |
| Anchored bundle | Demo bundle v1, Zenodo DOI 10.5281/zenodo.23311479 (concept 23311478) | phase5-demo/bundle-v1, bundle-v2 |
| Presentations | README status section; specs/*/plan.md + tasks.md phase records; Zenodo v1 record description; bundle HUMAN-README | repo + Zenodo |

## 2. Method

Every claim was re-run under the DN-010 stage model. Stages were awarded only on evidence: *checked* requires the claim to have been exercised by tests through production paths; *explained* requires a named human's explanation on record; *accepted* requires an acceptance act; *digested* requires both into the record. Every falsifier was checked for whether it could actually fire. Every verdict's evidence trail was re-verified **from its bundle alone** (standalone verifier + anchor verification against the independently fetched public record).

**Bundle-alone re-verification (2026-10-12):** bundle-v1 standalone verify OK; bundle-v2 standalone verify OK; bundle-v2 `verify_anchor` against the fetched Zenodo public record OK (checkpoint root and bundle hash as stated on the record; deposited file MD5 matches).

## 3. Stage reclassification (summary)

- **Spec 002 (29 claims previously "supported at 1.00"):** all reclassified **checked** — their evidence is the author's own seeded-defect test suite with CI green by read-back; that is checking, not settlement — except **CLM-002-13 → accepted** (its substance, the AR-1 anchor demonstration, was the object of the owner's G2 ratification act, DN-008). **CLM-002-10 → created** (K1 held; its falsifier is the Phase 7 frozen evaluation, not yet run). **CLM-002-31…40 (UI) → created** (UI unbuilt; wireframe gate T219-WF pending at audit time).
- **Spec 001:** 001-01…04 **checked** (mechanisms built and tested under Spec 002; 001-01's basis records that drift-prevention *efficacy* over live studies is untested); 001-05, 001-06 **created**; **001-07 → accepted** (owner OD-1 ratification, DN-002).
- **Spec 003:** 003-01…05, 07…11 **checked** (built with seeded-defect tests, suite green); **003-06 → created at audit time** (NC-3 below; corrected and re-staged checked the same day); **003-12 → created at audit time** (worked study not yet run; re-staged checked after the study completed, 2026-10-12).
- **No claim in any bundle is explained or digested.** No named-human explanation or digestion record exists for any Tekmerion claim. Under DN-010 this is the program's honest position: lane 1 is populated, lane 2 is empty except for two owner acceptance acts (G2, OD-1).

Full per-claim stages and bases are recorded in the bundles themselves (`lifecycle_stage` + `stage_basis` on every claim; Spec 001 v0.3.0, Spec 002 v0.7.0, Spec 003 v0.1.1) with dated addenda in each assessment record. Git history is the append-only trail for the bundles.

## 4. Nonconformances found

- **NC-1 — README status false.** The README read "Design phase (October 2026). No implementation yet" — false since Phase 0/1 (2026-10-11). Corrected by commit (see §5); the correction is noted in the README itself.
- **NC-2 — Zenodo v1 description pre-written.** The Phase 5 deposit's description was drafted expecting an INCONCLUSIVE outcome; the run was in fact INVALID. The text was corrected in place post-deposit (metadata only, same DOI) and the record now states INVALID with an explicit correction note. The original text was public from 2026-10-12T06:46:48Z until the correction — that interval cannot be unpublished. **Historical limitation** (see §6).
- **NC-3 — CLM-003-06 marked done on build alone (self-flagged).** `openness_check` shipped with no test exercising it and had never run; tasks T308/T309 were checked off on build alone. Correction: fixture test landed 2026-10-12 (tests/test_mathclaims.py, module 15/15) and the check ran live in the worked study; claim re-staged checked with the NC recorded in its assessment addendum.
- **NC-4 — CLM-001-07 presentation tension.** Bundle v0.2.0 carried status "supported" at assessor score 0.68 (below the 0.70 threshold its siblings were held to). Resolved by reclassification: the claim is *accepted* (OD-1 ratification act, DN-002); the lifecycle stage, not the score, now carries its state, and the tension is recorded in its stage_basis.
- **NC-5 — Weak falsifier F-001-D6.** Spec 001's F-001-D6 is comparative against a K3 evaluation protocol that does not exist; the falsifier cannot fire today. Recorded here and in CLM-001-06's stage_basis; not silently repaired (rewriting a falsifier would break the append-only rule). It becomes operable only when a K3 protocol exists (Phase 7 preparation).
- **NC-6 — Anchored bundle carries no run-outcome statement.** In bundle-v2, verdicts.json is `{"verdicts": []}` and controls.json holds control *definitions* only; the INVALID outcome of the demo run lives in the Zenodo description and tasks.md, not in the bundle's verdict record. A reader of the bundle alone cannot see the run's outcome. Correction applied: the run-outcome stage event was appended to the ledger itself (below), so bundle v3/v4 carry it; an exporter run-outcome projection is filed as Phase 7 preparation alongside the swap-control line-selection fix — deliberately NOT built inside this audit.
- **Phase-record "complete" language — ruled defensible, with the stage labels governing.** Phase records use "complete" to mean tasks done + tests green, which is exactly the *checked* stage; with §3's labels now on every claim, the language no longer outruns the stage. DN-008's "G2 RATIFIED" is a genuine acceptance act for the gate; the underlying claims remain checked, and DN-008's caveats already said so.

## 5. Corrections applied (append / reclassify only)

1. **Demo ledger appends** (actor "auditor", 2026-10-12; driver `~/workspace/phase5-demo/audit_append.py`): three `audit.stage_assigned` events — seq 15: CLM-D-001 → **checked** (metadata-level only; run INVALID; no explanation or acceptance on record); seq 16: run ar1-demo-1905/2026-10-12 → **"invalid — no stage earned"** (swap control exchanged actor fields of ledger lines 1–2, both "researcher" in that single-actor study — a no-op the verifier correctly treated as an intact chain; also records NC-6); seq 17: AR-1 anchor demonstration → **accepted** (owner's G2 ratification, DN-008). New checkpoint root: `52e08f7ac25b18dd26fbb90f6a8cdfd52bb36a7a208982c6e46e0510c5e37223`.
2. **New bundle + new Zenodo version:** bundle-v3 exported (hash `7fc697fd721b54a10869dce41129d1f17a2011b5d2ea3f7522dfcb01a2ded600`, standalone verify OK) and deposited as **version 2 under the same concept record 23311478 → DOI 10.5281/zenodo.23317023** (v1 intact and reachable). The new anchor receipt was appended (actor "auditor"), bundle-v4 exported (hash `e3644ac143391160efb275cb613d4d3f4d667642c6d9664d5ef7b9b8dd9d5d7f`), and the v2 anchor verified against the independently fetched public record — OK. (The first newversion attempt returned HTTP 504; a resume driver adopted/created the draft exactly once — record 23317023, version field "2", file bundle-v3.zip md5 `86f7174d7ce993a1301a5dc88d99df09`.)
3. **AEE bundle reclassifications:** Spec 001 v0.2.0 → v0.3.0; Spec 002 v0.6.0 → v0.7.0; Spec 003 v0.1.0 → v0.1.1. Every claim gained `lifecycle_stage` + `stage_basis`; no claim text, falsifier, or evidence was rewritten. Dated audit addenda appended to all three assessment records; the assessor was re-run per bundle (outcomes unchanged: 001 gather_evidence, 002 iterate, 003 gather_evidence at after_specify).
4. **README status correction** (NC-1) by new commit, with the correction noted in the text.
5. **CLM-003-06 fixture test** (NC-3) + live exercise in the worked study; re-staged checked.

## 6. Historical limitations (unfixable, labeled)

- **HL-1:** The Zenodo v1 description's original (pre-correction) text was public for an interval on 2026-10-12 before correction. It cannot be unpublished; the correction note on the record is the honest remainder.
- **HL-2:** Bundle v1/v2 (the G2 evidence as ratified) contain no run-outcome statement in their verdicts projection (NC-6). They are frozen evidence and are not edited; the outcome is stated on the Zenodo record, in DN-008's caveats, and — from v3 onward — in the ledger itself.
- **HL-3:** No Tekmerion claim has ever been explained or digested by a named human. Stages cannot be back-filled retroactively; lane-2 work is future work, and every claim's stage_basis says so.
- **HL-4:** The Phase 5 demo study was single-actor, which made its swap control a no-op by construction. The run's INVALID verdict stands as issued; the control line-selection fix is Phase 7 preparation, not an audit patch.

## 7. The audit's own conformity assertion, with its falsifier

**Assertion:** as of this report, every Tekmerion claim, verdict, and public presentation carries a DN-010 lifecycle stage no higher than its evidence supports, and every correction above was made by append or reclassification only.
**Falsifier:** any of — (i) a claim in the current bundles whose `lifecycle_stage` exceeds what its cited evidence carries (e.g. an "accepted" claim with no acceptance act on record); (ii) a diff in git history or the demo ledger showing a rewritten (not appended) correction; (iii) a public surface (README, Zenodo record) presenting a checked claim as settled. Any one observation falsifies the assertion and reopens this audit.

## 8. Owner decisions needed

None. The wireframe gate (T219-WF) was pending at audit start and is noted, not re-asked; it has since been resolved by the owner outside this audit (the audit changed nothing there). G3 thresholds (OD-5) remain owed before the Phase 7 evaluation freeze, as recorded in DN-008 — that is a standing item, not an audit question.
