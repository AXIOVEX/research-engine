# Spec 010 — OSF Registration — plan

1. Claims + assessment at after_specify (this package, bundle v0.1.0).
2. Build `src/tekmerion/osf_deposit.py`: `OSFTransport` (stdlib urllib;
   serial, ≥ 1 s spacing, 429 = stop) + `deposit_bundle_osf` (gate → state →
   project → components → files → existing-registration check → draft →
   responses → submit → approval-if-offered → receipt) + `verify_osf_anchor`.
3. Tests `tests/test_osf_deposit.py` against a fake transport implementing
   the same method surface with recorded OSF API shapes: payload derivation
   from a real fixture bundle (built through production paths, Phase 5
   pattern), the three gate refusals (with a counting transport proving no
   OSF object was created), the duplicate guard, failure surfacing +
   resume-from-state, receipt recording into a fixture study ledger via
   `record_anchor`, and `verify_osf_anchor` pass/mismatch.
4. Live embargo demonstration (T-P2) on a fixture study labelled as a test,
   fetched back and recorded.
5. Live demonstration (T-P4) on the Phase 7 evaluation study's bundle-v2
   (`specs/002-mvp-implementation/evaluation/study/bundle-v2/`), with
   before/after hashes of the whole study directory recorded first.
   Independent verification in a separate step: unauthenticated fetch of the
   public registration + project structure, compared against
   `osf_metadata` anchor values; fetched JSON kept in `records/`.
6. Claims re-assessed at after_implement on the built + live evidence;
   dated assessment record; branch CI green by `gh` read-back.

## Ambiguities in DESIGN §4, and the resolutions taken

1. **§4.2.4 ledgers the receipt into the study ledger (`anchor.recorded`,
   re-checkpoint).** For the T-P4 demonstration the target study is a
   frozen, already-Zenodo-anchored artifact; appending to its ledger would
   alter the frozen record to document an anchor *of* that record.
   Resolution: the mechanism is implemented and test-exercised on fixture
   studies (the existing `record_anchor` accepts the OSF receipt
   unchanged), and the production flow for future live studies ledgers
   exactly as §4.2.4 describes. The demonstration receipt is recorded in
   this spec's `records/` instead, and CLM-010-06 makes the frozen study's
   immutability a falsifiable claim with before/after hashes as evidence.
2. **Draft vs submitted end-state is not named in §4.** §4.2.3 calls the
   deliverable "an OSF registration (the registry snapshot)" — a submitted
   registration, not a draft. Resolution: submit. For the demonstration
   study, submit public/immediate: the study is already public via Zenodo
   (DOI 10.5281/zenodo.23319126), so a public registration opens no new
   disclosure surface. The embargo path §4.2.3 requires is demonstrated on
   a separate test registration (CLM-010-07).
3. **§4 names no registration schema.** Resolution: "Open-Ended
   Registration" — the general-purpose schema; its summary field carries
   the anchor statement verbatim (§4.2.3's "anchor values stated in the
   registration itself"). Resolved by name through the API at deposit
   time, never by hardcoded GUID, so a provider-side schema change fails
   loudly at lookup instead of silently mis-registering.
4. **Creators.** `osf_metadata` names creators ("Pierson, Tristen",
   Axiovex Systems, LLC); the OSF API binds project creatorship to the
   depositing account and does not accept arbitrary unregistered creator
   names. Resolution: deposits run from the owner's account (the named
   creator); verification compares the fetched project's contributor list
   against the mapping's creators and records the observed value. A
   mismatch would be recorded as a verification failure, not edited away.
5. **§4.2.4's `verify_anchor` re-exports the study before fetching.** That
   re-export belongs to the live-study ledger flow. For the frozen
   demonstration study there is nothing to re-export; `verify_osf_anchor`
   compares the fetched record against the deposited bundle's
   `osf_metadata` anchor values directly. The function's contract (pass
   only on stated-value equality + structure match) is unchanged.
6. **Component file layout.** The mapping lists bundle-relative paths;
   OSF storage is per-component. Resolution: paths are preserved inside
   their component (folders created for nested paths), so the OSF
   structure mirrors the bundle structure under each component, and
   verification checks the same layout.
