"""Phase 6 tests: the register-first UI (T219) through production paths.

Every test drives the real HTTP surface against the real machinery —
no mocking of the store, register, pipeline, freeze, verdicts,
export, or deposit services. The only fakes are at the transport
seams the production code itself defines (the connector's HTTP
object, the deposit transport), exactly as in Phases 4–5.

Claims under test: CLM-002-31 … CLM-002-40.
"""

import http.client
import json
import shutil
import threading
from pathlib import Path
from urllib.parse import urlencode

import pytest

pytest.importorskip("axiomere")

from tekmerion.connectors import CrossrefConnector, HttpJson
from tekmerion.deposit import LocalTransport
from tekmerion.store import StudyStore
from tekmerion.ui.server import create_server

PHASE5_DEMO = Path(__file__).resolve().parents[2] / "phase5-demo"

REAL_WORK = {
    "DOI": "10.1000/xyz123",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "Auricular stimulation improved sleep quality significantly in a controlled trial.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

META_WORK = {  # resolves and agrees, but carries no checkable content
    "DOI": "10.1000/metaonly",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


class RoutingHttp(HttpJson):
    """Same fake as Phase 4: routes by DOI substring; unknown DOIs
    raise, which the connector turns into a not-found outcome."""

    def get(self, url, headers=None):
        for marker, work in (("xyz123", REAL_WORK), ("metaonly", META_WORK)):
            if marker in url:
                return {"message": work}
        raise RuntimeError("404 from source of record")


class Client:
    def __init__(self, server):
        self.port = server.server_address[1]

    def req(self, method, path, form=None, role=None, actor=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers, body = {}, None
        if form is not None:
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if role:
            headers["X-Tekmerion-Role"] = role
        if actor:
            headers["X-Tekmerion-Actor"] = actor
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        status, headers_out = resp.status, dict(resp.getheaders())
        conn.close()
        return status, headers_out, data

    def get(self, path, **kw):
        return self.req("GET", path, **kw)

    def post(self, path, form, **kw):
        return self.req("POST", path, form=form, **kw)


@pytest.fixture()
def ui(tmp_path):
    server = create_server(
        tmp_path / "ws",
        port=0,
        connector_factory=lambda: [CrossrefConnector(http=RoutingHttp())],
        transport_factory=lambda: LocalTransport(tmp_path / "deposits"),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield Client(server), tmp_path / "ws"
    server.shutdown()


def ledger(ws_root: Path, sid: str) -> StudyStore:
    return StudyStore.open(str(ws_root / "studies" / sid / "study.axmr"))


def event_types(ws_root: Path, sid: str) -> list[str]:
    return [e["type"] for e in ledger(ws_root, sid).events()]


def make_study(client: Client, sid: str = "s1") -> None:
    status, _, _ = client.post("/studies", {"study_id": sid, "title": "Sleep study"},
                               role="researcher", actor="op-one")
    assert status == 303


CLAIM_FORM = {
    "claim_id": "CLM-T-001",
    "statement": "Auricular stimulation improves sleep quality",
    "falsifier": "A controlled trial shows no improvement in sleep quality",
    "kind": "data", "margin": "0.1", "sufficiency_floor": "1",
    "dependencies": "", "supersedes": "",
}

CITATION_FORM = {
    "citation_id": "CIT-1", "doi": "10.1000/xyz123",
    "proposition": "Auricular stimulation improves sleep quality",
    "title": "Auricular Stimulation and Sleep Quality",
    "authors": "Ada Lovelace", "year": "2024", "venue": "Journal of X",
    "dataset_id": "", "derived_from": "",
}


def register_claim(client: Client, sid: str = "s1", actor: str = "op-one",
                   **overrides) -> tuple[int, str]:
    form = {**CLAIM_FORM, **overrides}
    status, _, body = client.post(f"/studies/{sid}/claims", form,
                                  role="researcher", actor=actor)
    return status, body


def attach_citation(client: Client, sid: str = "s1", actor: str = "op-two",
                    **overrides) -> tuple[int, str]:
    form = {**CITATION_FORM, **overrides}
    status, _, body = client.post(
        f"/studies/{sid}/claims/CLM-T-001/citations", form,
        role="researcher", actor=actor)
    return status, body


def freeze_study(client: Client, sid: str = "s1") -> tuple[int, str]:
    form = {
        "mode": "confirmation", "deployment_shape": "hosted",
        "linked_exploratory": "",
        "ctl0_failure_mode": "retrieval broken: known-true claim not supported",
        "ctl0_expected": "supported",
        "ctl0_rationale": "known-answer control in the study's own domain",
        "ctl1_failure_mode": "verification decorative: fabricated citation accepted",
        "ctl1_expected": "contradicted",
        "ctl1_rationale": "planted fabrication in the study's own domain",
        "ctl2_failure_mode": "integrity machinery decorative: provenance swap undetected",
        "ctl2_expected": "", "ctl2_rationale": "the verifier is the product",
    }
    status, _, body = client.post(f"/studies/{sid}/freeze", form,
                                  role="adjudicator", actor="op-adj")
    return status, body


# ---------------------------------------------------------------- CLM-002-31

def test_register_is_the_studys_first_screen(ui):
    client, _ = ui
    make_study(client)
    status, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert status == 200
    assert "<h1>Claim register</h1>" in body
    status, _, body = client.get("/", role="researcher", actor="op-one")
    assert 'href="/studies/s1/"' in body  # the index only points at registers


# ---------------------------------------------------------------- CLM-002-32

def test_falsifier_less_registration_refused_and_appends_nothing(ui):
    client, ws = ui
    make_study(client)
    before = len(ledger(ws, "s1").events())
    status, body = register_claim(client, falsifier="")
    assert status == 200  # the refusal is rendered, not hidden behind a redirect
    assert "Registration refused." in body
    assert "CLM-T-001: no falsifier — not registered (Article II)" in body
    assert "required-missing" in body  # the falsifier field carries the state
    assert len(ledger(ws, "s1").events()) == before
    _, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert "CLM-T-001" not in body


# ---------------------------------------------------------------- CLM-002-33

def test_no_edit_or_delete_affordance_anywhere(ui):
    client, _ = ui
    make_study(client)
    register_claim(client)
    for path in ("/studies/s1/", "/studies/s1/claims/CLM-T-001",
                 "/studies/s1/queue", "/studies/s1/freeze", "/studies/s1/export"):
        _, _, body = client.get(path, role="adjudicator", actor="op-adj")
        assert ">Edit<" not in body and ">Delete<" not in body, path
        assert 'name="edit"' not in body and 'name="delete"' not in body, path


# ------------------------------------------------------- CLM-002-31/33/37 flow

def test_full_flow_event_sequence_matches_the_api_path(ui):
    client, ws = ui
    make_study(client)
    assert register_claim(client)[0] == 303
    assert attach_citation(client)[0] == 303  # second actor: the swap control can bite
    assert freeze_study(client)[0] == 303
    status, _, _ = client.post("/studies/s1/run", {}, role="adjudicator",
                               actor="op-adj")
    assert status == 303
    status, _, _ = client.post("/studies/s1/export", {}, role="researcher",
                               actor="op-one")
    assert status == 303
    assert event_types(ws, "s1") == [
        "record.snapshot", "citation.checked", "study.frozen", "checkpoint",
        "verdict.issued", "export.generated",
    ]
    _, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert "SUPPORTED" in body
    issued = [e["payload"] for e in ledger(ws, "s1").events()
              if e["type"] == "verdict.issued"]
    assert len(issued) == 1 and issued[0]["verdict"] == "supported"
    lo, hi = issued[0]["interval"]
    _, _, body = client.get("/studies/s1/freeze", role="adjudicator", actor="op-adj")
    assert "SUPPORTED" in body and f"[{lo:.2f}, {hi:.2f}]" in body


# ---------------------------------------------------------------- CLM-002-35

def test_invalid_run_renders_invalid_with_zero_claim_verdicts(ui):
    client, ws = ui
    make_study(client)
    register_claim(client)
    # A fabricated citation: not found at the source, quarantined,
    # never adjudicated — its evidence item stays unverified.
    attach_citation(client, citation_id="CIT-9", doi="10.1000/fabricated",
                    title="No Such Paper", proposition="A fabricated result")
    assert freeze_study(client)[0] == 303
    _, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert "Latest run: INVALID" in body
    assert "run invalid" in body
    assert "SUPPORTED" not in body and "INCONCLUSIVE" not in body
    _, _, body = client.get("/studies/s1/freeze", role="adjudicator", actor="op-adj")
    assert "RUN VERDICT: INVALID" in body
    assert "unverified citation in evidence for CLM-T-001: CIT-9" in body
    assert "No claim verdicts" in body
    assert "verdict.issued" not in event_types(ws, "s1")


# ---------------------------------------------------------------- CLM-002-37

def _study_with_pending_item(client: Client) -> None:
    make_study(client)
    register_claim(client)
    attach_citation(client, citation_id="CIT-9", doi="10.1000/fabricated",
                    title="No Such Paper", proposition="A fabricated result")


def test_decide_through_the_engine_and_double_decide_refused(ui):
    client, ws = ui
    _study_with_pending_item(client)
    _, _, body = client.get("/studies/s1/queue", role="adjudicator", actor="op-adj")
    assert "ADQ-001" in body and "PENDING" in body
    status, _, _ = client.post(
        "/studies/s1/queue/ADQ-001/decide",
        {"decision": "exclude", "rationale": "DOI does not resolve — fabricated"},
        role="adjudicator", actor="op-adj")
    assert status == 303
    decided = [e for e in ledger(ws, "s1").events()
               if e["type"] == "adjudication.decided"]
    assert len(decided) == 1
    assert decided[0]["actor"] == "op-adj"
    assert decided[0]["payload"]["rationale"] == "DOI does not resolve — fabricated"
    # Deciding again is refused by the engine and surfaced; nothing appends.
    status, _, body = client.post(
        "/studies/s1/queue/ADQ-001/decide",
        {"decision": "variant", "rationale": "changed my mind"},
        role="adjudicator", actor="op-adj")
    assert status == 200
    assert "already decided" in body
    assert len([e for e in ledger(ws, "s1").events()
                if e["type"] == "adjudication.decided"]) == 1


def test_second_review_recorded_under_the_reviewers_identity(ui):
    client, ws = ui
    _study_with_pending_item(client)
    client.post("/studies/s1/queue/ADQ-001/decide",
                {"decision": "exclude", "rationale": "fabricated"},
                role="adjudicator", actor="op-adj")
    # fraction 1.0 is not the default; the default draw (10%, seed 0)
    # is what the workspace registered — assert via the API instead if
    # not sampled. The UI path is exercised when sampled.
    from tekmerion.verification import pending_second_reviews
    store = ledger(ws, "s1")
    if "ADQ-001" not in pending_second_reviews(store, fraction=0.10, seed=0):
        pytest.skip("default RT-4 draw did not sample ADQ-001 in this fixture")
    status, _, _ = client.post(
        "/studies/s1/queue/ADQ-001/second-review", {"agrees": "yes"},
        role="reviewer", actor="op-rev")
    assert status == 303
    reviews = [e for e in ledger(ws, "s1").events()
               if e["type"] == "adjudication.second_review"]
    assert len(reviews) == 1 and reviews[0]["actor"] == "op-rev"


# ---------------------------------------------------------------- CLM-002-34

def test_dead_claim_renders_dead_with_reason_and_zero_score(ui):
    client, ws = ui
    make_study(client)
    register_claim(client)
    status, _, _ = client.post(
        "/studies/s1/claims/CLM-T-001/withdraw",
        {"reason": "superseded protocol made the claim untestable"},
        role="researcher", actor="op-one")
    assert status == 303
    _, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert "dead-row" in body and "DEAD" in body
    assert "superseded protocol made the claim untestable" in body
    assert "0.0" in body
    _, _, body = client.get("/studies/s1/claims/CLM-T-001",
                            role="researcher", actor="op-one")
    assert "Withdrawn" in body and "dead-statement" not in body  # detail strikes via register; panel carries reason
    assert "superseded protocol made the claim untestable" in body


# ---------------------------------------------------------------- CLM-002-36

def test_metadata_only_evidence_is_flagged_on_register_and_claim(ui):
    client, _ = ui
    make_study(client)
    register_claim(client)
    attach_citation(client, citation_id="CIT-M", doi="10.1000/metaonly")
    _, _, body = client.get("/studies/s1/", role="researcher", actor="op-one")
    assert "metadata-only" in body
    _, _, body = client.get("/studies/s1/claims/CLM-T-001",
                            role="researcher", actor="op-one")
    assert "metadata-only" in body
    assert "0 of 1 groups content-checked (0%)" in body


# ---------------------------------------------------------------- CLM-002-38

def test_integrity_view_offers_no_mutating_control_and_posts_are_refused(ui):
    client, ws = ui
    _study_with_pending_item(client)
    for path in ("/studies/s1/", "/studies/s1/register",
                 "/studies/s1/claims/CLM-T-001", "/studies/s1/queue",
                 "/studies/s1/freeze", "/studies/s1/export"):
        _, _, body = client.get(path, role="integrity", actor="op-audit")
        for marker in ("Register claim", "Check citation", "Withdraw claim",
                       'name="decision"', "Freeze registration", "Run evaluation",
                       "Export bundle"):
            assert marker not in body, (path, marker)
    before = len(ledger(ws, "s1").events())
    status, _, body = client.post(
        "/studies/s1/queue/ADQ-001/decide",
        {"decision": "exclude", "rationale": "x"},
        role="integrity", actor="op-audit")
    assert "cannot do this" in body
    assert len(ledger(ws, "s1").events()) == before


def test_researcher_cannot_decide_and_actor_comes_from_the_server_identity(ui):
    client, ws = ui
    _study_with_pending_item(client)
    before = len(ledger(ws, "s1").events())
    _, _, body = client.post(
        "/studies/s1/queue/ADQ-001/decide",
        {"decision": "exclude", "rationale": "sneaky", "actor": "op-adj"},
        role="researcher", actor="op-one")
    assert "cannot do this" in body
    assert len(ledger(ws, "s1").events()) == before


# ---------------------------------------------------------------- CLM-002-39

def test_export_refusals_and_truthful_verification(ui):
    client, ws = ui
    make_study(client)
    register_claim(client)
    # Unfrozen: the engine refuses, the refusal is the page.
    _, _, body = client.post("/studies/s1/export", {}, role="researcher",
                             actor="op-one")
    assert "not frozen" in body
    attach_citation(client)
    assert freeze_study(client)[0] == 303
    client.post("/studies/s1/run", {}, role="adjudicator", actor="op-adj")
    assert client.post("/studies/s1/export", {}, role="researcher",
                       actor="op-one")[0] == 303
    _, _, body = client.get("/studies/s1/export", role="researcher", actor="op-one")
    assert "PASS" in body  # standalone verification of the held bundle
    # Tamper with the bundle: the verifier must say so, by name.
    bundle = ws / "studies" / "s1" / "exports" / "bundle-001"
    claims_file = bundle / "claims.json"
    claims_file.write_text(claims_file.read_text() + " ", encoding="utf-8")
    _, _, body = client.post("/studies/s1/verify-bundle",
                             {"bundle_path": str(bundle)},
                             role="integrity", actor="op-audit")
    assert "Verification failed." in body


# ---------------------------------------------------------------- CLM-002-40

def test_deposit_gate_and_receipt_through_the_ui(ui):
    client, ws = ui
    make_study(client)
    register_claim(client)
    attach_citation(client)
    freeze_study(client)
    client.post("/studies/s1/run", {}, role="adjudicator", actor="op-adj")
    client.post("/studies/s1/export", {}, role="researcher", actor="op-one")
    # The approval gate is mechanical: no approver, no deposit.
    _, _, body = client.post("/studies/s1/deposit", {"approved_by": ""},
                             role="adjudicator", actor="op-adj")
    assert "adjudicator-approved actions" in body  # the engine's gate, verbatim
    assert "anchor.recorded" not in event_types(ws, "s1")
    status, _, _ = client.post("/studies/s1/deposit",
                               {"approved_by": "op-adj (adjudicator)"},
                               role="adjudicator", actor="op-adj")
    assert status == 303
    receipts = [e for e in ledger(ws, "s1").events()
                if e["type"] == "anchor.recorded"]
    assert len(receipts) == 1
    assert receipts[0]["payload"]["mechanism"] == "local-filesystem"
    _, _, body = client.get("/studies/s1/export", role="researcher", actor="op-one")
    assert "Local filesystem (test transport)" in body
    assert receipts[0]["payload"]["root"] in body


@pytest.mark.skipif(not PHASE5_DEMO.exists(),
                    reason="Phase 5 demo study not present in this checkout")
def test_demo_study_anchor_receipts_render_from_the_record(ui):
    client, ws = ui
    sid = "ar1-demo-1905"
    client.post("/studies", {"study_id": sid,
                             "title": "AR-1 demonstration — the 1905 electrodynamics paper"},
                role="researcher", actor="op-one")
    study_dir = ws / "studies" / sid
    shutil.copy(PHASE5_DEMO / "study.axmr", study_dir / "study.axmr")
    reg_doc = json.loads((PHASE5_DEMO / "bundle-v2" / "registration.json")
                         .read_text(encoding="utf-8"))
    (study_dir / "freeze.json").write_text(json.dumps(
        {"document": reg_doc, "controls": reg_doc["controls"]}), encoding="utf-8")
    _, _, body = client.get(f"/studies/{sid}/export", role="researcher",
                            actor="op-one")
    assert "10.5281/zenodo.23311479" in body          # the AR-1 receipt (seq 13)
    assert "7434209696ea39ba8e97a33b5caa0ae08928269" in body
    assert "92093186dcd717eaa823d04e5f93d99b41a35ec" in body
    assert "anchor.recorded" in body and "seq 13" in body
    assert "10.5281/zenodo.23317023" in body          # the audit re-anchor (seq 19)
    _, _, body = client.get(f"/studies/{sid}/", role="researcher", actor="op-one")
    # Phase 7 re-derivation: this page used to show "Latest run: INVALID",
    # replayed under the swap control's defective fixed lines-1/2 selection
    # (both 'researcher' in this study — a no-op exchange). The control now
    # selects the first distinct-actor pair (lines 2 and 8 here:
    # 'researcher'/'adjudicator') and detects its tamper, so a replay under
    # current machinery finds no run failure; with no verdict.issued events
    # the study presents as not-run. The historical INVALID stands as
    # issued — it is in the ledger's audit.stage_assigned event, the
    # anchored bundles, and DN-008 — and no verdicts are issued
    # retroactively. (Spec 002 Phase 7, Step 1a.)
    assert "Latest run: INVALID" not in body          # fixed control: replay is clean
    assert "Latest run: valid" not in body            # and nothing was ever issued
    assert "1 / 2" in body                            # citations resolved


def test_specimens_page_labels_its_states_as_specimens(ui):
    client, _ = ui
    _, _, body = client.get("/specimens", role="researcher", actor="op-one")
    assert "Design specimens — component states, not study data" in body
    assert "CLM-SPEC-009" in body and "dead-row" in body
