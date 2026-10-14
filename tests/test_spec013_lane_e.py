"""Spec 013 WS-5 (Lane E) regression battery: CLM-013-28 … CLM-013-35.

Each test re-runs, in repo form, the rt-d probe that demonstrated
the break: lane-2 fabrication (p10), faithfulness re-pinning (p03 /
p10), deposit self-approval (p09), the Phase 6 UI drive-by (p14),
console CSRF (p15), path fingerprinting (p10 / p11), fabricated
second reviews (p12 / p13), and the error/result-shape warts
(p08 / p11 / p12). Post-remediation every one of those attacks must
fail, and the honest flow beside it must still work.
"""

import http.client
import http.cookies
import io
import re
import threading
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

import e4_world
from tekmerion.connectors import CrossrefConnector, HttpJson
from tekmerion.console.server import ConsoleApp, create_server as console_server
from tekmerion.deposit import DepositError
from tekmerion.freeze import FreezeError
from tekmerion.mathclaims import pin_faithfulness
from tekmerion.mcp.server import ServerConfig, Session, SurfaceRefusal
from tekmerion.store import StudyStore
from tekmerion.ui import state as ui_state
from tekmerion.ui.server import create_server as ui_server
from tekmerion.verification import queue_state

REPO = Path(__file__).resolve().parents[1]

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

REAL_WORK_2 = {
    "DOI": "10.1000/abc456",
    "title": ["Beta Finding Replicates in a Second Cohort"],
    "author": [{"given": "Bea", "family": "Smith"}],
    "issued": {"date-parts": [[2024, 6, 1]]},
    "container-title": ["Journal of Y"],
    "abstract": "The beta finding replicates in the second cohort with "
                "the same effect size.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

PROP = "auricular stimulation improves sleep quality"
PROP_2 = "the beta finding replicates in the second cohort"


class RoutingHttp(HttpJson):
    def get(self, url, headers=None):
        if "xyz123" in url:
            return {"message": REAL_WORK}
        if "abc456" in url:
            return {"message": REAL_WORK_2}
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None,
                                     fp=io.BytesIO(b"{}"))


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
         "representative_rationale": "same domain and difficulty class",
         "fixture": {"claim": fixture_claim, "groups": groups}},
        {"kind": "negative",
         "failure_mode": "verification decorative: fabricated citation accepted",
         "expected": "contradicted", "representative_rationale": "",
         "fixture": {"claim": neg_claim, "groups": neg_groups}},
        {"kind": "swap",
         "failure_mode": "integrity machinery decorative: provenance swap undetected",
         "expected": None, "representative_rationale": "", "fixture": None},
    ]


def math_study(tmp_path):
    """A math study with a registered theorem, via two instances."""
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    researcher.create_study("math", "Math study")
    out = researcher.register_theorem(
        "math", "CLM-M-110", "the headline result holds",
        "Claimant", "the original problem")
    return researcher, adjudicator, out["claims"]


def note_file(tmp_path, text="a human explanation of the result\n"):
    path = tmp_path / "ws" / "studies" / "math" / "notes" / "explanation.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return "notes/explanation.md"


# ---------------------------------------------------------- CLM-013-28

def test_lane2_appends_are_adjudicator_acts(tmp_path):
    researcher, adjudicator, _ = math_study(tmp_path)
    ref = note_file(tmp_path)
    # A researcher instance cannot record digestion or acceptance,
    # even with a reference that resolves.
    with pytest.raises(SurfaceRefusal, match="may not call record_digestion"):
        researcher.record_digestion("math", "CLM-M-110", explainer="ada",
                                    artifact_ref=ref)
    with pytest.raises(SurfaceRefusal, match="may not call record_acceptance"):
        researcher.record_acceptance("math", "CLM-M-110", stage="digested",
                                     by="ada", evidence_ref=ref)
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert state["lane2"] == "unexplained"
    assert state["digestion"]["risk_flag"] is True


def test_lane2_invented_references_are_refused(tmp_path):
    """rt-d p10: invented explainer, invented artifact, invented
    approver — the appends must fail and the risk flag must stay."""
    researcher, adjudicator, _ = math_study(tmp_path)
    with pytest.raises(SurfaceRefusal, match="does not resolve"):
        adjudicator.record_digestion(
            "math", "CLM-M-110",
            explainer="A. Famous-Mathematician (invented by probe)",
            artifact_ref="no-such-artifact")
    with pytest.raises(SurfaceRefusal, match="does not resolve"):
        adjudicator.record_acceptance(
            "math", "CLM-M-110", stage="digested",
            by="The Entire Field (invented by probe)",
            evidence_ref="no-evidence-exists")
    events = adjudicator.ws.open("math").events()
    assert not [e for e in events
                if e["type"] in ("math.digestion", "math.acceptance")]
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert state["lane2"] == "unexplained"
    assert state["digestion"]["risk_flag"] is True


def test_lane2_records_name_the_recorder_beside_the_human(tmp_path):
    researcher, adjudicator, _ = math_study(tmp_path)
    ref = note_file(tmp_path)
    adjudicator.record_digestion("math", "CLM-M-110", explainer="ada",
                                 artifact_ref=ref)
    adjudicator.record_acceptance("math", "CLM-M-110", stage="accepted",
                                  by="ada", evidence_ref=ref)
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert state["lane2"] == "accepted"
    assert state["digestion"]["explainer"] == "ada"
    assert state["digestion"]["recorded_by"] == "grace"
    assert state["acceptance"]["by"] == "ada"
    assert state["acceptance"]["recorded_by"] == "grace"


def test_lane2_reference_may_be_an_ingested_artifact_url(tmp_path):
    researcher, adjudicator, _ = math_study(tmp_path)
    store = adjudicator.ws.open("math")
    from tekmerion.mathclaims import ingest_lean_artifact
    ingest_lean_artifact(
        store, url="https://example.org/proof.lean", actor="ada",
        fetcher=lambda url: b"theorem t : True := trivial\n")
    adjudicator.record_digestion(
        "math", "CLM-M-110", explainer="ada",
        artifact_ref="https://example.org/proof.lean")
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert state["digestion"]["state"] == "explained"


# ---------------------------------------------------------- CLM-013-29

def test_pin_refuses_nonexistent_claim_and_empty_fields(tmp_path):
    researcher, _, claims = math_study(tmp_path)
    faithful = claims["faithful"]["claim_id"]
    with pytest.raises(SurfaceRefusal, match="no such claim"):
        researcher.pin_faithfulness(
            "math", "CLM-M-999", formal_statement="theorem x : True",
            original_statement="x holds", original_source="the problem post")
    with pytest.raises(ValueError, match="empty"):
        researcher.pin_faithfulness(
            "math", faithful, formal_statement="",
            original_statement="", original_source="")
    store = researcher.ws.open("math")
    assert not [e for e in store.events()
                if e["type"] == "math.faithfulness_pinned"]


def test_pin_empty_fields_refused_at_the_record_layer(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    with pytest.raises(ValueError, match="empty"):
        pin_faithfulness(store, claim_id="CLM-X-1", formal_statement="  ",
                         original_statement="orig", original_source="src",
                         actor="ada")


def test_repin_is_adjudicator_only_and_history_is_surfaced(tmp_path):
    """rt-d p10: a researcher silently re-pinned a weaker pair over
    the real one. The re-pin must now be refused for a researcher,
    allowed for an adjudicator, and visible either way."""
    researcher, adjudicator, claims = math_study(tmp_path)
    faithful = claims["faithful"]["claim_id"]
    researcher.pin_faithfulness(
        "math", faithful,
        formal_statement="theorem eternal_youth : forall p, ~ages p",
        original_statement="No human ages after treatment.",
        original_source="claimant post, 2026-10-13")
    with pytest.raises(SurfaceRefusal, match="re-pin"):
        researcher.pin_faithfulness(
            "math", faithful, formal_statement="theorem trivial : True",
            original_statement="Something is true.",
            original_source="rewritten by probe")
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert "eternal_youth" in state["faithfulness_pair"]["formal_statement"]
    adjudicator.pin_faithfulness(
        "math", faithful, formal_statement="theorem trivial : True",
        original_statement="Something is true.",
        original_source="corrected by the adjudicator")
    state = researcher.get_theorem_state("math", "CLM-M-110")
    assert state["faithfulness_pair"]["formal_statement"] == \
        "theorem trivial : True"
    history = state["faithfulness_history"]
    assert len(history) == 2
    assert [h["recorded_by"] for h in history] == ["ada", "grace"]
    assert "eternal_youth" in history[0]["formal_statement"]


# ---------------------------------------------------------- CLM-013-30

def _depositable(tmp_path):
    researcher = make_session(tmp_path, "ada", "researcher",
                              deposit_root=str(tmp_path / "deposits"))
    adjudicator = make_session(tmp_path, "grace", "adjudicator",
                               deposit_root=str(tmp_path / "deposits"))
    researcher.create_study("dep", "Deposit study")
    researcher.register_claim("dep", "CLM-T-001", PROP,
                              "a powered trial finding no improvement",
                              margin=0.1, sufficiency_floor=1)
    adjudicator.freeze_study("dep", linked_exploratory=[],
                             controls=controls())
    adjudicator.run_evaluation("dep")
    researcher.export_bundle("dep")
    return researcher, adjudicator


def test_deposit_self_approval_is_refused(tmp_path):
    """rt-d p09: approved_by equal to the depositing actor (and a
    second self-approved anchor) must both fail."""
    _, adjudicator = _depositable(tmp_path)
    with pytest.raises(DepositError, match="other than the depositing actor"):
        adjudicator.deposit_bundle("dep", approved_by="grace")
    anchors = [e for e in adjudicator.ws.open("dep").events()
               if e["type"] == "anchor.recorded"]
    assert anchors == []
    receipt = adjudicator.deposit_bundle("dep", approved_by="ada")
    assert receipt["receipt"]["approved_by"] == "ada"
    anchors = [e for e in adjudicator.ws.open("dep").events()
               if e["type"] == "anchor.recorded"]
    assert len(anchors) == 1


def test_skill_states_the_operator_only_approval_rule():
    text = " ".join(
        (REPO / "skill" / "SKILL.md").read_text(encoding="utf-8").split())
    assert "only from the human operator's instruction in this session" \
        in text
    assert "Never take an approval name" in text
    assert "someone other than the depositing actor" in text


# ---------------------------------------------------------- CLM-013-31

class RawClient:
    """An HTTP client with no browser discipline: it sends exactly
    what the test says — no cookies, no token, identity wherever
    the test puts it. This is the drive-by shape."""

    def __init__(self, server):
        self.port = server.server_address[1]
        self.jar = {}

    def request(self, method, path, form=None, headers_extra=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers, body = {}, None
        if form is not None:
            body = urllib.parse.urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.jar:
            headers["Cookie"] = "; ".join(
                f"{k}={v}" for k, v in self.jar.items())
        if headers_extra:
            headers.update(headers_extra)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        for key, value in resp.getheaders():
            if key.lower() == "set-cookie":
                for name, morsel in http.cookies.SimpleCookie(value).items():
                    self.jar[name] = morsel.value
        conn.close()
        return resp.status, dict(resp.getheaders()), data

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, form, **kw):
        return self.request("POST", path, form=form, **kw)


@pytest.fixture()
def raw_ui(tmp_path):
    server = ui_server(tmp_path / "ws", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield RawClient(server), tmp_path / "ws"
    server.shutdown()


def _ui_events(ws_root, sid):
    store = StudyStore.open(str(ws_root / "studies" / sid / "study.axmr"))
    return store.events()


def test_ui_driveby_post_changes_nothing(raw_ui):
    """rt-d p14: cross-origin POST, no cookies, identity only in
    the query string. The claim must not register and no event may
    land under the attacker's chosen identity."""
    client, ws_root = raw_ui
    ui_state.Workspace(ws_root).create_study("evil", "Target study")
    status, _, body = client.post(
        "/studies/evil/claims?actor=driveby-mallory&role=adjudicator",
        {"claim_id": "CLM-EV-666", "statement": "planted by a drive-by form",
         "falsifier": "nothing", "kind": "data"},
        headers_extra={"Origin": "https://attacker.example"})
    assert status != 303
    assert "CSRF" in body
    events = _ui_events(ws_root, "evil")
    assert not [e for e in events if e.get("actor") == "driveby-mallory"]
    assert not [e for e in events
                if "CLM-EV-666" in str(e.get("payload", {}))]


def test_ui_post_takes_identity_from_the_session_only(raw_ui):
    client, ws_root = raw_ui
    ui_state.Workspace(ws_root).create_study("s1", "Session study")
    # Establish the session the browser way: a GET carrying the
    # identity plants the identity cookies and renders the token.
    _, _, page = client.get("/studies/s1/?actor=cookie-op&role=adjudicator")
    token = re.search(r'name="csrf-token" content="([0-9a-f]{64})"',
                      page).group(1)
    # A POST whose query string names somebody else still acts as
    # the session's identity — and only with the session's token.
    status, _, _ = client.post(
        "/studies/s1/claims?actor=mallory&role=researcher",
        {"claim_id": "CLM-S-001", "statement": "a claim",
         "falsifier": "its falsifier", "kind": "data",
         "csrf_token": token})
    assert status == 303
    snaps = [e for e in _ui_events(ws_root, "s1")
             if e["type"] == "record.snapshot"]
    assert snaps and all(e["actor"] == "cookie-op" for e in snaps)
    # The same session without the token is refused.
    status, _, body = client.post(
        "/studies/s1/claims",
        {"claim_id": "CLM-S-002", "statement": "a second claim",
         "falsifier": "its falsifier", "kind": "data"})
    assert status != 303 and "CSRF" in body
    assert not [e for e in _ui_events(ws_root, "s1")
                if "CLM-S-002" in str(e.get("payload", {}))]


# ---------------------------------------------------------- CLM-013-32

@pytest.fixture()
def console_world(tmp_path):
    world = e4_world.build_two_tenant_world(tmp_path)
    app = ConsoleApp(world.service)
    httpd = console_server(app, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield world, RawClient(httpd)
    httpd.shutdown()


def test_console_post_without_token_creates_nothing(console_world):
    """rt-d p15: a foreign-Origin POST with the session cookie but
    no token created a tenant server-side. It must now be refused,
    and the same POST with the session's token must work."""
    world, client = console_world
    client.jar["tekmerion_session"] = world.root_session
    status, _, body = client.post(
        "/platform/tenants",
        {"tenant_id": "csrf-one", "name": "CSRF Created",
         "shape": "hosted"},
        headers_extra={"Origin": "https://attacker.example"})
    assert "csrf-one" not in world.service.directory.tenants
    assert "CSRF" in body
    # The rendered page carries the token; with it, the POST works.
    _, _, page = client.get("/platform/tenants")
    csrf = re.search(r'name="csrf-token" content="([0-9a-f]{64})"',
                     page).group(1)
    client.post("/platform/tenants",
                {"tenant_id": "csrf-one", "name": "CSRF Created",
                 "shape": "hosted", "csrf_token": csrf})
    assert "csrf-one" in world.service.directory.tenants


# ---------------------------------------------------------- CLM-013-33

def test_ingest_lean_refuses_non_http_schemes(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("lean", "Lean study")
    for url in ("file:///etc/passwd", "file:///etc/hostname",
                "ftp://example.org/x.lean", "/etc/passwd"):
        with pytest.raises(SurfaceRefusal, match="http"):
            s.ingest_lean("lean", url=url)
    store = s.ws.open("lean")
    assert not [e for e in store.events()
                if e["type"] == "math.lean_ingested"]


def test_adapter_paths_are_confined_to_the_workspace(tmp_path):
    """rt-d p11: /etc/passwd through cif_path / manuscript_path /
    recorded_output_path produced success-shaped runs carrying the
    file's hash and length. Outside paths are refused now; a file
    inside the workspace still runs."""
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("paths", "Path study")
    with pytest.raises(SurfaceRefusal, match="inside the workspace"):
        s.run_checkcif("paths", cif_path="/etc/passwd")
    with pytest.raises(SurfaceRefusal, match="inside the workspace"):
        s.run_checkcif("paths", recorded_output_path="/etc/hostname")
    with pytest.raises(SurfaceRefusal, match="inside the workspace"):
        s.run_statcheck("paths", manuscript_path="/etc/passwd")
    outside = tmp_path / "outside.cif"
    outside.write_text("data_x\n", encoding="utf-8")
    with pytest.raises(SurfaceRefusal, match="inside the workspace"):
        s.run_checkcif("paths", cif_path="../outside.cif")
    assert s.list_adapter_runs("paths")["runs"] == []
    inside = tmp_path / "ws" / "inside.cif"
    inside.write_text("data_x\n_cell_length_a 5.0\n", encoding="utf-8")
    run = s.run_checkcif("paths", cif_path="inside.cif")
    assert run["run"]["adapter_id"]
    assert s.list_adapter_runs("paths")["runs"]


# ---------------------------------------------------------- CLM-013-34

def _study_with_decided_item(tmp_path):
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    reviewer = make_session(tmp_path, "bob", "reviewer")
    researcher.create_study("q", "Queue study")
    researcher.register_claim("q", "CLM-T-001", PROP,
                              "a powered trial finding no improvement",
                              margin=0.1, sufficiency_floor=1)
    bad = researcher.attach_citation(
        "q", "CIT-BAD", "CLM-T-001", "a fabricated result",
        doi="10.1000/fabricated-999", title="Nonexistent Findings",
        authors=["N. Obody"], year=2024, venue="Journal of Nowhere")
    qid = bad["pending_queue"][0]
    adjudicator.decide_adjudication("q", qid, "exclude",
                                    rationale="fabricated DOI")
    return researcher, adjudicator, reviewer, qid


def test_second_review_must_target_a_real_decided_item(tmp_path):
    _, _, reviewer, qid = _study_with_decided_item(tmp_path)
    with pytest.raises(ValueError, match="unknown queue item"):
        reviewer.record_second_review("q", "ADQ-999", agrees=True)
    # A second, still-pending item cannot be reviewed either.
    researcher = make_session(tmp_path, "ada", "researcher")
    bad = researcher.attach_citation(
        "q", "CIT-BAD-2", "CLM-T-001", "another fabrication",
        doi="10.1000/fabricated-1000", title="More Nonexistence",
        authors=["N. Obody"], year=2024, venue="Journal of Nowhere")
    pending_qid = bad["pending_queue"][0]
    with pytest.raises(ValueError, match="not decided"):
        reviewer.record_second_review("q", pending_qid, agrees=True)


def test_second_review_decider_cannot_review_their_own_decision(tmp_path):
    _, adjudicator, reviewer, qid = _study_with_decided_item(tmp_path)
    with pytest.raises(ValueError, match="other than the decider"):
        adjudicator.record_second_review("q", qid, agrees=True)
    event = reviewer.record_second_review("q", qid, agrees=True)
    assert event["event"]["actor"] == "bob"
    view = reviewer.list_adjudication_queue("q")
    decided = [i for i in view["decided"] if i["queue_id"] == qid]
    assert decided[0]["second_reviews"][0]["independent"] is True


def test_second_review_agrees_is_strictly_boolean(tmp_path):
    _, _, reviewer, qid = _study_with_decided_item(tmp_path)
    with pytest.raises(SurfaceRefusal, match="strictly|boolean"):
        reviewer.record_second_review("q", qid, agrees="yes")


def test_queue_projection_flags_a_legacy_self_review(tmp_path):
    """A self-review written before the gate existed (appended
    directly, as the old code allowed) is flagged not independent
    in the projection — visible, not hidden."""
    _, adjudicator, _, qid = _study_with_decided_item(tmp_path)
    store = adjudicator.ws.open("q")
    store.db.append("adjudication.second_review",
                    {"queue_id": qid, "agrees": True}, actor="grace")
    item = queue_state(store)["items"][qid]
    assert item["second_reviews"][0]["independent"] is False


# ---------------------------------------------------------- CLM-013-35

def test_oserror_surfaces_without_an_absolute_path(tmp_path):
    """rt-d p11: a 300-character study id produced a raw OS error
    naming the workspace's absolute path."""
    s = make_session(tmp_path, "ada", "researcher")
    with pytest.raises(SurfaceRefusal) as ei:
        s.create_study("a" * 300, "too long")
    assert str(tmp_path) not in str(ei.value)


def test_run_grim_refuses_an_empty_case_list(tmp_path):
    s = make_session(tmp_path, "ada", "researcher")
    s.create_study("grim", "GRIM study")
    with pytest.raises(SurfaceRefusal, match="empty"):
        s.run_grim("grim", cases=[])
    assert s.list_adapter_runs("grim")["runs"] == []


def test_confirmation_freeze_requires_the_disclosure_explicitly(tmp_path):
    """rt-d p12: an omitted linked_exploratory was indistinguishable
    from an explicit disclosure of none."""
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    researcher.create_study("frz", "Freeze study")
    researcher.register_claim("frz", "CLM-T-001", PROP,
                              "a powered trial finding no improvement",
                              margin=0.1, sufficiency_floor=1)
    researcher.attach_citation(
        "frz", "CIT-1", "CLM-T-001", PROP, doi="10.1000/xyz123",
        title="Auricular Stimulation and Sleep Quality",
        authors=["Ada Lovelace"], year=2024, venue="Journal of X")
    with pytest.raises(FreezeError, match="disclose linked exploratory"):
        adjudicator.freeze_study("frz", controls=controls())
    frozen = adjudicator.freeze_study("frz", linked_exploratory=[],
                                      controls=controls())
    assert frozen["registration_hash"]


def test_dead_claim_verdict_is_marked_not_issued(tmp_path):
    """rt-d p08/p12: the run result carried a computed verdict for
    a dead claim that the ledger never received, presented as if
    issued."""
    researcher = make_session(tmp_path, "ada", "researcher")
    adjudicator = make_session(tmp_path, "grace", "adjudicator")
    researcher.create_study("dead", "Dead claim study")
    for cid, doi, prop, title, authors, venue in (
            ("CLM-T-001", "10.1000/xyz123", PROP,
             "Auricular Stimulation and Sleep Quality",
             ["Ada Lovelace"], "Journal of X"),
            ("CLM-T-002", "10.1000/abc456", PROP_2,
             "Beta Finding Replicates in a Second Cohort",
             ["Bea Smith"], "Journal of Y")):
        researcher.register_claim(
            "dead", cid, prop, "a powered trial finding no improvement",
            margin=0.1, sufficiency_floor=1)
        researcher.attach_citation(
            "dead", f"CIT-{cid}", cid, prop, doi=doi, title=title,
            authors=authors, year=2024, venue=venue)
    adjudicator.freeze_study("dead", linked_exploratory=[],
                             controls=controls())
    researcher.withdraw_claim("dead", "CLM-T-002",
                              "withdrawn before issuance")
    run = adjudicator.run_evaluation("dead")
    assert run["run_verdict"] == "valid", run["invalid_reasons"]
    by_claim = {v["claim_id"]: v for v in run["claim_verdicts"]}
    assert by_claim["CLM-T-001"]["issued"] is True
    assert by_claim["CLM-T-002"]["issued"] is False
    assert "never issued" in by_claim["CLM-T-002"]["not_issued_reason"]
    issued = [e for e in adjudicator.ws.open("dead").events()
              if e["type"] == "verdict.issued"]
    assert {e["payload"]["claim_id"] for e in issued} == {"CLM-T-001"}
