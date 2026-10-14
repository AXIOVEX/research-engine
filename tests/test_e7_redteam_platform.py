"""Spec 013 WS-4 — the Team C red-team battery, ported (T1/T29).

Each test is a port of one probe from the 2026-10-13 platform red
team (rt-c/probes/p01..p18). Attack tests assert the refusal the
corresponding CLM-013-15..27 requires; each was verified FAILING
against the pre-remediation code. The HELD batteries (p13 SAML,
p14 OIDC, p15 SCIM, p18 hygiene) asserted refusals that already
held and must keep holding — they are regression tests here.
p08 (unsigned ledger appends) is a core/WS-1 item, not this lane;
p19 (anchor self-attestation) belongs to WS-2.
"""

import base64
import hashlib
import hmac
import json
from xml.dom import minidom

import axiomere
import pytest

from e1_world import (
    ISSUER_A, ISSUER_PLATFORM, PLATFORM_TENANT_ID, USERS_A,
    build_world, login_user,
)
from e2_world import (
    IDP_A_ENTITY, KEY_A, KEY_B, build_saml_world, parse_authn_request,
    saml_login, saml_respond, _sign_element, cert_b64,
)
from e4_world import TENANT_B, build_two_tenant_world

from tekmerion.platform import authz, compliance, ed25519
from tekmerion.platform.directory import IdPConfig
from tekmerion.platform.errors import (
    AuthenticationError, AuthorizationDenied, ConfigurationError,
    GateDenied, PlatformError, RateLimited,
)
from tekmerion.platform.gate import (
    ApiKeyAuth, GatedStudyWriter, SessionAuth, canonical_intent,
)
from tekmerion.platform.keys import LocalKeySigner, fingerprint
from tekmerion.platform.scim import ScimError
from tekmerion.store import StudyStore

STUDY_ID = "study-e7"
CLAIM = {"text": "Water boils at 100C at 1 atm.", "status": "contested"}
VERDICT = {"state": "SUPPORTED", "basis": "two independent checks"}


def step_up_now(w, session, identity, users=None):
    """The post-Spec-013 step-up ceremony: the service issues a
    single-use challenge (begin_step_up); the IdP token must carry
    that challenge as its nonce, with a fresh auth_time."""
    svc = w.service
    config = svc.directory.idp(identity.tenant_id, identity.issuer)
    profile = (users or USERS_A)[identity.subject]
    nonce = svc.begin_step_up(session)
    token = w.mock.issue_token(
        issuer=identity.issuer, subject=identity.subject,
        audience=config.client_id, nonce=nonce, profile=profile)
    svc.step_up(session, id_token=token, nonce=nonce)


def enroll_self(w, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = w.service.begin_enrollment(session)
    rec = w.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


# -- p01 (CLM-013-17): require-MFA policy enforced for admin mutations


def test_p01_admin_mutations_require_mfa_evidence(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    # nomfa authenticates with a password only (mock profile amr=["pwd"]).
    _, nomfa = login_user(w, "nomfa")
    svc.grant_role(w.root_session, identity_id=nomfa.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=w.tenant_id)
    nomfa_session = w.login(w.tenant_id, w.issuer_a, "nomfa")
    _, alice = login_user(w, "alice")
    bot = svc.create_service_identity(
        w.admin_session, tenant_id=w.tenant_id, name="p01-bot")
    attempts = [
        lambda: svc.grant_role(nomfa_session, identity_id=alice.identity_id,
                               role=authz.RESEARCHER, tenant_id=w.tenant_id),
        lambda: svc.configure_idp(nomfa_session, IdPConfig(
            tenant_id=w.tenant_id, issuer="https://idp-a2.test",
            client_id="tekmerion-uni-a2", client_secret_ref="secret:a2",
            redirect_uri="https://uni-a.test/callback"),
            client_secret="test-only"),
        lambda: svc.issue_api_key(
            nomfa_session, tenant_id=w.tenant_id,
            principal_identity_id=bot.identity_id, role_class="researcher",
            scopes=["study.register_claim"], lifetime_seconds=600),
        lambda: svc.declare_break_glass_policy(
            nomfa_session, tenant_id=w.tenant_id,
            invoker_roles=[authz.TENANT_ADMIN],
            second_authorizer_plane="tenant_admin",
            max_duration_seconds=3600,
            scopes=[authz.TENANT_AUDIT_EXPORT]),
    ]
    for attempt in attempts:
        with pytest.raises(AuthorizationDenied):
            attempt()
    assert authz.RESEARCHER not in svc.roles_of(alice.identity_id, w.tenant_id)


# -- p02 (CLM-013-16): admin-plane actions require step-up at the service


def test_p02_admin_plane_actions_require_step_up(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    _, alice = login_user(w, "alice")
    bot = svc.create_service_identity(
        w.admin_session, tenant_id=w.tenant_id, name="p02-bot")
    # Fresh logins: MFA evidence present, no step-up performed.
    admin_fresh = w.login(w.tenant_id, w.issuer_a, "admin-a")
    root_fresh = w.login(PLATFORM_TENANT_ID, ISSUER_PLATFORM, "root")
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(admin_fresh, identity_id=alice.identity_id,
                       role=authz.RESEARCHER, tenant_id=w.tenant_id)
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(root_fresh, identity_id=alice.identity_id,
                       role=authz.PLATFORM_ADMIN, tenant_id=None)
    with pytest.raises(AuthorizationDenied):
        svc.issue_api_key(
            admin_fresh, tenant_id=w.tenant_id,
            principal_identity_id=bot.identity_id, role_class="researcher",
            scopes=["study.register_claim"], lifetime_seconds=600)
    with pytest.raises(AuthorizationDenied):
        svc.declare_break_glass_policy(
            admin_fresh, tenant_id=w.tenant_id,
            invoker_roles=[authz.TENANT_ADMIN],
            second_authorizer_plane="tenant_admin",
            max_duration_seconds=3600,
            scopes=[authz.TENANT_AUDIT_EXPORT])
    # Control: after a real step-up the same actions succeed.
    step_up_now(w, admin_fresh, w.admin)
    svc.grant_role(admin_fresh, identity_id=alice.identity_id,
                   role=authz.RESEARCHER, tenant_id=w.tenant_id)
    assert authz.RESEARCHER in svc.roles_of(alice.identity_id, w.tenant_id)


# -- p03 (CLM-013-18): step-up replay / caller-asserted nonce / stale auth


def test_p03_stepup_replay_and_stale_assertion_refused(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    session, alice = login_user(w, "alice", role=authz.RESEARCHER)
    config = svc.directory.idp(w.tenant_id, w.issuer_a)

    def mint(nonce):
        return w.mock.issue_token(
            issuer=w.issuer_a, subject="alice", audience=config.client_id,
            nonce=nonce, profile=USERS_A["alice"])

    def stepped_at():
        return svc.directory.session(session).stepped_up_at

    # (a) A caller-asserted nonce is not accepted: no challenge was issued.
    with pytest.raises(AuthenticationError):
        svc.step_up(session, id_token=mint("attacker-chosen"),
                    nonce="attacker-chosen")
    assert stepped_at() is None
    # (b) The server-challenge ceremony succeeds exactly once.
    nonce = svc.begin_step_up(session)
    token1 = mint(nonce)
    svc.step_up(session, id_token=token1, nonce=nonce)
    assert stepped_at() is not None
    # (c) Replaying the same ID token against a fresh challenge fails:
    # the token's nonce is bound to the consumed challenge.
    nonce2 = svc.begin_step_up(session)
    with pytest.raises(AuthenticationError):
        svc.step_up(session, id_token=token1, nonce=nonce2)
    # (d) A token whose auth_time is 1500s old (freshness is 600s),
    # still unexpired, is refused as a stale step-up assertion.
    saved = w.clock_box[0]
    w.clock_box[0] = saved - 1500
    nonce3 = svc.begin_step_up(session)
    stale = w.mock.issue_token(
        issuer=w.issuer_a, subject="alice", audience=config.client_id,
        nonce=nonce3, profile=USERS_A["alice"], lifetime=7200)
    w.clock_box[0] = saved
    before = stepped_at()
    with pytest.raises(AuthenticationError):
        svc.step_up(session, id_token=stale, nonce=nonce3)
    assert stepped_at() == before


# -- p04 (CLM-013-15): a bearer API key alone can never issue a verdict


def test_p04_api_key_alone_cannot_issue_verdict(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    bot = svc.create_service_identity(
        w.admin_session, tenant_id=w.tenant_id, name="verdict-bot")
    svc.grant_role(w.admin_session, identity_id=bot.identity_id,
                   role=authz.ADJUDICATOR, tenant_id=w.tenant_id)
    record, secret = svc.issue_api_key(
        w.admin_session, tenant_id=w.tenant_id,
        principal_identity_id=bot.identity_id, role_class="adjudicator",
        scopes=["study.issue_verdict"],
        lifetime_seconds=3600)
    store = StudyStore.create(str(tmp_path / "study.axmr"))
    writer = GatedStudyWriter(svc, store, tenant_id=w.tenant_id,
                              study_id=STUDY_ID)
    alice_session, alice = login_user(w, "alice", role=authz.RESEARCHER)
    signer, _ = enroll_self(w, alice_session)
    intent = canonical_intent(
        action=authz.REGISTER_CLAIM, tenant_id=w.tenant_id,
        study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    writer.register_claim(
        SessionAuth(alice_session, signer.fingerprint, signer.sign(intent)),
        "CLM-1", CLAIM)
    # The bearer key alone reaches for a verdict — refused at the gate.
    with pytest.raises(GateDenied):
        writer.issue_verdict(ApiKeyAuth(record.key_id, secret),
                             "CLM-1", VERDICT)
    assert [e for e in store.events() if e["type"] == "verdict.issued"] == []
    # Control: a non-verdict append under a researcher-class key
    # still works — the refusal is verdict-class-specific.
    bot2 = svc.create_service_identity(
        w.admin_session, tenant_id=w.tenant_id, name="bench-bot")
    rec2, sec2 = svc.issue_api_key(
        w.admin_session, tenant_id=w.tenant_id,
        principal_identity_id=bot2.identity_id, role_class="researcher",
        scopes=["study.register_claim"], lifetime_seconds=3600)
    writer.register_claim(ApiKeyAuth(rec2.key_id, sec2), "CLM-2", CLAIM)
    # Control: an adjudicator's session path (enrolled key + fresh
    # step-up) still issues verdicts.
    ada_session, ada = login_user(w, "ada", role=authz.ADJUDICATOR)
    step_up_now(w, ada_session, ada)
    ada_signer, _ = enroll_self(w, ada_session)
    vint = canonical_intent(
        action=authz.ISSUE_VERDICT, tenant_id=w.tenant_id,
        study_id=STUDY_ID, event="verdict.issued",
        payload={"claim_id": "CLM-1", **VERDICT})
    writer.issue_verdict(
        SessionAuth(ada_session, ada_signer.fingerprint,
                    ada_signer.sign(vint)), "CLM-1", VERDICT)
    assert [e for e in store.events() if e["type"] == "verdict.issued"]


# -- p05 (CLM-013-19): adjudicator self-grant refused


def test_p05_adjudicator_self_grant_refused(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(w.admin_session, identity_id=w.admin.identity_id,
                       role=authz.ADJUDICATOR, tenant_id=w.tenant_id)
    assert authz.ADJUDICATOR not in svc.roles_of(
        w.admin.identity_id, w.tenant_id)
    granted = [e for e in svc._tenant_ledger(w.tenant_id).events()
               if e["type"] == "identity.role_granted"
               and e["payload"].get("identity_id") == w.admin.identity_id
               and e["payload"].get("role") == authz.ADJUDICATOR]
    assert granted == []
    # Plane separation with self as counterparty everywhere: the
    # tenant admin cannot hand THEMSELVES any further role either —
    # a self-grant of a study role through the member-manage branch
    # is refused on the same rule.
    with pytest.raises(AuthorizationDenied):
        svc.grant_role(w.admin_session, identity_id=w.admin.identity_id,
                       role=authz.RESEARCHER, tenant_id=w.tenant_id)
    assert authz.RESEARCHER not in svc.roles_of(
        w.admin.identity_id, w.tenant_id)
    # Control: granting ANOTHER identity the adjudicator role works.
    _, alice = login_user(w, "alice")
    svc.grant_role(w.admin_session, identity_id=alice.identity_id,
                   role=authz.ADJUDICATOR, tenant_id=w.tenant_id)
    assert authz.ADJUDICATOR in svc.roles_of(alice.identity_id, w.tenant_id)


# -- p06 (CLM-013-20): revoked-key re-enrollment needs a countersign


def test_p06_revoked_key_reenrollment_needs_countersign(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    # Researcher half (the adjudicator half was already guarded by
    # the T522 rule): self-service re-enrollment of the REVOKED key
    # itself must refuse for every role.
    session, alice = login_user(w, "alice", role=authz.RESEARCHER)
    signer, rec = enroll_self(w, session)
    svc.revoke_key(w.admin_session,
                   key_fingerprint=signer.fingerprint, reason="suspected leak")
    nonce = svc.begin_enrollment(session)
    with pytest.raises(GateDenied):
        svc.enroll_self_key(
            session, public_key=signer.public_key,
            proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    # Control: a NEW key still self-enrolls (reactivation path intact).
    enroll_self(w, session)
    # The way back for the revoked key is an admin countersign.
    admin_nonce = svc.begin_enrollment(session)
    svc.enroll_key_countersigned(
        w.admin_session,
        identity_id=alice.identity_id, public_key=signer.public_key,
        proof_signature=signer.sign(admin_nonce.encode()),
        nonce=admin_nonce)
    assert svc.registry(w.tenant_id).status(signer.fingerprint) == "enrolled"


# -- p07 (CLM-013-21): small-order keys refused at enrollment


def test_p07_small_order_key_refused_at_enrollment(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    session, alice = login_user(w, "alice", role=authz.RESEARCHER)
    identity_enc = b"\x01" + b"\x00" * 31  # the identity point encoding
    assert not ed25519.is_prime_order_key(identity_enc)
    seed_hex, pk_hex = axiomere.generate_keypair()
    assert ed25519.is_prime_order_key(bytes.fromhex(pk_hex))
    # Textbook forgery the bare verifier accepts for the identity key:
    # S = r, R = [r]B satisfies [S]B == R + [H(R,A,M)]A when A is the
    # identity point. Enrollment must refuse the KEY, by name.
    nonce = svc.begin_enrollment(session)
    r = int.from_bytes(hashlib.sha512(b"p07" + nonce.encode()).digest(),
                       "little") % ed25519._L
    forged = ed25519._encode_point(ed25519._scalarmult(ed25519._B, r)) \
        + r.to_bytes(32, "little")
    assert ed25519.verify(identity_enc, nonce.encode(), forged)
    with pytest.raises(GateDenied, match="prime-order|small-order"):
        svc.enroll_self_key(session, public_key=identity_enc,
                            proof_signature=forged, nonce=nonce)
    assert svc.registry(w.tenant_id).keys == {}


# -- p09 (CLM-013-22): break-glass scope is the TARGET tenant; act needs
#    the invoker's session credential


def test_p09_break_glass_target_scope_and_act_credential(tmp_path):
    from e4_world import login_b
    w = build_two_tenant_world(tmp_path)
    svc = w.service
    B = w.tenant_b
    svc.declare_break_glass_policy(
        w.admin_b_session, tenant_id=B, invoker_roles=[authz.RESEARCHER],
        second_authorizer_plane="tenant_admin", max_duration_seconds=3600,
        scopes=[authz.TENANT_MEMBER_MANAGE, authz.TENANT_AUDIT_EXPORT])
    # Alice is a researcher of tenant A only. Tenant B's policy
    # names "researcher" — a role she holds in A, not in B; her
    # home-tenant roles must not carry across (the probe's shape).
    alice_session, alice = login_user(w, "alice", role=authz.RESEARCHER)
    with pytest.raises(GateDenied):
        svc.invoke_break_glass(
            alice_session, tenant_id=B,
            reason="cross-tenant invocation probe", duration_seconds=600)
    assert svc.directory.break_glass_sessions == {}
    # Control: a researcher OF tenant B invokes, B's admin
    # authorizes (dual control intact).
    bob_session, bob = login_b(w, "bob", role=authz.RESEARCHER)
    bg = svc.invoke_break_glass(
        bob_session, tenant_id=B, reason="records access",
        duration_seconds=600)
    svc.authorize_break_glass(w.admin_b_session, bg_session_id=bg.bg_session_id)
    # Acting presents NO credential at all: refused by signature.
    with pytest.raises(TypeError):
        svc.break_glass_act(bg.bg_session_id, action="tenant.audit_export")
    # Acting with someone else's session: refused and recorded.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, session_token=alice_session,
                            action="tenant.audit_export")
    # The invoker, with their own session, acts.
    events = svc.break_glass_act(bg.bg_session_id, session_token=bob_session,
                                 action="tenant.audit_export")
    assert isinstance(events, list) and events


# -- p10 (CLM-013-23): no credential-free service reads


def test_p10_service_reads_require_authentication(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    with pytest.raises(TypeError):
        svc.break_glass_state(tenant_id=w.tenant_id)
    with pytest.raises(TypeError):
        svc.pending_deliveries()
    with pytest.raises(TypeError):
        svc.active_holds(tenant_id=w.tenant_id)
    with pytest.raises(TypeError):
        svc.residency_pin(w.tenant_id)
    with pytest.raises(PlatformError):
        svc.break_glass_state("bogus-token", tenant_id=w.tenant_id)
    with pytest.raises(PlatformError):
        svc.residency_pin("bogus-token", w.tenant_id)
    # An authenticated identity without audit access is refused too.
    alice_session, _ = login_user(w, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        svc.break_glass_state(alice_session, tenant_id=w.tenant_id)
    with pytest.raises(AuthorizationDenied):
        svc.active_holds(alice_session, tenant_id=w.tenant_id)
    # Controls: tenant admin and platform admin reads succeed.
    assert svc.break_glass_state(w.admin_session, tenant_id=w.tenant_id)
    assert svc.active_holds(w.admin_session, tenant_id=w.tenant_id) == []
    assert svc.residency_pin(w.root_session, w.tenant_id)
    assert svc.pending_deliveries(w.root_session) == []


# -- p11 (CLM-013-24): legal hold binds the break-glass export too


def test_p11_break_glass_export_refused_under_legal_hold(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    A = w.tenant_id
    hold = svc.place_legal_hold(
        w.admin_session, tenant_id=A, scope_ref=f"tenant:{A}",
        reason="litigation hold — p11", authority="Office of Counsel",
        out_dir=str(tmp_path / "hold-export"))
    # The documented tenant-plane export is refused under the hold
    # (HELD behavior, T545)...
    with pytest.raises(AuthorizationDenied):
        svc.export_tenant_audit(w.admin_session, A, str(tmp_path / "x1"))
    svc.declare_break_glass_policy(
        w.admin_session, tenant_id=A, invoker_roles=[authz.TENANT_ADMIN],
        second_authorizer_plane="platform_admin",
        max_duration_seconds=3600, scopes=[authz.TENANT_AUDIT_EXPORT])
    bg = svc.invoke_break_glass(
        w.admin_session, tenant_id=A, reason="hold bypass probe",
        duration_seconds=900)
    svc.authorize_break_glass(w.root_session, bg_session_id=bg.bg_session_id)
    # ...and the break-glass path to the same records is refused too.
    with pytest.raises(GateDenied):
        svc.break_glass_act(bg.bg_session_id, session_token=w.admin_session,
                            action="tenant.audit_export")
    # Control: the platform plane retains export under a hold (T545).
    svc.export_tenant_audit(w.root_session, A, str(tmp_path / "x2"))
    # Control: once the hold is released, the break-glass act succeeds.
    svc.release_legal_hold(w.admin_session, tenant_id=A,
                           hold_id=hold["hold_id"], note="hold lifted")
    events = svc.break_glass_act(bg.bg_session_id, session_token=w.admin_session,
                                 action="tenant.audit_export")
    assert isinstance(events, list) and events


# -- p12 (CLM-013-25): SPRS evidence links must resolve


def test_p12_sprs_evidence_links_must_resolve(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    svc.seed_control_states(w.root_session, tenant_id=None)
    base = svc.sprs_report(w.root_session, tenant_id=None)
    assert base["score"] == -156
    assert base["evidence_failures"] == []
    # A bare assertion is not a reference: refused at write.
    with pytest.raises(ConfigurationError):
        svc.set_control_state(
            w.root_session, tenant_id=None, requirement="3.13.10",
            state="implemented",
            evidence_link="operator assertion — red team probe, no artifact")
    # A platform-form link naming a POA&M item that does not exist:
    # refused at write.
    with pytest.raises(ConfigurationError):
        svc.set_control_state(
            w.root_session, tenant_id=None, requirement="3.13.10",
            state="implemented", evidence_link="poam:POAM-9999")
    # An anchored document link whose anchor names a DIFFERENT
    # requirement than the state it evidences: refused.
    with pytest.raises(ConfigurationError):
        svc.set_control_state(
            w.root_session, tenant_id=None, requirement="3.13.10",
            state="implemented",
            evidence_link=compliance.MATRIX_REF + "#3.13.6")
    # Controls: the seeded POA&M item resolves; operator-namespace
    # references remain the organization's own attested evidence and
    # are labeled as such in the computed record.
    assert svc.seed_poam_fips_item(w.root_session) == "POAM-0001"
    svc.set_control_state(
        w.root_session, tenant_id=None, requirement="3.13.11",
        state="implemented", evidence_link="poam:POAM-0001")
    report = svc.sprs_report(w.root_session, tenant_id=None)
    assert report["evidence"]["3.13.11"] == "resolved"
    assert report["evidence_failures"] == []
    svc.seed_control_states(w.admin_session, tenant_id=w.tenant_id)
    svc.set_control_state(
        w.admin_session, tenant_id=w.tenant_id, requirement="3.13.6",
        state="implemented", evidence_link="org/network-rules-2026-10")
    tenant_report = svc.sprs_report(w.admin_session, tenant_id=w.tenant_id)
    assert tenant_report["evidence"]["3.13.6"] == "operator-attested"


# -- p16 (CLM-013-26): duplicate create_tenant refused, nothing reset


def test_p16_create_tenant_duplicate_refused(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    # The probe's tenant: pinned, marked, hardened, and under hold.
    svc.create_tenant(w.root_session, tenant_id="uni-c",
                      name="University C", shape="self-hosted",
                      region="eu-central")
    svc.provision_tenant_idp(w.root_session, IdPConfig(
        tenant_id="uni-c", issuer=w.issuer_a, client_id="tekmerion-uni-c",
        client_secret_ref="secret:uni-c-idp",
        redirect_uri="https://uni-c.test/callback"), client_secret="probe")
    c_session = w.login("uni-c", w.issuer_a, "admin-a")
    c_admin = svc.directory.find_identity("uni-c", w.issuer_a, "admin-a")
    svc.grant_role(w.root_session, identity_id=c_admin.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id="uni-c")
    c_session = w.login("uni-c", w.issuer_a, "admin-a")
    svc.set_tenant_marking(c_session, "uni-c", category="CUI",
                           authority="probe", dissemination="SP-PRVC")
    tenant_c = svc.directory.tenant("uni-c")
    tenant_c.policy.rate_limit_per_minute = 5  # hardened by the tenant
    svc.place_legal_hold(c_session, tenant_id="uni-c",
                         scope_ref="tenant:uni-c", reason="probe hold",
                         authority="Counsel",
                         out_dir=str(tmp_path / "hold-c"))
    before = len(svc.deployment_ledger.events())
    with pytest.raises(ConfigurationError):
        svc.create_tenant(w.root_session, tenant_id="uni-c",
                          name="University C (recreated)")
    after = svc.directory.tenant("uni-c")
    assert after.name == "University C"
    assert after.region == "eu-central"
    assert after.shape == "self-hosted"
    assert after.cui_marking.get("category") == "CUI"
    assert after.policy.rate_limit_per_minute == 5
    new_events = svc.deployment_ledger.events()[before:]
    assert any(e["type"] == "authz.decision_denied"
               and e["payload"].get("target") == "tenant:uni-c"
               for e in new_events)
    # The hold still stands; the pin still reports as recorded.
    assert svc.active_holds(w.root_session, tenant_id="uni-c")
    assert svc.residency_pin(w.root_session, "uni-c")["region"] == "eu-central"


# -- p17 (CLM-013-27): unknown-tenant SCIM ledgering is rate-limited


def test_p17_unknown_tenant_scim_failures_rate_limited(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    before = len(svc.deployment_ledger.events())
    limited = 0
    refused = 0
    for i in range(30):
        try:
            svc.scim_list_users(f"ghost-tenant-{i}", "cred-x", "secret-x")
        except RateLimited:
            limited += 1
        except ScimError:
            refused += 1
    growth = len(svc.deployment_ledger.events()) - before
    assert refused >= 1          # early probes are ledgered, as before
    assert limited >= 1          # then the flood is cut off
    assert growth <= 10          # bounded regardless of tenant rotation
    # Control: the known tenant's SCIM door still works.
    cred, secret = svc.issue_scim_token(w.admin_session, tenant_id=w.tenant_id)
    status, _ = svc.scim_list_users(
        w.tenant_id, cred.credential_id, secret)
    assert status == 200


# -- p13 (HELD regression): the SAML battery still refuses


def test_p13_saml_battery_held(tmp_path):
    w = build_saml_world(tmp_path)
    svc = w.service
    A = "uni-a"
    token = saml_login(w, "alice")
    assert token

    def login_with(**kw):
        url = svc.begin_saml_login(A, IDP_A_ENTITY)
        state, resp = saml_respond(w, url, "alice", **kw)
        return svc.complete_saml_login(A, IDP_A_ENTITY, state, resp)

    attacks = [
        ("unsigned assertion", dict(sign_assertion=False)),
        ("response signed only", dict(sign_assertion=False, sign_response=True)),
        ("attacker key", dict(key=KEY_B)),
        ("keyinfo cert swap", dict(keyinfo_cert=w.cert_b)),
        ("wrong audience", dict(audience="https://other.test/sp")),
        ("wrong recipient", dict(recipient="https://evil.test/acs")),
        ("wrong destination", dict(destination="https://evil.test/acs")),
    ]
    for _name, kw in attacks:
        with pytest.raises(PlatformError):
            login_with(**kw)
    # Replay: the same response twice.
    url = svc.begin_saml_login(A, IDP_A_ENTITY)
    state, resp = saml_respond(w, url, "alice")
    svc.complete_saml_login(A, IDP_A_ENTITY, state, resp)
    with pytest.raises(PlatformError):
        svc.complete_saml_login(A, IDP_A_ENTITY, state, resp)
    # XSW: the signed assertion duplicated verbatim.
    url = svc.begin_saml_login(A, IDP_A_ENTITY)
    state, resp = saml_respond(w, url, "alice")
    xml = base64.b64decode(resp).decode("utf-8")
    start = xml.find("<saml:Assertion")
    end = xml.find("</saml:Assertion>") + len("</saml:Assertion>")
    doubled = xml[:end] + xml[start:end] + xml[end:]
    with pytest.raises(PlatformError):
        svc.complete_saml_login(
            A, IDP_A_ENTITY, state,
            base64.b64encode(doubled.encode()).decode())
    # EncryptedAssertion injection.
    injected = xml.replace("</samlp:Response>",
                           "<saml:EncryptedAssertion/></samlp:Response>")
    with pytest.raises(PlatformError):
        svc.complete_saml_login(
            A, IDP_A_ENTITY, state,
            base64.b64encode(injected.encode()).decode())


# -- p14 (HELD regression): the OIDC battery still refuses


def test_p14_oidc_battery_held(tmp_path):
    from e1_world import ATTACKER_N, ATTACKER_E, ATTACKER_D
    w = build_world(tmp_path)
    svc = w.service
    config = svc.directory.idp(w.tenant_id, ISSUER_A)
    client = svc.oidc

    def good(**kw):
        args = dict(issuer=ISSUER_A, subject="alice",
                    audience=config.client_id, nonce="n1",
                    profile=USERS_A["alice"])
        args.update(kw)
        return w.mock.issue_token(**args)

    def validate(jwt, nonce="n1"):
        return client.validate_id_token(
            jwt, issuer=ISSUER_A, client_id=config.client_id, nonce=nonce)

    assert validate(good())
    hdr = {"alg": "none", "typ": "JWT"}
    claims = {"iss": ISSUER_A, "sub": "alice", "aud": config.client_id,
              "exp": w.clock_box[0] + 3600, "iat": w.clock_box[0],
              "nonce": "n1"}
    from tekmerion.platform.oidc import _b64url_encode
    none_tok = (_b64url_encode(json.dumps(hdr).encode()) + "." +
                _b64url_encode(json.dumps(claims).encode()) + ".")
    with pytest.raises(AuthenticationError):
        validate(none_tok)
    hdr2 = {"alg": "HS256", "typ": "JWT", "kid": "test-key-1"}
    si = (_b64url_encode(json.dumps(hdr2).encode()) + "." +
          _b64url_encode(json.dumps(claims).encode()))
    hs_tok = si + "." + _b64url_encode(
        hmac.new(b"whatever", si.encode(), hashlib.sha256).digest())
    with pytest.raises(AuthenticationError):
        validate(hs_tok)
    with pytest.raises(AuthenticationError):
        validate(good(key=(ATTACKER_N, ATTACKER_E, ATTACKER_D)))
    with pytest.raises(AuthenticationError):
        validate(good(audience="other-app"))
    with pytest.raises(AuthenticationError):
        validate(good(issuer="https://evil.test"))
    with pytest.raises(AuthenticationError):
        validate(good(lifetime=-60))
    with pytest.raises(AuthenticationError):
        validate(good(), nonce="other")
    # Login state is single-use; cross-tenant codes fail.
    url = svc.begin_login(w.tenant_id, ISSUER_A)
    code, state = w.mock.authorize(url, "alice")
    svc.complete_login(state, code)
    url2 = svc.begin_login(w.tenant_id, ISSUER_A)
    code2, state2 = w.mock.authorize(url2, "alice")
    with pytest.raises(PlatformError):
        svc.complete_login(state, code2)
    with pytest.raises(PlatformError):
        svc.complete_login(state2, "code-999-mallory")


# -- p15 (HELD regression): the SCIM battery still refuses


def test_p15_scim_battery_held(tmp_path):
    w = build_two_tenant_world(tmp_path)
    svc = w.service
    A, B = w.tenant_id, w.tenant_b
    cred_a, sec_a = svc.issue_scim_token(w.admin_session, tenant_id=A)
    cred_b, sec_b = svc.issue_scim_token(w.admin_b_session, tenant_id=B)
    cid_a = cred_a.credential_id
    for expr in ('userName eq "x" or userName eq "y"',
                 'userName eq "x" and active eq true',
                 'emails[type eq "work"].value eq "a@b.test"',
                 'userName sw "a"; DROP',
                 '(userName eq "x")'):
        with pytest.raises(ScimError):
            svc.scim_list_users(A, cid_a, sec_a, filter_expr=expr)
    with pytest.raises(ScimError):
        svc.scim_list_users(B, cid_a, sec_a)
    _, user = svc.scim_create_user(A, cid_a, sec_a, doc={
        "userName": "carol@uni-a.test", "displayName": "Carol",
        "emails": [{"value": "carol@uni-a.test", "primary": True}]})
    _, group = svc.scim_create_group(A, cid_a, sec_a, doc={
        "displayName": "adjudicators", "members": []})
    ident_id = user["urn:tekmerion:params:scim:identity"]["identity_id"]
    svc.scim_patch_group(A, cid_a, sec_a, group["id"], doc={"Operations": [
        {"op": "add", "path": "members", "value": [{"value": ident_id}]}]})
    assert svc.roles_of(ident_id, tenant_id=A) == set()
    with pytest.raises(PlatformError):
        svc.approve_group_mapping(w.admin_session, tenant_id=A,
                                  group_ref="adjudicators",
                                  role="tenant_admin")
    svc.approve_group_mapping(w.admin_session, tenant_id=A,
                              group_ref="adjudicators", role="adjudicator")
    # As the probe observed: approval applies to current members.
    assert svc.roles_of(ident_id, tenant_id=A) == {authz.ADJUDICATOR}
    svc.scim_patch_group(A, cid_a, sec_a, group["id"], doc={"Operations": [
        {"op": "remove", "path": "members", "value": [{"value": ident_id}]}]})
    svc.scim_patch_group(A, cid_a, sec_a, group["id"], doc={"Operations": [
        {"op": "add", "path": "members", "value": [{"value": ident_id}]}]})
    assert svc.roles_of(ident_id, tenant_id=A) == {authz.ADJUDICATOR}
    _, user2 = svc.scim_create_user(A, cid_a, sec_a, doc={
        "userName": "dave@uni-a.test", "displayName": "Dave"})
    with pytest.raises(ScimError):
        svc.scim_patch_user(A, cid_a, sec_a, user2["id"], doc={"Operations": [
            {"op": "replace", "path": "userName",
             "value": "carol@uni-a.test"}]})
    svc.scim_patch_user(A, cid_a, sec_a, user["id"], doc={"Operations": [
        {"op": "replace", "path": "active", "value": False}]})
    ident = svc.directory.identity(ident_id)
    assert ident.active is False
    svc.scim_delete_user(A, cid_a, sec_a, user["id"])
    _, user3 = svc.scim_create_user(A, cid_a, sec_a, doc={
        "userName": "carol@uni-a.test", "displayName": "Carol"})
    ident3 = svc.directory.identity(
        user3["urn:tekmerion:params:scim:identity"]["identity_id"])
    assert ident3.identity_id == ident_id
    assert user3["id"] != user["id"]
    assert ident3.active is True
    assert svc.roles_of(ident3.identity_id, tenant_id=A) == set()


# -- p18 (HELD regression): custody / key-storage / receiver hygiene


def test_p18_hygiene_held(tmp_path):
    from tekmerion.platform.webhooks import ReferenceReceiver, sign_delivery
    w = build_world(tmp_path)
    svc = w.service
    ada_session, ada = login_user(w, "ada", role=authz.ADJUDICATOR)
    step_up_now(w, ada_session, ada)
    seed_hex, pk_hex = axiomere.generate_keypair()
    svc.enroll_delegated_key(ada_session, seed_hex=seed_hex)
    blob = json.dumps(svc._tenant_ledger(w.tenant_id).events())
    dep_blob = json.dumps(svc.deployment_ledger.events())
    assert seed_hex not in blob and seed_hex not in dep_blob
    assert pk_hex in blob
    bot = svc.create_service_identity(
        w.admin_session, tenant_id=w.tenant_id, name="hygiene-bot")
    krec, ksecret = svc.issue_api_key(
        w.admin_session, tenant_id=w.tenant_id,
        principal_identity_id=bot.identity_id, role_class="researcher",
        scopes=["study.register_claim"], lifetime_seconds=600)
    stored = svc.directory.find_api_key(krec.key_id, ksecret)
    assert ksecret not in repr(stored)
    assert svc.directory.find_api_key(krec.key_id, "wrong") is None
    secret = b"whsec_p18"
    receiver = ReferenceReceiver(signing="hmac-sha256", hmac_secret=secret,
                                 now=lambda: w.clock_box[0])
    body = json.dumps({"event": "security.break_glass_use"}).encode()
    ts = str(int(w.clock_box[0]))
    sig = sign_delivery(signing="hmac-sha256",
                        timestamp=int(w.clock_box[0]), body=body,
                        hmac_secret=secret)
    headers = {"X-Tekmerion-Timestamp": ts, "X-Tekmerion-Signature": sig,
               "X-Tekmerion-Delivery": "dlv_p18_1"}
    receiver.accept(headers, body)
    with pytest.raises(PlatformError):
        receiver.accept(headers, body)  # replay of the same delivery id
    forged = dict(headers)
    forged["X-Tekmerion-Delivery"] = "dlv_p18_2"
    with pytest.raises(PlatformError):
        receiver.accept(forged, json.dumps(
            {"event": "security.break_glass_use", "actor": "mallory"}
        ).encode())
    garbage = dict(headers)
    garbage["X-Tekmerion-Delivery"] = "dlv_p18_3"
    garbage["X-Tekmerion-Signature"] = "00" * 32
    with pytest.raises(PlatformError):
        receiver.accept(garbage, body)
