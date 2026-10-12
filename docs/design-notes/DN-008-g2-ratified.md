# Design Note 008 — Gate G2 (AR-1) Ratified

**Date:** 2026-10-12 · **Status:** Ratified by the owner (Tristen Pierson) on the Phase 5 evidence below.
**Gate:** Spec 002, G2 — "anchor implemented + demonstrated before any institutional pilot."

## Decision

Gate **G2 is RATIFIED**. The AR-1 requirement — audit-bundle export with
independent verification, and external anchoring of a study's Merkle
checkpoint root, demonstrated end-to-end — is satisfied on the evidence
recorded here. Institutional pilot work is no longer blocked by G2.
Ratification is not a pilot start: any pilot remains a separate owner
decision, and gates G3 (OD-5 thresholds, before the evaluation freeze)
and G4 (spend) still bind.

## Evidence (all verified by read-back at ratification time)

- **Implementation:** Spec 002 Phase 5, commit `3ba8542` on `main`
  (AXIOVEX/tekmerion); CI run 38214358137 completed/success; 68/68 tests
  green locally and in CI, including seeded-tamper tests in which the
  attacker rehashes the bundle manifest after tampering — the exported
  ledger's own chain/signature/checkpoint cross-checks still fail the
  verification.
- **Claims:** CLM-002-11 (audit bundle) and CLM-002-13 (AR-1 anchoring),
  decomposed into atomic claims CLM-002-21…30 and assessed before code
  (0.675–0.756, drafts) and after the build + live demonstration — all
  twelve at **1.00 / supported** in `aee-assessment.json`.
- **Live anchor:** a demo study built through production paths (live
  Crossref resolution; one real 1905 citation, one fabricated citation)
  froze at Merkle root
  `7434209696ea39ba8e97a33b5caa0ae08928269ea81c7d6407f423191e86e317`;
  its audit bundle (SHA-256
  `92093186dcd717eaa823d04e5f93d99b41a35ec31f4e7085da273891b6b7fc54`)
  was deposited to Zenodo under the mechanical adjudicator-approval
  gate — **DOI [10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479)**,
  created 2026-10-12T06:46:48Z. The anchor receipt was appended to the
  study ledger (`anchor.recorded`), the ledger re-checkpointed, and the
  re-exported bundle passes `verify_anchor` against the public record
  fetched independently (root + bundle hash stated in the record;
  deposited-file MD5 matches the local package). Demo artifacts are
  preserved at `~/workspace/phase5-demo/` (working copy, not the record
  of ratification — this note and the repo are).

## Recorded caveats (ratified with eyes open)

1. **The demo evaluation run was INVALID and issued no verdicts.** The
   Phase 3 swap control tampers the actor fields of ledger lines 1–2;
   in the single-actor demo study both are `researcher`, so the tamper
   was a no-op, the verifier correctly saw an intact chain, and the
   control — being unable to fail — invalidated the run under WS3. This
   is the machinery behaving as designed, and it exposes a real defect:
   the control's fixed line selection assumes distinct early actors.
   The fix is recorded as **Phase 7 preparation** in tasks.md and the
   assessment record; it was not silently patched during Phase 5. The
   Zenodo record's description, pre-written anticipating an
   INCONCLUSIVE verdict, was corrected in place post-deposit (metadata
   edit, same DOI, files untouched) to state the INVALID outcome and
   why — the correction is noted on the public record itself.
2. **T217 scope:** the executable deposit transport is Zenodo (the DOI
   AR-1 names). OSF support is deposit-ready metadata + component
   mapping only; an OSF registration workflow is a separate owner
   decision, outstanding.
3. **K1 remains open by design.** CLM-002-10 stands at 0.68 (draft):
   its falsifier is the Phase 7 frozen evaluation, and neither Phase 4's
   pipeline nor this ratification discharges it.

## Falsifier for this decision

If an independent party, given only a Phase 5 audit bundle and its
public anchor record, cannot confirm that the bundle's ledger matches
the anchored root exactly — or if a tampered bundle passes the
standalone verifier — AR-1 is not in fact demonstrated and this
ratification must be revisited.
