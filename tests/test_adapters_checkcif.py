"""Spec 006 (checkCIF adapter, P2) tests — seeded negatives through
production paths.

The parser is validated against RECORDED REAL checkCIF/PLATON outputs
(fixtures with provenance in tests/fixtures/adapters/checkcif/
PROVENANCE.json): an IUCr service HTML report carrying 8 level-A
alerts, and two PLATON .chk files from public test data. No checkCIF
run is fabricated anywhere in this module: PLATON is author-distributed
and not OSI-licensed, so no live binary exists in this environment —
the live invocation seam is exercised with a test-double binary that
emits the recorded real .chk bytes (it tests this adapter's invocation
machinery, never PLATON's correctness), and live-PLATON verification
by a licensed operator is a recorded open item.

One fixture limitation, stated plainly: no public matched pair
(CIF + its own A-bearing output) was found, so the A-alert mapping row
is tested at the parser + mapping + evidence-builder level, and the
full run path end-to-end on the matched C/G pairs. Pairing the
sucrose report with an unrelated CIF's bytes to manufacture an
end-to-end A test would fabricate provenance — the exact defect this
adapter exists to prevent.
"""

import hashlib
import stat
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.adapters.checkcif import (
    PlatonRunner,
    checkcif_evidence,
    map_alert_counts,
    parse_checkcif_output,
    run_checkcif,
)
from tekmerion.adapters.core import (
    AdapterEvidenceError,
    AdapterRun,
    adapter_runs,
    emit_adapter_evidence,
)
from tekmerion.claims import Claim, ClaimRegister
from tekmerion.store import StudyStore

FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "checkcif"
SF_CIF = (FIXTURES / "structurefinder" / "DK_NTD51a-final.cif").read_bytes()
SF_CHK = (FIXTURES / "structurefinder" / "DK_NTD51a.chk").read_bytes()
AL_CIF = (FIXTURES / "alsynagent" / "mo_R3HQ_PrK_0m_a.cif").read_bytes()
AL_CHK = (FIXTURES / "alsynagent" / "mo_R3HQ_PrK_0m_a.chk").read_bytes()
HTML_REPORT = (FIXTURES / "olex2" / "checkcif-sucrose.html").read_bytes()


def _store(tmp_path):
    return StudyStore.create(str(tmp_path / "study.axmr"))


def _register():
    reg = ClaimRegister()
    reg.register(Claim(
        claim_id="CLM-S-101",
        statement="The deposited crystal structure is as reported",
        falsifier="checkCIF validation of the deposited CIF reports level A alerts",
        kind="data"))
    return reg


# ---------------------------------------------------------------- parser

def test_parse_chk_fixture_counts_and_versions():
    parse = parse_checkcif_output(SF_CHK.decode("utf-8"))
    assert parse.counts == {"A": 0, "B": 0, "C": 0, "G": 5}
    assert parse.platon_version == "270106"
    assert parse.checkdef_version == "120309"
    assert parse.version_complete
    codes = {a["code"] for a in parse.alerts}
    assert "048_ALERT_1_G" in codes


def test_parse_second_chk_fixture_counts_and_versions():
    parse = parse_checkcif_output(AL_CHK.decode("utf-8"))
    assert parse.counts == {"A": 0, "B": 0, "C": 15, "G": 43}
    assert len(parse.alerts) == 58
    assert parse.platon_version == "90622"
    assert parse.checkdef_version == "220517"


def test_parse_html_service_report():
    parse = parse_checkcif_output(HTML_REPORT.decode("utf-8"))
    # The report's own summary block prints 8 A / 0 B / 10 C / 11 G —
    # the line-parsed counts must reproduce it exactly.
    assert parse.counts == {"A": 8, "B": 0, "C": 10, "G": 11}
    assert parse.reported_summary_counts == {"A": 8, "B": 0, "C": 10, "G": 11}
    assert parse.as_dict()["summary_agrees_with_alerts"] is True
    assert parse.platon_version == "13/08/2009"
    assert parse.checkdef_version == "12/08/2009"
    assert parse.datablock == "sucrose"
    assert parse.syntax_errors_found is False
    a_alerts = [a for a in parse.alerts if a["level"] == "A"]
    assert len(a_alerts) == 8
    assert any(a["code"] == "PLAT417_ALERT_2_A" for a in a_alerts)


# ---------------------------------------------------------------- mapping

def test_alert_mapping_registered_rows():
    a = map_alert_counts({"A": 1, "B": 0, "C": 0, "G": 0})
    assert a["stance"] == "contradicts" and a["contradiction_mass"] == 1.00
    assert a["falsifier_observation"] is True
    b = map_alert_counts({"A": 0, "B": 2, "C": 0, "G": 0})
    assert b["stance"] == "contradicts" and b["contradiction_mass"] == 0.50
    assert b["falsifier_observation"] is False
    cg = map_alert_counts({"A": 0, "B": 0, "C": 3, "G": 4})
    assert cg["stance"] == "contextual" and cg["contradiction_mass"] == 0.0
    clean = map_alert_counts({"A": 0, "B": 0, "C": 0, "G": 0})
    # A clean run is context, never support (CLM-006-02 blind spot).
    assert clean["stance"] == "contextual" and clean["support_mass"] == 0.0


def test_a_alerts_build_contradiction_evidence():
    parse = parse_checkcif_output(HTML_REPORT.decode("utf-8"))
    item = checkcif_evidence(parse, item_id="EV-CHK-1", origin_group="EVG-CHK-1")
    assert item.stance == "contradicts"
    assert item.contradiction_mass == 1.00
    assert item.falsifier_observation is True
    assert item.could_falsify is True


# ------------------------------------------------------------- run paths

def test_recorded_run_matched_pair_contextual_evidence_and_replay(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=SF_CIF, cif_label="DK_NTD51a-final.cif", actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-1",
        origin_group="EVG-CHK-1", runner=PlatonRunner(binary="/nonexistent/platon"),
        recorded_output=SF_CHK,
        recorded_provenance="dkratzert/StructureFinder test data (recorded output)")
    assert run.outcome == "recorded_output"
    assert run.checker_version == "PLATON 270106; check.def 120309"
    items = reg.evidence["CLM-S-101"]
    assert len(items) == 1 and items[0].stance == "contextual"
    assert items[0].contradiction_mass == 0.0 and items[0].support_mass == 0.0
    # Replay from the ledger: provenance intact.
    runs = adapter_runs(store, "checkcif")
    assert len(runs) == 1
    rec = runs[0]
    assert rec["scope_claim_id"] == "CLM-006-02"
    assert rec["artifact"]["sha256"] == hashlib.sha256(SF_CIF).hexdigest()
    assert rec["raw_output_sha256"] == hashlib.sha256(SF_CHK).hexdigest()
    assert rec["checker"]["version"] == "PLATON 270106; check.def 120309"
    assert len(rec["findings"]) == 5


def test_recorded_run_second_pair(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=AL_CIF, cif_label="mo_R3HQ_PrK_0m_a.cif", actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-2",
        origin_group="EVG-CHK-2", runner=PlatonRunner(binary="/nonexistent/platon"),
        recorded_output=AL_CHK, recorded_provenance="rguooo/AL-SynAgent (recorded output)")
    assert run.outcome == "recorded_output"
    assert run.extra["parse"]["alert_counts"] == {"A": 0, "B": 0, "C": 15, "G": 43}
    assert reg.evidence["CLM-S-101"][0].stance == "contextual"


def test_recorded_output_without_artifact_is_context_not_evidence(tmp_path):
    # F-006-1 direction: the sucrose report is real, but its source CIF
    # is not distributed with it — no CIF hash, no evidence item.
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=None, actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-3",
        origin_group="EVG-CHK-3", runner=PlatonRunner(binary="/nonexistent/platon"),
        recorded_output=HTML_REPORT,
        recorded_provenance="Olex2 captured IUCr service report (recorded output)")
    assert run.outcome == "recorded_output"
    assert len(run.findings) == 29  # parsed alerts stand as context
    assert "CLM-S-101" not in reg.evidence
    assert "CLM-006-01" in run.extra["evidence_withheld"]


def test_output_without_versions_is_not_evidence(tmp_path):
    # Seeded defect: strip the version header from the recorded .chk —
    # the alert record now lacks checker identity/versions (F-006-1).
    lines = SF_CHK.decode("utf-8").splitlines()
    stripped = "\n".join(l for l in lines if "PLATON/CHECK" not in l).encode()
    assert parse_checkcif_output(stripped.decode()).version_complete is False
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=SF_CIF, cif_label="DK_NTD51a-final.cif", actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-4",
        origin_group="EVG-CHK-4", runner=PlatonRunner(binary="/nonexistent/platon"),
        recorded_output=stripped, recorded_provenance="version-stripped test variant")
    assert run.checker_version is None
    assert "CLM-S-101" not in reg.evidence
    assert "CLM-006-01" in run.extra["evidence_withheld"]


def test_no_checker_available_is_honest_unavailable(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=SF_CIF, cif_label="DK_NTD51a-final.cif", actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-5",
        origin_group="EVG-CHK-5", runner=PlatonRunner(binary="/nonexistent/platon"))
    assert run.outcome == "not_runnable_here"
    assert "PLATON" in run.reason
    assert "CLM-S-101" not in reg.evidence
    assert len(adapter_runs(store, "checkcif")) == 1  # ledgered, not silent


def test_live_seam_with_test_double_binary(tmp_path):
    # The binary is a test double; the output bytes are the recorded
    # real PLATON .chk. This exercises the adapter's own invocation
    # machinery (argv, cwd, .chk discovery, parse, evidence) — the
    # path a licensed operator's real PLATON will take.
    double = tmp_path / "platon"
    chk_path = FIXTURES / "structurefinder" / "DK_NTD51a.chk"
    double.write_text(f"#!/bin/sh\ncp '{chk_path}' ./artifact.chk\n")
    double.chmod(double.stat().st_mode | stat.S_IEXEC)
    store, reg = _store(tmp_path), _register()
    run = run_checkcif(
        store, cif_bytes=SF_CIF, cif_label="artifact.cif", actor="op",
        claim_id="CLM-S-101", register=reg, item_id="EV-CHK-6",
        origin_group="EVG-CHK-6", runner=PlatonRunner(binary=str(double)))
    assert run.outcome == "run_by_us"
    assert run.checker_name == "PLATON (local binary)"
    assert reg.evidence["CLM-S-101"][0].stance == "contextual"
    assert run.raw_output_sha256 == hashlib.sha256(SF_CHK).hexdigest()


# ------------------------------------------------------- seam enforcement

def _hand_run(**overrides):
    base = dict(
        adapter_id="checkcif", pattern="P2", scope_claim_id="CLM-006-02",
        outcome="recorded_output", checker_name="checkCIF/PLATON (recorded output)",
        checker_version="PLATON 270106; check.def 120309",
        artifact_sha256="a" * 64, raw_output_sha256="b" * 64)
    base.update(overrides)
    return AdapterRun(**base)


def test_scope_claim_attachment_is_mechanically_enforced(tmp_path):
    store, reg = _store(tmp_path), _register()
    item = checkcif_evidence(parse_checkcif_output(SF_CHK.decode()),
                             item_id="EV-X", origin_group="EVG-X")
    with pytest.raises(AdapterEvidenceError):
        emit_adapter_evidence(store, run=_hand_run(scope_claim_id=""),
                              register=reg, claim_id="CLM-S-101", item=item, actor="op")
    with pytest.raises(AdapterEvidenceError):
        emit_adapter_evidence(store, run=_hand_run(outcome="not_runnable_here"),
                              register=reg, claim_id="CLM-S-101", item=item, actor="op")
    with pytest.raises(AdapterEvidenceError):
        emit_adapter_evidence(store, run=_hand_run(checker_version=None),
                              register=reg, claim_id="CLM-S-101", item=item, actor="op")
    with pytest.raises(AdapterEvidenceError):
        emit_adapter_evidence(store, run=_hand_run(raw_output_sha256=None),
                              register=reg, claim_id="CLM-S-101", item=item, actor="op")
    assert "CLM-S-101" not in reg.evidence
    assert adapter_runs(store) == []  # refused runs ledger nothing
