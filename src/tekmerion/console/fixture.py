"""Fixture mode for the admin console (Spec 005, E5) — TESTS AND
SCREENSHOTS ONLY.

A `--fixture` run builds a complete, labeled specimen world against
the REAL platform service: two tenants, OIDC configured for both,
SAML configured for one, SCIM issued, keys in several states, a
declared break-glass policy with one reviewed session and one
pending session, seeded SPRS inputs and the FIPS POA&M item, an
anchored audit export. Every fact on every screen is then real
service state — the screens render exactly what a deployment's
screens render; only the world is specimen.

The fixture's identity provider is an in-process stand-in speaking
real OIDC to the service (the service validates its RS256 tokens,
PKCE, nonces, and MFA claims exactly as in production — the same
discipline as the platform test suite's mock). Its signing key is
the platform test suite's TEST-ONLY key, copied from
`tests/e1_world.py`; it generates no trust and must never be used
outside this fixture. The fixture IdP's authentication ceremony is
choosing the specimen user on a clearly labeled interstitial page —
in a deployment, that ceremony is the institution's own IdP.

KNOWN LIMITATION, stated plainly: SAML sign-in is not completable
in fixture mode (the SAML IdP is configured for display — real
entity, real certificate fingerprint — but no fixture SAML
responder exists). SAML sign-in is exercised end-to-end against the
service in the E2 battery and through this console's routes in the
E5 console tests, which drive the ACS over HTTP with the E2 test
world's responder.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets as _secrets
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from ..platform import ed25519
from ..platform.authz import ROLE_ACTIONS
from ..platform.directory import IdPConfig
from ..platform.oidc import OIDCClient
from ..platform.service import PLATFORM_TENANT_ID, PlatformService

# ------------------------------------------------------------ test-only key
# RSA keypair of the platform test suite's mock IdP (tests/e1_world.py).
# TEST-ONLY: public in the repo's tests; signs nothing real.
_IDP_N = 89595937415518251967979091840252030680752732949391027684172429872018744118014960611115202540259266885304429220906715176203498192892544197369309953052061928653020367450973719216482682943527605668572182068564088952414228295174014323947485930295479426167783598030231013424039015624194312864003339678626317110599
_IDP_E = 65537
_IDP_D = 77842938743604517555834558942031991500405276624476633296256742861478970506428000323434085060993982886754569172199343304286543282470992974933373647356217176926046424289056740901548056473611990064358220720439794363307457941148156280876865686331839007146561667165792277672480907043030958907503715234775812946273

PLATFORM_ISSUER = "https://idp-platform.fixture"
TENANT_A_ISSUER = "https://idp-a.fixture"
TENANT_B_ISSUER = "https://idp-b.fixture"
SAML_A_ENTITY = "https://idp-a.fixture/shibboleth"
SAML_A_SSO = "https://idp-a.fixture/saml/sso"
CLIENT_ID = "tekmerion-console"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _rs256_sign(message: bytes, n: int, d: int) -> bytes:
    digest = hashlib.sha256(message).digest()
    t = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    k = (n.bit_length() + 7) // 8
    em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


class FixtureTransport:
    """Routes the OIDC client's HTTP calls to the fixture IdPs."""

    def __init__(self, idp: "FixtureIdP") -> None:
        self._idp = idp

    def get_json(self, url: str) -> dict:
        return self._idp.handle_get(url)

    def post_form(self, url: str, data: dict) -> dict:
        return self._idp.handle_post(url, data)


class FixtureIdP:
    """In-process OIDC provider for the fixture world. Validates
    PKCE S256 for real; issues RS256 tokens the service verifies."""

    def __init__(self) -> None:
        self.issuers: dict[str, dict] = {}
        self._codes: dict[str, dict] = {}

    def add_issuer(self, issuer: str, users: dict[str, dict]) -> None:
        self.issuers[issuer] = {"users": users}

    # -- transport side
    def handle_get(self, url: str) -> dict:
        for issuer in self.issuers:
            if url == issuer + "/.well-known/openid-configuration":
                return {"issuer": issuer,
                        "authorization_endpoint": issuer + "/authorize",
                        "token_endpoint": issuer + "/token",
                        "jwks_uri": issuer + "/jwks"}
            if url == issuer + "/jwks":
                return {"keys": [{
                    "kty": "RSA", "kid": "fixture-1", "use": "sig", "alg": "RS256",
                    "n": _b64url(_IDP_N.to_bytes((_IDP_N.bit_length() + 7) // 8, "big")),
                    "e": _b64url(_IDP_E.to_bytes(3, "big"))}]}
        raise KeyError(f"fixture IdP: unknown GET {url}")

    def handle_post(self, url: str, data: dict) -> dict:
        for issuer in self.issuers:
            if url == issuer + "/token":
                record = self._codes.pop(data.get("code", ""), None)
                if record is None or record["issuer"] != issuer:
                    return {"error": "invalid_grant"}
                verifier = data.get("code_verifier", "")
                challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
                if challenge != record["challenge"]:
                    return {"error": "invalid_grant",
                            "error_description": "PKCE verification failed"}
                return {"id_token": self.issue_token(
                            issuer, record["subject"], nonce=record["nonce"]),
                        "access_token": "fixture-access", "token_type": "Bearer"}
        raise KeyError(f"fixture IdP: unknown POST {url}")

    # -- console/browser side
    def issue_code(self, issuer: str, subject: str, *, challenge: str,
                   nonce: str) -> str:
        code = _secrets.token_urlsafe(24)
        self._codes[code] = {"issuer": issuer, "subject": subject,
                             "challenge": challenge, "nonce": nonce}
        return code

    def issue_token(self, issuer: str, subject: str, *, nonce: str = "n-1") -> str:
        user = self.issuers[issuer]["users"][subject]
        amr = user.get("amr", ["pwd", "mfa"])
        now = int(time.time())
        header = {"alg": "RS256", "kid": "fixture-1", "typ": "JWT"}
        claims = {"iss": issuer, "sub": subject, "aud": CLIENT_ID,
                  "exp": now + 600, "iat": now, "nonce": nonce,
                  "name": user["name"], "email": user["email"],
                  "affiliation": user.get("affiliation", ""),
                  "amr": amr,
                  "acr": "https://refeds.org/profile/mfa" if "mfa" in amr else "pwd"}
        signing_input = (_b64url(json.dumps(header).encode()) + "." +
                         _b64url(json.dumps(claims).encode())).encode("ascii")
        return (signing_input.decode("ascii") + "." +
                _b64url(_rs256_sign(signing_input, _IDP_N, _IDP_D)))

    def users_for(self, issuer: str) -> list[tuple[str, str]]:
        return [(subject, u["label"]) for subject, u in
                self.issuers[issuer]["users"].items()]


# ------------------------------------------------------- SAML cert (DER)
# Minimal self-signed-certificate writer, after tests/e2_world.py —
# the fixture SAML IdP's certificate is real X.509 with a real
# SHA-256 fingerprint; only its trust is specimen.

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
    from datetime import datetime, timezone  # local: fixture-only helper
    return _seq(_tlv(0x31, _seq(_oid(2, 5, 4, 3), _tlv(0x0C, cn.encode("utf-8")))))


def _utctime(ts: float) -> bytes:
    from datetime import datetime, timezone
    text = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%y%m%d%H%M%SZ")
    return _tlv(0x17, text.encode("ascii"))


def _make_cert(cn: str, not_before: float, not_after: float) -> bytes:
    alg = _seq(_oid(1, 2, 840, 113549, 1, 1, 11), _tlv(0x05, b""))
    spki = _seq(_seq(_oid(1, 2, 840, 113549, 1, 1, 1), _tlv(0x05, b"")),
                _tlv(0x03, b"\x00" + _seq(_int(_IDP_N), _int(_IDP_E))))
    tbs = _seq(_tlv(0xA0, _int(2)), _int(1), alg, _name(cn),
               _seq(_utctime(not_before), _utctime(not_after)), _name(cn), spki)
    return _seq(tbs, alg, _tlv(0x03, b"\x00" + _rs256_sign(tbs, _IDP_N, _IDP_D)))


def _metadata_xml(entity_id: str, sso_url: str, cert_der: bytes) -> str:
    b64 = base64.b64encode(cert_der).decode("ascii")
    wrapped = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    md = "urn:oasis:names:tc:SAML:2.0:metadata"
    proto = "urn:oasis:names:tc:SAML:2.0:protocol"
    dsig = "http://www.w3.org/2000/09/xmldsig#"
    return (
        f'<md:EntityDescriptor xmlns:md="{md}" entityID="{entity_id}">'
        f'<md:IDPSSODescriptor protocolSupportEnumeration="{proto}">'
        f'<md:KeyDescriptor use="signing"><ds:KeyInfo xmlns:ds="{dsig}">'
        f"<ds:X509Data><ds:X509Certificate>\n{wrapped}\n</ds:X509Certificate></ds:X509Data>"
        f"</ds:KeyInfo></md:KeyDescriptor>"
        f'<md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{sso_url}"/>'
        f'<md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{sso_url}"/>'
        f"</md:IDPSSODescriptor></md:EntityDescriptor>")


# ------------------------------------------------------------------ world

@dataclass
class FixtureWorld:
    service: PlatformService
    idp: FixtureIdP
    base_url: str
    root: Path

    def rewrite(self, url: str) -> str | None:
        """Map a fixture IdP authorization URL to the console's
        local fixture-IdP interstitial (OIDC only)."""
        parsed = urllib.parse.urlparse(url)
        for issuer in self.idp.issuers:
            ip = urllib.parse.urlparse(issuer)
            if parsed.netloc == ip.netloc and parsed.path == "/authorize":
                q = urllib.parse.parse_qs(parsed.query)
                flat = {k: v[0] for k, v in q.items()}
                flat["issuer"] = issuer
                return "/fixture/idp/authorize?" + urllib.parse.urlencode(flat)
        return None


def _login(svc: PlatformService, idp: FixtureIdP, tenant_id: str,
           issuer: str, subject: str, *, step_up: bool = False) -> str:
    url = svc.begin_login(tenant_id, issuer)
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    code = idp.issue_code(issuer, subject,
                          challenge=params["code_challenge"],
                          nonce=params["nonce"])
    token = svc.complete_login(params["state"], code)
    if step_up:
        challenge = svc.begin_step_up(token)
        svc.step_up(token, id_token=idp.issue_token(issuer, subject, nonce=challenge),
                    nonce=challenge)
    return token


def build_fixture_world(root: str | Path, base_url: str) -> FixtureWorld:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    idp = FixtureIdP()
    idp.add_issuer(PLATFORM_ISSUER, {
        "root": {"name": "Root Operator", "email": "root@platform.fixture",
                 "label": "Root Operator — platform admin"}})
    idp.add_issuer(TENANT_A_ISSUER, {
        "admin-a": {"name": "Ada Admin", "email": "ada@uni-a.fixture",
                    "affiliation": "University A IT",
                    "label": "Ada Admin — tenant admin"},
        "alice": {"name": "Alice Researcher", "email": "alice@uni-a.fixture",
                  "affiliation": "University A",
                  "label": "Alice Researcher — researcher + tenant admin"},
        "adaeze": {"name": "Adaeze Verifier", "email": "adaeze@uni-a.fixture",
                   "affiliation": "University A",
                   "label": "Adaeze Verifier — integrity officer"},
        "ivy": {"name": "Ivy Chen", "email": "ivy@uni-a.fixture",
                "affiliation": "University A",
                "label": "Ivy Chen — reviewer"},
        "rudy": {"name": "Rudy Reyes", "email": "rudy@uni-a.fixture",
                 "affiliation": "University A",
                 "label": "Rudy Reyes — researcher"},
        "nils": {"name": "Nils No-MFA", "email": "nils@uni-a.fixture",
                 "affiliation": "University A",
                 "label": "Nils No-MFA — researcher, password-only (no MFA evidence)",
                 "amr": ["pwd"]},
        "mallory": {"name": "Mallory Departed", "email": "mallory@uni-a.fixture",
                    "affiliation": "University A (departed)",
                    "label": "Mallory Departed — deactivated during seeding"}})
    idp.add_issuer(TENANT_B_ISSUER, {
        "admin-b": {"name": "Bea Admin", "email": "bea@uni-b.fixture",
                    "affiliation": "University B IT",
                    "label": "Bea Admin — tenant admin"},
        "bob": {"name": "Bob Lindqvist", "email": "bob@uni-b.fixture",
                "affiliation": "University B",
                "label": "Bob Lindqvist — researcher"}})
    svc = PlatformService(root, oidc_client=OIDCClient(FixtureTransport(idp)))
    callback = base_url + "/auth/oidc/callback"
    acs = base_url + "/auth/saml/acs"
    svc.directory.add_idp(IdPConfig(
        tenant_id=PLATFORM_TENANT_ID, issuer=PLATFORM_ISSUER,
        client_id=CLIENT_ID,
        client_secret_ref="secret:fixture/deployment-oidc",
        redirect_uri=callback))
    svc.secrets.put("secret:fixture/deployment-oidc",
                    "fixture-deployment-secret")
    svc.bootstrap_platform_admin(issuer=PLATFORM_ISSUER, subject="root",
                                 display_name="Root Operator")
    root_session = _login(svc, idp, PLATFORM_TENANT_ID, PLATFORM_ISSUER,
                          "root", step_up=True)

    svc.create_tenant(root_session, tenant_id="uni-a", name="University A",
                      shape="hosted", region="us-east")
    svc.create_tenant(root_session, tenant_id="uni-b", name="University B",
                      shape="self-hosted", region="eu-west")
    svc.provision_tenant_idp(root_session, IdPConfig(
        tenant_id="uni-a", issuer=TENANT_A_ISSUER, client_id=CLIENT_ID,
        client_secret_ref="secret:fixture/uni-a-oidc",
        redirect_uri=callback), client_secret="fixture-uni-a-secret")
    now = time.time()
    cert = _make_cert("fixture-idp-a", now - 86400, now + 365 * 86400)
    svc.provision_tenant_saml_idp(
        root_session, tenant_id="uni-a", sp_entity_id="https://uni-a.fixture/sp",
        acs_url=acs, metadata_xml=_metadata_xml(SAML_A_ENTITY, SAML_A_SSO, cert))
    svc.provision_tenant_idp(root_session, IdPConfig(
        tenant_id="uni-b", issuer=TENANT_B_ISSUER, client_id=CLIENT_ID,
        client_secret_ref="secret:fixture/uni-b-oidc",
        redirect_uri=callback), client_secret="fixture-uni-b-secret")

    # --- uni-a membership
    _login(svc, idp, "uni-a", TENANT_A_ISSUER, "admin-a")
    admin_a_id = svc.directory.find_identity("uni-a", TENANT_A_ISSUER, "admin-a")
    svc.grant_role(root_session, tenant_id="uni-a",
                   identity_id=admin_a_id.identity_id, role="tenant_admin")
    admin_a = _login(svc, idp, "uni-a", TENANT_A_ISSUER, "admin-a", step_up=True)
    svc.issue_scim_token(admin_a, tenant_id="uni-a")
    grants = {"alice": ["researcher", "tenant_admin"],
              "adaeze": ["integrity_officer"], "ivy": ["reviewer"],
              "rudy": ["researcher"], "nils": ["researcher"]}
    sessions: dict[str, str] = {}
    for subject, roles in grants.items():
        sessions[subject] = _login(svc, idp, "uni-a", TENANT_A_ISSUER, subject,
                                   step_up=(subject != "nils"))
        ident = svc.directory.find_identity("uni-a", TENANT_A_ISSUER, subject)
        for role in roles:
            # tenant_admin itself is granted only from the platform
            # plane (the service reserves it); study roles are the
            # tenant admin's to grant.
            grantor = root_session if role == "tenant_admin" else admin_a
            svc.grant_role(grantor, tenant_id="uni-a",
                           identity_id=ident.identity_id, role=role)
    alice = sessions["alice"]

    # --- keys in several states
    def enroll_self(session: str, seed_byte: int) -> str:
        seed = bytes([seed_byte]) * 32
        pub = ed25519.publickey_from_seed(seed)
        nonce = svc.begin_enrollment(session)
        proof = ed25519.sign(seed, nonce.encode("utf-8"))
        rec = svc.enroll_self_key(session, public_key=pub,
                                  proof_signature=proof, nonce=nonce)
        return rec.fingerprint

    fp1 = enroll_self(alice, 0xA1)
    seed2 = bytes([0xA2]) * 32
    pub2 = ed25519.publickey_from_seed(seed2)
    nonce = svc.begin_enrollment(alice)
    svc.rotate_key(alice, old_fingerprint=fp1, new_public_key=pub2,
                   proof_signature=ed25519.sign(seed2, nonce.encode("utf-8")),
                   nonce=nonce)
    svc.enroll_delegated_key(alice, seed_hex=(bytes([0xA3]) * 32).hex())
    svc.enroll_delegated_key(sessions["adaeze"], seed_hex=(bytes([0xA4]) * 32).hex())
    ivy_fp = enroll_self(sessions["ivy"], 0xA5)
    svc.revoke_key(admin_a, key_fingerprint=ivy_fp,
                   reason="specimen revocation — fixture world")

    mallory = svc.admin_create_identity(
        admin_a, tenant_id="uni-a", issuer=TENANT_A_ISSUER,
        subject="mallory", display_name="Mallory Departed",
        email="mallory@uni-a.fixture", affiliation="University A (departed)")
    mallory_session = _login(svc, idp, "uni-a", TENANT_A_ISSUER, "mallory")
    enroll_self(mallory_session, 0xA6)
    svc.deactivate_identity(admin_a, identity_id=mallory.identity_id)

    # --- API key (machine principal)
    ingest = svc.create_service_identity(admin_a, tenant_id="uni-a",
                                         name="Ingest pipeline")
    svc.issue_api_key(admin_a, tenant_id="uni-a",
                      principal_identity_id=ingest.identity_id,
                      role_class="researcher",
                      scopes=sorted(ROLE_ACTIONS["researcher"])[:3],
                      lifetime_seconds=90 * 86400)

    # --- break-glass: declared policy, one reviewed session, one pending
    svc.declare_break_glass_policy(
        alice, tenant_id="uni-a", invoker_roles=["tenant_admin"],
        second_authorizer_plane="platform_admin",
        scopes=["tenant.audit_export", "tenant.key_manage",
                "tenant.member_manage"],
        max_duration_seconds=2 * 3600)
    bg1 = svc.invoke_break_glass(
        alice, tenant_id="uni-a",
        reason="IdP signing-certificate rotation — emergency membership repair",
        duration_seconds=3600)
    svc.authorize_break_glass(root_session, bg_session_id=bg1.bg_session_id)
    svc.break_glass_act(bg1.bg_session_id, session_token=alice,
                        action="tenant.audit_export")
    svc.close_break_glass(alice, bg_session_id=bg1.bg_session_id)
    state = svc.break_glass_state(alice, tenant_id="uni-a")
    review_item = [s for s in state["sessions"]
                   if s.bg_session_id == bg1.bg_session_id][0].review_item_id
    assert review_item
    svc.record_break_glass_review(
        admin_a, tenant_id="uni-a", bg_session_id=bg1.bg_session_id,
        disposition="reviewed — actions appropriate to the stated reason",
        note="Fixture specimen review.")
    svc.invoke_break_glass(
        alice, tenant_id="uni-a",
        reason="Pending specimen — awaiting platform authorization",
        duration_seconds=1800)

    # --- uni-b: minimal membership, no break-glass policy, no SCIM
    _login(svc, idp, "uni-b", TENANT_B_ISSUER, "admin-b")
    admin_b_id = svc.directory.find_identity("uni-b", TENANT_B_ISSUER, "admin-b")
    svc.grant_role(root_session, tenant_id="uni-b",
                   identity_id=admin_b_id.identity_id, role="tenant_admin")
    admin_b = _login(svc, idp, "uni-b", TENANT_B_ISSUER, "admin-b", step_up=True)
    _login(svc, idp, "uni-b", TENANT_B_ISSUER, "bob")
    bob_id = svc.directory.find_identity("uni-b", TENANT_B_ISSUER, "bob")
    svc.grant_role(admin_b, tenant_id="uni-b", identity_id=bob_id.identity_id,
                   role="researcher")

    # --- compliance + records
    svc.seed_control_states(root_session)
    svc.seed_poam_fips_item(root_session)
    exports_dir = root / "exports"
    manifest = svc.export_tenant_audit(root_session, "uni-a", exports_dir)
    svc.record_export_anchor(root_session, tenant_id="uni-a",
                             export_id=manifest["export_id"],
                             mechanism="fixture specimen anchor",
                             ref="FIXTURE-ANCHOR-001")
    svc.set_tenant_marking(root_session, tenant_id="uni-a", category="CTI",
                           authority="Fixture specimen contract clause",
                           dissemination="Fixture data only")
    return FixtureWorld(service=svc, idp=idp, base_url=base_url, root=root)
