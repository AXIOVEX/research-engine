"""Spec 013 Lane B1 — WS-3 freeze & claims integrity + WS-2 issuance
records (CLM-013-06, -07, -08, -09, -10, -11, -03, -04, -05).

These tests are the red-team battery, ported: each one embodies a
DEMONSTRATED attack from the 2026-10-13 engagement (rt-a p03/p03b/
p04/p05/p09, rt-d p04/p07/p08/p18/p19, rt-a RTA-10) and asserts the
attack now fails; the HELD defenses (Article II falsifier wall
verbatim, dependency-cycle refusal) are ported beside them as
must-stay-green. The probes drove the production workspace actions
(`tekmerion.ui.state`) — the same functions the Phase 6 UI and the
MCP server call — so the ports drive those actions and the freeze
layer directly; the MCP/UI surfaces inherit the refusals from these
layers (that inheritance is the claims' substance).
"""

import json

import pytest

pytest.importorskip("axiomere")

from tekmerion import export as export_mod
from tekmerion import verification as vf
from tekmerion.claims import Claim, ClaimRegister, RegistrationError
from tekmerion.connectors import RetrievedItem
from tekmerion.freeze import (
    FreezeError,
    amend_freeze,
    freeze,
    freeze_check,
    predictions_hash,
    record_predictions,
    registration_document,
    registration_hash,
)
from tekmerion.store import StudyStore
from tekmerion.ui import state as st
from tekmerion.ui.state import Workspace
from tekmerion.verdicts import Control, fixture_identity


# ------------------------------------------------------------------ scaffolding
# (the rt-a ws_common scaffolding: stub connector, production actions)

ABSTRACT = ("Cognitive behavioral therapy improves sleep quality and "
            "reduces insomnia severity in adults.")


class StubConnector:
    name = "stub"

    def resolve(self, doi):
        return RetrievedItem(
            source="stub", source_id=doi,
            title="Stub paper on sleep therapy outcomes",
            authors=["Trauer, J."], year=2023, venue="Stub Journal",
            abstract=ABSTRACT,
            license_basis="CC BY 4.0 (creativecommons.org/licenses/by/4.0)",
            hosted_ok=True)

    def search(self, query, *, limit=10):
        return [self.resolve("10.1000/stub1")]


def claim(cid, statement, falsifier):
    return Claim(claim_id=cid, statement=statement, falsifier=falsifier,
                 margin=0.1, sufficiency_floor=1)


def citation(cid, claim_id, doi):
    return vf.Citation(
        citation_id=cid, claim_id=claim_id,
        proposition="cognitive behavioral therapy improves sleep quality",
        doi=doi, title="Stub paper on sleep therapy outcomes",
        authors=["Trauer, J."], year=2023, venue="Stub Journal")


def fixture_claim(cid):
    return {"claim_id": cid, "statement": f"fixture claim {cid}",
            "falsifier": "fixture falsifier", "kind": "data",
            "dependencies": [], "margin": 0.1, "sufficiency_floor": 1,
            "supersedes": None, "status": "proposed"}


GOOD_GROUP = {"origin_group": "EVG-C1", "support_mass": 0.8,
              "contradiction_mass": 0.0, "could_falsify": True,
              "falsifier_observation": False, "metadata_only": False,
              "verified": True, "items": 1}
BAD_GROUP = {"origin_group": "EVG-C1", "support_mass": 0.0,
             "contradiction_mass": 0.0, "could_falsify": False,
             "falsifier_observation": False, "metadata_only": False,
             "verified": True, "items": 1}
NEG_GROUP = {"origin_group": "EVG-C2", "support_mass": 0.0,
             "contradiction_mass": 0.8, "could_falsify": True,
             "falsifier_observation": True, "metadata_only": False,
             "verified": True, "items": 1}


def control_fields(positive_groups, positive_expected="supported"):
    return [
        {"failure_mode": "verdict machinery marks a known fixture wrong",
         "kind": "positive", "expected": positive_expected,
         "representative_rationale": "fixture from the study's own class",
         "fixture": {"claim": fixture_claim("CLM-C-001"),
                     "groups": positive_groups}},
        {"failure_mode": "verdict machinery misses a falsified fixture",
         "kind": "negative", "expected": "contradicted",
         "representative_rationale": "fixture from the study's own class",
         "fixture": {"claim": {**fixture_claim("CLM-C-002"), "margin": 0.0},
                     "groups": [NEG_GROUP]}},
        {"failure_mode": "provenance swap undetected", "kind": "swap",
         "expected": None, "representative_rationale": ""},
    ]


def load(ws, store, study_id):
    register, _info = st.rebuild_register(store)
    retrieved = ws.read_sidecar(study_id, "retrieved.json", {}) or {}
    st.derive_evidence(store, register, retrieved)
    return register


def build_study(ws, study_id, fields):
    """One claim + one supporting citation, frozen through the
    production workspace actions (rt-a ws_common.build_study)."""
    ws.create_study(study_id, f"probe study {study_id}")
    store = ws.open(study_id)
    register, _ = st.rebuild_register(store)
    st.action_register_claim(
        store, register,
        claim("CLM-T-001", "CBT-I improves sleep quality in adults.",
              "Falsified if a checked record contradicts the sleep "
              "improvement finding."),
        actor="researcher")
    st.action_attach_citation(store, ws, study_id,
                              citation("CIT-T-101", "CLM-T-001", "10.1000/stub1"),
                              [StubConnector()], actor="researcher")
    register = load(ws, store, study_id)
    st.action_freeze(store, register, ws, study_id, actor="researcher",
                     mode="confirmation", linked_exploratory=[],
                     control_fields=fields)
    return store, load(ws, store, study_id)


def verdict_events(store):
    return [(e["payload"]["claim_id"], e["payload"]["verdict"])
            for e in store.events() if e["type"] == "verdict.issued"]


# ------------------------------------------------- CLM-013-06 (rt-a p03, rt-d p07)

def test_postfreeze_new_claim_registration_refused(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    res = st.action_run(store, register, str(ws.ledger_path("t1")),
                        st.freeze_control_fields(ws, "t1", store),
                        actor="adjudicator")
    assert res.run_verdict == "valid"
    assert verdict_events(store) == [("CLM-T-001", "supported")]

    register = load(ws, store, "t1")
    assert register.frozen
    snapshots_before = sum(1 for e in store.events()
                           if e["type"] == "record.snapshot")
    with pytest.raises(RegistrationError):
        st.action_register_claim(
            store, register,
            claim("CLM-T-002", "A claim the freeze never saw.",
                  "Falsified if a checked record contradicts it."),
            actor="researcher")
    # Nothing was appended for the refused claim, and no later run can
    # issue a verdict for a claim the freeze never saw.
    assert sum(1 for e in store.events()
               if e["type"] == "record.snapshot") == snapshots_before
    register = load(ws, store, "t1")
    assert "CLM-T-002" not in register.claims
    res2 = st.action_run(store, register, str(ws.ledger_path("t1")),
                         st.freeze_control_fields(ws, "t1", store),
                         actor="adjudicator")
    assert {cid for cid, _ in verdict_events(store)} == {"CLM-T-001"}


def test_register_refuses_any_registration_while_frozen():
    reg = ClaimRegister()
    reg.register(claim("CLM-F-001", "s1", "f1"))
    reg.frozen = True
    with pytest.raises(RegistrationError):  # a brand-new id
        reg.register(claim("CLM-F-002", "s2", "f2"))
    with pytest.raises(RegistrationError):  # an existing id, unchanged text
        reg.register(claim("CLM-F-001", "s1", "f1"))


# ------------------------------------------- CLM-013-07 (rt-a p03b, rt-d p08)

def test_second_freeze_refused_unlabeled(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    frozen_before = [e for e in store.events() if e["type"] == "study.frozen"]
    assert len(frozen_before) == 1
    with pytest.raises(FreezeError):
        st.action_freeze(store, register, ws, "t1", actor="researcher",
                         mode="confirmation", linked_exploratory=[],
                         control_fields=st.freeze_control_fields(ws, "t1", store))
    assert [e for e in store.events()
            if e["type"] == "study.frozen"] == frozen_before
    assert not [e for e in store.events()
                if e["type"] == "study.frozen.amended"]


def test_amendment_act_is_labeled_and_binds_consumers(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    first = st.frozen_event(store)
    first_hash = first["payload"]["registration_hash"]

    # An amendment requires a stated reason.
    with pytest.raises(FreezeError):
        st.action_amend_freeze(store, register, ws, "t1", actor="researcher",
                               reason="  ", mode="confirmation",
                               linked_exploratory=[],
                               control_fields=control_fields([GOOD_GROUP]))

    result = st.action_amend_freeze(
        store, register, ws, "t1", actor="researcher",
        reason="correct the control set before the confirmation run",
        mode="confirmation", linked_exploratory=[],
        control_fields=control_fields([GOOD_GROUP]))
    amended = [e for e in store.events() if e["type"] == "study.frozen.amended"]
    assert len(amended) == 1
    assert amended[0]["payload"]["amends_registration_hash"] == first_hash
    assert amended[0]["payload"]["reason"]
    assert result["registration_hash"] != first_hash
    # Exactly one (unlabeled) study.frozen event still exists, and
    # consumers bind to the amendment — not to a silent last freeze.
    assert len([e for e in store.events()
                if e["type"] == "study.frozen"]) == 1
    binding = st.frozen_event(store)
    assert binding["type"] == "study.frozen.amended"
    assert binding["payload"]["registration_hash"] == result["registration_hash"]

    # A run under the amended regime issues verdicts, and the bundle
    # states the regime they were issued under.
    register = load(ws, store, "t1")
    res = st.action_run(store, register, str(ws.ledger_path("t1")),
                        st.freeze_control_fields(ws, "t1", store),
                        actor="adjudicator")
    assert res.run_verdict == "valid"
    _manifest, verification, out = st.action_export(
        store, register, ws, "t1", actor="adjudicator")
    assert verification.ok, verification.failures
    run_outcome = json.loads((out / "verdicts.json").read_text())["run_outcome"]
    assert run_outcome["registration_hash"] == result["registration_hash"]
    assert run_outcome["regime"]["amended"] is True
    assert run_outcome["regime"]["frozen_event_seq"] == binding["seq"]


def test_unlabeled_second_freeze_binding_is_the_stopped_component(tmp_path):
    """STOPPED COMPONENT of CLM-013-07 — recorded, not smoothed over.

    The claim's bind-to-FIRST-freeze consumer rule is not shipped:
    the deposited Spec 003 math-study ledger carries two unlabeled
    study.frozen events (run-2 re-freeze, seq 62 and 87) with its
    registration and verdicts issued under the second, so binding to
    the first fails verification of a frozen, deposited artifact and
    falsifies CLM-013-46 (measured: frozen-set check, math-study
    bundle-v1/v2). The shipped precedence — latest labeled amendment
    if any, else the last study.frozen — coincides with bind-to-first
    on every ledger the remediated code can produce, because freeze()
    refuses a second freeze at the append (the demonstrated RTA-03
    entry point; see test_second_freeze_refused_unlabeled). The
    residual gap this test documents: a second study.frozen appended
    DIRECTLY to the ledger, bypassing freeze(), still moves the
    binding on a multi-freeze ledger. Spec resolution of the
    CLM-013-07 / CLM-013-46 conflict is the coordinator's."""
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    first = st.frozen_event(store)
    store.db.append("study.frozen", {
        "registration_hash": "0" * 64, "mode": "confirmation",
        "claims": ["CLM-T-001", "CLM-T-999"], "linked_exploratory": [],
    }, actor="mallory")
    binding = st.frozen_event(store)
    # Shipped (legacy) precedence: the appended event binds. This is
    # the limitation stated above, asserted so it cannot drift
    # silently — a future spec resolution changes this test by name.
    assert binding["seq"] != first["seq"]
    assert binding["payload"]["registration_hash"] == "0" * 64


# ------------------------------------------------------- CLM-013-08 (rt-d p18/p19)

def test_freeze_mode_must_be_in_enum(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    reg.register(claim("CLM-M-001", "s", "f"))
    controls = st.control_objects(control_fields([GOOD_GROUP]))
    with pytest.raises(FreezeError):
        freeze(store, reg, controls, actor="adjudicator", mode="sideways",
               linked_exploratory=[])
    assert not [e for e in store.events() if e["type"] == "study.frozen"]


def test_workspace_freeze_sideways_refused_and_exports_nothing(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.create_study("mx", "mode probe")
    store = ws.open("mx")
    register, _ = st.rebuild_register(store)
    st.action_register_claim(store, register,
                             claim("CLM-T-001", "s", "f"), actor="researcher")
    register = load(ws, store, "mx")
    with pytest.raises(FreezeError):
        st.action_freeze(store, register, ws, "mx", actor="researcher",
                         mode="sideways", linked_exploratory=[],
                         control_fields=control_fields([GOOD_GROUP]))
    assert st.frozen_event(store) is None
    res = st.action_run(store, register, str(ws.ledger_path("mx")),
                        control_fields([GOOD_GROUP]), actor="adjudicator")
    assert res.run_verdict == "invalid"
    assert verdict_events(store) == []


# ------------------------------------------------------------- CLM-013-09 (rt-a p04)

def test_sidecar_fixture_swap_cannot_flip_a_run(tmp_path):
    fields = control_fields([BAD_GROUP])  # honest execution FAILS
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t2", fields)
    res1 = st.action_run(store, register, str(ws.ledger_path("t2")),
                         st.freeze_control_fields(ws, "t2", store),
                         actor="adjudicator")
    assert res1.run_verdict == "invalid"
    assert verdict_events(store) == []

    # The attack: rewrite only the sidecar's fixture.
    sidecar_path = ws.study_dir("t2") / "freeze.json"
    sidecar = json.loads(sidecar_path.read_text())
    sidecar["controls"][0]["fixture"]["groups"] = [GOOD_GROUP]
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True))

    register = load(ws, store, "t2")
    res2 = st.action_run(store, register, str(ws.ledger_path("t2")),
                         st.freeze_control_fields(ws, "t2", store),
                         actor="adjudicator")
    assert res2.run_verdict == "invalid"
    assert any("commitment" in r or "fixture" in r
               for r in res2.invalid_reasons), res2.invalid_reasons
    assert verdict_events(store) == []

    # Export refuses the substituted fixture as well.
    register = load(ws, store, "t2")
    with pytest.raises(export_mod.ExportError):
        st.action_export(store, register, ws, "t2", actor="adjudicator")


def test_fixture_identity_committed_in_registration_document():
    reg = ClaimRegister()
    reg.register(claim("CLM-D-001", "s", "f"))
    controls = st.control_objects(control_fields([GOOD_GROUP]))
    doc = registration_document(reg, controls, "confirmation", [])
    committed = {c["kind"]: c.get("fixture") for c in doc["controls"]}
    expected = fixture_identity(controls[0])
    assert committed["positive"] == expected
    assert committed["negative"] is not None
    assert committed["swap"] is None  # no fixture to identify


# ------------------------------------------------------------ CLM-013-10 (rt-a p05)

def _vacuous_controls():
    fixture = Claim(claim_id="CLM-C-001", statement="fixture",
                    falsifier="fixture falsifier", margin=0.1,
                    sufficiency_floor=1)
    return [
        Control(failure_mode="machinery cannot reach a verdict",
                kind="positive", claim=fixture, groups=[],
                expected="inconclusive",
                representative_rationale="registered as representative"),
        Control(failure_mode="machinery invents a verdict",
                kind="negative", claim=fixture, groups=[],
                expected="inconclusive",
                representative_rationale="registered as representative"),
        Control(failure_mode="provenance swap undetected", kind="swap"),
    ]


def test_freeze_gate_rejects_vacuous_fixture_controls(tmp_path):
    reg = ClaimRegister()
    reg.register(claim("CLM-V-001", "s", "f"))
    failures = freeze_check(reg, _vacuous_controls(), mode="confirmation",
                            linked_exploratory=[])
    assert any("decisive" in f for f in failures), failures
    assert any("no evidence groups" in f for f in failures), failures
    store = StudyStore.create(str(tmp_path / "v.axmr"))
    with pytest.raises(FreezeError):
        freeze(store, reg, _vacuous_controls(), actor="a",
               linked_exploratory=[])


def test_freeze_gate_accepts_decisive_fixture_controls():
    reg = ClaimRegister()
    reg.register(claim("CLM-V-001", "s", "f"))
    controls = st.control_objects(control_fields([GOOD_GROUP]))
    failures = freeze_check(reg, controls, mode="confirmation",
                            linked_exploratory=[])
    assert not any("decisive" in f or "evidence groups" in f
                   for f in failures), failures


# ------------------------------------------------------------ CLM-013-11 (rt-d p04)

def test_reregistration_cannot_change_statement_or_falsifier():
    reg = ClaimRegister()
    reg.register(claim("CLM-L2-001", "Treatment X reduces mortality by 50%.",
                       "An RCT showing no mortality effect."))
    # Byte-identical re-registration is an idempotent retry: allowed.
    reg.register(claim("CLM-L2-001", "Treatment X reduces mortality by 50%.",
                       "An RCT showing no mortality effect."))
    with pytest.raises(RegistrationError):  # changed statement (proposed)
        reg.register(claim("CLM-L2-001", "Treatment X is completely safe.",
                           "An RCT showing no mortality effect."))
    with pytest.raises(RegistrationError):  # changed falsifier only
        reg.register(claim("CLM-L2-001", "Treatment X reduces mortality by 50%.",
                           "Anything at all."))
    assert reg.claims["CLM-L2-001"].statement.startswith("Treatment X reduces")


def test_reregistration_refused_after_evidence_attaches(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.create_study("life", "re-registration probe")
    store = ws.open("life")
    register, _ = st.rebuild_register(store)
    st.action_register_claim(
        store, register,
        claim("CLM-L2-001", "Treatment X reduces mortality by 50%.",
              "An RCT showing no mortality effect."),
        actor="researcher")
    st.action_attach_citation(store, ws, "life",
                              citation("CIT-1", "CLM-L2-001", "10.1000/stub1"),
                              [StubConnector()], actor="researcher")
    register = load(ws, store, "life")
    assert register.evidence.get("CLM-L2-001")  # evidence has attached
    with pytest.raises(RegistrationError):
        st.action_register_claim(
            store, register,
            claim("CLM-L2-001", "Treatment X cures baldness.",
                  "A photo of a bald treated patient."),
            actor="researcher")
    register = load(ws, store, "life")
    assert register.claims["CLM-L2-001"].statement.startswith(
        "Treatment X reduces")


def test_statement_change_flows_through_supersedes():
    reg = ClaimRegister()
    reg.register(claim("CLM-S-001", "original statement", "original falsifier"))
    successor = Claim(claim_id="CLM-S-002", statement="changed statement",
                      falsifier="changed falsifier", supersedes="CLM-S-001")
    reg.register(successor)
    assert reg.claims["CLM-S-001"].status == "superseded"
    assert reg.claims["CLM-S-002"].statement == "changed statement"


# ------------------------------------------- CLM-013-03 (rt-a p09) + regime record

def _rehash_bundle(bundle):
    """Recompute a bundle's manifest hashes after an in-place edit
    (the rt-a rt_common.rehash attack step)."""
    import hashlib
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    manifest["bundle_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _export_valid_study(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    res = st.action_run(store, register, str(ws.ledger_path("t1")),
                        st.freeze_control_fields(ws, "t1", store),
                        actor="adjudicator")
    assert res.run_verdict == "valid"
    return ws, store, register


def test_run_issuance_appends_control_outcome_events(tmp_path):
    _ws, store, _register = _export_valid_study(tmp_path)
    run_events = [e for e in store.events() if e["type"] == "run.issued"]
    outcome_events = [e for e in store.events()
                      if e["type"] == "control.outcome"]
    assert len(run_events) == 1
    assert sorted(o["payload"]["kind"] for o in outcome_events) == [
        "negative", "positive", "swap"]
    assert all(o["payload"]["passed"] for o in outcome_events)
    binding = st.frozen_event(store)
    assert run_events[0]["payload"]["registration_hash"] == \
        binding["payload"]["registration_hash"]
    assert run_events[0]["payload"]["regime_amended"] is False


def test_bundle_control_outcomes_cross_checked_against_ledger(tmp_path):
    import shutil
    ws, store, register = _export_valid_study(tmp_path)
    _m, verification, out = st.action_export(store, register, ws, "t1",
                                             actor="adjudicator")
    assert verification.ok, verification.failures
    run_outcome = json.loads((out / "verdicts.json").read_text())["run_outcome"]
    assert run_outcome["controls_recorded"] is True
    recorded = [e["payload"] for e in store.events()
                if e["type"] == "control.outcome"]
    # The projection covers the committed control set; its EXECUTED
    # entries are the recorded events, payload-for-payload.
    executed = [o for o in run_outcome["controls"] if o["executed"]]
    canon = lambda lst: sorted(json.dumps(o, sort_keys=True) for o in lst)
    assert canon(executed) == canon(recorded)

    def variant(name, mutate):
        target = tmp_path / name
        shutil.copytree(out, target)
        doc = json.loads((target / "verdicts.json").read_text())
        mutate(doc["run_outcome"]["controls"])
        (target / "verdicts.json").write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n")
        _rehash_bundle(target)
        result = export_mod.verify_bundle(str(target))
        assert not result.ok, f"{name}: tamper passed verification"

    def by_kind(controls, kind):
        return next(o for o in controls if o["kind"] == kind)

    variant("obs", lambda cs: by_kind(cs, "positive").update(
        observed="inconclusive"))
    variant("exec", lambda cs: by_kind(cs, "positive").update(
        executed=False, passed=None, observed=None))
    variant("fixid", lambda cs: by_kind(cs, "positive")["fixture"].update(
        sha256="0" * 64))
    variant("detail", lambda cs: by_kind(cs, "positive").update(
        detail="control executed on a different fixture entirely"))
    # HELD before, must still fail: passed flipped to false.
    variant("passed", lambda cs: by_kind(cs, "positive").update(passed=False))
    variant("swappassed", lambda cs: by_kind(cs, "swap").update(passed=False))


def test_pre_issuance_run_bundle_labels_outcomes_operator_attested(tmp_path):
    """A run whose verdicts were issued without control.outcome
    events (the pre-Spec-013 shape, driven here by issuing verdicts
    directly) exports with its fixture outcomes labeled
    operator-attested in the HUMAN-README — and still verifies."""
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    result = st.evaluate_workspace_run(
        store, register, str(ws.ledger_path("t1")),
        st.freeze_control_fields(ws, "t1", store))
    assert result.run_verdict == "valid"
    for verdict in result.claim_verdicts:  # the pre-013 issuance shape
        store.issue_verdict(verdict.claim_id, verdict.as_dict(),
                            actor="adjudicator")
    assert not [e for e in store.events() if e["type"] == "control.outcome"]
    _m, verification, out = st.action_export(store, register, ws, "t1",
                                             actor="adjudicator")
    assert verification.ok, verification.failures
    run_outcome = json.loads((out / "verdicts.json").read_text())["run_outcome"]
    assert run_outcome["controls_recorded"] is False
    readme = (out / "HUMAN-README.md").read_text()
    assert "operator-attested" in readme


# ------------------------------------------------------------- CLM-013-04 (RTA-10i)

PREDICTIONS = {"CLM-E-001": "supported", "CLM-E-002": "inconclusive"}


def test_predictions_committed_in_registration_document():
    reg = ClaimRegister()
    reg.register(claim("CLM-E-001", "s", "f"))
    controls = st.control_objects(control_fields([GOOD_GROUP]))
    doc = registration_document(reg, controls, "confirmation", [],
                                predictions=PREDICTIONS)
    assert doc["predictions"] == PREDICTIONS
    assert doc["predictions_hash"] == predictions_hash(PREDICTIONS)
    # The commitment is inside the hash: a different prediction set is
    # a different registration.
    other = registration_document(reg, controls, "confirmation", [],
                                  predictions={"CLM-E-001": "contradicted"})
    assert registration_hash(other) != registration_hash(doc)
    # No predictions -> the document is exactly the legacy shape.
    legacy = registration_document(reg, controls, "confirmation", [])
    assert "predictions" not in legacy and "predictions_hash" not in legacy


def test_predictions_recorded_as_pre_freeze_ledger_event(tmp_path):
    store = StudyStore.create(str(tmp_path / "e.axmr"))
    reg = ClaimRegister()
    reg.register(claim("CLM-E-001", "s", "f"))
    event = record_predictions(store, PREDICTIONS, actor="researcher")
    assert event["payload"]["predictions_hash"] == predictions_hash(PREDICTIONS)
    controls = st.control_objects(control_fields([GOOD_GROUP]))
    out = freeze(store, reg, controls, actor="researcher",
                 linked_exploratory=[], predictions=PREDICTIONS)
    frozen = [e for e in store.events() if e["type"] == "study.frozen"]
    assert event["seq"] < frozen[0]["seq"]
    assert frozen[0]["payload"]["registration_hash"] == out["registration_hash"]


# ------------------------------------------------------------ CLM-013-05 (RTA-10ii)

def test_workspace_attach_logs_connector_queries(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store, register = build_study(ws, "t1", control_fields([GOOD_GROUP]))
    queries = [e["payload"] for e in store.events()
               if e["type"] == "connector.query"]
    assert queries, "workspace attach path logged no connector.query events"
    assert all(q["connector"] == "stub" for q in queries)
    _m, verification, out = st.action_export(store, register, ws, "t1",
                                             actor="adjudicator")
    assert verification.ok, verification.failures
    queries_doc = json.loads((out / "queries.json").read_text())
    assert queries_doc["queries"] == queries


# ------------------------------------------------------------- HELD defenses (port)

def test_held_falsifier_wall_verbatim():
    reg = ClaimRegister()
    with pytest.raises(RegistrationError) as excinfo:
        reg.register(claim("CLM-H-001", "s", "   "))
    assert "no falsifier — not registered (Article II)" in str(excinfo.value)


def test_held_dependency_cycle_refused_at_freeze():
    reg = ClaimRegister()
    a = claim("CLM-H-001", "s", "f")
    b = claim("CLM-H-002", "s", "f")
    a.dependencies = ["CLM-H-002"]
    reg.register(b)
    reg.register(a)
    b.dependencies = ["CLM-H-001"]  # close the cycle in the register
    failures = freeze_check(reg, st.control_objects(control_fields([GOOD_GROUP])),
                            mode="confirmation", linked_exploratory=[])
    assert any("cycle" in f for f in failures), failures
