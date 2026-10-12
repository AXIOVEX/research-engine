"""Spec 009 tests: the MCP tool layer over the production services.

Handlers are exercised directly (the SDK shell is a thin registration
layer, tested separately with importorskip). Seeded defects per
claim: verbatim refusals with no append (CLM-009-02), identity on
events (CLM-009-03), the deposit gate (CLM-009-04), role denials
against the imported UI matrix (CLM-009-03), adapter/Lean state
passthrough (CLM-009-08), and the no-delete inventory (CLM-009-10).
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import RegistrationError
from tekmerion.connectors import CrossrefConnector, HttpJson
from tekmerion.deposit import DepositError
from tekmerion.export import ExportError
from tekmerion.freeze import FreezeError
from tekmerion.mcp.server import (ConfigError, ServerConfig, Session,
                                  SurfaceRefusal, TOOL_ROLES)
from tekmerion.ui.server import PERMISSIONS

REAL_WORK = {
    "DOI": "10.1000/xyz123",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "Auricular stimulation improved sleep quality significantly "
                "in a controlled trial.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

PROP = "auricular stimulation improves sleep quality"


class RoutingHttp(HttpJson):
    def get(self, url, headers=None):
        if "xyz123" in url:
            return {"message": REAL_WORK}
        raise RuntimeError("404 from source of record")


def connectors():
    return [CrossrefConnector(http=RoutingHttp())]


def make_session(tmp_path, actor, role, **kw):
    cfg = ServerConfig(workspace_root=str(tmp_path / "ws"), actor=actor,
                       role=role, **kw)
    return Session(cfg, connector_factory=connectors)


def controls():
    fixture_claim = {
        "claim_id": "CLM-T-900", "statement": "known-true fixture claim",
        "falsifier": "observing the fixture evidence contradict it",
        "kind": "data", "dependencies": [], "margin": 0.1,
        "sufficiency_floor": 2, "supersedes": None, "status": "proposed",
    }
    groups = [
        {"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
         "could_falsify": True, "falsifier_observation": False,
         "verified": True, "items": 1},
        {"origin_group": "G2", "support_mass": 0.9, "contradiction_mass": 0.0,
         "could_falsify": True, "falsifier_observation": False,
         "verified": True, "items": 1},
    ]
    neg_claim = {**fixture_claim, "claim_id": "CLM-T-901"}
    neg_groups = [
        {"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
         "could_falsify": True, "falsifier_observation": True,
         "verified": True, "items": 1},
        {"origin_group": "G8", "support_mass": 0.0, "contradiction_mass": 0.9,
         "could_falsify": True, "falsifier_observation": True,
         "verified": True, "items": 1},
    ]
    return [
        {"kind": "positive",
         "failure_mode": "retrieval broken: known-true claim not supported",
         "expected": "supported",
         "representative_rationale": "same domain and difficulty class as the study claims",
         "fixture": {"claim": fixture_claim, "groups": groups}},
        {"kind": "negative",
         "failure_mode": "verification decorative: fabricated citation accepted",
         "expected": "contradicted", "representative_rationale": "",
         "fixture": {"claim": neg_claim, "groups": neg_groups}},
        {"kind": "swap",
         "failure_mode": "integrity machinery decorative: provenance swap undetected",
         "expected": None, "representative_rationale": "", "fixture": None},
    ]


# -- configuration + identity (CLM-009-03) -----------------------------------

def test_config_requires_a_named_actor():
    with pytest.raises(ConfigError, match="TEKMERION_ACTOR"):
        ServerConfig.from_env({})
    with pytest.raises(ConfigError, match="not a WS6 role"):
        ServerConfig.from_env({"TEKMERION_ACTOR": "x", "TEKMERION_ROLE": "root"})
    cfg = ServerConfig.from_env({"TEKMERION_ACTOR": "ada", "TEKMERION_ROLE": "reviewer"})
    assert (cfg.actor, cfg.role) == ("ada", "reviewer")


def test_tool_roles_are_the_ui_matrix_not_a_copy():
    for key, ui_key in (("create_study", "create_study"),
                        ("register_claim", "register_claim"),
                        ("freeze_study", "freeze"),
                        ("run_evaluation", "run"),
                        ("decide_adjudication", "decide"),
                        ("deposit_bundle", "deposit"),
                        ("export_bundle", "export")):
        assert TOOL_ROLES[key] is PERMISSIONS[ui_key]


def test_no_delete_shaped_tool_exists():
    handlers = {n for n in dir(Session) if not n.startswith("_")}
    assert not any(("delete" in n or "update" in n or "edit" in n)
                   for n in handlers)
    expected = {
        "list_studies", "create_study", "get_study_status", "register_claim",
        "list_claims", "get_claim", "withdraw_claim", "attach_citation",
        "list_adjudication_queue", "decide_adjudication",
        "record_second_review", "freeze_study", "run_evaluation",
        "get_verdicts", "export_bundle", "verify_bundle", "verify_anchor",
        "deposit_bundle", "run_checkcif", "run_codecheck", "run_grim",
        "run_statcheck", "list_adapter_runs", "register_theorem",
        "pin_faithfulness", "ingest_lean", "record_digestion",
        "record_acceptance", "get_theorem_state",
    }
    assert expected <= handlers


def test_sdk_import_is_confined_to_build_server():
    src = Path(sys.modules[Session.__module__].__file__).read_text()
    tree = ast.parse(src)
    top_level = [n for n in tree.body
                 if isinstance(n, (ast.Import, ast.ImportFrom))]
    offenders = []
    for node in top_level:
        names = [a.name for a in node.names]
        if isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        offenders += [n for n in names if n == "mcp" or n.startswith("mcp.")]
    assert offenders == []


def test_core_imports_without_the_sdk(tmp_path):
    code = (
        "import sys\n"
        "class Blocker:\n"
        "    def find_module(self, name, path=None):\n"
        "        return self if name == 'mcp' or name.startswith('mcp.') else None\n"
        "    def load_module(self, name):\n"
        "        raise ImportError('blocked for CLM-009-05 test')\n"
        "sys.meta_path.insert(0, Blocker())\n"
        "import tekmerion\n"
        "import tekmerion.mcp\n"
        "from tekmerion.mcp.server import Session\n"
        "print('imports ok without sdk')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "imports ok without sdk" in proc.stdout


# -- refusals verbatim (CLM-009-02) -------------------------------------------

def test_falsifier_refusal_is_verbatim_and_appends_nothing(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("s1", "Study One")
    n_before = len(s.ws.open("s1").events())
    with pytest.raises(RegistrationError) as ei:
        s.register_claim("s1", "CLM-T-001", "X holds", "  ",
                         margin=0.1, sufficiency_floor=1)
    assert "no falsifier" in str(ei.value)
    assert "Article II" in str(ei.value)
    assert len(s.ws.open("s1").events()) == n_before


def test_events_carry_the_configured_actor(tmp_path):
    s = make_session(tmp_path, "ada-lovelace", "researcher")
    s.create_study("s1", "Study One")
    s.register_claim("s1", "CLM-T-001", "X holds", "not-X observed",
                     margin=0.1, sufficiency_floor=1)
    snaps = [e for e in s.ws.open("s1").events()
             if e["type"] == "record.snapshot"]
    assert snaps and all(e["actor"] == "ada-lovelace" for e in snaps)


def test_role_denials(tmp_path):
    researcher = make_session(tmp_path, "ada", "researcher")
    reviewer = make_session(tmp_path, "bob", "reviewer")
    integrity = make_session(tmp_path, "ivy", "integrity")
    researcher.create_study("s1", "Study One")
    with pytest.raises(SurfaceRefusal, match="may not call freeze_study"):
        researcher.freeze_study("s1", linked_exploratory=[])
    with pytest.raises(SurfaceRefusal, match="may not call register_claim"):
        reviewer.register_claim("s1", "CLM-T-001", "X", "not-X")
    with pytest.raises(SurfaceRefusal, match="may not call decide_adjudication"):
        integrity.decide_adjudication("s1", "ADQ-001", "exclude")
    with pytest.raises(SurfaceRefusal, match="may not call run_evaluation"):
        researcher.run_evaluation("s1")


def test_withdrawal_requires_reason_and_marks_dead(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("s1", "Study One")
    s.register_claim("s1", "CLM-T-001", "X holds", "not-X",
                     margin=0.1, sufficiency_floor=1)
    with pytest.raises(SurfaceRefusal, match="requires a reason"):
        s.withdraw_claim("s1", "CLM-T-001", " ")
    s.withdraw_claim("s1", "CLM-T-001", "superseded by a narrower claim")
    claim = s.get_claim("s1", "CLM-T-001")["claim"]
    assert claim["status"] == "dead"
    assert claim["dead"]["reason"] == "superseded by a narrower claim"
    assert claim["dead"]["score"] == 0.0


# -- the full flow through handlers (CLM-009-01/07) ----------------------------

def test_full_flow_two_instances(tmp_path):
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    researcher.create_study("flow", "Flow study")

    researcher.register_claim(
        "flow", "CLM-T-001", PROP, "a powered trial finding no improvement",
        margin=0.1, sufficiency_floor=1)
    adjudicator.register_claim(
        "flow", "CLM-T-002", "the fabricated source exists",
        "the source of record holding no such work",
        margin=0.1, sufficiency_floor=1)

    good = researcher.attach_citation(
        "flow", "CIT-1", "CLM-T-001", PROP, doi="10.1000/xyz123",
        title="Auricular Stimulation and Sleep Quality",
        authors=["Ada Lovelace"], year=2024, venue="Journal of X")
    assert good["result"]["resolution"] == "resolved"
    assert good["result"]["content"] == "supports"

    bad = researcher.attach_citation(
        "flow", "CIT-2", "CLM-T-002", "a fabricated result",
        doi="10.1000/fabricated-999", title="Nonexistent Findings",
        authors=["N. Obody"], year=2024, venue="Journal of Nowhere")
    assert bad["result"]["resolution"] == "not_found"
    assert bad["pending_queue"], "fabricated citation must be quarantined"

    qid = bad["pending_queue"][0]
    with pytest.raises(SurfaceRefusal):
        researcher.decide_adjudication("flow", qid, "exclude")
    adjudicator.decide_adjudication(
        "flow", qid, "exclude", rationale="source of record holds no such work")

    with pytest.raises(SurfaceRefusal):
        researcher.freeze_study("flow", linked_exploratory=[],
                                controls=controls())
    frozen = adjudicator.freeze_study("flow", linked_exploratory=[],
                                      controls=controls())
    assert frozen["registration_hash"]

    run = adjudicator.run_evaluation("flow")
    assert run["run_verdict"] == "valid", run["invalid_reasons"]
    verdicts = {v["claim_id"]: v["verdict"] for v in run["claim_verdicts"]}
    assert verdicts["CLM-T-001"] == "supported"
    assert verdicts["CLM-T-002"] == "inconclusive"

    issued = [e for e in adjudicator.ws.open("flow").events()
              if e["type"] == "verdict.issued"]
    assert {e["payload"]["claim_id"] for e in issued} == {"CLM-T-001", "CLM-T-002"}
    assert all(e["actor"] == "grace" for e in issued)

    exported = researcher.export_bundle("flow")
    assert exported["verification"]["ok"] is True
    v = adjudicator.verify_bundle(exported["bundle_dir"])
    assert v["ok"] is True and v["failures"] == []


def test_run_after_failed_freeze_issues_nothing(tmp_path):
    """F1 regression (Spec 009 follow-up): the coordinator's skill
    exercise sequence. A refused freeze appends nothing; a run
    attempted afterwards must NOT silently re-mode to exploratory
    and issue verdicts the export then disowns as unfrozen. The run
    is INVALID with the wall reason, no verdict.issued events land,
    and export agrees. After a real freeze the same study runs,
    issues, and exports — issued verdicts are exportable."""
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    researcher.create_study("wall", "Wall study")
    researcher.register_claim(
        "wall", "CLM-T-001", PROP, "a powered trial finding no improvement",
        margin=0.1, sufficiency_floor=1)
    adjudicator.register_claim(
        "wall", "CLM-T-002", "the fabricated source exists",
        "the source of record holding no such work",
        margin=0.1, sufficiency_floor=1)

    # Default controls carry no representative rationale: the
    # confirmation freeze is refused (RT-6) and appends nothing.
    with pytest.raises(FreezeError, match="representative rationale"):
        adjudicator.freeze_study("wall", linked_exploratory=[])
    events = adjudicator.ws.open("wall").events()
    assert not [e for e in events if e["type"] == "study.frozen"]

    run = adjudicator.run_evaluation("wall")
    assert run["run_verdict"] == "invalid", run
    assert any("frozen registration" in r for r in run["invalid_reasons"])
    assert run["claim_verdicts"] == []
    events = adjudicator.ws.open("wall").events()
    assert not [e for e in events if e["type"] == "verdict.issued"]
    assert adjudicator.get_verdicts("wall")["issued"] is False

    # Export agrees with the run: nothing issued, nothing exportable.
    with pytest.raises(ExportError, match="not frozen"):
        researcher.export_bundle("wall")

    # A real freeze unblocks the chain end to end.
    adjudicator.freeze_study("wall", linked_exploratory=[],
                             controls=controls())
    run = adjudicator.run_evaluation("wall")
    assert run["run_verdict"] == "valid", run["invalid_reasons"]
    assert run["claim_verdicts"]
    exported = researcher.export_bundle("wall")
    assert exported["verification"]["ok"] is True


def test_deposit_gate_refuses_without_approver(tmp_path):
    researcher = make_session(tmp_path, "ada", "researcher",
                              deposit_root=str(tmp_path / "deposits"))
    adjudicator = make_session(tmp_path, "grace", "adjudicator",
                               deposit_root=str(tmp_path / "deposits"))
    researcher.create_study("dep", "Deposit study")
    researcher.register_claim("dep", "CLM-T-001", PROP,
                              "a powered trial finding no improvement",
                              margin=0.1, sufficiency_floor=1)
    adjudicator.register_claim("dep", "CLM-T-002", "second claim",
                               "its falsifier", margin=0.1, sufficiency_floor=1)
    adjudicator.freeze_study("dep", linked_exploratory=[], controls=controls())
    adjudicator.run_evaluation("dep")
    researcher.export_bundle("dep")

    with pytest.raises(DepositError) as ei:
        adjudicator.deposit_bundle("dep", approved_by="")
    assert "deposit refused" in str(ei.value)
    assert "adjudicator-approved" in str(ei.value)
    anchors = [e for e in adjudicator.ws.open("dep").events()
               if e["type"] == "anchor.recorded"]
    assert anchors == []

    receipt = adjudicator.deposit_bundle("dep", approved_by="grace (adjudicator)")
    assert receipt["receipt"]
    anchors = [e for e in adjudicator.ws.open("dep").events()
               if e["type"] == "anchor.recorded"]
    assert len(anchors) == 1


def test_verify_bundle_detects_tampering(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    adj = make_session(tmp_path, "grace", "adjudicator")
    s.create_study("tam", "Tamper study")
    s.register_claim("tam", "CLM-T-001", PROP, "no improvement found",
                     margin=0.1, sufficiency_floor=1)
    adj.register_claim("tam", "CLM-T-002", "second", "its falsifier",
                       margin=0.1, sufficiency_floor=1)
    adj.freeze_study("tam", linked_exploratory=[], controls=controls())
    adj.run_evaluation("tam")
    exported = s.export_bundle("tam")
    bundle = Path(exported["bundle_dir"])
    target = bundle / "claims.json"
    target.write_text(target.read_text() + " ", encoding="utf-8")
    v = s.verify_bundle(str(bundle))
    assert v["ok"] is False and v["failures"]


# -- adapter + Lean passthrough (CLM-009-08) -----------------------------------

def test_grim_run_records_impossibility_and_attaches_evidence(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("grim", "GRIM study")
    s.register_claim("grim", "CLM-T-010",
                     "the fixture's reported means are arithmetically possible",
                     "a GRIM impossibility among the fixture cases",
                     margin=0.1, sufficiency_floor=1)
    # 5.19 at n=28 is the scrutiny manual's published impossible case.
    run = s.run_grim("grim", cases=[{"label": "manual case", "mean": "5.19",
                                     "n": 28, "items": 1}],
                     claim_id="CLM-T-010", item_id="EVG-T-010",
                     origin_group="G-GRIM")
    rec = run["run"]
    assert rec["outcome"] == "run_by_us"
    assert rec["scope_claim_id"] == "CLM-008-02"
    assert any(f.get("kind") == "grim_impossibility"
               for f in rec["findings"])
    replayed = s.list_adapter_runs("grim")["runs"]
    assert replayed and replayed[0]["outcome"] == "run_by_us"
    groups = s.get_claim("grim", "CLM-T-010")["claim"]["groups"]
    assert any(g["contradiction_mass"] > 0 for g in groups)


def test_checkcif_without_binary_or_recorded_output_is_not_runnable(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("cif", "CIF study")
    run = s.run_checkcif("cif")
    assert run["run"]["outcome"] == "not_runnable_here"
    assert run["run"]["reason"]


def test_lean_ingestion_records_state_as_it_is(tmp_path):
    lean = tmp_path / "artifact.lean"
    lean.write_text("theorem t1 : True := by sorry\n", encoding="utf-8")
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("lean", "Lean study")
    out = s.ingest_lean("lean", url=lean.as_uri(), theorem_name="t1")
    ing = out["ingestion"]
    assert ing["sorry_count"] == 1
    assert ing["compile_status"] == "not_attempted"
    assert ing["sha256"]


def test_theorem_registration_and_lane2_records(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("math", "Math study")
    out = s.register_theorem("math", "CLM-M-110", "the headline result holds",
                             "Claimant", "the original problem")
    claims = out["claims"]
    assert set(claims) == {"faithful", "proof_verified", "genuinely_open",
                           "attribution", "significance", "parent"}
    assert all(c["falsifier"] for c in claims.values())
    state = s.get_theorem_state("math", "CLM-M-110")
    assert state["lane2"] == "unexplained"
    assert state["digestion"]["risk_flag"] is True
    s.record_digestion("math", "CLM-M-110", explainer="ada",
                       artifact_ref="notes/explanation.md")
    state = s.get_theorem_state("math", "CLM-M-110")
    assert state["lane2"] == "explained"
    assert state["digestion"]["risk_flag"] is False


# -- SDK shell (needs the extra) ------------------------------------------------

def test_sdk_shell_lists_every_tool():
    pytest.importorskip("mcp")
    import asyncio

    from tekmerion.mcp.server import ServerConfig, Session, build_server

    cfg = ServerConfig(workspace_root="/tmp/ws-unused", actor="ada",
                       role="researcher")
    server = build_server(Session(cfg))
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert {"register_claim", "freeze_study", "run_evaluation",
            "deposit_bundle", "verify_bundle", "run_grim",
            "ingest_lean"} <= names
    assert not any("delete" in n for n in names)


def test_sdk_shell_carries_refusals_verbatim(tmp_path):
    """CLM-009-02 on the wire: SDK 2.x masks non-ToolError exceptions
    ("Error executing tool <name>" only), so the shell converts every
    handler exception to a ToolError carrying str(exc) — the client
    must receive the engine's refusal text itself, and the refused
    call must append nothing."""
    pytest.importorskip("mcp")
    import asyncio

    from tekmerion.mcp.server import ServerConfig, Session, build_server

    cfg = ServerConfig(workspace_root=str(tmp_path / "ws"), actor="ada",
                       role="researcher")
    session = Session(cfg, connector_factory=connectors)
    server = build_server(session)

    from mcp.server.mcpserver.exceptions import ToolError

    async def probe():
        await server.call_tool("create_study", {"study_id": "wire"})
        with pytest.raises(ToolError) as ei:
            await server.call_tool("register_claim", {
                "study_id": "wire", "claim_id": "CLM-W-000",
                "statement": "a claim with an empty falsifier",
                "falsifier": "  ", "margin": 0.1, "sufficiency_floor": 1})
        return str(ei.value)

    text = asyncio.run(probe())
    assert "no falsifier — not registered (Article II)" in text, text
    events = session.ws.open("wire").events()
    assert not [e for e in events
                if "CLM-W-000" in json.dumps(e, default=str)]
    assert session.list_claims("wire")["claims"] == []
