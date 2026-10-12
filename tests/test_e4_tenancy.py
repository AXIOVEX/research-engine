"""Spec 005 E4 — tenancy hardening batteries (T526/T527/T528/T530/T532).

The systematic isolation battery: on EVERY platform surface built in
E1–E3, tenant A's context tries to see or move tenant B's artifacts,
and the platform plane and the study plane try to act in each
other's scope. Every refusal must be a refusal (typed, ledgered) and
must return zero of the other tenant's bytes; every target chain
must still verify afterwards. Plus: session/transport baseline
(T530), audit reads + verification (T526), and the reconciliation
join (T532).
"""

import axiomere
import pytest

from e1_world import build_world, login_user
from e4_world import TENANT_B, build_two_tenant_world, login_b
from tekmerion.platform import authz, ed25519
from tekmerion.platform import baseline
from tekmerion.platform.errors import (
    AuthorizationDenied, ConfigurationError, GateDenied, RateLimited,
)
from tekmerion.platform.scim import ScimAuthenticationError, ScimNotFoundError
from tekmerion.platform.gate import (
    ApiKeyAuth, GatedStudyWriter, SessionAuth, canonical_intent,
)
from tekmerion.platform.directory import IdPConfig
from tekmerion.platform.keys import LocalKeySigner
from tekmerion.store import StudyStore

CLAIM = {"text": "Isolation battery claim.", "status": "contested"}
VERDICT = {"state": "SUPPORTED", "basis": "battery"}


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


def step_up_oidc(w, session, identity, users, nonce="su-e4"):
    svc = w.service
    config = svc.directory.idp(identity.tenant_id, identity.issuer)
    profile = users[identity.subject]
    token = w.mock.issue_token(
        issuer=identity.issuer, subject=identity.subject,
        audience=config.client_id, nonce=nonce, profile=profile)
    svc.step_up(session, id_token=token, nonce=nonce)


def make_writer(svc, tmp_path, name, tenant_id, study_id):
    store = StudyStore.create(str(tmp_path / name))
    return GatedStudyWriter(svc, store, tenant_id=tenant_id,
                            study_id=study_id), store


def ledger_types(svc, tenant_id):
    if tenant_id is None:
        return set(svc.deployment_ledger.event_types())
    return set(svc._tenant_ledger(tenant_id).event_types())


# ---------------------------------------------------------------- T526

def test_admin_surfaces_are_tenant_scoped(world):
    """T526: one battery pass over the administrative/read surfaces.
    Tenant A's admin context against tenant B's artifacts: every
    operation refuses, and B's state is byte-for-byte unmoved."""
    svc = world.service
    a_admin = world.admin_session           # tenant admin of uni-a
    bob_session, bob = login_b(world, "bob", role=authz.RESEARCHER)
    _, bob_record = enroll_self(svc, bob_session)
    events_before = len(svc._tenant_ledger(TENANT_B).events())
    roles_before = set(svc.roles_of(bob.identity_id, TENANT_B))

    with pytest.raises(AuthorizationDenied):
        svc.read_tenant_audit(a_admin, tenant_id=TENANT_B)
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(a_admin, identity_id=bob.identity_id,
                       role=authz.ADJUDICATOR, tenant_id=TENANT_B)
    with pytest.raises(AuthorizationDenied):
        svc.deactivate_identity(a_admin, identity_id=bob.identity_id)
    with pytest.raises(AuthorizationDenied):
        svc.update_identity(a_admin, identity_id=bob.identity_id,
                            display_name="pwned")
    with pytest.raises(AuthorizationDenied):
        svc.configure_idp(a_admin, IdPConfig(
            tenant_id=TENANT_B, issuer=world.issuer_b, client_id="x",
            client_secret_ref="secret:x", redirect_uri="https://x.test/cb"),
            client_secret="x")
    with pytest.raises(AuthorizationDenied):
        svc.issue_api_key(a_admin, tenant_id=TENANT_B,
                          principal_identity_id=bob.identity_id,
                          role_class=authz.RESEARCHER,
                          scopes=[authz.REGISTER_CLAIM], lifetime_seconds=60)
    with pytest.raises(AuthorizationDenied):
        svc.issue_scim_token(a_admin, tenant_id=TENANT_B)
    with pytest.raises(AuthorizationDenied):
        svc.revoke_scim_token(a_admin, tenant_id=TENANT_B,
                              credential_id="whatever")
    with pytest.raises(AuthorizationDenied):
        svc.read_deployment_audit(a_admin)
    with pytest.raises(AuthorizationDenied):
        svc.declare_break_glass_policy(
            a_admin, tenant_id=TENANT_B, invoker_roles=[authz.PLATFORM_ADMIN],
            second_authorizer_plane="platform_admin",
            max_duration_seconds=600, scopes=[authz.TENANT_AUDIT_EXPORT])
    with pytest.raises(AuthorizationDenied):
        svc.register_webhook(a_admin, tenant_id=TENANT_B,
                             url="https://hooks.evil.test/x",
                             signing="hmac-sha256", event_classes=["*"])
    # A's registry does not contain B's key — the refusal is the
    # uniform unknown-key refusal, returning none of B's bytes.
    with pytest.raises(GateDenied):
        svc.revoke_key(a_admin, key_fingerprint=bob_record.fingerprint,
                       reason="cross-tenant attempt")

    # B unmoved: identity intact, roles intact, key still enrolled,
    # and B's chain still verifies. (B's ledger DID gain the denial
    # records — attempts against B are B's audit facts, by design.)
    assert svc.directory.identity(bob.identity_id).active
    assert svc.directory.identity(bob.identity_id).display_name != "pwned"
    assert set(svc.roles_of(bob.identity_id, TENANT_B)) == roles_before
    assert svc.registry(TENANT_B).get(bob_record.fingerprint).status == "enrolled"
    assert svc._tenant_ledger(TENANT_B).verify().ok
    assert len(svc._tenant_ledger(TENANT_B).events()) > events_before

    # Symmetric spot-checks in the other direction.
    with pytest.raises(AuthorizationDenied):
        svc.read_tenant_audit(world.admin_b_session, tenant_id=world.tenant_id)
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        svc.deactivate_identity(world.admin_b_session,
                                identity_id=alice.identity_id)
    assert svc._tenant_ledger(world.tenant_id).verify().ok


def test_audit_reads_and_verification_doors(world):
    """T526: audit reads exist, are plane-checked, and verification
    reports the chain state honestly."""
    svc = world.service
    events = svc.read_tenant_audit(world.admin_session,
                                   tenant_id=world.tenant_id)
    types = {e["type"] for e in events}
    assert "identity.created" in types and "auth.login_succeeded" in types
    # A study role holds no audit power (CMMC 3.3.9).
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        svc.read_tenant_audit(alice_session, tenant_id=world.tenant_id)
    with pytest.raises(AuthorizationDenied):
        svc.verify_tenant_audit(alice_session, tenant_id=world.tenant_id)
    # The platform plane may verify any tenant's chain (its door).
    assert svc.verify_tenant_audit(world.admin_session,
                                   tenant_id=world.tenant_id)["ok"]
    assert svc.verify_tenant_audit(world.root_session,
                                   tenant_id=TENANT_B)["ok"]
    assert svc.verify_deployment_audit(world.root_session)["ok"]
    with pytest.raises(AuthorizationDenied):
        svc.verify_deployment_audit(world.admin_session)


# ---------------------------------------------------------------- T527

def test_session_replay_across_tenants(world, tmp_path):
    """A session minted in tenant A presented for tenant B's study:
    refused at the binding, before any role or key question."""
    svc = world.service
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(svc, alice_session)
    writer_b, _ = make_writer(svc, tmp_path, "b-study.axmr", TENANT_B, "study-b")
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=TENANT_B,
                              study_id="study-b", event="claim.registered",
                              payload=CLAIM)
    with pytest.raises(GateDenied):
        writer_b.register_claim(
            SessionAuth(alice_session, signer.fingerprint, signer.sign(intent)),
            "CLM-B1", CLAIM)
    assert svc._tenant_ledger(TENANT_B).verify().ok


def test_cross_tenant_key_presentation(world, tmp_path):
    """Bob (tenant B identity, B session) presenting ALICE's tenant-A
    key fingerprint for a B append: B's registry has never heard of
    the key — refused, with no A bytes in the answer."""
    svc = world.service
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    _, a_record = enroll_self(svc, alice_session)
    bob_session, bob = login_b(world, "bob", role=authz.RESEARCHER)
    enroll_self(svc, bob_session)
    writer_b, _ = make_writer(svc, tmp_path, "b2.axmr", TENANT_B, "study-b")
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=TENANT_B,
                              study_id="study-b", event="claim.registered",
                              payload=CLAIM)
    with pytest.raises(GateDenied):
        writer_b.register_claim(
            SessionAuth(bob_session, a_record.fingerprint, b"\x00" * 64),
            "CLM-B2", CLAIM)


def test_scim_credential_cross_tenant_battery(world):
    """E3's provisioning credentials are tenant-bound: A's credential
    at B's endpoints is an authentication failure, ledgered in B,
    and creates nothing in B."""
    svc = world.service
    cred_a, secret_a = svc.issue_scim_token(world.admin_session,
                                            tenant_id=world.tenant_id)
    users_before = len(svc.scim_list_users(world.tenant_id, cred_a.credential_id,
                                           secret_a)[1]["Resources"])
    with pytest.raises(ScimAuthenticationError):
        svc.scim_list_users(TENANT_B, cred_a.credential_id, secret_a)
    with pytest.raises(ScimAuthenticationError):
        svc.scim_create_user(TENANT_B, cred_a.credential_id, secret_a,
                             {"userName": "intruder"})
    failures_b = [e for e in svc._tenant_ledger(TENANT_B).events()
                  if e["type"] == "scim.sync_failed"]
    assert len(failures_b) >= 2
    # Nothing was provisioned in B by the attempts.
    cred_b, secret_b = svc.issue_scim_token(world.admin_b_session,
                                            tenant_id=TENANT_B)
    listed_b = svc.scim_list_users(TENANT_B, cred_b.credential_id, secret_b)
    assert all(r["userName"] != "intruder" for r in listed_b[1]["Resources"])
    # An entirely unknown tenant is the uniform not-found, ledgered
    # in the deployment log (there is no tenant ledger to hold it).
    with pytest.raises(ScimNotFoundError):
        svc.scim_list_users("uni-zzz", cred_a.credential_id, secret_a)
    assert "scim.sync_failed" in ledger_types(svc, None)
    assert users_before >= 0


def test_api_key_cross_tenant_reuse(world):
    """A tenant-B API key presented for a tenant-A append fails as an
    authentication failure in A's ledger — the key material of B
    authenticates nothing in A."""
    svc = world.service
    svc_ident_session, svc_ident = login_b(world, "bob", role=authz.RESEARCHER)
    record, secret = svc.issue_api_key(
        world.admin_b_session, tenant_id=TENANT_B,
        principal_identity_id=svc_ident.identity_id,
        role_class=authz.RESEARCHER, scopes=[authz.REGISTER_CLAIM],
        lifetime_seconds=3600)
    with pytest.raises(GateDenied):
        svc.authorize_api_append(record.key_id, secret,
                                 tenant_id=world.tenant_id,
                                 action=authz.REGISTER_CLAIM)
    failures_a = [e for e in svc._tenant_ledger(world.tenant_id).events()
                  if e["type"] == "auth.apikey_failed"]
    assert failures_a


def test_saml_cross_tenant_battery(tmp_path):
    """The SAML door under the E4 battery (e2 world): B's assertion at
    A's ACS was refused in E2 — here the E4 rows: a SAML-born session
    of one tenant replayed into the other tenant's study append, and
    a SAML-born identity reading the other tenant's audit."""
    from e2_world import (
        ACS_A, IDP_B_ENTITY, KEY_B, SP_A, TENANT_A as SA, TENANT_B as SB,
        build_saml_world, parse_authn_request, saml_login,
    )
    w = build_saml_world(tmp_path)
    svc = w.service
    # B assertion at A's ACS: refused (uniform login failure).
    from tekmerion.platform.errors import AuthenticationError
    url = svc.begin_saml_login(SA, w.idp_a)
    state, params = parse_authn_request(url)
    resp_b = w.saml.respond(subject="bob", issuer=IDP_B_ENTITY, key=KEY_B,
                            sp_entity_id=SP_A, acs_url=ACS_A,
                            in_response_to=params["request_id"])
    with pytest.raises(AuthenticationError):
        svc.complete_saml_login(SA, w.idp_a, state, resp_b)
    # SAML-born B session replayed into an A append: the session's
    # tenant binding refuses it before any role or key question —
    # bob needs no B roles for the refusal to be the binding's.
    b_session = saml_login(w, subject="bob", tenant=SB, entity=w.idp_b)
    signer, _ = enroll_self(svc, b_session)
    store_a = StudyStore.create(str(tmp_path / "a-study.axmr"))
    writer_a = GatedStudyWriter(svc, store_a, tenant_id=SA, study_id="study-a")
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=SA,
                              study_id="study-a", event="claim.registered",
                              payload=CLAIM)
    with pytest.raises(GateDenied):
        writer_a.register_claim(
            SessionAuth(b_session, signer.fingerprint, signer.sign(intent)),
            "CLM-A1", CLAIM)
    with pytest.raises(AuthorizationDenied):
        svc.read_tenant_audit(b_session, tenant_id=SA)


def test_tenant_chains_are_independent(world):
    """Per-tenant chains: separate files, separate verification, and
    neither tenant's ledger carries the other's subject actors."""
    svc = world.service
    login_b(world, "bob", role=authz.RESEARCHER)
    login_user(world, "alice", role=authz.RESEARCHER)
    files = {p.name for p in svc.root.glob("*.axmr")}
    assert "tenant-uni-a.axmr" in files and "tenant-uni-b.axmr" in files
    a_events = svc._tenant_ledger(world.tenant_id).events()
    b_events = svc._tenant_ledger(TENANT_B).events()
    a_subjects = {e["payload"].get("subject") for e in a_events}
    b_subjects = {e["payload"].get("subject") for e in b_events}
    assert "bob" not in a_subjects and "alice" not in b_subjects
    assert svc._tenant_ledger(world.tenant_id).verify().ok
    assert svc._tenant_ledger(TENANT_B).verify().ok


# ---------------------------------------------------------------- T528

def test_cross_plane_battery(world, tmp_path):
    """F-005-09 both directions: the platform admin cannot sign study
    events; tenant actors cannot reach platform powers; a tenant
    admin cannot sign verdicts on tenant-admin power alone."""
    svc = world.service
    writer_a, store = make_writer(svc, tmp_path, "a.axmr", world.tenant_id, "study-a")
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(svc, alice_session)
    # Platform admin (root) at the study gate: no study roles anywhere.
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id="study-a", event="claim.registered",
                              payload=CLAIM)
    with pytest.raises(GateDenied):
        svc.authorize_study_append(
            world.root_session, tenant_id=world.tenant_id,
            action=authz.REGISTER_CLAIM, key_fingerprint=signer.fingerprint,
            signature=signer.sign(intent), intent=intent)
    # Platform admin at tenant-admin powers: refused.
    with pytest.raises(AuthorizationDenied):
        svc.deactivate_identity(world.root_session, identity_id=alice.identity_id)
    with pytest.raises(AuthorizationDenied):
        svc.configure_idp(world.root_session, IdPConfig(
            tenant_id=world.tenant_id, issuer=world.issuer_a, client_id="x",
            client_secret_ref="secret:x", redirect_uri="https://x.test/cb"),
            client_secret="x")
    # Tenant admin at platform powers: refused.
    with pytest.raises(AuthorizationDenied):
        svc.create_tenant(world.admin_session, tenant_id="uni-evil", name="Evil")
    with pytest.raises(AuthorizationDenied):
        svc.update_tenant(world.admin_session, tenant_id=TENANT_B, name="Renamed")
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(world.admin_session, identity_id=alice.identity_id,
                       role=authz.PLATFORM_ADMIN, tenant_id=None)
    # Tenant admin at study powers: tenant-admin is not a study role.
    with pytest.raises(GateDenied):
        writer_a.register_claim(
            SessionAuth(world.admin_session, signer.fingerprint,
                        signer.sign(intent)), "CLM-A9", CLAIM)
    verdict_intent = canonical_intent(
        action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
        study_id="study-a", event="verdict.issued", payload=VERDICT)
    with pytest.raises(GateDenied):
        svc.authorize_study_append(
            world.admin_session, tenant_id=world.tenant_id,
            action=authz.ISSUE_VERDICT, key_fingerprint=signer.fingerprint,
            signature=signer.sign(verdict_intent), intent=verdict_intent)


# ---------------------------------------------------------------- T530

def test_session_lifetime_battery(world, tmp_path):
    """Session lifetimes are enforced, not merely configured: idle
    expiry despite a valid token, activity refreshing idle, and the
    absolute cap killing a session that stays busy (§6)."""
    svc = world.service
    writer_a, _ = make_writer(svc, tmp_path, "life.axmr", world.tenant_id, "study-life")

    def append(session, signer, n):
        content = {"text": f"claim {n}", "status": "contested"}
        intent = canonical_intent(action=authz.REGISTER_CLAIM,
                                  tenant_id=world.tenant_id, study_id="study-life",
                                  event="claim.registered", payload=content)
        return writer_a.register_claim(
            SessionAuth(session, signer.fingerprint, signer.sign(intent)),
            f"CLM-L{n}", content)

    # Idle death: 1801s of silence kills the session.
    s1, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(svc, s1)
    world.clock_box[0] += 1801
    with pytest.raises(GateDenied):
        append(s1, signer, 1)

    # Activity refreshes idle — but the absolute cap (12h from THIS
    # session's creation) still ends it.
    s2, _ = login_user(world, "alice")
    t_login = world.clock_box[0]
    n = 0
    while world.clock_box[0] < t_login + 43200 - 1700:
        world.clock_box[0] += 1700
        n += 1
        append(s2, signer, 100 + n)
    world.clock_box[0] += 1701  # past the absolute cap despite activity
    with pytest.raises(GateDenied):
        append(s2, signer, 999)


def test_transport_baseline_contract():
    """The §9 baseline as data: headers present by name, cookie
    attributes present by name, TLS posture decided per scheme, and
    the shipped policy defaults equal to the spec's numbers."""
    headers = baseline.security_headers()
    for name in ("Strict-Transport-Security", "Content-Security-Policy",
                 "X-Content-Type-Options", "Referrer-Policy"):
        assert name in headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    cookie = baseline.render_session_cookie("tok123")
    for attribute in ("Secure", "HttpOnly", "SameSite=Lax", "Path=/"):
        assert attribute in cookie
    assert baseline.tls_posture("https://x.test/hook")[0] == "serve"
    posture, location = baseline.tls_posture("http://x.test/hook")
    assert posture == "redirect" and location == "https://x.test/hook"
    with pytest.raises(ConfigurationError):
        baseline.tls_posture("ftp://x.test/hook")
    assert baseline.policy_defaults_match_spec()


def test_rate_limit_battery(world):
    """Per-tenant, per-endpoint-class rate limits: trips are 429s
    with a retry hint, recorded in the tenant's ledger; classes and
    tenants are independent; the window recovers."""
    svc = world.service
    # Age out the world's own construction logins from the window.
    world.clock_box[0] += 61
    svc.directory.tenant(world.tenant_id).policy.rate_limit_per_minute = 3
    for _ in range(3):
        svc.begin_login(world.tenant_id, world.issuer_a)
    with pytest.raises(RateLimited) as excinfo:
        svc.begin_login(world.tenant_id, world.issuer_a)
    assert excinfo.value.http_status == 429
    assert excinfo.value.retry_after_seconds > 0
    trips = [e for e in svc._tenant_ledger(world.tenant_id).events()
             if e["type"] == "ratelimit.exceeded"]
    assert len(trips) == 1
    assert trips[0]["payload"]["endpoint_class"] == "auth.login"
    # Tenant B's budget is untouched.
    svc.begin_login(TENANT_B, world.issuer_b)
    # A different endpoint class in A is untouched: SCIM still answers.
    cred, secret = svc.issue_scim_token(world.admin_session,
                                        tenant_id=world.tenant_id)
    svc.scim_list_users(world.tenant_id, cred.credential_id, secret)
    # The window recovers.
    world.clock_box[0] += 61
    svc.begin_login(world.tenant_id, world.issuer_a)
    # The guard precedes authentication on the append API: with the
    # budget spent, even a bad-secret call gets the 429, not the
    # auth refusal — exhaustion is a load fact, recorded as such.
    svc.directory.tenant(world.tenant_id).policy.rate_limit_per_minute = 2
    admin_identity = svc.directory.find_identity(
        world.tenant_id, world.issuer_a, "admin-a")
    record, secret_k = svc.issue_api_key(
        world.admin_session, tenant_id=world.tenant_id,
        principal_identity_id=admin_identity.identity_id,
        role_class=authz.TENANT_ADMIN, scopes=[authz.TENANT_AUDIT_EXPORT],
        lifetime_seconds=3600)
    for _ in range(2):
        with pytest.raises(GateDenied):
            svc.authorize_api_append(record.key_id, "wrong",
                                     tenant_id=world.tenant_id,
                                     action=authz.TENANT_AUDIT_EXPORT)
    with pytest.raises(RateLimited):
        svc.authorize_api_append(record.key_id, "wrong",
                                 tenant_id=world.tenant_id,
                                 action=authz.TENANT_AUDIT_EXPORT)


# ---------------------------------------------------------------- T532

def test_reconciliation_walk(world, tmp_path):
    """The F-005-22 walk: platform events and study appends for one
    actor join ONLY on the identity↔key binding."""
    from e1_world import USERS_A
    svc = world.service
    writer_a, store = make_writer(svc, tmp_path, "walk.axmr", world.tenant_id, "study-walk")
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    a_signer, a_record = enroll_self(svc, alice_session)
    ada_session, ada = login_user(world, "ada", role=authz.ADJUDICATOR)
    step_up_oidc(world, ada_session, ada, USERS_A)
    d_signer, d_record = enroll_self(svc, ada_session)

    claim_intent = canonical_intent(action=authz.REGISTER_CLAIM,
                                    tenant_id=world.tenant_id, study_id="study-walk",
                                    event="claim.registered", payload=CLAIM)
    writer_a.register_claim(
        SessionAuth(alice_session, a_signer.fingerprint, a_signer.sign(claim_intent)),
        "CLM-W1", CLAIM)
    verdict_intent = canonical_intent(
        action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
        study_id="study-walk", event="verdict.issued",
        payload={"claim_id": "CLM-W1", **VERDICT})
    writer_a.issue_verdict(
        SessionAuth(ada_session, d_signer.fingerprint, d_signer.sign(verdict_intent)),
        "CLM-W1", VERDICT)
    study_events = store.events()

    walk = svc.reconcile_actor(world.admin_session, tenant_id=world.tenant_id,
                               actor_id=alice.actor_id, study_events=study_events)
    assert walk["identity"]["identity_id"] == alice.identity_id
    assert any(b["key_fingerprint"] == a_record.fingerprint
               for b in walk["bindings"])
    # Study-ledger shapes: a claim append is a record.snapshot
    # envelope carrying payload.record_id + content.attribution; a
    # verdict is a verdict.issued envelope with payload.attribution.
    paired = walk["paired_appends"]
    assert any(e["payload"].get("record_id") == "CLM-W1" for e in paired)
    assert all(e["type"] != "verdict.issued" for e in paired)  # ada's, not alice's
    platform_types = {e["type"] for e in walk["platform_events"]}
    assert "key.enrolled" in platform_types and "auth.login_succeeded" in platform_types
    assert not walk["key_mismatches"]

    walk_ada = svc.reconcile_actor(world.admin_session, tenant_id=world.tenant_id,
                                   actor_id=ada.actor_id, study_events=study_events)
    assert {e["type"] for e in walk_ada["paired_appends"]} == {"verdict.issued"}

    # A forged append claiming alice under ADA's key: flagged as a
    # mismatch, never paired.
    forged = {
        "type": "claim.registered", "actor": alice.actor_id,
        "payload": {"content": {"attribution": {
            "actor_id": alice.actor_id,
            "key_fingerprint": d_record.fingerprint}}},
    }
    walk2 = svc.reconcile_actor(world.admin_session, tenant_id=world.tenant_id,
                                actor_id=alice.actor_id,
                                study_events=study_events + [forged])
    assert len(walk2["key_mismatches"]) == 1
    assert all(e is not forged for e in walk2["paired_appends"])

    # Cross-tenant: alice has no identity in B — nothing pairs there.
    walk_b = svc.reconcile_actor(world.admin_b_session, tenant_id=TENANT_B,
                                 actor_id=alice.actor_id,
                                 study_events=study_events)
    assert walk_b["identity"] is None and not walk_b["paired_appends"]

    # The walk itself is an audit-plane act.
    with pytest.raises(AuthorizationDenied):
        svc.reconcile_actor(alice_session, tenant_id=world.tenant_id,
                            actor_id=alice.actor_id, study_events=study_events)
