"""Spec 005 E2 — SAML 2.0 service provider (T513–T517) against the
Shibboleth-class mock IdP in e2_world (T516: the harness is
in-process and runs in CI; no external federation dependency).

The battery is built around F-005-02: an authentication succeeding
on an unsigned assertion, an assertion from an IdP not configured
for that tenant, or a SAML login for a tenant with no SAML IdP
configured falsifies CLM-005-02. Every attack case asserts the
refusal AND its platform-audit-ledger record (§13.4 discipline:
refusals are events, recorded before the raise).
"""

import base64
import json

import axiomere
import pytest

from e1_world import TENANT_A, login_user
from e2_world import (
    ACS_A, IDP_A_ENTITY, IDP_B_ENTITY, KEY_B, PASSWORD_CONTEXT, REFEDS_MFA,
    SP_A, TENANT_B, TENANT_C, build_saml_world, cert_b64, make_cert,
    metadata_xml, parse_authn_request, saml_login, saml_respond,
)
from tekmerion.platform import authz
from tekmerion.platform.errors import (
    AuthenticationError, AuthorizationDenied, ConfigurationError, GateDenied,
)
from tekmerion.platform.gate import GatedStudyWriter, SessionAuth, canonical_intent
from tekmerion.platform.keys import LocalKeySigner
from tekmerion.platform.saml import parse_metadata
from tekmerion.platform.x509 import parse_certificate
from tekmerion.platform.xmlc14n import canonicalize, parse_xml
from tekmerion.store import StudyStore

STUDY_ID = "study-e2"
CLAIM = {"text": "Water boils at 100C at 1 atm.", "status": "contested"}
VERDICT = {"state": "SUPPORTED", "basis": "two independent checks"}


@pytest.fixture()
def world(tmp_path):
    return build_saml_world(tmp_path)


def tenant_ledger(w, tenant=TENANT_A):
    return w.service._tenant_ledger(tenant)


def saml_failure_reasons(w, tenant=TENANT_A) -> list[str]:
    return [ev["payload"].get("reason", "")
            for ev in tenant_ledger(w, tenant).events()
            if ev["type"] == "auth.login_failed"
            and ev["payload"].get("protocol") == "saml"]


def assert_no_identity(w, subject, tenant=TENANT_A, entity=IDP_A_ENTITY):
    assert w.service.directory.find_identity(tenant, entity, subject) is None


# -- canonicalization + certificate units -----------------------------------


def test_c14n_apex_renders_utilized_inherited_namespaces():
    doc = parse_xml(
        b'<root xmlns="urn:root" xmlns:p="urn:p">'
        b'<p:child a="1" xmlns:q="urn:q" q:b="2">text</p:child></root>')
    child = doc.documentElement.firstChild
    assert canonicalize(child) == (
        b'<p:child xmlns:p="urn:p" xmlns:q="urn:q" a="1" q:b="2">text</p:child>')
    assert canonicalize(doc.documentElement) == (
        b'<root xmlns="urn:root">'
        b'<p:child xmlns:p="urn:p" xmlns:q="urn:q" a="1" q:b="2">text</p:child></root>')


def test_c14n_insensitive_to_attribute_order_sensitive_to_content():
    a = parse_xml(b'<e xmlns="urn:x" b="2" a="1">t &amp; u</e>').documentElement
    b = parse_xml(b'<e xmlns="urn:x" a="1" b="2">t &amp; u</e>').documentElement
    assert canonicalize(a) == canonicalize(b)
    c = parse_xml(b'<e xmlns="urn:x" a="1" b="2">t &amp; v</e>').documentElement
    assert canonicalize(a) != canonicalize(c)


def test_c14n_refuses_doctype():
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_xml(b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "y">]><r>&x;</r>')


def test_certificate_round_trip(world):
    info = parse_certificate(world.cert_a)
    from e1_world import IDP_E, IDP_N
    assert (info.rsa_n, info.rsa_e) == (IDP_N, IDP_E)
    assert info.not_before < world.clock_box[0] < info.not_after
    assert len(info.fingerprint) == 64


# -- T513: configuration from metadata ---------------------------------------


def test_provisioning_records_config_without_cert_material(world):
    events = [ev for ev in tenant_ledger(world).events()
              if ev["type"] == "idp.configured"
              and ev["payload"].get("protocol") == "saml"]
    assert len(events) == 1
    payload = events[0]["payload"]
    info = parse_certificate(world.cert_a)
    assert payload["signing_cert_fingerprints"] == [info.fingerprint]
    assert payload["idp_entity_id"] == IDP_A_ENTITY
    blob = json.dumps(tenant_ledger(world).events())
    assert cert_b64(world.cert_a)[:40] not in blob  # material never reaches the ledger
    assert payload["signing_cert_refs"][0].startswith("saml-cert:")


def test_metadata_without_signing_cert_is_refused(world):
    world.service.create_tenant(world.root_session, tenant_id="uni-d", name="University D")
    bad = metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a)
    bad = bad.replace('<md:KeyDescriptor use="signing">', '<md:KeyDescriptor use="encryption">')
    with pytest.raises(ConfigurationError, match="no signing certificate"):
        world.service.provision_tenant_saml_idp(
            world.root_session, tenant_id="uni-d", sp_entity_id=SP_A, acs_url=ACS_A,
            metadata_xml=bad)


def test_expired_metadata_and_certificates_are_refused(world):
    world.service.create_tenant(world.root_session, tenant_id="uni-d", name="University D")
    stale = metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a,
                         valid_until="2020-01-01T00:00:00Z")
    with pytest.raises(ConfigurationError, match="expired"):
        world.service.provision_tenant_saml_idp(
            world.root_session, tenant_id="uni-d", sp_entity_id=SP_A, acs_url=ACS_A,
            metadata_xml=stale)
    from e1_world import IDP_D, IDP_E, IDP_N
    dead_cert = make_cert(IDP_N, IDP_E, IDP_D, cn="dead.test",
                          not_before=world.clock_box[0] - 90000,
                          not_after=world.clock_box[0] - 60)
    with pytest.raises(ConfigurationError, match="expired"):
        world.service.provision_tenant_saml_idp(
            world.root_session, tenant_id="uni-d", sp_entity_id=SP_A, acs_url=ACS_A,
            metadata_xml=metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", dead_cert))


def test_metadata_parse_rejects_non_idp(world):
    with pytest.raises(ConfigurationError, match="IDPSSODescriptor"):
        parse_metadata('<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"'
                       ' entityID="https://x.test"/>', now=world.clock_box[0])


def test_tenant_admin_can_configure_and_researcher_cannot(world):
    world.service.configure_saml_idp(
        world.admin_session, tenant_id=TENANT_A, sp_entity_id=SP_A, acs_url=ACS_A,
        metadata_xml=metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a))
    types = [ev["payload"].get("via") for ev in tenant_ledger(world).events()
             if ev["type"] in ("idp.configured", "idp.updated")
             and ev["payload"].get("protocol") == "saml"]
    assert "tenant-admin" in types
    alice_session, _ = login_user(world, "alice")
    with pytest.raises(AuthorizationDenied):
        world.service.configure_saml_idp(
            alice_session, tenant_id=TENANT_A, sp_entity_id=SP_A, acs_url=ACS_A,
            metadata_xml=metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a))


def test_tenant_without_saml_idp_refuses_login(world):
    """F-005-02, third clause: no SAML IdP configured -> no SAML login,
    and the refusal is ledgered in that tenant's own ledger."""
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_C, IDP_A_ENTITY, None, "AAAA")
    assert any("no SAML IdP configured" in r
               for r in saml_failure_reasons(world, TENANT_C))
    with pytest.raises(ConfigurationError):
        world.service.begin_saml_login(TENANT_C, IDP_A_ENTITY)


# -- T513/T515: happy paths + attribute mapping -------------------------------


def test_sp_initiated_login_maps_attributes(world):
    session = saml_login(world, "alice")
    assert world.service.directory.session(session) is not None
    ident = world.service.directory.find_identity(TENANT_A, IDP_A_ENTITY, "alice")
    assert ident is not None and ident.created_via == "saml"
    assert ident.display_name == "Alice Researcher"          # displayName (friendly form)
    assert ident.email == "alice@uni-a.test"                  # mail
    assert ident.affiliation == "member@uni-a.test"           # eduPersonScopedAffiliation (OID form)
    successes = [ev for ev in tenant_ledger(world).events()
                 if ev["type"] == "auth.login_succeeded"
                 and ev["payload"].get("protocol") == "saml"]
    assert len(successes) == 1 and successes[0]["payload"]["mfa"] is True


def test_idp_initiated_login(world):
    resp = world.saml.respond(subject="alice")
    session = world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, None, resp)
    assert world.service.directory.session(session) is not None


def test_response_level_signature_also_accepted(world):
    session = saml_login(world, "alice", sign_response=True)
    assert world.service.directory.session(session) is not None


def test_eppn_subject_mapping(world):
    world.service.configure_saml_idp(
        world.admin_session, tenant_id=TENANT_A, sp_entity_id=SP_A, acs_url=ACS_A,
        metadata_xml=metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a),
        subject_source="eppn")
    saml_login(world, "alice")
    ident = world.service.directory.find_identity(
        TENANT_A, IDP_A_ENTITY, "alice@uni-a.test")
    assert ident is not None and ident.subject == "alice@uni-a.test"


# -- T514: the refusal battery (F-005-02) --------------------------------------


def attempt(world, subject="alice", tenant=TENANT_A, entity=IDP_A_ENTITY, **kw):
    """An SP-initiated attempt expected to fail at completion."""
    url = world.service.begin_saml_login(tenant, entity)
    state, resp = saml_respond(world, url, subject, tenant=tenant, issuer=entity, **kw)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(tenant, entity, state, resp)
    return saml_failure_reasons(world, tenant)


def test_unsigned_assertion_refused(world):
    reasons = attempt(world, sign_assertion=False)
    assert any("unsigned" in r for r in reasons)
    assert_no_identity(world, "alice")


def test_response_signature_does_not_rescue_unsigned_assertion(world):
    reasons = attempt(world, sign_assertion=False, sign_response=True)
    assert any("unsigned" in r for r in reasons)
    assert_no_identity(world, "alice")


def test_wrong_signing_key_refused(world):
    reasons = attempt(world, key=KEY_B)   # signed by tenant B's IdP key
    assert any("does not verify" in r or "not the configured IdP key" in r
               for r in reasons)
    assert_no_identity(world, "alice")


def test_keyinfo_naming_an_unconfigured_cert_refused(world):
    reasons = attempt(world, keyinfo_cert=world.cert_b)
    assert any("not the configured IdP key" in r for r in reasons)
    assert_no_identity(world, "alice")


def test_tampered_assertion_refused(world):
    reasons = attempt(world, tamper=("alice@uni-a.test", "alice@evil.test"))
    assert any("digest mismatch" in r for r in reasons)
    assert_no_identity(world, "alice")


def test_expired_assertion_refused(world):
    reasons = attempt(world, not_after_offset=-900)
    assert any("expired" in r for r in reasons)


def test_not_yet_valid_assertion_refused(world):
    reasons = attempt(world, not_before_offset=900)
    assert any("not yet valid" in r for r in reasons)


def test_wrong_audience_refused(world):
    reasons = attempt(world, audience="https://other.test/sp")
    assert any("audience" in r for r in reasons)


def test_wrong_recipient_refused(world):
    reasons = attempt(world, recipient="https://uni-a.test/not-the-acs")
    assert any("Recipient" in r for r in reasons)


def test_wrong_issuer_refused(world):
    url = world.service.begin_saml_login(TENANT_A, IDP_A_ENTITY)
    state, resp = saml_respond(world, url, "alice", tenant=TENANT_A,
                               issuer=IDP_B_ENTITY, key=KEY_B)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, state, resp)
    assert any("issuer" in r for r in saml_failure_reasons(world))


def test_in_response_to_mismatch_refused(world):
    url = world.service.begin_saml_login(TENANT_A, IDP_A_ENTITY)
    state, _info = parse_authn_request(url)
    resp = world.saml.respond(subject="alice", in_response_to="_someone-elses-request")
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, state, resp)
    assert any("InResponseTo" in r for r in saml_failure_reasons(world))


def test_replayed_assertion_refused(world):
    resp = world.saml.respond(subject="alice")   # IdP-initiated: replayable bytes
    world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, None, resp)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, None, resp)
    assert any("replay" in r for r in saml_failure_reasons(world))


def test_cross_tenant_assertion_refused(world):
    """Tenant B's IdP assertion presented at tenant A's ACS: A's
    configuration is the trust anchor, so B's (valid, for B) signed
    assertion fails here — the seeded tenant-isolation case."""
    url = world.service.begin_saml_login(TENANT_A, IDP_A_ENTITY)
    state, resp = saml_respond(world, url, "alice", tenant=TENANT_A,
                               issuer=IDP_B_ENTITY, key=KEY_B)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, state, resp)
    assert_no_identity(world, "alice")
    # And B's own flow state presented at A's ACS dies at the state check.
    url_b = world.service.begin_saml_login(TENANT_B, IDP_B_ENTITY)
    state_b, resp_b = saml_respond(world, url_b, "bob", tenant=TENANT_B,
                                   issuer=IDP_B_ENTITY)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, state_b, resp_b)


def test_idp_initiated_disabled_by_tenant_config(world):
    world.service.configure_saml_idp(
        world.admin_session, tenant_id=TENANT_A, sp_entity_id=SP_A, acs_url=ACS_A,
        metadata_xml=metadata_xml(IDP_A_ENTITY, "https://idp-a.test/saml/sso", world.cert_a),
        allow_idp_initiated=False)
    resp = world.saml.respond(subject="alice")
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(TENANT_A, IDP_A_ENTITY, None, resp)
    assert any("IdP-initiated" in r for r in saml_failure_reasons(world))


def test_encrypted_assertion_refused_by_name(world):
    xml = (
        '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
        ' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r1" Version="2.0">'
        "<saml:Issuer>https://idp-a.test/shibboleth</saml:Issuer>"
        '<samlp:Status><samlp:StatusCode'
        ' Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>'
        "<saml:EncryptedAssertion/></samlp:Response>")
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(
            TENANT_A, IDP_A_ENTITY, None, base64.b64encode(xml.encode()).decode())
    assert any("encrypted" in r for r in saml_failure_reasons(world))


def test_doctype_response_refused(world):
    xml = ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "y">]>'
           '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
           ' ID="_r1" Version="2.0"/>')
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_login(
            TENANT_A, IDP_A_ENTITY, None, base64.b64encode(xml.encode()).decode())
    assert any("DOCTYPE" in r for r in saml_failure_reasons(world))


def test_non_success_status_refused(world):
    reasons = attempt(world, status="urn:oasis:names:tc:SAML:2.0:status:AuthnFailed")
    assert any("non-success" in r for r in reasons)


def test_refusal_battery_leaves_chains_verifiable(world):
    attempt(world, sign_assertion=False)
    attempt(world, key=KEY_B)
    attempt(world, not_after_offset=-900)
    saml_login(world, "alice")
    assert tenant_ledger(world).verify().ok
    assert world.service.deployment_ledger.verify().ok
    assert len(saml_failure_reasons(world)) >= 3


# -- T517 + §3: the SAML door reaches the same identity machinery --------------


def enroll_self(w, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = w.service.begin_enrollment(session)
    rec = w.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


def make_writer(w, tmp_path):
    store = StudyStore.create(str(tmp_path / "study.axmr"))
    return GatedStudyWriter(w.service, store, tenant_id=w.tenant_id,
                            study_id=STUDY_ID), store


def test_saml_identity_enrolls_key_and_appends(world, tmp_path):
    session = saml_login(world, "alice")
    ident = world.service.directory.find_identity(TENANT_A, IDP_A_ENTITY, "alice")
    world.service.grant_role(world.admin_session, identity_id=ident.identity_id,
                             role=authz.RESEARCHER, tenant_id=TENANT_A)
    signer, rec = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    writer.register_claim(
        SessionAuth(session, rec.fingerprint, signer.sign(intent)), "CLM-1", CLAIM)
    events = [ev for ev in store.events() if ev["type"] == "record.snapshot"]
    assert events and events[0]["payload"]["content"]["attribution"]["actor_id"] == ident.actor_id


def test_no_mfa_saml_session_cannot_append(world, tmp_path):
    """§13.5 parity: a SAML session whose AuthnContext evidences no
    MFA is refused at the append gate exactly like an OIDC one."""
    session = saml_login(world, "alice", context_ref=PASSWORD_CONTEXT)
    ident = world.service.directory.find_identity(TENANT_A, IDP_A_ENTITY, "alice")
    world.service.grant_role(world.admin_session, identity_id=ident.identity_id,
                             role=authz.RESEARCHER, tenant_id=TENANT_A)
    signer, rec = enroll_self(world, session)
    writer, _store = make_writer(world, tmp_path)
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    with pytest.raises(GateDenied, match="MFA"):
        writer.register_claim(
            SessionAuth(session, rec.fingerprint, signer.sign(intent)), "CLM-1", CLAIM)


def saml_step_up(world, session, subject):
    url = world.service.begin_saml_step_up(session)
    _state, info = parse_authn_request(url)
    assert info["force_authn"] is True
    state, resp = saml_respond(world, url, subject)
    return world.service.complete_saml_step_up(state, resp)


def test_adjudicator_step_up_parity(world, tmp_path):
    session = saml_login(world, "ada")   # MFA context, but no step-up yet
    ident = world.service.directory.find_identity(TENANT_A, IDP_A_ENTITY, "ada")
    world.service.grant_role(world.admin_session, identity_id=ident.identity_id,
                             role=authz.ADJUDICATOR, tenant_id=TENANT_A)
    nonce = world.service.begin_enrollment(session)
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    with pytest.raises(GateDenied, match="step-up"):
        world.service.enroll_self_key(
            session, public_key=signer.public_key,
            proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    saml_step_up(world, session, "ada")
    rec = world.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    stepups = [ev for ev in tenant_ledger(world).events()
               if ev["type"] == "auth.stepup"
               and ev["payload"].get("protocol") == "saml"]
    assert len(stepups) == 1
    # Verdict-class append now works for the SAML-born adjudicator...
    writer, store = make_writer(world, tmp_path)
    rsession = saml_login(world, "alice")
    rident = world.service.directory.find_identity(TENANT_A, IDP_A_ENTITY, "alice")
    world.service.grant_role(world.admin_session, identity_id=rident.identity_id,
                             role=authz.RESEARCHER, tenant_id=TENANT_A)
    rsigner, rrec = enroll_self(world, rsession)
    rintent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                               study_id=STUDY_ID, event="claim.registered", payload=CLAIM)
    writer.register_claim(
        SessionAuth(rsession, rrec.fingerprint, rsigner.sign(rintent)), "CLM-1", CLAIM)
    vint = canonical_intent(action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
                            study_id=STUDY_ID, event="verdict.issued",
                            payload={"claim_id": "CLM-1", **VERDICT})
    writer.issue_verdict(
        SessionAuth(session, rec.fingerprint, signer.sign(vint)), "CLM-1", VERDICT)
    # ...but a fresh SAML session without step-up still cannot sign one.
    fresh = saml_login(world, "ada")
    with pytest.raises(GateDenied, match="step-up"):
        writer.issue_verdict(
            SessionAuth(fresh, rec.fingerprint, signer.sign(vint)), "CLM-1", VERDICT)


def test_step_up_for_a_different_identity_refused(world):
    ada_session = saml_login(world, "ada")
    url = world.service.begin_saml_step_up(ada_session)
    state, resp = saml_respond(world, url, "alice")   # alice's assertion, ada's state
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_step_up(state, resp)
    assert any("different identity" in r for r in saml_failure_reasons(world))


def test_step_up_without_mfa_refused(world):
    session = saml_login(world, "ada")
    url = world.service.begin_saml_step_up(session)
    state, resp = saml_respond(world, url, "ada", context_ref=PASSWORD_CONTEXT)
    with pytest.raises(AuthenticationError):
        world.service.complete_saml_step_up(state, resp)
    assert any("MFA" in r for r in saml_failure_reasons(world))
