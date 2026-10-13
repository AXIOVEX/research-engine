# Spec 013 — Plan

## Sequence

1. **Claims first.** `aee-claims.json` v0.1.0 (47 claims, all draft) assessed at
   `after_specify` with the pinned assessor (engine 1.0.4, threshold 0.70)
   before any implementation. Result as computed: outcome `iterate`, 0 claims
   below threshold (assessment in `aee-assessment.json`). Recorded, not
   massaged.
2. **Battery port.** The in-scope red-team probes (rt-a, rt-c, rt-d, rt-e) are
   ported into the repo test suite as regression tests and verified to FAIL
   against the pre-fix code — a battery that is green before the fix proves
   nothing (Article VI). The workspace suites stay the reference; the ported
   tests are the build's working target (CLM-013-47).
3. **Parallel build lanes** (module-disjoint except where noted; each lane in
   its own worktree, coordinator merges):
   - **Lane A — WS-6 connectors** (`src/tekmerion/connectors.py`,
     `verification.py` resolution/enrichment seams). Independent from day one.
     Claims 36–45.
   - **Lane B — WS-3 freeze & claims integrity** (`claims.py`, `freeze.py`,
     run paths) **plus** the WS-2 items that live in the same machinery
     (control-outcome issuance events, predictions in the registration,
     study-path query logging). Claims 06–14 with 03/04/05.
   - **Lane C — WS-4 platform** (`src/tekmerion/platform/`). Fully independent
     module tree; the largest lane (13 claims, 15–27). Its battery is the rt-c
     probe set, including re-running the HELD SAML/OIDC/SCIM batteries to
     prove no regression.
   - **Lane D — WS-2 verification consumers** (`export.py` verify paths).
     Claims 01/02 start immediately; claim 03's bundle cross-check starts once
     Lane B fixes the outcome-event shape.
   - **Lane E — WS-5 surfaces** (`mcp/server.py`, Phase 6 UI, console,
     `skill/SKILL.md`). Starts after Lane B's freeze-layer refusals (mode
     enum, register wall) and Lane C's service gates exist to inherit; the UI
     mechanics (CSRF tokens, session identity) are independent and may start
     immediately. Claims 28–35.
   - **File-sharing rule:** `verification.py` is touched by Lane A (resolution,
     enrichment, error classification) and Lane B (falsifier naming, stance
     checker, intake normalization). One lane owns the file at a time; the
     coordinator sequences the two windows.
4. **Integration & gates, before merge:**
   - Full repo suite green.
   - Console conformance captures re-run; served-surface identity asserted by
     BUILD_ID, appearance unchanged (Article XIV — no wireframe delta exists
     in this spec; any delta found stops the lane and is flagged).
   - **Backward-compatibility measurement** (CLM-013-46): the frozen set
     (Phase 5 lineage, Phase 7 bundles, Spec 003 bundle, Spec 010/OSF copies)
     and the deposited copies re-verify to identical verdicts. A frozen bundle
     failing post-remediation is treated as a remediation defect until proven
     otherwise. This gate precedes merge, not follows it.
   - **Battery re-run** (CLM-013-47): every in-scope DEMONSTRATED attack
     fails; every HELD defense still holds.
5. **Records.** Re-assess at `after_implement`; dated assessment record in this
   package. Spec 005 bookkeeping: a dated qualification note in
   `specs/005-enterprise-platform/` recording the path-level limits the probes
   demonstrated against CLM-005-03/-04/-08/-09/-10/-11/-12/-17/-27, and
   re-assessment of the affected claims in that bundle — the remediation does
   not silently rewrite another spec's record. CHANGELOG entry per the
   release-hygiene rule.
6. **PR; the coordinator merges.** (This spec package itself ships as its own
   PR first, per Article XII: spec before code.)

## Risks / open questions carried into the build

- **Stricter verifiers vs frozen records** (CLM-013-01/02 vs CLM-013-46): the
  re-derivation and anchor-binding checks must pass every honest frozen
  bundle. Mitigation is the step-4 measurement gate; if a frozen bundle's own
  evidence fold does not reproduce its issued verdicts, that is a finding
  about the record, surfaced to the owner — never resolved by editing the
  frozen artifact (Article IV).
- **Anchor receipts for existing exports** (CLM-013-02): historical bundles
  were exported before per-export receipts existed. Their verify_anchor
  behavior under the new binding is decided by the CLM-013-46 measurement:
  they must verify identically, so the binding applies to bundles with a
  per-bundle receipt and the older receipt-chain behavior is preserved for
  the frozen set — if the build finds this cannot be made consistent, it
  stops and flags rather than weakening the new check.
- **Run issuance changes shape** (CLM-013-03): control-outcome events are new
  event types; replay of pre-remediation runs must not reinterpret them, and
  the Spec 011-style backward-compat replay covers this.
- **All-source resolution changes call patterns and measured cost**
  (CLM-013-40 with 05/45): more calls per citation, all now logged. Budget
  semantics unchanged; K5 accounting reads the complete log and its numbers
  will move — recorded in the assessment, not smoothed.
- **Platform gate tightening vs the E5 console's legitimate flows** (WS-4 +
  WS-5): step-up/signature requirements on every path must keep real console
  flows working; the conformance re-run (step 4) is the check, with the rt-c
  HELD batteries as the regression floor.
- **WS-1 dependency honesty:** none of these lanes wait on the axiomere
  sibling spec, and none of their claims cover core behavior (signature
  presence in core verify, core checkpoint recomputation, trusted-map
  exposure). If a lane discovers its fix cannot be completed at the Tekmerion
  layer, it records the dependency and stops that claim — it does not reach
  into the core from this spec.
