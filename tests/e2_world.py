"""E2 test world: a Shibboleth-class mock SAML IdP + the E1 world.

No sockets, no external federation, no spend (Spec 005 E2 testing
constraints). The mock IdP builds real SAML Responses and signs them
with real XML-DSig (exclusive C14N + RSA-SHA256) using the E1 world's
TEST-ONLY RSA keys, so the SP's verifier is exercised on the same
terms a Shibboleth IdP would present — including the attack set:
the mock can sign with the wrong key, omit signatures, lie in
KeyInfo, and mint expired / wrong-audience / wrong-issuer messages.

Certificates are self-signed X.509 built in pure Python (DER) around
those keys — TEST-ONLY material, signing nothing outside these
tests.
"""

from __future__ import annotations

import base64
import hashlib
import urllib.parse
import zlib
from datetime import datetime, timezone
from types import SimpleNamespace
from xml.dom import minidom
from xml.sax.saxutils import escape as xml_escape

from e1_world import (
    ATTACKER_D, ATTACKER_E, ATTACKER_N, IDP_D, IDP_E, IDP_N,
    TENANT_A, _rs256_sign, build_world,
)
from tekmerion.platform.saml import (
    BINDING_POST, BINDING_REDIRECT, DSIG, SAML_ASSERTION, SAML_PROTOCOL,
)
from tekmerion.platform.xmlc14n import canonicalize, in_scope_namespaces

MD = "urn:oasis:names:tc:SAML:2.0:metadata"
REFEDS_MFA = "https://refeds.org/profile/mfa"
PASSWORD_CONTEXT = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

IDP_A_ENTITY = "https://idp-a.test/shibboleth"
SSO_A = "https://idp-a.test/saml/sso"
SP_A = "https://uni-a.test/sp"
ACS_A = "https://uni-a.test/saml/acs"

IDP_B_ENTITY = "https://idp-b.test/shibboleth"
SSO_B = "https://idp-b.test/saml/sso"
SP_B = "https://uni-b.test/sp"
ACS_B = "https://uni-b.test/saml/acs"
TENANT_B = "uni-b"
TENANT_C = "uni-c"   # exists, but has no SAML IdP (F-005-02, clause 3)

KEY_A = (IDP_N, IDP_E, IDP_D)            # tenant A's IdP key
KEY_B = (ATTACKER_N, ATTACKER_E, ATTACKER_D)  # tenant B's IdP key (a different IdP's key)


# ---------------------------------------------------------------- DER / certs


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _seq(*parts: bytes) -> bytes:
    return _tlv(0x30, b"".join(parts))


def _oid(*arcs: int) -> bytes:
    body = bytes([40 * arcs[0] + arcs[1]])
    for arc in arcs[2:]:
        stack = [arc & 0x7F]
        arc >>= 7
        while arc:
            stack.append(0x80 | (arc & 0x7F))
            arc >>= 7
        body += bytes(reversed(stack))
    return _tlv(0x06, body)


def _int(x: int) -> bytes:
    raw = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return _tlv(0x02, raw)


def _name(cn: str) -> bytes:
    return _seq(_tlv(0x31, _seq(_oid(2, 5, 4, 3), _tlv(0x0C, cn.encode("utf-8")))))


def _utctime(ts: float) -> bytes:
    text = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%y%m%d%H%M%SZ")
    return _tlv(0x17, text.encode("ascii"))


def make_cert(n: int, e: int, d: int, *, cn: str,
              not_before: float, not_after: float, serial: int = 1) -> bytes:
    """A minimal self-signed X.509 v3 certificate (test-only)."""
    alg = _seq(_oid(1, 2, 840, 113549, 1, 1, 11), _tlv(0x05, b""))  # sha256WithRSAEncryption
    spki = _seq(
        _seq(_oid(1, 2, 840, 113549, 1, 1, 1), _tlv(0x05, b"")),     # rsaEncryption
        _tlv(0x03, b"\x00" + _seq(_int(n), _int(e))))
    tbs = _seq(
        _tlv(0xA0, _int(2)), _int(serial), alg, _name(cn),
        _seq(_utctime(not_before), _utctime(not_after)), _name(cn), spki)
    signature = _rs256_sign(tbs, n, d)
    return _seq(tbs, alg, _tlv(0x03, b"\x00" + signature))


def cert_b64(der: bytes) -> str:
    return base64.b64encode(der).decode("ascii")


def metadata_xml(entity_id: str, sso_url: str, cert_der: bytes,
                 valid_until: str | None = None) -> str:
    b64 = cert_b64(cert_der)
    wrapped = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    vu = f' validUntil="{valid_until}"' if valid_until else ""
    return (
        f'<md:EntityDescriptor xmlns:md="{MD}" entityID="{entity_id}"{vu}>'
        f'<md:IDPSSODescriptor protocolSupportEnumeration="{SAML_PROTOCOL}">'
        f'<md:KeyDescriptor use="signing"><ds:KeyInfo xmlns:ds="{DSIG}">'
        f"<ds:X509Data><ds:X509Certificate>\n{wrapped}\n</ds:X509Certificate></ds:X509Data>"
        f"</ds:KeyInfo></md:KeyDescriptor>"
        f'<md:SingleSignOnService Binding="{BINDING_REDIRECT}" Location="{sso_url}"/>'
        f'<md:SingleSignOnService Binding="{BINDING_POST}" Location="{sso_url}"/>'
        f"</md:IDPSSODescriptor></md:EntityDescriptor>")


# ---------------------------------------------------------------- mock IdP


def _instant(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign_element(doc, element, key, keyinfo_cert_b64: str) -> None:
    """Append a real enveloped XML-DSig signature to `element`."""
    n, _e, d = key
    element_id = element.getAttribute("ID")
    apex_scope = in_scope_namespaces(element)
    digest = hashlib.sha256(canonicalize(element, apex_scope)).digest()
    sig_xml = (
        f'<ds:Signature xmlns:ds="{DSIG}"><ds:SignedInfo>'
        '<ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>'
        f'<ds:Reference URI="#{element_id}"><ds:Transforms>'
        '<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
        '<ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        "</ds:Transforms>"
        '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
        f"<ds:DigestValue>{base64.b64encode(digest).decode()}</ds:DigestValue>"
        "</ds:Reference></ds:SignedInfo><ds:SignatureValue></ds:SignatureValue>"
        f"<ds:KeyInfo><ds:X509Data><ds:X509Certificate>{keyinfo_cert_b64}"
        "</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature>")
    sig_el = doc.importNode(minidom.parseString(sig_xml).documentElement, True)
    element.appendChild(sig_el)
    signed_info = [c for c in sig_el.childNodes if c.localName == "SignedInfo"][0]
    signature = _rs256_sign(canonicalize(signed_info), n, d)
    sig_value = [c for c in sig_el.childNodes if c.localName == "SignatureValue"][0]
    sig_value.appendChild(doc.createTextNode(base64.b64encode(signature).decode()))


SAML_USERS = {
    "alice": {
        "name_id": "alice",
        "attributes": {
            "urn:oid:1.3.6.1.4.1.5923.1.1.1.6": ("eduPersonPrincipalName", ["alice@uni-a.test"]),
            "urn:oid:1.3.6.1.4.1.5923.1.1.1.9": ("eduPersonScopedAffiliation", ["member@uni-a.test"]),
            "mail": ("mail", ["alice@uni-a.test"]),
            "displayName": ("displayName", ["Alice Researcher"]),
        },
    },
    "ada": {
        "name_id": "ada",
        "attributes": {
            "urn:oid:1.3.6.1.4.1.5923.1.1.1.6": ("eduPersonPrincipalName", ["ada@uni-a.test"]),
            "urn:oid:1.3.6.1.4.1.5923.1.1.1.9": ("eduPersonScopedAffiliation", ["member@uni-a.test"]),
            "mail": ("mail", ["ada@uni-a.test"]),
            "displayName": ("displayName", ["Ada Adjudicator"]),
        },
    },
    "bob": {   # tenant B's user
        "name_id": "bob",
        "attributes": {
            "mail": ("mail", ["bob@uni-b.test"]),
            "displayName": ("displayName", ["Bob Researcher"]),
        },
    },
}


class MockSamlIdP:
    """Builds SAML Responses the way a Shibboleth IdP would — signed
    properly by default, wrong in exactly the ways the tests ask."""

    def __init__(self, clock):
        self.clock = clock
        self.counter = 0
        self.certs = {IDP_A_ENTITY: None, IDP_B_ENTITY: None}  # filled by build_saml_world

    def _ids(self, assertion_id, response_id):
        self.counter += 1
        return (assertion_id or f"_assert{self.counter}",
                response_id or f"_resp{self.counter}")

    def respond(self, *, subject: str = "alice",
                issuer: str = IDP_A_ENTITY, sp_entity_id: str = SP_A,
                acs_url: str = ACS_A, in_response_to: str | None = None,
                key=KEY_A, keyinfo_cert: bytes | None = None,
                context_ref: str = REFEDS_MFA,
                attributes: dict | None = None, name_id: str | None = None,
                sign_assertion: bool = True, sign_response: bool = False,
                audience: str | None = None, recipient: str | None = None,
                destination: str | None = None,
                not_before_offset: float = -60, not_after_offset: float = 300,
                conf_not_after_offset: float = 300,
                status: str = "urn:oasis:names:tc:SAML:2.0:status:Success",
                assertion_id: str | None = None, response_id: str | None = None,
                tamper: tuple[str, str] | None = None) -> str:
        now = self.clock()
        profile = SAML_USERS[subject]
        attrs = attributes if attributes is not None else profile["attributes"]
        attr_xml = "".join(
            f'<saml:Attribute Name="{xml_escape(name)}" FriendlyName="{xml_escape(friendly)}">'
            + "".join(f"<saml:AttributeValue>{xml_escape(v)}</saml:AttributeValue>" for v in vals)
            + "</saml:Attribute>"
            for name, (friendly, vals) in attrs.items())
        aid, rid = self._ids(assertion_id, response_id)
        irt_attr = f' InResponseTo="{in_response_to}"' if in_response_to else ""
        conf_irt = f' InResponseTo="{in_response_to}"' if in_response_to else ""
        xml = (
            f'<samlp:Response xmlns:samlp="{SAML_PROTOCOL}" xmlns:saml="{SAML_ASSERTION}"'
            f' ID="{rid}" Version="2.0" IssueInstant="{_instant(now)}"{irt_attr}'
            f' Destination="{destination if destination is not None else acs_url}">'
            f"<saml:Issuer>{issuer}</saml:Issuer>"
            f'<samlp:Status><samlp:StatusCode Value="{status}"/></samlp:Status>'
            f'<saml:Assertion ID="{aid}" Version="2.0" IssueInstant="{_instant(now)}">'
            f"<saml:Issuer>{issuer}</saml:Issuer>"
            "<saml:Subject>"
            f"<saml:NameID>{xml_escape(name_id if name_id is not None else profile['name_id'])}</saml:NameID>"
            '<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">'
            f'<saml:SubjectConfirmationData NotOnOrAfter="{_instant(now + conf_not_after_offset)}"'
            f' Recipient="{recipient if recipient is not None else acs_url}"{conf_irt}/>'
            "</saml:SubjectConfirmation></saml:Subject>"
            f'<saml:Conditions NotBefore="{_instant(now + not_before_offset)}"'
            f' NotOnOrAfter="{_instant(now + not_after_offset)}">'
            "<saml:AudienceRestriction>"
            f"<saml:Audience>{audience if audience is not None else sp_entity_id}</saml:Audience>"
            "</saml:AudienceRestriction></saml:Conditions>"
            f'<saml:AuthnStatement AuthnInstant="{_instant(now)}">'
            "<saml:AuthnContext>"
            f"<saml:AuthnContextClassRef>{context_ref}</saml:AuthnContextClassRef>"
            "</saml:AuthnContext></saml:AuthnStatement>"
            f"<saml:AttributeStatement>{attr_xml}</saml:AttributeStatement>"
            "</saml:Assertion></samlp:Response>")
        doc = minidom.parseString(xml)
        response_el = doc.documentElement
        assertion_el = [c for c in response_el.childNodes if c.localName == "Assertion"][0]
        keyinfo_b64 = cert_b64(keyinfo_cert if keyinfo_cert is not None
                               else self.certs[issuer])
        if sign_assertion:
            _sign_element(doc, assertion_el, key, keyinfo_b64)
        if sign_response:
            _sign_element(doc, response_el, key, keyinfo_b64)
        out = doc.toxml()
        doc.unlink()
        if tamper is not None:
            assert tamper[0] in out, f"tamper target not in document: {tamper[0]}"
            out = out.replace(tamper[0], tamper[1], 1)
        return base64.b64encode(out.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------- world


def build_saml_world(tmp_path) -> SimpleNamespace:
    """The E1 world, plus: tenant A's SAML IdP (platform-provisioned
    from mock metadata), tenant B with its own IdP and key, and
    tenant C with no SAML configuration at all."""
    w = build_world(tmp_path)
    service = w.service
    now0 = w.clock_box[0]
    cert_a = make_cert(IDP_N, IDP_E, IDP_D, cn="idp-a.test",
                       not_before=now0 - 86400, not_after=now0 + 30 * 86400)
    cert_b = make_cert(ATTACKER_N, ATTACKER_E, ATTACKER_D, cn="idp-b.test",
                       not_before=now0 - 86400, not_after=now0 + 30 * 86400)
    mock = MockSamlIdP(lambda: w.clock_box[0])
    mock.certs[IDP_A_ENTITY] = cert_a
    mock.certs[IDP_B_ENTITY] = cert_b
    service.provision_tenant_saml_idp(
        w.root_session, tenant_id=TENANT_A, sp_entity_id=SP_A, acs_url=ACS_A,
        metadata_xml=metadata_xml(IDP_A_ENTITY, SSO_A, cert_a))
    service.create_tenant(w.root_session, tenant_id=TENANT_B, name="University B")
    service.provision_tenant_saml_idp(
        w.root_session, tenant_id=TENANT_B, sp_entity_id=SP_B, acs_url=ACS_B,
        metadata_xml=metadata_xml(IDP_B_ENTITY, SSO_B, cert_b))
    service.create_tenant(w.root_session, tenant_id=TENANT_C, name="University C")
    w.saml = mock
    w.cert_a, w.cert_b = cert_a, cert_b
    w.idp_a, w.idp_b = IDP_A_ENTITY, IDP_B_ENTITY
    w.sp = {TENANT_A: SP_A, TENANT_B: SP_B}
    w.acs = {TENANT_A: ACS_A, TENANT_B: ACS_B}
    w.sso = {IDP_A_ENTITY: SSO_A, IDP_B_ENTITY: SSO_B}
    w.key = {IDP_A_ENTITY: KEY_A, IDP_B_ENTITY: KEY_B}
    return w


def parse_authn_request(url: str) -> tuple[str, dict]:
    """(relay_state, {request_id, force_authn, destination}) from an
    SP redirect-binding URL — the browser/IdP side of the flow."""
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    raw = zlib.decompress(base64.b64decode(params["SAMLRequest"]), -15)
    doc = minidom.parseString(raw)
    req = doc.documentElement
    info = {
        "request_id": req.getAttribute("ID"),
        "force_authn": req.getAttribute("ForceAuthn") == "true",
        "destination": req.getAttribute("Destination"),
        "acs": req.getAttribute("AssertionConsumerServiceURL"),
        "issuer": [c for c in req.childNodes if c.localName == "Issuer"][0].firstChild.data,
    }
    doc.unlink()
    return params["RelayState"], info


def saml_respond(w, url: str, subject: str, **kw):
    """Play the IdP for an SP-initiated flow started at `url`.
    Returns (relay_state, response_b64)."""
    state, info = parse_authn_request(url)
    tenant = kw.pop("tenant", TENANT_A)
    entity = kw.pop("issuer", IDP_A_ENTITY)
    resp = w.saml.respond(
        subject=subject, issuer=entity, sp_entity_id=w.sp[tenant],
        acs_url=w.acs[tenant], in_response_to=info["request_id"],
        key=kw.pop("key", w.key[entity]), **kw)
    return state, resp


def saml_login(w, subject: str = "alice", tenant: str = TENANT_A,
               entity: str = IDP_A_ENTITY, **kw) -> str:
    """A full SP-initiated SAML login; returns the session token."""
    url = w.service.begin_saml_login(tenant, entity)
    state, resp = saml_respond(w, url, subject, tenant=tenant, issuer=entity, **kw)
    return w.service.complete_saml_login(tenant, entity, state, resp)
