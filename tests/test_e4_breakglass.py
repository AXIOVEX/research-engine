"""Spec 005 E4 — break-glass (T529, F-005-10).

The declared mechanism: no declaration → no invocation, by
construction; declaration is a tenant-admin act naming invoker
roles, a second-authorizer plane, scopes, and a time box under the
hard 4h ceiling; invocation mints a pending session; a second
authorizer (never the invoker) activates it; every action is a
marked event in BOTH the tenant ledger and the deployment security
log; expiry closes the session and auto-creates the post-use review
item; there is no extension — a longer need is a new session.
"""

import axiomere
import pytest

from e1_world import login_user
from e4_world import TENANT_B, build_two_tenant_world, login_b
from tekmerion.platform import authz
from tekmerion.platform.breakglass import (
    STATE_ACTIVE, STATE_CLOSED, STATE_DENIED, STATE_EXPIRED, STATE_PENDING,
)
from tekmerion.platform.errors import (
    AuthorizationDenied, ConfigurationError, GateDenied,
)
from tekmerion.platform.gate import GatedStudyWriter, SessionAuth, canonical_intent
from tekmerion.platform.keys import LocalKeySigner
from tekmerion.store import StudyStore

CLAIM = {"text": "bg battery claim", "status": "contested"}


@pytest.fixture()
def world(tmp_path):
    return build_two_tenant_world(tmp_path)


def enroll_self(svc, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = svc.begin_enrollment(session)
    rec = svc.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


def declare(world, **overrides):
    kwargs = dict(
        tenant_id=world.tenant_id,
        invoker_roles=[authz.PLATFORM_ADMIN],
        second_authorizer_plane="tenant_admin",
        max_duration_seconds=1800,
        scopes=[authz.TENANT_AUDIT_EXPORT, authz.TENANT_KEY_MANAGE],
    )
    kwargs.update(overrides)
    return world.service.declare_break_glass_policy(world.admin_session, **kwargs)


def bg_events(svc, tenant_id, event_type=None):
    events = svc._tenant_ledger(tenant_id).events()
    out = [e for e in events if e["payload"].get("break_glass")]
    if event_type:
        out = [e for e in out if e["type"] == event_type]
    return out


def test_undeclared_tenant_cannot_be_invoked(world):
    """The wireframe's undeclared state IS the requirement: with no
    declaration, invocation does not exist — refused, ledgered in
    both logs, and the tenant's posture honestly reports none."""
    svc = world.service
    with pytest.raises(GateDenied):
        svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                               reason="fire drill", duration_seconds=600)
    refused = bg_events(svc, world.tenant_id, "breakglass.invocation_refused")
    assert len(refused) == 1
    dep = [e for e in svc.deployment_ledger.events()
           if e["type"] == "breakglass.invocation_refused"]
    assert len(dep) == 1
    state = svc.break_glass_state(world.tenant_id)
    assert state["policy"] is None and state["sessions"] == []


def test_declaration_validation(world):
    svc = world.service
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    # Declaration is a tenant-admin act.
    with pytest.raises(AuthorizationDenied):
        svc.declare_break_glass_policy(
            alice_session, tenant_id=world.tenant_id,
            invoker_roles=[authz.PLATFORM_ADMIN],
            second_authorizer_plane="tenant_admin",
            max_duration_seconds=600, scopes=[authz.TENANT_AUDIT_EXPORT])
    # The 4h ceiling is not configurable up.
    with pytest.raises(ConfigurationError):
        declare(world, max_duration_seconds=4 * 3600 + 1)
    declare(world, max_duration_seconds=4 * 3600)  # exactly 4h is lawful
    # Scopes the mechanism cannot exercise cannot be declared —
    # study powers are never break-glass powers.
    with pytest.raises(ConfigurationError):
        declare(world, scopes=[authz.ISSUE_VERDICT])
    with pytest.raises(ConfigurationError):
        declare(world, scopes=[])
    with pytest.raises(ConfigurationError):
        declare(world, second_authorizer_plane="study_adjudicator")
    with pytest.raises(ConfigurationError):
        declare(world, invoker_roles=["superuser"])
    policy = declare(world)
    declared = [e for e in svc._tenant_ledger(world.tenant_id).events()
                if e["type"] == "breakglass.policy_declared"]
    assert declared and declared[-1]["payload"]["scopes"] == list(policy.scopes)


def test_dual_authorization_flow_and_actions(world, tmp_path):
    svc = world.service
    declare(world)
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    a_signer, a_record = enroll_self(svc, alice_session)

    # Invoker role not held by the caller: refused.
    with pytest.raises(GateDenied):
        svc.invoke_break_glass(world.admin_session, tenant_id=world.tenant_id,
                               reason="tenant admin is not an invoker here",
                               duration_seconds=600)
    # Time box beyond the declared maximum: refused.
    with pytest.raises(GateDenied):
        svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                               reason="too long", duration_seconds=1801)
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="ledger export during incident",
                                duration_seconds=900)
    assert bg.state == STATE_PENDING
    # A pending session confers nothing.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    # The invoker cannot be their own second authorizer.
    with pytest.raises(GateDenied):
        svc.authorize_break_glass(world.root_session, bg_session_id=bg.bg_session_id)
    denied = bg_events(svc, world.tenant_id, "breakglass.authorization_denied")
    assert denied
    # A caller outside the declared authorizer plane cannot authorize.
    with pytest.raises(GateDenied):
        svc.authorize_break_glass(alice_session, bg_session_id=bg.bg_session_id)
    # The declared plane's holder authorizes; the box starts now.
    svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)
    assert bg.state == STATE_ACTIVE
    assert bg.expires_at == world.clock_box[0] + 900
    # Use is a T554 security event at authorization.
    emitted = [e for e in svc._tenant_ledger(world.tenant_id).events()
               if e["type"] == "security.event_emitted"]
    assert any(e["payload"]["event_class"] == "security.break_glass_use"
               for e in emitted)
    # In-scope action: audit export returns the tenant's record.
    events = svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    assert any(e["type"] == "breakglass.invoked" for e in events)
    # In-scope action: key management revokes a live key — and the
    # gate then refuses that key, while history still verifies.
    svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_KEY_MANAGE,
                        key_fingerprint=a_record.fingerprint,
                        reason="compromised during incident")
    assert svc.registry(world.tenant_id).get(a_record.fingerprint).status == "revoked"
    store = StudyStore.create(str(tmp_path / "bg.axmr"))
    writer = GatedStudyWriter(svc, store, tenant_id=world.tenant_id, study_id="bg")
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id="bg", event="claim.registered", payload=CLAIM)
    with pytest.raises(GateDenied):
        writer.register_claim(
            SessionAuth(alice_session, a_record.fingerprint, a_signer.sign(intent)),
            "CLM-BG1", CLAIM)
    assert svc._tenant_ledger(world.tenant_id).verify().ok
    # Out-of-scope action: refused, ledgered, nothing changes.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_MEMBER_MANAGE,
                            identity_id=alice.identity_id)
    assert svc.directory.identity(alice.identity_id).active
    refused = bg_events(svc, world.tenant_id, "breakglass.action_refused")
    assert refused
    # Actions are marked in BOTH ledgers, tied to this session id.
    for ledger in (svc._tenant_ledger(world.tenant_id), svc.deployment_ledger):
        acts = [e for e in ledger.events() if e["type"] == "breakglass.action"]
        assert acts and all(
            e["payload"]["bg_session_id"] == bg.bg_session_id for e in acts)
    # Double authorization is impossible.
    with pytest.raises(GateDenied):
        svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)


def test_authorizer_can_deny(world):
    svc = world.service
    declare(world)
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="drill", duration_seconds=300)
    svc.deny_break_glass(world.admin_session, bg_session_id=bg.bg_session_id,
                         note="no incident in progress")
    assert bg.state == STATE_DENIED
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)


def test_expiry_closes_session_and_creates_review(world):
    svc = world.service
    declare(world, max_duration_seconds=600)
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="short drill", duration_seconds=300)
    svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)
    svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    world.clock_box[0] += 301
    # The first touch after the box runs out closes the session.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    assert bg.state == STATE_EXPIRED
    assert bg.review_item_id is not None
    created = bg_events(svc, world.tenant_id, "breakglass.review_created")
    assert created and created[-1]["payload"]["actions_taken"] == 1
    # The review is the tenant admin's recorded disposition.
    svc.record_break_glass_review(world.admin_session, tenant_id=world.tenant_id,
                                  bg_session_id=bg.bg_session_id,
                                  disposition="actions confirmed necessary")
    assert bg.review_completed
    with pytest.raises(ConfigurationError):
        svc.record_break_glass_review(world.admin_session,
                                      tenant_id=world.tenant_id,
                                      bg_session_id=bg.bg_session_id,
                                      disposition="again")
    # No extension exists: an expired session cannot be re-authorized;
    # a longer need is a new invocation under the declaration.
    with pytest.raises(GateDenied):
        svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)


def test_policy_revocation_closes_live_sessions(world):
    svc = world.service
    declare(world)
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="incident", duration_seconds=900)
    svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)
    assert bg.state == STATE_ACTIVE
    svc.revoke_break_glass_policy(world.admin_session, tenant_id=world.tenant_id)
    assert bg.state == STATE_CLOSED and bg.review_item_id is not None
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    # And with the declaration withdrawn, invocation is gone again.
    with pytest.raises(GateDenied):
        svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                               reason="again", duration_seconds=60)


def test_tenant_plane_authorizer_and_member_action(world):
    """The other authorizer plane + the member-manage action through
    the shared deactivation core: tenant admin invokes, platform
    admin authorizes, a compromised member is deactivated — and the
    event stream shows via='break-glass'."""
    svc = world.service
    declare(world,
            invoker_roles=[authz.TENANT_ADMIN],
            second_authorizer_plane="platform_admin",
            scopes=[authz.TENANT_MEMBER_MANAGE])
    bob_session, bob = login_b(world, "bob", role=authz.RESEARCHER)
    # (bob is tenant B; this declaration is tenant A's — the action
    # target must be one of A's own identities.)
    ivy_session, ivy = login_user(world, "ivy", role=authz.RESEARCHER)
    enroll_self(svc, ivy_session)
    bg = svc.invoke_break_glass(world.admin_session, tenant_id=world.tenant_id,
                                reason="ivy account takeover",
                                duration_seconds=600)
    with pytest.raises(GateDenied):
        svc.authorize_break_glass(world.admin_b_session,
                                  bg_session_id=bg.bg_session_id)
    svc.authorize_break_glass(world.root_session, bg_session_id=bg.bg_session_id)
    # Cross-tenant target: refused even under an active session.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_MEMBER_MANAGE,
                            identity_id=bob.identity_id)
    svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_MEMBER_MANAGE,
                        identity_id=ivy.identity_id, reason="takeover response")
    assert not svc.directory.identity(ivy.identity_id).active
    deactivated = [e for e in svc._tenant_ledger(world.tenant_id).events()
                   if e["type"] == "identity.deactivated"]
    assert deactivated and deactivated[-1]["payload"]["via"] == "break-glass"
    # Tenant B saw none of it.
    assert not bg_events(svc, TENANT_B)


def test_f005_10_no_use_without_audit_trail(world):
    """F-005-10, positively: run a full session, then sweep — every
    break-glass state change and every action has its audit events,
    in both ledgers; there is no path that used the session silently."""
    svc = world.service
    declare(world)
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="f10 sweep", duration_seconds=600)
    svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)
    svc.break_glass_act(bg.bg_session_id, action=authz.TENANT_AUDIT_EXPORT)
    svc.close_break_glass(world.root_session, bg_session_id=bg.bg_session_id)
    assert bg.state == STATE_CLOSED
    tenant_types = {e["type"] for e in bg_events(svc, world.tenant_id)}
    dep_types = {e["type"] for e in svc.deployment_ledger.events()
                 if e["payload"].get("break_glass")}
    expected = {"breakglass.invoked", "breakglass.authorized",
                "breakglass.action", "breakglass.session_closed",
                "breakglass.review_created"}
    assert expected <= tenant_types
    assert expected <= dep_types
    # Unknown session ids cannot act, and the refusal is on record.
    with pytest.raises(GateDenied):
        svc.break_glass_act("bg_nonexistent", action=authz.TENANT_AUDIT_EXPORT)
    dep_refusals = [e for e in svc.deployment_ledger.events()
                    if e["type"] == "breakglass.action_refused"]
    assert dep_refusals
