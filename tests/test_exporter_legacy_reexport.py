"""Regression tests: re-exporting a legacy (pre-Spec-013) study must
state the study's recorded history honestly.

A legacy study's frozen registration commits no fixture material —
its control entries are descriptors (kind, failure mode, expected
verdict), and a re-export presents bare `Control` objects built from
them. The export's run-outcome projection replays the run-level
checks for a study with no `verdict.issued` events; replaying the
bare descriptors as if they were executable controls manufactured
"control missing claim/groups/expected" failures — invalid reasons
no run ever produced — and branded every such re-export INVALID
(the Phase 5 demo study's bundle-v5 export attempt: the study's
recorded invalidity rested on the swap control, yet the export
cited two fixture artifacts instead and recorded the swap control
as passed under a construction that postdates the run).

The replay now follows the workspace's execution discipline: it
executes only the controls it can execute (the swap control, and
fixture controls whose fixtures are presented at export), and a
registered control whose fixture is not presented is recorded as
not executed (`passed: null`) — never as failed. These tests pin
that behavior.
"""

import json
from pathlib import Path

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem
from tekmerion.export import export_bundle, verify_bundle
from tekmerion.freeze import freeze, registration_hash
from tekmerion.store import StudyStore
from tekmerion.verdicts import Control, evaluate_run

FAILURE_POS = "retrieval broken: known-true claim not supported"
FAILURE_NEG = "verification decorative: fabricated citation accepted"
FAILURE_SWAP = "integrity machinery decorative: provenance swap undetected"


def _fixture_controls():
    pos = Control(
        failure_mode=FAILURE_POS, kind="positive",
        claim=Claim(claim_id="CLM-L-900", statement="control: a true claim",
                    falsifier="observing it false", margin=0.1,
                    sufficiency_floor=1),
        groups=[{"origin_group": "G1", "support_mass": 0.9,
                 "contradiction_mass": 0.0, "could_falsify": True,
                 "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported",
        representative_rationale="known-answer control in the study's own domain")
    neg = Control(
        failure_mode=FAILURE_NEG, kind="negative",
        claim=Claim(claim_id="CLM-L-901", statement="control: a false claim",
                    falsifier="observing it true", margin=0.1,
                    sufficiency_floor=1),
        groups=[{"origin_group": "G9", "support_mass": 0.0,
                 "contradiction_mass": 0.9, "could_falsify": True,
                 "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    swap = Control(failure_mode=FAILURE_SWAP, kind="swap")
    return [pos, neg, swap]


def _bare_controls():
    """The control descriptors a legacy re-export presents: what the
    frozen registration document carries — no fixture material."""
    return [
        Control(failure_mode=FAILURE_POS, kind="positive",
                expected="supported",
                representative_rationale="known-answer control in the study's own domain"),
        Control(failure_mode=FAILURE_NEG, kind="negative",
                expected="contradicted"),
        Control(failure_mode=FAILURE_SWAP, kind="swap"),
    ]


def _legacy_document(register, controls):
    """A pre-Spec-013 registration document: control entries carry no
    fixture field at all (the shape of the Phase 5 demo study's
    deposited registration.json)."""
    return {
        "mode": "confirmation",
        "claims": [c.as_dict() for c in register.claims.values()],
        "controls": [
            {"failure_mode": c.failure_mode, "kind": c.kind,
             "expected": c.expected,
             "representative_rationale": c.representative_rationale}
            for c in controls
        ],
        "linked_exploratory": [],
    }


def _legacy_study(tmp_path, *, verified=True):
    """A frozen study in the legacy shape: the `study.frozen` event
    commits a fixture-less registration document, as the Phase 5-era
    freeze appended it. No run is performed. Returns (store, path,
    register, legacy_doc)."""
    store = StudyStore.create(str(tmp_path / "legacy.axmr"))
    reg = ClaimRegister()
    claim = Claim(claim_id="CLM-L-001", statement="X holds",
                  falsifier="observing not-X", margin=0.1, sufficiency_floor=1)
    reg.register(claim)
    store.register_claim("CLM-L-001", claim.as_dict(), actor="researcher")
    reg.add_evidence("CLM-L-001", EvidenceItem(
        item_id="EV-1", origin_group="G1", stance="supports",
        support_mass=0.9, could_falsify=True, verified=verified))
    doc = _legacy_document(reg, _fixture_controls())
    store.db.append("study.frozen", {
        "claims": sorted(reg.claims), "mode": "confirmation",
        "linked_exploratory": [],
        "registration_hash": registration_hash(doc),
    }, actor="researcher")
    store.freeze(actor="researcher")  # the Merkle checkpoint
    reg.frozen_document = doc
    return store, str(tmp_path / "legacy.axmr"), reg, doc


def _verdicts_doc(bundle_dir):
    return json.loads((Path(bundle_dir) / "verdicts.json").read_text(encoding="utf-8"))


def test_legacy_reexport_without_issued_verdicts_states_not_run(tmp_path):
    """The defect case: a legacy study that issued no verdicts,
    re-exported with bare control descriptors. The replay must not
    manufacture invalid reasons from fixtures it was never given:
    the outcome is not-run, the fixture controls are recorded as
    not executed (passed null, never failed), and only the swap
    control — executable from the ledger alone — is replayed."""
    store, path, reg, _doc = _legacy_study(tmp_path)
    out = tmp_path / "bundle"
    export_bundle(store, path, str(out), register=reg,
                  controls=_bare_controls(), linked_exploratory=[])
    doc = _verdicts_doc(out)
    run_outcome = doc["run_outcome"]
    assert run_outcome["outcome"] == "not-run"
    assert run_outcome["verdicts_issued"] == 0
    assert run_outcome["invalid_reasons"] == []
    assert doc["verdicts"] == []
    outcomes = {o["kind"]: o for o in run_outcome["controls"]}
    for kind in ("positive", "negative"):
        assert outcomes[kind]["executed"] is False
        assert outcomes[kind]["passed"] is None
        assert "not presented at export" in outcomes[kind]["detail"]
    assert outcomes["swap"]["executed"] is True
    assert outcomes["swap"]["passed"] is True
    assert run_outcome["controls_replayed"] == ["swap"]
    verification = verify_bundle(str(out))
    assert verification.ok, verification.failures


def test_legacy_reexport_replay_invalid_states_only_real_reasons(tmp_path):
    """A legacy study whose replay genuinely fails (an unverified
    citation in its evidence) is INVALID — with the engine's real
    reason only. The absent fixtures contribute no reasons and no
    failed control outcomes."""
    store, path, reg, _doc = _legacy_study(tmp_path, verified=False)
    out = tmp_path / "bundle"
    export_bundle(store, path, str(out), register=reg,
                  controls=_bare_controls(), linked_exploratory=[])
    doc = _verdicts_doc(out)
    run_outcome = doc["run_outcome"]
    assert run_outcome["outcome"] == "invalid"
    assert run_outcome["verdicts_issued"] == 0
    assert any("unverified citation" in r for r in run_outcome["invalid_reasons"])
    assert not any("control missing" in r for r in run_outcome["invalid_reasons"])
    outcomes = {o["kind"]: o for o in run_outcome["controls"]}
    for kind in ("positive", "negative"):
        assert outcomes[kind]["executed"] is False
        assert outcomes[kind]["passed"] is None
    verification = verify_bundle(str(out))
    assert verification.ok, verification.failures


def test_legacy_reexport_with_issued_verdict_keeps_it_issued(tmp_path):
    """A study that ran valid and issued its verdict, re-exported in
    the legacy presentation (bare control descriptors): the recorded
    verdict stands as issued in the bundle — the run outcome is
    valid with the issued count — and the unpresented fixture
    controls are recorded as attested (passed null), not failed."""
    store = StudyStore.create(str(tmp_path / "issued.axmr"))
    reg = ClaimRegister()
    claim = Claim(claim_id="CLM-L-002", statement="Y holds",
                  falsifier="observing not-Y", margin=0.1, sufficiency_floor=1)
    reg.register(claim)
    store.register_claim("CLM-L-002", claim.as_dict(), actor="researcher")
    reg.add_evidence("CLM-L-002", EvidenceItem(
        item_id="EV-1", origin_group="G1", stance="supports",
        support_mass=0.9, could_falsify=True))
    controls = _fixture_controls()
    freeze(store, reg, controls, actor="researcher", linked_exploratory=[])
    result = evaluate_run(reg, mode="confirmation", controls=controls,
                          store_path=str(tmp_path / "issued.axmr"))
    assert result.run_verdict == "valid", result.invalid_reasons
    for verdict in result.claim_verdicts:
        store.issue_verdict(verdict.claim_id, verdict.as_dict(),
                            actor="verdict-service")
    out = tmp_path / "bundle"
    export_bundle(store, str(tmp_path / "issued.axmr"), str(out),
                  register=reg, controls=_bare_controls(),
                  linked_exploratory=[])
    doc = _verdicts_doc(out)
    run_outcome = doc["run_outcome"]
    assert run_outcome["outcome"] == "valid"
    assert run_outcome["verdicts_issued"] == 1
    assert len(doc["verdicts"]) == 1
    assert doc["verdicts"][0]["claim_id"] == "CLM-L-002"
    assert doc["verdicts"][0]["verdict"] == "supported"
    outcomes = {o["kind"]: o for o in run_outcome["controls"]}
    for kind in ("positive", "negative"):
        assert outcomes[kind]["executed"] is False
        assert outcomes[kind]["passed"] is None
    assert outcomes["swap"]["executed"] is True
    assert outcomes["swap"]["passed"] is True
    verification = verify_bundle(str(out))
    assert verification.ok, verification.failures


def test_unrun_study_export_with_fixtures_presented_still_replays_them(tmp_path):
    """The fix filters only what cannot be executed: when the
    fixtures ARE presented at export, the replay executes them, and
    an unrun study's bundle records all three controls as run and
    passed under the replay — the not-run statement then rests on
    the replay the bundle shows."""
    store = StudyStore.create(str(tmp_path / "unrun.axmr"))
    reg = ClaimRegister()
    claim = Claim(claim_id="CLM-L-003", statement="Z holds",
                  falsifier="observing not-Z", margin=0.1, sufficiency_floor=1)
    reg.register(claim)
    store.register_claim("CLM-L-003", claim.as_dict(), actor="researcher")
    reg.add_evidence("CLM-L-003", EvidenceItem(
        item_id="EV-1", origin_group="G1", stance="supports",
        support_mass=0.9, could_falsify=True))
    controls = _fixture_controls()
    freeze(store, reg, controls, actor="researcher", linked_exploratory=[])
    out = tmp_path / "bundle"
    export_bundle(store, str(tmp_path / "unrun.axmr"), str(out),
                  register=reg, controls=controls, linked_exploratory=[])
    doc = _verdicts_doc(out)
    run_outcome = doc["run_outcome"]
    assert run_outcome["outcome"] == "not-run"
    assert run_outcome["controls_replayed"] == ["positive", "negative", "swap"]
    for entry in run_outcome["controls"]:
        assert entry["executed"] is True
        assert entry["passed"] is True
    verification = verify_bundle(str(out))
    assert verification.ok, verification.failures
