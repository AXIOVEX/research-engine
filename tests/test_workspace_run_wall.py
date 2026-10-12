"""Service-level regression for the workspace run wall (Spec 009 F1).

The verdict-issuing workspace run — `tekmerion.ui.state.action_run`,
shared by the Phase 6 UI and the Spec 009 MCP server — issues
verdicts only against a recorded freeze. `evaluate_workspace_run`
on an unfrozen study (never frozen, or frozen-then-refused: a
FreezeError appends nothing) is INVALID with the WS3 §4 wall
reason and appends no `verdict.issued` events; it must not infer
"exploratory" from the freeze event's absence. After a real freeze
the same study runs valid and its issued verdicts export through
`action_export` — the run and the export read the same ledger and
cannot disagree.
"""

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim
from tekmerion.freeze import FreezeError
from tekmerion.ui import state as st
from tekmerion.ui.state import Workspace

FIXTURE_CLAIM = {
    "claim_id": "CLM-T-900", "statement": "known-true fixture claim",
    "falsifier": "observing the fixture evidence contradict it",
    "kind": "data", "dependencies": [], "margin": 0.1,
    "sufficiency_floor": 2, "supersedes": None, "status": "proposed",
}
GROUPS = [
    {"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
     "could_falsify": True, "falsifier_observation": False,
     "verified": True, "items": 1},
    {"origin_group": "G2", "support_mass": 0.9, "contradiction_mass": 0.0,
     "could_falsify": True, "falsifier_observation": False,
     "verified": True, "items": 1},
]


def control_fields(rationale=""):
    return [
        {"kind": "positive",
         "failure_mode": "retrieval broken: known-true claim not supported",
         "expected": "supported", "representative_rationale": rationale,
         "fixture": {"claim": FIXTURE_CLAIM, "groups": GROUPS}},
        {"kind": "negative",
         "failure_mode": "verification decorative: fabricated citation accepted",
         "expected": "contradicted", "representative_rationale": "",
         "fixture": {"claim": {**FIXTURE_CLAIM, "claim_id": "CLM-T-901"},
                     "groups": [{**g, "support_mass": 0.0,
                                 "contradiction_mass": 0.9,
                                 "falsifier_observation": True}
                                for g in GROUPS]}},
        {"kind": "swap",
         "failure_mode": "integrity machinery decorative: provenance swap undetected",
         "expected": None, "representative_rationale": "", "fixture": None},
    ]


def build_study(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.create_study("svc", "Service wall study")
    store = ws.open("svc")
    register, _ = st.rebuild_register(store)
    st.action_register_claim(store, register, Claim(
        claim_id="CLM-T-001", statement="the record resolves",
        falsifier="resolution returns not_found",
        margin=0.1, sufficiency_floor=1), actor="ada")
    st.action_register_claim(store, register, Claim(
        claim_id="CLM-T-002", statement="the fabricated source exists",
        falsifier="the source of record holding no such work",
        margin=0.1, sufficiency_floor=1), actor="grace")
    return ws, store, register


def issued(store):
    return [e for e in store.events() if e["type"] == "verdict.issued"]


def test_unfrozen_workspace_run_is_invalid_and_issues_nothing(tmp_path):
    ws, store, register = build_study(tmp_path)
    result = st.evaluate_workspace_run(store, register,
                                        str(ws.ledger_path("svc")), [])
    assert result.run_verdict == "invalid"
    assert any("frozen registration" in r for r in result.invalid_reasons)
    assert result.claim_verdicts == []

    result = st.action_run(store, register, str(ws.ledger_path("svc")),
                           st.freeze_control_fields(ws, "svc", store), "grace")
    assert result.run_verdict == "invalid"
    assert issued(store) == []


def test_run_after_failed_freeze_then_freeze_run_export(tmp_path):
    ws, store, register = build_study(tmp_path)

    # A refused freeze appends nothing (RT-6: no rationale).
    with pytest.raises(FreezeError, match="representative rationale"):
        st.action_freeze(store, register, ws, "svc", "grace",
                         mode="confirmation", linked_exploratory=[],
                         control_fields=control_fields())
    assert st.frozen_event(store) is None

    # The run attempted anyway is INVALID — not silently exploratory.
    result = st.action_run(store, register, str(ws.ledger_path("svc")),
                           st.freeze_control_fields(ws, "svc", store), "grace")
    assert result.run_verdict == "invalid", result.invalid_reasons
    assert any("frozen registration" in r for r in result.invalid_reasons)
    assert issued(store) == []

    # A real freeze: the same study runs, issues, and exports.
    st.action_freeze(store, register, ws, "svc", "grace",
                     mode="confirmation", linked_exploratory=[],
                     control_fields=control_fields(
                         "same domain and difficulty class as the study claims"))
    register, _ = st.rebuild_register(store)
    result = st.action_run(store, register, str(ws.ledger_path("svc")),
                           st.freeze_control_fields(ws, "svc", store), "grace")
    assert result.run_verdict == "valid", result.invalid_reasons
    assert {e["payload"]["claim_id"] for e in issued(store)} == {
        "CLM-T-001", "CLM-T-002"}

    _manifest, verification, _out = st.action_export(
        store, register, ws, "svc", "ada")
    assert verification.ok is True
