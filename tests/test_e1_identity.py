"""Spec 005 E1 — identity core: OIDC login (T502/T503), planes and
RBAC (T508/T509), deactivation (T512 mechanism), the audit ledger
and the CMMC AU sweep (T510/T550), API keys (T511), and the F-005-01
no-local-credential audit. All against the in-process mock IdP —
no external services (Spec 005 E1 testing constraints).
"""

import ast
import json
import pathlib

import pytest

from e1_world import (
    ATTACKER_D, ATTACKER_E, ATTACKER_N, ISSUER_A, TENANT_A, USERS_A,
    build_world, login_user,
)
from tekmerion.platform import authz
from tekmerion.platform.directory import IdPConfig
from tekmerion.platform.errors import (
    AuthenticationError, AuthorizationDenied, ConfigurationError, GateDenied,
)
from tekmerion.platform.ledger import AU_EVENT_CLASSES
from tekmerion.platform.service import PLATFORM_TENANT_ID


@pytest.fixture()
def world(tmp_path):
    return build_world(tmp_path)


def tenant_ledger(w):
    return w.service._tenant_ledger(w.tenant_id)


def tenant_types(w):
    return tenant_ledger(w).event_types()


def step_up(w, session, identity, nonce="stepup-nonce"):
    config = w.service.directory.idp(identity.tenant_id, identity.issuer)
    token = w.mock.issue_token(
        issuer=identity.issuer, subject=identity.subject,
        audience=config.client_id, nonce=nonce,
        profile=USERS_A[identity.subject])
    w.service.step_up(session, id_token=token, nonce=nonce)


# -- OIDC login (T502/T503) ---------------------------------------------


def test_login_happy_path_creates_identity_without_roles(world):
    session, mallory = login_user(world, "mallory")
    assert session
    assert world.service.roles_of(mallory.identity_id, world.tenant_id) == set()
    types = tenant_types(world)
    assert "identity.created" in types
    assert "auth.login_succeeded" in types
    # The ledger carries the random actor ID, never the email (§4).
    blob = json.dumps(tenant_ledger(world).events())
    assert "mallory@uni-a.test" not in blob
    assert mallory.actor_id in blob


def test_failed_login_is_recorded(world):
    url = world.service.begin_login(world.tenant_id, world.issuer_a)
    _, state = world.mock.authorize(url, "alice")
    with pytest.raises(AuthenticationError):
        world.service.complete_login(state, "not-a-real-code")
    assert "auth.login_failed" in tenant_types(world)


def test_forged_id_token_signature_is_refused_and_recorded(world):
    world.mock.sign_key = (ATTACKER_N, ATTACKER_E, ATTACKER_D)
    with pytest.raises(AuthenticationError):
        world.login(world.tenant_id, world.issuer_a, "alice")
    assert "auth.login_failed" in tenant_types(world)


def test_expired_id_token_is_refused(world):
    world.mock.token_lifetime = -10
    with pytest.raises(AuthenticationError):
        world.login(world.tenant_id, world.issuer_a, "alice")


def test_nonce_mismatch_is_refused(world):
    config = world.service.directory.idp(world.tenant_id, world.issuer_a)
    token = world.mock.issue_token(
        issuer=world.issuer_a, subject="alice", audience=config.client_id,
        nonce="attacker-nonce", profile=USERS_A["alice"])
    with pytest.raises(AuthenticationError):
        world.service.oidc.validate_id_token(
            token, issuer=world.issuer_a, client_id=config.client_id, nonce="real-nonce")


def test_idp_client_secret_never_reaches_a_ledger(world):
    login_user(world, "alice", role=authz.RESEARCHER)
    for ledger in (tenant_ledger(world), world.service.deployment_ledger):
        blob = json.dumps(ledger.events())
        assert "test-only-uni-a-secret" not in blob
        assert "test-only-platform-secret" not in blob
    config = world.service.directory.idp(world.tenant_id, world.issuer_a)
    assert not hasattr(config, "client_secret")
    assert "secret:uni-a-idp" in json.dumps(tenant_ledger(world).events())


# -- MFA / step-up (§13.5, T503) ------------------------------------------


def test_session_without_mfa_evidence_cannot_append(world):
    from tekmerion.platform.gate import GatedStudyWriter, SessionAuth
    from tekmerion.platform.keys import LocalKeySigner
    import axiomere

    session, nomfa = login_user(world, "nomfa", role=authz.RESEARCHER)
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = world.service.begin_enrollment(session)
    world.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    from tekmerion.store import StudyStore
    store = StudyStore.create(str(world.service.root / "study.axmr"))
    writer = GatedStudyWriter(world.service, store, tenant_id=world.tenant_id, study_id="s1")
    content = {"text": "claim"}
    from tekmerion.platform.gate import canonical_intent
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id="s1", event="claim.registered", payload=content)
    with pytest.raises(GateDenied, match="MFA"):
        writer.register_claim(SessionAuth(session, signer.fingerprint, signer.sign(intent)),
                              "CLM-X", content)
    assert "authz.decision_denied" in tenant_types(world)


def test_step_up_requires_mfa_and_records(world):
    session, rudy = login_user(world, "rudy", role=authz.REVIEWER)
    step_up(world, session, rudy)
    assert "auth.stepup" in tenant_types(world)


def test_step_up_with_non_mfa_token_refused(world):
    session, nomfa = login_user(world, "nomfa", role=authz.RESEARCHER)
    config = world.service.directory.idp(world.tenant_id, world.issuer_a)
    token = world.mock.issue_token(
        issuer=world.issuer_a, subject="nomfa", audience=config.client_id,
        nonce="n", profile=USERS_A["nomfa"])
    with pytest.raises(AuthenticationError):
        world.service.step_up(session, id_token=token, nonce="n")


# -- planes and service-layer RBAC (T508/T509) -------------------------------


def test_tenant_admin_cannot_reach_platform_functions(world):
    with pytest.raises(AuthorizationDenied):
        world.service.create_tenant(world.admin_session, tenant_id="uni-b", name="B")
    assert "authz.decision_denied" in world.service.deployment_ledger.event_types()


def test_platform_admin_cannot_administer_tenant_idp(world):
    with pytest.raises(AuthorizationDenied):
        world.service.configure_idp(world.root_session, IdPConfig(
            tenant_id=world.tenant_id, issuer="https://other.test", client_id="x",
            client_secret_ref="secret:x", redirect_uri="https://x.test/cb"),
            client_secret="s")
    assert "authz.decision_denied" in tenant_types(world)


def test_researcher_cannot_grant_roles_service_layer(world):
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    _, mallory = login_user(world, "mallory")
    with pytest.raises(AuthorizationDenied):
        world.service.grant_role(alice_session, identity_id=mallory.identity_id,
                                 role=authz.ADJUDICATOR, tenant_id=world.tenant_id)


def test_role_grant_and_revoke_are_ledger_events(world):
    _, mallory = login_user(world, "mallory")
    world.service.grant_role(world.admin_session, identity_id=mallory.identity_id,
                             role=authz.REVIEWER, tenant_id=world.tenant_id)
    assert world.service.roles_of(mallory.identity_id, world.tenant_id) == {authz.REVIEWER}
    world.service.revoke_role(world.admin_session, identity_id=mallory.identity_id,
                              role=authz.REVIEWER, tenant_id=world.tenant_id)
    assert world.service.roles_of(mallory.identity_id, world.tenant_id) == set()
    types = tenant_types(world)
    assert "role.granted" in types and "role.revoked" in types


def test_cross_tenant_grant_is_refused(world):
    _, mallory = login_user(world, "mallory")
    world.service.create_tenant(world.root_session, tenant_id="uni-b", name="B")
    # Tenant A's admin holds no member-management power in tenant B:
    # the service layer refuses before any grant is recorded.
    with pytest.raises(AuthorizationDenied):
        world.service.grant_role(world.admin_session, identity_id=mallory.identity_id,
                                 role=authz.RESEARCHER, tenant_id="uni-b")


# -- deactivation (T512 mechanism; SCIM wiring is E3) --------------------------


def test_deactivated_identity_refused_at_next_request(world):
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    world.service.deactivate_identity(world.admin_session, identity_id=alice.identity_id,
                                      reason="left the institution")
    # The already-issued session is dead at the next request.
    with pytest.raises(AuthenticationError):
        world.service.begin_enrollment(session)
    # And a fresh login is refused, recorded as a failure.
    with pytest.raises(AuthenticationError):
        world.login(world.tenant_id, world.issuer_a, "alice")
    types = tenant_types(world)
    assert "identity.deactivated" in types
    assert "session.revoked" in types
    assert world.service.directory.identity(alice.identity_id).active is False


def test_logout_revokes_session(world):
    session, _ = login_user(world, "alice")
    world.service.logout(session)
    with pytest.raises(AuthenticationError):
        world.service.begin_enrollment(session)
    assert "auth.logout" in tenant_types(world)


def test_session_absolute_expiry(world):
    session, _ = login_user(world, "alice")
    world.clock_box[0] += 43201  # beyond the 12h absolute bound
    with pytest.raises(AuthenticationError):
        world.service.begin_enrollment(session)


# -- API keys (T511) --------------------------------------------------------------


def _service_principal(world):
    return world.service.create_service_identity(
        world.admin_session, tenant_id=world.tenant_id, name="bench-runner")


def test_api_key_issuance_bounds(world):
    svc_ident = _service_principal(world)
    record, secret = world.service.issue_api_key(
        world.admin_session, tenant_id=world.tenant_id,
        principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
        scopes=[authz.REGISTER_CLAIM], lifetime_seconds=3600)
    assert secret
    assert record.key_id.startswith("tk_")
    assert "apikey.issued" in tenant_types(world)
    # The secret itself is nowhere in the record.
    assert secret not in json.dumps(tenant_ledger(world).events())


def test_api_key_scopes_cannot_exceed_role_class(world):
    svc_ident = _service_principal(world)
    with pytest.raises(ConfigurationError):
        world.service.issue_api_key(
            world.admin_session, tenant_id=world.tenant_id,
            principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
            scopes=[authz.ISSUE_VERDICT], lifetime_seconds=3600)


def test_api_key_lifetime_capped_at_one_year(world):
    svc_ident = _service_principal(world)
    with pytest.raises(ConfigurationError):
        world.service.issue_api_key(
            world.admin_session, tenant_id=world.tenant_id,
            principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
            scopes=[authz.REGISTER_CLAIM], lifetime_seconds=366 * 24 * 3600)


# -- F-005-01: no local credential path ----------------------------------------------


def test_no_local_password_path_exists_in_platform_package():
    pkg = pathlib.Path(__file__).resolve().parents[1] / "src" / "tekmerion" / "platform"
    offenders = []
    for path in sorted(pkg.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if "password" in node.name.lower():
                    offenders.append(f"{path.name}:{node.name}")
    src = "\n".join(p.read_text(encoding="utf-8") for p in pkg.glob("*.py"))
    for forbidden in ("password_hash", "set_password", "check_password", "verify_password"):
        assert forbidden not in src, forbidden
    assert offenders == [], offenders


# -- CMMC AU sweep (T550) ---------------------------------------------------------------


def test_au_event_class_completeness_sweep(world):
    """Every E1 admin/auth action — including failures — must be in the
    platform audit ledgers. This battery exercises the surface; the
    assertion maps the CMMC AU classes onto what was recorded."""
    import axiomere
    from tekmerion.platform.gate import GatedStudyWriter, SessionAuth, canonical_intent
    from tekmerion.platform.keys import LocalKeySigner
    from tekmerion.store import StudyStore

    svc = world.service
    # Tenant administration (deployment ledger).
    svc.update_tenant(world.root_session, tenant_id=world.tenant_id, name="University A (renamed)")
    # Authentication failure.
    url = svc.begin_login(world.tenant_id, world.issuer_a)
    _, state = world.mock.authorize(url, "alice")
    with pytest.raises(AuthenticationError):
        svc.complete_login(state, "bogus-code")
    # Logins + identity administration.
    admin2_session = world.admin_session
    svc.update_identity(admin2_session, identity_id=world.admin.identity_id,
                        affiliation="Uni A")
    rudy_session, rudy = login_user(world, "rudy", role=authz.REVIEWER)
    svc.revoke_role(admin2_session, identity_id=rudy.identity_id,
                    role=authz.REVIEWER, tenant_id=world.tenant_id)
    svc.grant_role(admin2_session, identity_id=rudy.identity_id,
                   role=authz.REVIEWER, tenant_id=world.tenant_id)
    # Step-up + key lifecycle.
    step_up(world, rudy_session, rudy)
    seed1, _ = axiomere.generate_keypair()
    signer1 = LocalKeySigner(seed1)
    nonce = svc.begin_enrollment(rudy_session)
    rec = svc.enroll_self_key(rudy_session, public_key=signer1.public_key,
                              proof_signature=signer1.sign(nonce.encode()), nonce=nonce)
    seed2, _ = axiomere.generate_keypair()
    signer2 = LocalKeySigner(seed2)
    nonce = svc.begin_enrollment(rudy_session)
    svc.rotate_key(rudy_session, old_fingerprint=rec.fingerprint,
                   new_public_key=signer2.public_key,
                   proof_signature=signer2.sign(nonce.encode()), nonce=nonce)
    svc.revoke_key(rudy_session, key_fingerprint=signer2.fingerprint, reason="lost device")
    # Authorization denial (recorded).
    store = StudyStore.create(str(svc.root / "sweep-study.axmr"))
    writer = GatedStudyWriter(svc, store, tenant_id=world.tenant_id, study_id="sweep")
    with pytest.raises(GateDenied):
        writer.register_claim(SessionAuth(rudy_session, signer2.fingerprint, b"x" * 64),
                              "CLM-S", {"text": "t"})
    # API key lifecycle + failed use.
    svc_ident = _service_principal(world)
    record, secret = svc.issue_api_key(
        admin2_session, tenant_id=world.tenant_id,
        principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
        scopes=[authz.REGISTER_CLAIM], lifetime_seconds=3600)
    with pytest.raises(GateDenied):
        svc.authorize_api_append(record.key_id, "wrong-secret",
                                 tenant_id=world.tenant_id, action=authz.REGISTER_CLAIM)
    svc.revoke_api_key(admin2_session, tenant_id=world.tenant_id, key_id=record.key_id)
    # IdP update by the tenant admin.
    svc.configure_idp(admin2_session, IdPConfig(
        tenant_id=world.tenant_id, issuer=world.issuer_a, client_id="tekmerion-uni-a",
        client_secret_ref="secret:uni-a-idp", redirect_uri="https://uni-a.test/callback"),
        client_secret="rotated-test-secret")
    # Deactivation (closes keys, revokes sessions) + logout.
    mallory_session, mallory = login_user(world, "mallory")
    mseed, _ = axiomere.generate_keypair()
    msigner = LocalKeySigner(mseed)
    mnonce = svc.begin_enrollment(mallory_session)
    svc.enroll_self_key(mallory_session, public_key=msigner.public_key,
                        proof_signature=msigner.sign(mnonce.encode()), nonce=mnonce)
    svc.deactivate_identity(admin2_session, identity_id=mallory.identity_id, reason="sweep")
    svc.logout(rudy_session)

    recorded = set(tenant_types(world)) | set(svc.deployment_ledger.event_types())
    for cls, types in AU_EVENT_CLASSES.items():
        missing = types - recorded
        assert not missing, f"AU class {cls} unexercised event types: {sorted(missing)}"
    # Both ledgers remain hash-chain valid after the whole battery.
    assert tenant_ledger(world).verify().ok
    assert svc.deployment_ledger.verify().ok
