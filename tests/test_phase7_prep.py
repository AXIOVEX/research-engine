"""Phase 7 preparation tests: the swap-control event-selection fix
(T218 finding) and the exporter run-outcome projection (audit NC-6).

The Phase 5 demo study's run was INVALID because the swap control
exchanged the actor fields of ledger lines 1–2, which in that
single-actor study are the same value — a no-op the verifier
correctly treated as an intact chain. These tests pin the fix: the
control now selects the first pair of events with *distinct* actors,
and on a ledger with no such pair it rewrites one event's actor to a
probe actor, so detection is genuinely possible on every ledger
shape. The historical INVALID stands; what changed is the control.
"""

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

import axiomere as ax

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem
from tekmerion.export import export_bundle, verify_bundle
from tekmerion.freeze import freeze
from tekmerion.store import StudyStore
from tekmerion.verdicts import (
    SWAP_PROBE_ACTOR, Control, _swap_tamper, evaluate_run, run_controls,
    swap_control_report,
)


def _ledger(tmp_path, actors, name="study.axmr"):
    """A ledger whose events are appended by `actors` in order."""
    path = tmp_path / name
    store = StudyStore.create(str(path))
    for i, actor in enumerate(actors):
        store.db.append("test.event", {"n": i}, actor=actor)
    return store, str(path)


def _old_style_swap_detected(path):
    """The pre-fix construction, verbatim in effect: exchange the
    actor fields of file lines 1 and 2, then ask the production
    verifier. Returns True iff that tamper is detected."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[1])
    e2 = json.loads(lines[2])
    e1["actor"], e2["actor"] = e2["actor"], e1["actor"]
    lines[1] = json.dumps(e1, sort_keys=True, separators=(",", ":"))
    lines[2] = json.dumps(e2, sort_keys=True, separators=(",", ":"))
    tampered = Path(path).with_suffix(".old-tamper.axmr")
    tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, _count, _reason = ax.verify_file(str(tampered))
    return not ok


# --------------------------------------------------------------- (a) the fix

def test_old_selection_was_a_noop_when_first_events_share_an_actor(tmp_path):
    """The defect mechanism, documented: same-actor lines 1–2 make the
    historical exchange change nothing, and the verifier — correctly —
    reports the 'tampered' copy intact."""
    _store, path = _ledger(tmp_path, ["researcher", "researcher", "adjudicator"])
    assert _old_style_swap_detected(path) is False


def test_swap_selects_first_distinct_actor_pair(tmp_path):
    """Same ledger shape as the defect case (lines 1–2 share an actor,
    a distinct actor appears later): the fixed control exchanges the
    distinct pair and the production verifier detects it."""
    _store, path = _ledger(tmp_path, ["researcher", "researcher", "adjudicator"])
    report = swap_control_report(path)
    assert report["failures"] == []
    assert report["detected"] is True
    assert "actor exchange" in report["construction"]
    assert "lines 2 and 4" in report["construction"]  # magic line is line 1


def test_swap_probe_rewrite_on_single_actor_ledger(tmp_path):
    """The Phase 5 demo shape: one actor throughout. No pair exists to
    exchange, so the control rewrites the first event's actor to the
    probe actor — and that forgery is detected."""
    _store, path = _ledger(tmp_path, ["researcher"] * 4)
    assert _old_style_swap_detected(path) is False  # the historical no-op
    report = swap_control_report(path)
    assert report["failures"] == []
    assert report["detected"] is True
    assert "probe rewrite" in report["construction"]
    assert SWAP_PROBE_ACTOR in report["construction"]


def test_swap_tamper_alters_signed_bytes_on_both_constructions(tmp_path):
    """The detection the control relies on is the production
    verifier's, not the control's say-so: an untampered copy verifies,
    and each construction's tampered copy fails verification."""
    for actors in (["researcher", "researcher", "adjudicator"], ["researcher"] * 3):
        _store, path = _ledger(tmp_path, actors, name=f"s-{len(actors)}-{actors[-1]}.axmr")
        ok, _c, _r = ax.verify_file(path)
        assert ok
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        built = _swap_tamper(lines)
        assert built is not None
        tampered_lines, _construction = built
        tampered = Path(path).with_suffix(".tamper.axmr")
        tampered.write_text("\n".join(tampered_lines) + "\n", encoding="utf-8")
        ok, _c, _r = ax.verify_file(str(tampered))
        assert not ok


def test_swap_control_passes_through_run_controls_on_demo_shapes(tmp_path):
    """Through the production control path (RT-1): both ledger shapes
    that defeated or defined the old control now pass the swap
    control, so a run on such a ledger is not invalidated by it."""
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    for actors in (["researcher", "researcher", "adjudicator"], ["researcher"] * 3):
        _store, path = _ledger(tmp_path, actors, name=f"rc-{actors[-1]}-{len(actors)}.axmr")
        assert run_controls([swap], store_path=path) == []


def test_swap_control_too_short_ledger_still_fails_closed(tmp_path):
    path = tmp_path / "tiny.axmr"
    store = StudyStore.create(str(path))
    store.db.append("test.event", {"n": 0}, actor="researcher")
    report = swap_control_report(str(path))
    assert report["detected"] is False
    assert "too short" in report["failures"][0]


def test_frozen_run_on_same_actor_opening_ledger_is_not_invalidated_by_swap(tmp_path):
    """Run-level regression of the demo outcome's mechanism: a frozen
    study whose first two events share one actor (a third actor joins
    later) evaluates VALID with the fixed control — under the old
    selection this exact shape produced the demo's INVALID."""
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    c = Claim(claim_id="CLM-P-001", statement="X holds",
              falsifier="observing not-X", margin=0.1, sufficiency_floor=1)
    reg.register(c)
    store.register_claim("CLM-P-001", c.as_dict(), actor="researcher")   # event line 2
    store.db.append("test.event", {"n": 1}, actor="researcher")          # event line 3
    reg.add_evidence("CLM-P-001", EvidenceItem(
        item_id="EV-1", origin_group="G1", stance="supports", support_mass=0.9,
        could_falsify=True))
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    pos = Control(failure_mode="retrieval broken", kind="positive", claim=Claim(
        claim_id="CLM-P-900", statement="control true", falsifier="observing it false",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported", representative_rationale="known-answer control")
    neg = Control(failure_mode="verification decorative", kind="negative", claim=Claim(
        claim_id="CLM-P-901", statement="control false", falsifier="observing it true",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    controls = [pos, neg, swap]
    freeze(store, reg, controls, actor="researcher", linked_exploratory=[])
    store.db.append("test.event", {"n": 2}, actor="adjudicator")  # distinct actor joins
    result = evaluate_run(reg, mode="confirmation", controls=controls,
                          store_path=str(tmp_path / "s.axmr"))
    assert result.run_verdict == "valid", result.invalid_reasons
    assert [v.verdict for v in result.claim_verdicts] == ["supported"]


# ------------------------------------------- (b) run-outcome projection (NC-6)

def _bundle_study(tmp_path, *, issue_verdicts):
    """A small frozen study through production paths; optionally a
    valid run's verdicts are issued. Returns (store, path, register,
    controls, out_dir)."""
    store = StudyStore.create(str(tmp_path / "b.axmr"))
    reg = ClaimRegister()
    c = Claim(claim_id="CLM-B-001", statement="X holds",
              falsifier="observing not-X", margin=0.1, sufficiency_floor=1)
    reg.register(c)
    store.register_claim("CLM-B-001", c.as_dict(), actor="researcher")
    reg.add_evidence("CLM-B-001", EvidenceItem(
        item_id="EV-1", origin_group="G1", stance="supports", support_mass=0.9,
        could_falsify=True))
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    pos = Control(failure_mode="retrieval broken", kind="positive", claim=Claim(
        claim_id="CLM-B-900", statement="control true", falsifier="observing it false",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported", representative_rationale="known-answer control")
    neg = Control(failure_mode="verification decorative", kind="negative", claim=Claim(
        claim_id="CLM-B-901", statement="control false", falsifier="observing it true",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    controls = [pos, neg, swap]
    freeze(store, reg, controls, actor="researcher", linked_exploratory=[])
    if issue_verdicts:
        result = evaluate_run(reg, mode="confirmation", controls=controls,
                              store_path=str(tmp_path / "b.axmr"))
        assert result.run_verdict == "valid", result.invalid_reasons
        for v in result.claim_verdicts:
            store.issue_verdict(v.claim_id, v.as_dict(), actor="verdict-service")
    out = tmp_path / "bundle"
    manifest = export_bundle(store, str(tmp_path / "b.axmr"), str(out),
                             register=reg, controls=controls, linked_exploratory=[])
    return store, str(tmp_path / "b.axmr"), reg, controls, out, manifest


def _verdicts_doc(bundle_dir):
    return json.loads((Path(bundle_dir) / "verdicts.json").read_text(encoding="utf-8"))


def test_bundle_of_valid_run_states_valid_outcome(tmp_path):
    _s, _p, _r, _c, out, _m = _bundle_study(tmp_path, issue_verdicts=True)
    doc = _verdicts_doc(out)
    assert doc["run_outcome"]["outcome"] == "valid"
    assert doc["run_outcome"]["verdicts_issued"] == 1
    assert len(doc["verdicts"]) == 1
    assert verify_bundle(str(out)).ok


def test_bundle_of_unrun_frozen_study_states_not_run(tmp_path):
    _s, _p, _r, _c, out, _m = _bundle_study(tmp_path, issue_verdicts=False)
    doc = _verdicts_doc(out)
    assert doc["run_outcome"]["outcome"] == "not-run"
    assert doc["run_outcome"]["verdicts_issued"] == 0
    assert doc["verdicts"] == []
    assert verify_bundle(str(out)).ok


def test_bundle_replay_reproduces_invalid_for_unverified_evidence(tmp_path):
    """A study whose register carries an unverified citation would
    have its run INVALID (WS3 §1) — and an INVALID run appends
    nothing, so only a projection can say so. The exported bundle
    must state the outcome in verdicts.json itself (NC-6), with the
    engine's reason, and the standalone verifier must accept the
    bundle as a truthful record of that outcome."""
    store = StudyStore.create(str(tmp_path / "i.axmr"))
    reg = ClaimRegister()
    c = Claim(claim_id="CLM-B-002", statement="Y holds",
              falsifier="observing not-Y", margin=0.1, sufficiency_floor=1)
    reg.register(c)
    store.register_claim("CLM-B-002", c.as_dict(), actor="researcher")
    reg.add_evidence("CLM-B-002", EvidenceItem(
        item_id="EV-bad", origin_group="G1", stance="contextual", verified=False))
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    pos = Control(failure_mode="retrieval broken", kind="positive", claim=Claim(
        claim_id="CLM-B-900", statement="control true", falsifier="observing it false",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported", representative_rationale="known-answer control")
    neg = Control(failure_mode="verification decorative", kind="negative", claim=Claim(
        claim_id="CLM-B-901", statement="control false", falsifier="observing it true",
        margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    controls = [pos, neg, swap]
    freeze(store, reg, controls, actor="researcher", linked_exploratory=[])
    # The run itself: INVALID, appends nothing (production semantics).
    result = evaluate_run(reg, mode="confirmation", controls=controls,
                          store_path=str(tmp_path / "i.axmr"))
    assert result.run_verdict == "invalid"
    assert not [e for e in store.events() if e["type"] == "verdict.issued"]
    out = tmp_path / "bundle-invalid"
    export_bundle(store, str(tmp_path / "i.axmr"), str(out),
                  register=reg, controls=controls, linked_exploratory=[])
    doc = _verdicts_doc(out)
    assert doc["run_outcome"]["outcome"] == "invalid"
    assert doc["run_outcome"]["verdicts_issued"] == 0
    assert any("unverified citation" in r for r in doc["run_outcome"]["invalid_reasons"])
    verification = verify_bundle(str(out))
    assert verification.ok, verification.failures


def test_verdicts_projection_outcome_tamper_is_detected(tmp_path):
    """Rewriting the stated outcome in a copy of the bundle (with the
    manifest rehashed, attacker-style) must fail the standalone
    verifier: the projection is cross-checked, not trusted."""
    _s, _p, _r, _c, out, _m = _bundle_study(tmp_path, issue_verdicts=False)
    forged = tmp_path / "bundle-forged"
    shutil.copytree(out, forged)
    doc = _verdicts_doc(forged)
    doc["run_outcome"]["outcome"] = "valid"
    doc["run_outcome"]["verdicts_issued"] = 0
    (forged / "verdicts.json").write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    import hashlib
    manifest = json.loads((forged / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"] == "verdicts.json":
            data = (forged / "verdicts.json").read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    manifest["bundle_hash"] = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    (forged / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_bundle(str(forged))
    assert not verification.ok
    assert any("run_outcome" in f for f in verification.failures)


def test_verdict_flip_in_rehashed_bundle_is_detected(tmp_path):
    """K2 finding (Phase 7 evaluation): the verdicts projection
    cross-check once compared only the COUNT of entries against the
    ledger — flipping a verdict string in verdicts.json on a
    competently rehashed bundle passed verification. Entries must
    equal the ledger's issued payloads exactly."""
    _s, _p, _r, _c, out, _m = _bundle_study(tmp_path, issue_verdicts=True)
    forged = tmp_path / "bundle-flipped"
    shutil.copytree(out, forged)
    doc = _verdicts_doc(forged)
    assert doc["verdicts"], "fixture must carry an issued verdict"
    doc["verdicts"][0]["verdict"] = "contradicted"
    (forged / "verdicts.json").write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    import hashlib
    manifest = json.loads((forged / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"] == "verdicts.json":
            data = (forged / "verdicts.json").read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    manifest["bundle_hash"] = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    (forged / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_bundle(str(forged))
    assert not verification.ok
    assert any("verdicts.json does not match" in f
               for f in verification.failures)
