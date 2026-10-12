"""SAML 2.0 service provider (Spec 005 §2, E2: T513–T515).

Web Browser SSO profile, SP-initiated (HTTP-Redirect request /
HTTP-POST response) and IdP-initiated (unsolicited POST response),
for Shibboleth / InCommon-class IdPs configured per tenant.

Validation policy (the F-005-02 falsifier is the design):
- assertions MUST be signed (XML-DSig, RSA-SHA256, exclusive C14N);
  an unsigned assertion is refused, never repaired;
- a signature present on the Response must also verify;
- the trust anchor is the certificate in the tenant's imported
  metadata — a key carried inside the message is a hint that must
  match it, never a substitute for it;
- issuer, audience, recipient, conditions window, InResponseTo,
  and assertion-ID replay are all checked; every refusal is an
  AuthenticationError the service records as an authentication
  failure event before raising (§13.4 AU discipline).

RSA verification reuses the OIDC module's RS256 verifier — the
DigestInfo construction is identical. Canonicalization is the
in-repo exclusive C14N (see `xmlc14n.py`); both are prototype-grade
pure Python, recorded in the crypto inventory. Encrypted assertions
are refused by name in v1 (no decryption key custody story exists
yet — refusing beats silently misreading scope).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as _secrets
import time
import urllib.parse
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from xml.dom import Node

from .errors import AuthenticationError, ConfigurationError
from .oidc import _rs256_verify
from .x509 import CertificateInfo, parse_certificate_b64
from .xmlc14n import EXC_C14N, canonicalize, in_scope_namespaces, parse_xml

SAML_PROTOCOL = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML_ASSERTION = "urn:oasis:names:tc:SAML:2.0:assertion"
DSIG = "http://www.w3.org/2000/09/xmldsig#"
MD = "urn:oasis:names:tc:SAML:2.0:metadata"

BINDING_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
BINDING_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
STATUS_SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success"
TRANSFORM_ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
ALG_RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
ALG_SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"

#: Clock skew tolerated on Conditions / SubjectConfirmationData
#: windows — named, because unnamed skew is how windows quietly
#: stop meaning anything.
CLOCK_SKEW_SECONDS = 300

#: AuthnContextClassRef values that evidence multi-factor auth
#: (REFEDS MFA profile, the SAML 2.0 contract classes, Entra's
#: multiple-authn claim URI). Anything else is single-factor as far
#: as the platform's §13.5 enforcement is concerned.
MFA_CONTEXT_REFS = frozenset({
    "https://refeds.org/profile/mfa",
    "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract",
    "urn:oasis:names:tc:SAML:2.0:ac:classes:SmartcardPKI",
    "urn:oasis:names:tc:SAML:2.0:ac:classes:TimeSyncToken",
    "http://schemas.microsoft.com/claims/multipleauthn",
})

#: Attribute names as (OID-form, friendly-form); a message may use
#: either (Shibboleth metadata/attribute maps appear in both).
EDU_PERSON_PRINCIPAL_NAME = ("urn:oid:1.3.6.1.4.1.5923.1.1.1.6", "eduPersonPrincipalName")
EDU_PERSON_SCOPED_AFFILIATION = ("urn:oid:1.3.6.1.4.1.5923.1.1.1.9", "eduPersonScopedAffiliation")

DEFAULT_ATTRIBUTE_MAP = {
    "display_name": "displayName",
    "email": "mail",
    "affiliation": "eduPersonScopedAffiliation",
}


def _parse_instant(text: str) -> float:
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthenticationError(f"unparseable SAML instant: {text!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _format_instant(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _el(parent, ns: str, local: str):
    for child in parent.childNodes:
        if (child.nodeType == Node.ELEMENT_NODE and child.namespaceURI == ns
                and child.localName == local):
            return child
    return None


def _els(parent, ns: str, local: str) -> list:
    return [c for c in parent.childNodes
            if c.nodeType == Node.ELEMENT_NODE and c.namespaceURI == ns
            and c.localName == local]


def _text(element) -> str:
    return "".join(n.data for n in element.childNodes
                   if n.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


# ---------------------------------------------------------------- metadata


@dataclass
class IdPMetadata:
    entity_id: str
    sso_redirect_url: Optional[str]
    sso_post_url: Optional[str]
    signing_certs: tuple[CertificateInfo, ...]
    valid_until: Optional[float]


def parse_metadata(xml_text: str, *, now: float) -> IdPMetadata:
    """Parse + validate one IdP's EntityDescriptor (T513). Raises
    ConfigurationError — a bad import is an admin-plane refusal,
    recorded by the caller, not an authentication event."""
    try:
        doc = parse_xml(xml_text.encode("utf-8"))
    except Exception as exc:
        raise ConfigurationError(f"IdP metadata is not parseable XML: {exc}") from exc
    root = doc.documentElement
    if root.namespaceURI != MD or root.localName != "EntityDescriptor":
        raise ConfigurationError("metadata root is not a SAML EntityDescriptor")
    entity_id = root.getAttribute("entityID")
    if not entity_id:
        raise ConfigurationError("metadata carries no entityID")
    valid_until = None
    if root.getAttribute("validUntil"):
        try:
            valid_until = _parse_instant(root.getAttribute("validUntil"))
        except AuthenticationError as exc:
            raise ConfigurationError(str(exc)) from exc
        if valid_until <= now:
            raise ConfigurationError("IdP metadata is expired (validUntil in the past)")
    idp_desc = _el(root, MD, "IDPSSODescriptor")
    if idp_desc is None:
        raise ConfigurationError("metadata has no IDPSSODescriptor (not an IdP)")
    certs: list[CertificateInfo] = []
    for kd in _els(idp_desc, MD, "KeyDescriptor"):
        if kd.getAttribute("use") not in ("", "signing"):
            continue
        key_info = _el(kd, DSIG, "KeyInfo")
        cert_el = None
        if key_info is not None:
            x509_data = _el(key_info, DSIG, "X509Data")
            if x509_data is not None:
                cert_el = _el(x509_data, DSIG, "X509Certificate")
        if cert_el is None:
            raise ConfigurationError("signing KeyDescriptor carries no X509Certificate")
        try:
            certs.append(parse_certificate_b64(_text(cert_el)))
        except Exception as exc:
            raise ConfigurationError(f"metadata signing certificate unusable: {exc}") from exc
    if not certs:
        raise ConfigurationError("metadata carries no signing certificate")
    redirect_url = post_url = None
    for svc in _els(idp_desc, MD, "SingleSignOnService"):
        if svc.getAttribute("Binding") == BINDING_REDIRECT:
            redirect_url = svc.getAttribute("Location")
        elif svc.getAttribute("Binding") == BINDING_POST:
            post_url = svc.getAttribute("Location")
    if not redirect_url and not post_url:
        raise ConfigurationError("metadata offers no SingleSignOnService endpoint")
    return IdPMetadata(entity_id=entity_id, sso_redirect_url=redirect_url,
                       sso_post_url=post_url, signing_certs=tuple(certs),
                       valid_until=valid_until)


# ---------------------------------------------------------------- AuthnRequest


def new_request_id() -> str:
    return "_" + _secrets.token_hex(20)


def build_authn_request(*, request_id: str, sp_entity_id: str, acs_url: str,
                        destination: str, issue_instant: float,
                        force_authn: bool = False,
                        mfa_context_ref: Optional[str] = None) -> str:
    """The SP-initiated request document. Requests are unsigned in
    v1 — the SP holds no request-signing key story yet, and
    Shibboleth-class IdPs accept unsigned requests from SPs whose
    metadata does not require them; recorded as an E2 scope fact."""
    from xml.sax.saxutils import quoteattr
    force = ' ForceAuthn="true"' if force_authn else ""
    context = ""
    if mfa_context_ref:
        context = (
            '<samlp:RequestedAuthnContext Comparison="exact">'
            f"<saml:AuthnContextClassRef>{mfa_context_ref}</saml:AuthnContextClassRef>"
            "</samlp:RequestedAuthnContext>")
    return (
        f'<samlp:AuthnRequest xmlns:samlp="{SAML_PROTOCOL}" xmlns:saml="{SAML_ASSERTION}"'
        f' ID={quoteattr(request_id)} Version="2.0" IssueInstant="{_format_instant(issue_instant)}"'
        f' Destination={quoteattr(destination)} ProtocolBinding="{BINDING_POST}"'
        f' AssertionConsumerServiceURL={quoteattr(acs_url)}{force}>'
        f"<saml:Issuer>{sp_entity_id}</saml:Issuer>"
        '<samlp:NameIDPolicy AllowCreate="true"'
        ' Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"/>'
        f"{context}</samlp:AuthnRequest>")


def redirect_binding_url(request_xml: str, *, endpoint: str, relay_state: str) -> str:
    """HTTP-Redirect binding: DEFLATE (raw), base64, URL-encode."""
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    deflated = compressor.compress(request_xml.encode("utf-8")) + compressor.flush()
    params = {
        "SAMLRequest": base64.b64encode(deflated).decode("ascii"),
        "RelayState": relay_state,
    }
    sep = "&" if "?" in endpoint else "?"
    return endpoint + sep + urllib.parse.urlencode(params)


# ---------------------------------------------------------------- signatures


def _verify_element_signature(element, certs: tuple[CertificateInfo, ...]) -> None:
    """Verify the enveloped XML-DSig signature on `element` against
    the metadata-configured certificates. Raises AuthenticationError
    with the specific failure; returns None on success."""
    signature = _el(element, DSIG, "Signature")
    if signature is None:
        raise AuthenticationError("unsigned element where a signature is required")
    signed_info = _el(signature, DSIG, "SignedInfo")
    if signed_info is None:
        raise AuthenticationError("signature carries no SignedInfo")
    canon_method = _el(signed_info, DSIG, "CanonicalizationMethod")
    if canon_method is None or canon_method.getAttribute("Algorithm") != EXC_C14N:
        raise AuthenticationError("SignedInfo does not use exclusive canonicalization")
    sig_method = _el(signed_info, DSIG, "SignatureMethod")
    if sig_method is None or sig_method.getAttribute("Algorithm") != ALG_RSA_SHA256:
        raise AuthenticationError("signature method is not RSA-SHA256")
    references = _els(signed_info, DSIG, "Reference")
    if len(references) != 1:
        raise AuthenticationError("expected exactly one signature Reference")
    reference = references[0]
    element_id = element.getAttribute("ID")
    if reference.getAttribute("URI") != f"#{element_id}":
        raise AuthenticationError("signature Reference does not name the signed element")
    transforms = []
    transforms_el = _el(reference, DSIG, "Transforms")
    if transforms_el is not None:
        transforms = [t.getAttribute("Algorithm")
                      for t in _els(transforms_el, DSIG, "Transform")]
    if set(transforms) != {TRANSFORM_ENVELOPED, EXC_C14N}:
        raise AuthenticationError("signature transforms are not enveloped + exclusive C14N")
    digest_method = _el(reference, DSIG, "DigestMethod")
    if digest_method is None or digest_method.getAttribute("Algorithm") != ALG_SHA256:
        raise AuthenticationError("digest method is not SHA-256")
    digest_value_el = _el(reference, DSIG, "DigestValue")
    if digest_value_el is None:
        raise AuthenticationError("signature carries no DigestValue")
    expected_digest = base64.b64decode("".join(_text(digest_value_el).split()))

    # Enveloped transform: digest the element with its Signature
    # child removed, under the in-scope namespaces of the original.
    apex_scope = in_scope_namespaces(element)
    clone = element.cloneNode(True)
    for child in list(clone.childNodes):
        if (child.nodeType == Node.ELEMENT_NODE and child.namespaceURI == DSIG
                and child.localName == "Signature"):
            clone.removeChild(child)
    actual_digest = hashlib.sha256(canonicalize(clone, apex_scope)).digest()
    if not hmac.compare_digest(actual_digest, expected_digest):
        raise AuthenticationError("signed content digest mismatch (content altered after signing)")

    # KeyInfo, when it carries a certificate, must name the trusted
    # key — the anchor is the metadata cert, never the message's.
    key_info = _el(signature, DSIG, "KeyInfo")
    if key_info is not None:
        x509_data = _el(key_info, DSIG, "X509Data")
        cert_el = _el(x509_data, DSIG, "X509Certificate") if x509_data is not None else None
        if cert_el is not None:
            try:
                presented = parse_certificate_b64(_text(cert_el))
            except Exception as exc:
                raise AuthenticationError("KeyInfo certificate unparseable") from exc
            if all((presented.rsa_n, presented.rsa_e) != (c.rsa_n, c.rsa_e) for c in certs):
                raise AuthenticationError("KeyInfo certificate is not the configured IdP key")

    sig_value_el = _el(signature, DSIG, "SignatureValue")
    if sig_value_el is None:
        raise AuthenticationError("signature carries no SignatureValue")
    signature_bytes = base64.b64decode("".join(_text(sig_value_el).split()))
    signed_bytes = canonicalize(signed_info)
    if not any(_rs256_verify(signed_bytes, signature_bytes, cert.jwk()) for cert in certs):
        raise AuthenticationError("signature does not verify against the configured IdP key")


# ---------------------------------------------------------------- validation


@dataclass
class SamlAssertion:
    """The protocol boundary's output — shaped like the OIDC claims
    so everything downstream speaks only of identities (§2)."""
    issuer: str                 # IdP entity ID
    subject: str
    audience: str               # SP entity ID the assertion was for
    expires_at: float           # Conditions NotOnOrAfter
    auth_time: float
    amr: tuple[str, ...]
    acr: str                    # AuthnContextClassRef
    attributes: dict            # mapped per the tenant's attribute_map
    assertion_id: str
    response_id: str
    name_id: str = ""

    @property
    def mfa(self) -> bool:
        return any(a in self.amr for a in ("mfa", "otp", "hwk", "pwd+mfa")) or "mfa" in self.acr


@dataclass
class SamlIdPSettings:
    """What validation needs from the tenant's SAML configuration —
    the service builds this from the directory record + secrets."""
    idp_entity_id: str
    sp_entity_id: str
    acs_url: str
    signing_certs: tuple[CertificateInfo, ...]
    attribute_map: dict = field(default_factory=lambda: dict(DEFAULT_ATTRIBUTE_MAP))
    subject_source: str = "nameid"     # "nameid" | "eppn"


def _attribute_values(assertion) -> dict[str, list[str]]:
    """All assertion attributes, keyed by BOTH their OID-form and
    friendly-form names when either is present."""
    values: dict[str, list[str]] = {}
    stmt = _el(assertion, SAML_ASSERTION, "AttributeStatement")
    if stmt is None:
        return values
    for attr in _els(stmt, SAML_ASSERTION, "Attribute"):
        vals = [_text(v) for v in _els(attr, SAML_ASSERTION, "AttributeValue")]
        for key in {attr.getAttribute("Name"), attr.getAttribute("FriendlyName")}:
            if key:
                values.setdefault(key, []).extend(vals)
    return values


def validate_response(response_b64: str | bytes, *, settings: SamlIdPSettings,
                      pending_request_id: Optional[str],
                      now: Optional[float] = None) -> SamlAssertion:
    """Full response validation (T514). `pending_request_id` is the
    outstanding SP-initiated request ID, or None for IdP-initiated
    (unsolicited) responses — the caller decides whether unsolicited
    responses are acceptable for the tenant at all."""
    ts = now if now is not None else time.time()
    if isinstance(response_b64, str):
        response_b64 = response_b64.encode("ascii")
    try:
        xml_bytes = base64.b64decode(response_b64, validate=True)
    except Exception as exc:
        raise AuthenticationError("SAML response is not valid base64") from exc
    try:
        doc = parse_xml(xml_bytes)
    except Exception as exc:
        raise AuthenticationError(f"SAML response is not parseable XML: {exc}") from exc
    response = doc.documentElement
    if response.namespaceURI != SAML_PROTOCOL or response.localName != "Response":
        raise AuthenticationError("message is not a SAML Response")
    response_id = response.getAttribute("ID")
    if not response_id:
        raise AuthenticationError("response carries no ID")

    # A signature on the Response, when present, must verify; its
    # absence is fine only because the Assertion signature (below)
    # is mandatory.
    if _el(response, DSIG, "Signature") is not None:
        _verify_element_signature(response, settings.signing_certs)

    in_response_to = response.getAttribute("InResponseTo")
    if pending_request_id is not None:
        if in_response_to != pending_request_id:
            raise AuthenticationError("response InResponseTo does not name the outstanding request")
    elif in_response_to:
        raise AuthenticationError("unsolicited response carries an InResponseTo")
    destination = response.getAttribute("Destination")
    if destination and destination != settings.acs_url:
        raise AuthenticationError("response Destination is not this tenant's ACS")
    # Issuer is an assertion-namespace element even inside protocol
    # messages (the SAML schema defines it once, in the assertion
    # namespace) — looking it up under the protocol namespace would
    # silently skip this check.
    resp_issuer = _el(response, SAML_ASSERTION, "Issuer")
    if resp_issuer is not None and _text(resp_issuer) != settings.idp_entity_id:
        raise AuthenticationError("response issuer is not the configured IdP")
    status = _el(response, SAML_PROTOCOL, "Status")
    status_code = _el(status, SAML_PROTOCOL, "StatusCode") if status is not None else None
    if status_code is None or status_code.getAttribute("Value") != STATUS_SUCCESS:
        raise AuthenticationError("IdP returned a non-success status")

    if _el(response, SAML_ASSERTION, "EncryptedAssertion") is not None:
        raise AuthenticationError("encrypted assertions are not supported in v1")
    assertions = _els(response, SAML_ASSERTION, "Assertion")
    if len(assertions) != 1:
        raise AuthenticationError(f"expected exactly one assertion, found {len(assertions)}")
    assertion = assertions[0]
    assertion_id = assertion.getAttribute("ID")
    if not assertion_id:
        raise AuthenticationError("assertion carries no ID")

    # The mandatory half: the assertion's own signature.
    _verify_element_signature(assertion, settings.signing_certs)

    issuer_el = _el(assertion, SAML_ASSERTION, "Issuer")
    if issuer_el is None or _text(issuer_el) != settings.idp_entity_id:
        raise AuthenticationError("assertion issuer is not the configured IdP")

    conditions = _el(assertion, SAML_ASSERTION, "Conditions")
    if conditions is None:
        raise AuthenticationError("assertion carries no Conditions")
    not_before = conditions.getAttribute("NotBefore")
    not_on_or_after = conditions.getAttribute("NotOnOrAfter")
    if not not_on_or_after:
        raise AuthenticationError("assertion Conditions carry no NotOnOrAfter")
    expires_at = _parse_instant(not_on_or_after)
    if ts >= expires_at + CLOCK_SKEW_SECONDS:
        raise AuthenticationError("assertion is expired")
    if not_before and ts < _parse_instant(not_before) - CLOCK_SKEW_SECONDS:
        raise AuthenticationError("assertion is not yet valid")
    audiences = []
    for restriction in _els(conditions, SAML_ASSERTION, "AudienceRestriction"):
        audiences.extend(_text(a) for a in _els(restriction, SAML_ASSERTION, "Audience"))
    if settings.sp_entity_id not in audiences:
        raise AuthenticationError("assertion audience does not include this SP")

    subject = _el(assertion, SAML_ASSERTION, "Subject")
    name_id_el = _el(subject, SAML_ASSERTION, "NameID") if subject is not None else None
    if name_id_el is None or not _text(name_id_el):
        raise AuthenticationError("assertion subject carries no NameID")
    name_id = _text(name_id_el)
    confirmations = _els(subject, SAML_ASSERTION, "SubjectConfirmation")
    bearer = None
    for conf in confirmations:
        if conf.getAttribute("Method") == "urn:oasis:names:tc:SAML:2.0:cm:bearer":
            bearer = conf
    if bearer is None:
        raise AuthenticationError("assertion has no bearer SubjectConfirmation")
    conf_data = _el(bearer, SAML_ASSERTION, "SubjectConfirmationData")
    if conf_data is not None:
        recipient = conf_data.getAttribute("Recipient")
        if recipient and recipient != settings.acs_url:
            raise AuthenticationError("assertion Recipient is not this tenant's ACS")
        conf_irt = conf_data.getAttribute("InResponseTo")
        if pending_request_id is not None:
            if conf_irt != pending_request_id:
                raise AuthenticationError("confirmation InResponseTo does not name the outstanding request")
        elif conf_irt:
            raise AuthenticationError("unsolicited assertion confirmation carries an InResponseTo")
        conf_expiry = conf_data.getAttribute("NotOnOrAfter")
        if conf_expiry and ts >= _parse_instant(conf_expiry) + CLOCK_SKEW_SECONDS:
            raise AuthenticationError("assertion confirmation window has closed")

    authn_stmt = _el(assertion, SAML_ASSERTION, "AuthnStatement")
    if authn_stmt is None:
        raise AuthenticationError("assertion carries no AuthnStatement")
    auth_instant = authn_stmt.getAttribute("AuthnInstant")
    auth_time = _parse_instant(auth_instant) if auth_instant else ts
    context = _el(authn_stmt, SAML_ASSERTION, "AuthnContext")
    class_ref = _el(context, SAML_ASSERTION, "AuthnContextClassRef") if context is not None else None
    acr = _text(class_ref) if class_ref is not None else ""
    amr = ("mfa",) if acr in MFA_CONTEXT_REFS else ()

    raw_attributes = _attribute_values(assertion)
    attributes: dict[str, str] = {}
    for local, remote in settings.attribute_map.items():
        candidates = [remote]
        for pair in (EDU_PERSON_PRINCIPAL_NAME, EDU_PERSON_SCOPED_AFFILIATION):
            if remote in pair:
                candidates.extend(pair)
        for name in candidates:
            if raw_attributes.get(name):
                attributes[local] = "; ".join(raw_attributes[name])
                break
    if settings.subject_source == "eppn":
        eppn = None
        for name in EDU_PERSON_PRINCIPAL_NAME:
            if raw_attributes.get(name):
                eppn = raw_attributes[name][0]
                break
        if not eppn:
            raise AuthenticationError("tenant maps subject from eduPersonPrincipalName but the assertion carries none")
        subject_value = eppn
    else:
        subject_value = name_id

    return SamlAssertion(
        issuer=settings.idp_entity_id, subject=subject_value,
        audience=settings.sp_entity_id, expires_at=expires_at,
        auth_time=auth_time, amr=amr, acr=acr, attributes=attributes,
        assertion_id=assertion_id, response_id=response_id, name_id=name_id)
