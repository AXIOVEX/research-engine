"""E1 test world: an in-process mock OIDC provider + a fully wired
PlatformService. No sockets, no external services, no spend (Spec 005
E1 testing constraints). The mock enforces PKCE S256 at its token
endpoint for real, so a broken relying party fails these tests.

The RSA keys below are TEST-ONLY constants generated for this mock.
They sign nothing outside these tests.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.parse
from types import SimpleNamespace

from tekmerion.platform import authz
from tekmerion.platform.directory import IdPConfig
from tekmerion.platform.oidc import OIDCClient, _b64url_encode
from tekmerion.platform.service import PLATFORM_TENANT_ID, PlatformService

# TEST-ONLY RSA keypair for the mock IdP.
IDP_N = 89595937415518251967979091840252030680752732949391027684172429872018744118014960611115202540259266885304429220906715176203498192892544197369309953052061928653020367450973719216482682943527605668572182068564088952414228295174014323947485930295479426167783598030231013424039015624194312864003339678626317110599
IDP_E = 65537
IDP_D = 77842938743604517555834558942031991500405276624476633296256742861478970506428000323434085060993982886754569172199343304286543282470992974933373647356217176926046424289056740901548056473611990064358220720439794363307457941148156280876865686331839007146561667165792277672480907043030958907503715234775812946273
# TEST-ONLY attacker keypair: tokens signed with this must never validate.
ATTACKER_N = 69612852007303211676241093770030350603675069893291314825319561103028497434907412862183774166300748746976565946762868391257262511294804527657725051701369978198404801213957894651244526853832992169421040545642475637527820710072310309686413145306029477762960482231485962062308537132845411030665794949552448745669
ATTACKER_E = 65537
ATTACKER_D = 22977329060255780322267533460996025821424525259497348403212120569765360887924640356359909711543369347003937845192400766584938319488673749825166063725895829948719123613792832284728724760946725686716414626469123232919030469673843607928368426747413004399688917987547386919837734598398039452867030211418403479553

_RS256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _rs256_sign(signing_input: bytes, n: int, d: int) -> bytes:
    k = (n.bit_length() + 7) // 8
    t = _RS256_PREFIX + hashlib.sha256(signing_input).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


def _int_b64(x: int) -> str:
    return _b64url_encode(x.to_bytes((x.bit_length() + 7) // 8, "big"))


class MockIdP:
    """A multi-issuer OIDC provider behind the transport interface the
    real client uses. `authorize()` plays the browser's role."""

    def __init__(self, clock):
        self.clock = clock
        self.issuers: dict[str, dict] = {}   # issuer -> {subject: profile}
        self.codes: dict[str, dict] = {}
        self.token_lifetime = 3600
        self.sign_key = (IDP_N, IDP_E, IDP_D)  # tests may swap in the attacker key

    def add_issuer(self, issuer: str, users: dict[str, dict]) -> None:
        self.issuers[issuer] = users

    # -- transport interface (what OIDCClient calls) -------------------

    def get_json(self, url: str) -> dict:
        for issuer in self.issuers:
            if url == issuer + "/.well-known/openid-configuration":
                return {
                    "issuer": issuer,
                    "authorization_endpoint": issuer + "/authorize",
                    "token_endpoint": issuer + "/token",
                    "jwks_uri": issuer + "/jwks",
                }
            if url == issuer + "/jwks":
                return {"keys": [{"kty": "RSA", "kid": "test-key-1",
                                  "n": _int_b64(IDP_N), "e": _int_b64(IDP_E)}]}
        raise AssertionError(f"mock IdP: unexpected GET {url}")

    def post_form(self, url: str, form: dict) -> dict:
        for issuer in self.issuers:
            if url == issuer + "/token":
                return self._token(issuer, form)
        raise AssertionError(f"mock IdP: unexpected POST {url}")

    # -- the browser's part ---------------------------------------------

    def authorize(self, auth_url: str, subject: str) -> tuple[str, str]:
        """Returns (code, state) as the redirect would carry them.
        Enforces that the RP actually offered PKCE S256."""
        parsed = urllib.parse.urlparse(auth_url)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        assert params["code_challenge_method"] == "S256", "RP must offer S256 PKCE"
        assert params["response_type"] == "code"
        issuer = f"{parsed.scheme}://{parsed.netloc}"
        code = f"code-{len(self.codes)}-{subject}"
        self.codes[code] = {
            "issuer": issuer, "subject": subject, "nonce": params["nonce"],
            "challenge": params["code_challenge"],
        }
        return code, params["state"]

    # -- token endpoint ---------------------------------------------------

    def _token(self, issuer: str, form: dict) -> dict:
        assert form["grant_type"] == "authorization_code"
        grant = self.codes.pop(form["code"])  # KeyError == invalid code, as at a real IdP
        verifier = form["code_verifier"]
        challenge = _b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
        assert challenge == grant["challenge"], "PKCE verification failed at the IdP"
        profile = self.issuers[issuer][grant["subject"]]
        return {"id_token": self.issue_token(
            issuer=issuer, subject=grant["subject"], audience=form["client_id"],
            nonce=grant["nonce"], profile=profile, key=self.sign_key)}

    def issue_token(self, *, issuer: str, subject: str, audience: str, nonce: str,
                    profile: dict, key: tuple[int, int, int] = (IDP_N, IDP_E, IDP_D),
                    lifetime: int | None = None) -> str:
        now = self.clock()
        claims = {
            "iss": issuer, "sub": subject, "aud": audience,
            "iat": now, "auth_time": now,
            "exp": now + (lifetime if lifetime is not None else self.token_lifetime),
            "nonce": nonce,
            "amr": profile.get("amr", ["pwd", "mfa"]),
            "acr": profile.get("acr", "urn:mfa"),
            "name": profile.get("name", ""), "email": profile.get("email", ""),
            "affiliation": profile.get("affiliation", ""),
        }
        header = {"alg": "RS256", "kid": "test-key-1", "typ": "JWT"}
        signing_input = (
            _b64url_encode(json.dumps(header).encode()) + "."
            + _b64url_encode(json.dumps(claims).encode())
        ).encode("ascii")
        n, _e, d = key
        sig = _rs256_sign(signing_input, n, d)
        return signing_input.decode("ascii") + "." + _b64url_encode(sig)


ISSUER_PLATFORM = "https://idp-platform.test"
ISSUER_A = "https://idp-a.test"
TENANT_A = "uni-a"

USERS_PLATFORM = {
    "root": {"name": "Root Operator", "email": "root@platform.test"},
}
USERS_A = {
    "admin-a": {"name": "Ada Admin", "email": "admin@uni-a.test"},
    "alice": {"name": "Alice Researcher", "email": "alice@uni-a.test", "affiliation": "Uni A"},
    "ada": {"name": "Ada Adjudicator", "email": "ada@uni-a.test", "affiliation": "Uni A"},
    "ivy": {"name": "Ivy Integrity", "email": "ivy@uni-a.test", "affiliation": "Uni A"},
    "rudy": {"name": "Rudy Reviewer", "email": "rudy@uni-a.test", "affiliation": "Uni A"},
    "mallory": {"name": "Mallory", "email": "mallory@uni-a.test"},
    "nomfa": {"name": "No Mfa", "email": "nomfa@uni-a.test", "amr": ["pwd"], "acr": "urn:basic"},
}


def build_world(tmp_path, *, start_time: float = 1_760_000_000.0) -> SimpleNamespace:
    """A complete E1 world: platform admin bootstrapped and logged in,
    tenant uni-a created, its IdP provisioned, tenant admin granted.
    Tenant users log in on demand via `login()`."""
    clock_box = [start_time]
    clock = lambda: clock_box[0]  # noqa: E731
    mock = MockIdP(clock)
    mock.add_issuer(ISSUER_PLATFORM, USERS_PLATFORM)
    mock.add_issuer(ISSUER_A, USERS_A)
    service = PlatformService(
        tmp_path / "platform", now=clock,
        oidc_client=OIDCClient(transport=mock, now=clock))
    w = SimpleNamespace(service=service, mock=mock, clock_box=clock_box,
                        tenant_id=TENANT_A, issuer_a=ISSUER_A)

    def login(tenant_id: str, issuer: str, subject: str) -> str:
        url = service.begin_login(tenant_id, issuer)
        code, state = mock.authorize(url, subject)
        return service.complete_login(state, code)

    w.login = login
    service.bootstrap_platform_admin(
        issuer=ISSUER_PLATFORM, subject="root", display_name="Root Operator")
    # Deployment IdP for the platform tenant (provisioning act).
    service.directory.add_idp(IdPConfig(
        tenant_id=PLATFORM_TENANT_ID, issuer=ISSUER_PLATFORM, client_id="tekmerion-platform",
        client_secret_ref="secret:platform-idp", redirect_uri="https://platform.test/callback"))
    service.secrets.put("secret:platform-idp", "test-only-platform-secret")
    w.root_session = login(PLATFORM_TENANT_ID, ISSUER_PLATFORM, "root")
    root = service.directory.find_identity(PLATFORM_TENANT_ID, ISSUER_PLATFORM, "root")
    w.root = root
    service.create_tenant(w.root_session, tenant_id=TENANT_A, name="University A")
    service.provision_tenant_idp(w.root_session, IdPConfig(
        tenant_id=TENANT_A, issuer=ISSUER_A, client_id="tekmerion-uni-a",
        client_secret_ref="secret:uni-a-idp", redirect_uri="https://uni-a.test/callback"),
        client_secret="test-only-uni-a-secret")
    # Tenant admin logs in (identity created, no roles) and is granted
    # tenant_admin by the platform admin — the bootstrap path.
    w.admin_session = login(TENANT_A, ISSUER_A, "admin-a")
    admin_ident = service.directory.find_identity(TENANT_A, ISSUER_A, "admin-a")
    w.admin = admin_ident
    service.grant_role(w.root_session, identity_id=admin_ident.identity_id,
                       role=authz.TENANT_ADMIN, tenant_id=TENANT_A)
    w.admin_session = login(TENANT_A, ISSUER_A, "admin-a")  # fresh session post-grant
    return w


def login_user(w: SimpleNamespace, subject: str, role: str | None = None):
    """Log a tenant user in; optionally grant them a study role (by the
    tenant admin). Returns (session_token, identity)."""
    session = w.login(w.tenant_id, w.issuer_a, subject)
    ident = w.service.directory.find_identity(w.tenant_id, w.issuer_a, subject)
    if role is not None:
        w.service.grant_role(w.admin_session, identity_id=ident.identity_id,
                             role=role, tenant_id=w.tenant_id)
        session = w.login(w.tenant_id, w.issuer_a, subject)
    return session, ident
