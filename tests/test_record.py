"""Record-service tests, including seeded-defect cases.

Per the constitution (Article VI), the defect tests are the point: each
one names the failure it exists to catch. A verification function that
cannot fail these tests would be decorative, and a run relying on it
would be INVALID."""

import json

from research_engine import EventStore, verify_log
from research_engine.record import export_events, replay


def make_store(tmp_path):
    store = EventStore(tmp_path / "study.jsonl")
    store.append("registration.frozen", {"question": "Does X hold?"}, actor="researcher-1")
    store.append(
        "claim.registered",
        {"claim_id": "CLM-EVAL-001", "statement": "X holds.", "falsifier": "Observation O."},
        actor="researcher-1",
    )
    store.append(
        "verdict.issued",
        {"claim_id": "CLM-EVAL-001", "verdict": "SUPPORTED"},
        actor="adjudicator-1",
    )
    return store


def test_append_chain_verifies(tmp_path):
    store = make_store(tmp_path)
    result = store.verify()
    assert result.ok and result.events == 3


def test_sequence_is_monotonic_and_linked(tmp_path):
    store = make_store(tmp_path)
    evs = list(store.events())
    assert [e["seq"] for e in evs] == [1, 2, 3]
    assert evs[1]["prev_hash"] == evs[0]["hash"]
    assert evs[2]["prev_hash"] == evs[1]["hash"]


def test_replay_projection(tmp_path):
    store = make_store(tmp_path)
    proj = replay(store.path)
    assert proj.valid
    assert "CLM-EVAL-001" in proj.claims
    assert proj.verdicts["CLM-EVAL-001"]["verdict"] == "SUPPORTED"


# --- Seeded defects: each must be DETECTED. If verify ever stops catching
# --- one of these, the integrity machinery is broken by definition (K2).

def test_tampered_payload_detected(tmp_path):
    store = make_store(tmp_path)
    lines = store.path.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[2])
    ev["payload"]["verdict"] = "CONTRADICTED"  # silent rewrite attempt
    lines[2] = json.dumps(ev)
    store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify_log(store.path)
    assert not result.ok and result.reason == "hash-mismatch"


def test_deleted_event_detected(tmp_path):
    store = make_store(tmp_path)
    lines = store.path.read_text(encoding="utf-8").splitlines()
    del lines[1]
    store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify_log(store.path)
    assert not result.ok and result.reason in ("seq-gap", "prev-link-mismatch", "hash-mismatch")


def test_reordered_events_detected(tmp_path):
    store = make_store(tmp_path)
    lines = store.path.read_text(encoding="utf-8").splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not verify_log(store.path).ok


def test_replay_of_tampered_log_is_invalid_and_silent(tmp_path):
    store = make_store(tmp_path)
    lines = store.path.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[0])
    ev["payload"]["question"] = "A different question entirely?"
    lines[0] = json.dumps(ev)
    store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proj = replay(store.path)
    assert not proj.valid
    assert proj.claims == {} and proj.verdicts == {}  # defective run issues no verdicts


# --- No redaction, ever (DN-005): masking was a soft delete and is removed.

def test_no_redaction_api_and_exports_are_faithful(tmp_path):
    store = make_store(tmp_path)
    assert not hasattr(store, "redact")  # the operation does not exist
    exported = export_events(store.path)
    target = [e for e in exported if e["seq"] == 2][0]
    assert target["payload"]["statement"]  # payload travels intact
    proj = replay(store.path)
    assert proj.claims.get("CLM-EVAL-001")  # projection sees it too
    assert store.verify().ok
