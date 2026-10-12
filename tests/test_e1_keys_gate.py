"""Spec 005 E1 — key lifecycle (T504/T505/T506) and the append gate
(T507), exercised on production paths: the seeded negatives from the
phase brief (unenrolled append refused; revoked-key append refused
with history still verifying) plus rotation, both custody modes,
the verdict step-up, and API-key appends (CLM-005-18).
"""

import axiomere
import pytest

from e1_world import build_world, login_user
from tekmerion.platform import authz, ed25519
from tekmerion.platform.errors import GateDenied
from tekmerion.platform.gate import (
    ApiKeyAuth, GatedStudyWriter, SessionAuth, canonical_intent,
)
from tekmerion.platform.keys import LocalKeySigner, fingerprint
from tekmerion.store import StudyStore

STUDY_ID = "study-e1"
CLAIM = {"text": "Water boils at 100C at 1 atm.", "status": "contested"}
VERDICT = {"state": "SUPPORTED", "basis": "two independent checks"}


@pytest.fixture()
def world(tmp_path):
    return build_world(tmp_path)


def make_writer(w, tmp_path):
    store = StudyStore.create(str(tmp_path / "study.axmr"))
    return GatedStudyWriter(w.service, store, tenant_id=w.tenant_id, study_id=STUDY_ID), store


def enroll_self(w, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = w.service.begin_enrollment(session)
    rec = w.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


def step_up(w, session, identity, nonce="su"):
    from e1_world import USERS_A
    config = w.service.directory.idp(identity.tenant_id, identity.issuer)
    token = w.mock.issue_token(
        issuer=identity.issuer, subject=identity.subject,
        audience=config.client_id, nonce=nonce, profile=USERS_A[identity.subject])
    w.service.step_up(session, id_token=token, nonce=nonce)


def sign_claim(signer, w, content=CLAIM):
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=w.tenant_id,
                              study_id=STUDY_ID, event="claim.registered", payload=content)
    return signer.sign(intent)


def claim_attribution(store, claim_id="CLM-1"):
    for ev in store.events():
        if ev["type"] == "record.snapshot" and ev["payload"]["record_id"] == claim_id:
            return ev["payload"]["content"]["attribution"], ev
    raise AssertionError("claim event not found")


# -- enrollment (T504) -----------------------------------------------------


def test_enrollment_requires_proof_of_possession(world):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = world.service.begin_enrollment(session)
    with pytest.raises(GateDenied, match="proof of possession"):
        world.service.enroll_self_key(
            session, public_key=signer.public_key,
            proof_signature=b"\x00" * 64, nonce=nonce)
    assert world.service.registry(world.tenant_id).keys == {}


def test_enrollment_rejects_replayed_nonce(world):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(world, session)
    nonce = world.service.begin_enrollment(session)
    seed2, _ = axiomere.generate_keypair()
    signer2 = LocalKeySigner(seed2)
    world.service.enroll_self_key(
        session, public_key=signer2.public_key,
        proof_signature=signer2.sign(nonce.encode()), nonce=nonce)
    seed3, _ = axiomere.generate_keypair()
    signer3 = LocalKeySigner(seed3)
    with pytest.raises(GateDenied, match="nonce"):
        world.service.enroll_self_key(
            session, public_key=signer3.public_key,
            proof_signature=signer3.sign(nonce.encode()), nonce=nonce)


# -- the gate: happy path + seeded negatives (T507) --------------------------


def test_self_custody_append_carries_attribution(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, rec = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    writer.register_claim(
        SessionAuth(session, signer.fingerprint, sign_claim(signer, world)), "CLM-1", CLAIM)
    attribution, ev = claim_attribution(store)
    assert attribution["actor_id"] == alice.actor_id
    assert attribution["custody"] == "self"
    assert attribution["key_fingerprint"] == signer.fingerprint
    assert attribution["role_basis"] == authz.RESEARCHER
    assert ev["actor"] == alice.actor_id
    assert store.verify().ok


def test_unenrolled_actor_append_refused_and_recorded(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    writer, store = make_writer(world, tmp_path)
    ghost_fp = fingerprint(b"\x07" * 32)
    with pytest.raises(GateDenied, match="not enrolled"):
        writer.register_claim(SessionAuth(session, ghost_fp, b"\x00" * 64), "CLM-1", CLAIM)
    assert store.events() == []  # nothing reached the record
    ledger = world.service._tenant_ledger(world.tenant_id)
    denials = [e for e in ledger.events() if e["type"] == "authz.decision_denied"]
    assert denials and denials[-1]["payload"]["actor_id"] == alice.actor_id


def test_role_denial_enforced_without_any_ui(world, tmp_path):
    # A researcher holds no verdict power; the refusal happens in the
    # service layer (the gate) — there is no UI in this test at all.
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    intent = canonical_intent(action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="verdict.issued",
                              payload={"claim_id": "CLM-1", **VERDICT})
    with pytest.raises(GateDenied):
        writer.issue_verdict(
            SessionAuth(session, signer.fingerprint, signer.sign(intent)), "CLM-1", VERDICT)
    assert [e for e in store.events() if e["type"] == "verdict.issued"] == []


def test_tampered_intent_signature_refused(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    good = sign_claim(signer, world)
    bad = bytes([good[0] ^ 1]) + good[1:]
    with pytest.raises(GateDenied, match="does not verify"):
        writer.register_claim(SessionAuth(session, signer.fingerprint, bad), "CLM-1", CLAIM)
    # A signature over a DIFFERENT payload is equally worthless here.
    other = sign_claim(signer, world, {"text": "a different claim"})
    with pytest.raises(GateDenied, match="does not verify"):
        writer.register_claim(SessionAuth(session, signer.fingerprint, other), "CLM-1", CLAIM)


def test_cross_tenant_session_cannot_append(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(world, session)
    store = StudyStore.create(str(tmp_path / "other-study.axmr"))
    foreign = GatedStudyWriter(world.service, store, tenant_id="uni-b", study_id="x")
    with pytest.raises(GateDenied, match="tenant context"):
        foreign.register_claim(
            SessionAuth(session, signer.fingerprint, sign_claim(signer, world)), "CLM-1", CLAIM)


# -- rotation + revocation (T505) ----------------------------------------------


def test_rotation_supersedes_and_history_still_verifies(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer1, rec1 = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    sig1 = sign_claim(signer1, world)
    writer.register_claim(SessionAuth(session, signer1.fingerprint, sig1), "CLM-1", CLAIM)

    seed2, _ = axiomere.generate_keypair()
    signer2 = LocalKeySigner(seed2)
    nonce = world.service.begin_enrollment(session)
    world.service.rotate_key(session, old_fingerprint=signer1.fingerprint,
                             new_public_key=signer2.public_key,
                             proof_signature=signer2.sign(nonce.encode()), nonce=nonce)
    registry = world.service.registry(world.tenant_id)
    assert registry.status(signer1.fingerprint) == "superseded"
    assert registry.status(signer2.fingerprint) == "enrolled"

    # The new key appends; the rotated-away key is refused for NEW appends.
    writer.register_claim(
        SessionAuth(session, signer2.fingerprint, sign_claim(signer2, world)), "CLM-2", CLAIM)
    with pytest.raises(GateDenied, match="superseded"):
        writer.register_claim(
            SessionAuth(session, signer1.fingerprint, sig1), "CLM-3", CLAIM)

    # But history still verifies: the CLM-1 attribution signature
    # checks out against the rotated key's public key (F-005-04).
    attribution, _ = claim_attribution(store, "CLM-1")
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    assert ed25519.verify(signer1.public_key, intent,
                          bytes.fromhex(attribution["intent_signature"]))
    assert store.verify().ok


def test_revoked_key_refused_and_history_still_verifies(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, rec = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    sig = sign_claim(signer, world)
    writer.register_claim(SessionAuth(session, signer.fingerprint, sig), "CLM-1", CLAIM)
    world.service.revoke_key(session, key_fingerprint=signer.fingerprint, reason="compromise")
    assert world.service.registry(world.tenant_id).status(signer.fingerprint) == "revoked"
    with pytest.raises(GateDenied, match="revoked"):
        writer.register_claim(SessionAuth(session, signer.fingerprint, sig), "CLM-2", CLAIM)
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    assert ed25519.verify(signer.public_key, intent, sig)
    assert store.verify().ok
    types = world.service._tenant_ledger(world.tenant_id).event_types()
    assert "key.revoked" in types


# -- verdict step-up + custody modes (T506) ---------------------------------------


def test_adjudicator_enrollment_and_verdict_need_step_up(world, tmp_path):
    session, ada = login_user(world, "ada", role=authz.ADJUDICATOR)
    writer, store = make_writer(world, tmp_path)
    with pytest.raises(GateDenied, match="step-up"):
        enroll_self(world, session)  # adjudicator enrollment without step-up
    step_up(world, session, ada, nonce="su-enroll")
    signer, _ = enroll_self(world, session)
    intent = canonical_intent(action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="verdict.issued",
                              payload={"claim_id": "CLM-1", **VERDICT})
    # The enrollment step-up ages out (freshness default 600s).
    world.clock_box[0] += 601
    with pytest.raises(GateDenied, match="step-up"):
        writer.issue_verdict(
            SessionAuth(session, signer.fingerprint, signer.sign(intent)), "CLM-1", VERDICT)
    step_up(world, session, ada, nonce="su-verdict")
    writer.issue_verdict(
        SessionAuth(session, signer.fingerprint, signer.sign(intent)), "CLM-1", VERDICT)
    verdicts = [e for e in store.events() if e["type"] == "verdict.issued"]
    assert verdicts and verdicts[0]["payload"]["attribution"]["custody"] == "self"


def test_delegated_custody_signs_in_session_and_is_recorded(world, tmp_path):
    session, ada = login_user(world, "ada", role=authz.ADJUDICATOR)
    step_up(world, session, ada, nonce="su-del")
    seed_hex, pk_hex = axiomere.generate_keypair()
    rec = world.service.enroll_delegated_key(session, seed_hex=seed_hex)
    assert rec.custody == "delegated"
    writer, store = make_writer(world, tmp_path)
    # No caller signature: the platform signer signs inside the session.
    writer.issue_verdict(SessionAuth(session, rec.fingerprint, None), "CLM-1", VERDICT)
    verdicts = [e for e in store.events() if e["type"] == "verdict.issued"]
    assert verdicts
    attribution = verdicts[0]["payload"]["attribution"]
    assert attribution["custody"] == "delegated"
    assert attribution["session_id"] is not None
    intent = canonical_intent(action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="verdict.issued",
                              payload={"claim_id": "CLM-1", **VERDICT})
    assert ed25519.verify(bytes.fromhex(pk_hex), intent,
                          bytes.fromhex(attribution["intent_signature"]))


def test_self_custody_without_signature_refused(world, tmp_path):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    with pytest.raises(GateDenied, match="requires the actor's signature"):
        writer.register_claim(SessionAuth(session, signer.fingerprint, None), "CLM-1", CLAIM)


# -- API-key appends (CLM-005-18) ---------------------------------------------------


def test_api_key_appends_are_scoped_and_attributed(world, tmp_path):
    svc_ident = world.service.create_service_identity(
        world.admin_session, tenant_id=world.tenant_id, name="bench")
    record, secret = world.service.issue_api_key(
        world.admin_session, tenant_id=world.tenant_id,
        principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
        scopes=[authz.REGISTER_CLAIM], lifetime_seconds=3600)
    writer, store = make_writer(world, tmp_path)
    writer.register_claim(ApiKeyAuth(record.key_id, secret), "CLM-1", CLAIM)
    attribution, _ = claim_attribution(store)
    assert attribution["custody"] == "api_key"
    assert attribution["actor_id"] == svc_ident.actor_id
    assert attribution["api_key_id"] == record.key_id
    # Out of scope: verdicts are beyond this key (and beyond its class).
    with pytest.raises(GateDenied, match="outside API key scopes"):
        writer.issue_verdict(ApiKeyAuth(record.key_id, secret), "CLM-1", VERDICT)
    # Revoked: refused.
    world.service.revoke_api_key(world.admin_session, tenant_id=world.tenant_id,
                                 key_id=record.key_id)
    with pytest.raises(GateDenied, match="revoked"):
        writer.register_claim(ApiKeyAuth(record.key_id, secret), "CLM-2", CLAIM)


def test_api_key_expiry_refused(world, tmp_path):
    svc_ident = world.service.create_service_identity(
        world.admin_session, tenant_id=world.tenant_id, name="bench2")
    record, secret = world.service.issue_api_key(
        world.admin_session, tenant_id=world.tenant_id,
        principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
        scopes=[authz.REGISTER_CLAIM], lifetime_seconds=60)
    writer, store = make_writer(world, tmp_path)
    world.clock_box[0] += 61
    with pytest.raises(GateDenied, match="expired"):
        writer.register_claim(ApiKeyAuth(record.key_id, secret), "CLM-1", CLAIM)
