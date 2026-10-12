"""OIDC relying party (Spec 005 §2, T503) — authorization code flow
with PKCE (S256 required), discovery, and ID-token validation
(RS256 against the issuer's JWKS). There is no other credential path:
no local passwords exist anywhere in this package (F-005-01).

Transport is injectable, in the connectors' house pattern
(`tekmerion.connectors.HttpJson`): tests drive the client against an
in-process mock IdP through the same callables production uses with
urllib. RSA verification is plain modular arithmetic + EMSA-PKCS1-v1_5
encoding comparison — verification only; the platform never signs
with RSA. (Prototype-grade, non-FIPS — see `ed25519.py`'s note and
the crypto inventory, T549.)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets as _secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .errors import AuthenticationError

USER_AGENT = "Tekmerion/0.1 (platform; +https://axiovexsystems.com)"


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class HttpTransport:
    """JSON/form HTTP for OIDC endpoints; injectable for tests."""

    def __init__(self, opener: Optional[Callable[..., Any]] = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def get_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with self._opener(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def post_form(self, url: str, form: dict) -> dict:
        body = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"User-Agent": USER_AGENT,
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        with self._opener(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))


def pkce_pair() -> tuple[str, str]:
    """(verifier, S256 challenge). S256 is the only method this RP
    will ever offer — plain PKCE is a falsifier hit (F-005-01)."""
    verifier = _secrets.token_urlsafe(48)
    challenge = _b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


_RS256_DIGESTINFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _rs256_verify(signing_input: bytes, signature: bytes, jwk: dict) -> bool:
    if jwk.get("kty") != "RSA":
        return False
    n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    k = (n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    m = pow(int.from_bytes(signature, "big"), e, n)
    em = m.to_bytes(k, "big")
    digest = hashlib.sha256(signing_input).digest()
    t = _RS256_DIGESTINFO_PREFIX + digest
    expected = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return hmac.compare_digest(em, expected)


@dataclass
class IdTokenClaims:
    issuer: str
    subject: str
    audience: str
    expires_at: float
    issued_at: float
    auth_time: float
    nonce: str
    amr: tuple[str, ...]
    acr: str
    attributes: dict          # mapped per the tenant's attribute_map

    @property
    def mfa(self) -> bool:
        return any(a in self.amr for a in ("mfa", "otp", "hwk", "pwd+mfa")) or "mfa" in self.acr


class OIDCClient:
    """One RP instance; per-tenant configuration comes from the
    directory's IdPConfig at call time, so one client serves all
    tenants and protocol state never leaks between them."""

    def __init__(self, transport: Optional[HttpTransport] = None, *,
                 now: Callable[[], float] = time.time) -> None:
        self.transport = transport or HttpTransport()
        self._now = now
        self._discovery: dict[str, dict] = {}
        self._jwks: dict[str, dict] = {}

    # -- discovery / keys --------------------------------------------------

    def discover(self, issuer: str) -> dict:
        if issuer not in self._discovery:
            doc = self.transport.get_json(issuer.rstrip("/") + "/.well-known/openid-configuration")
            if doc.get("issuer") != issuer:
                raise AuthenticationError("discovery document issuer mismatch")
            self._discovery[issuer] = doc
        return self._discovery[issuer]

    def _signing_key(self, issuer: str, kid: str) -> dict:
        doc = self.discover(issuer)
        jwks = self._jwks.get(issuer)
        if jwks is None or all(k.get("kid") != kid for k in jwks.get("keys", [])):
            jwks = self.transport.get_json(doc["jwks_uri"])  # refetch covers JWKS rotation
            self._jwks[issuer] = jwks
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise AuthenticationError("ID token signing key not found in JWKS")

    # -- flow -----------------------------------------------------------------

    def authorization_url(self, *, issuer: str, client_id: str, redirect_uri: str,
                          state: str, nonce: str, code_challenge: str,
                          acr_values: Optional[str] = None) -> str:
        doc = self.discover(issuer)
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if acr_values:
            params["acr_values"] = acr_values
        return doc["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)

    def exchange_code(self, *, issuer: str, client_id: str, client_secret: str,
                      redirect_uri: str, code: str, code_verifier: str) -> dict:
        doc = self.discover(issuer)
        return self.transport.post_form(doc["token_endpoint"], {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        })

    def validate_id_token(self, id_token: str, *, issuer: str, client_id: str,
                          nonce: str, attribute_map: Optional[dict] = None) -> IdTokenClaims:
        """Full validation: signature (JWKS/RS256), issuer, audience,
        expiry, nonce. Any failure is an AuthenticationError — the
        caller records it as an authentication failure event."""
        try:
            header_b64, payload_b64, sig_b64 = id_token.split(".")
        except ValueError:
            raise AuthenticationError("malformed ID token")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "RS256":
            raise AuthenticationError(f"unexpected ID token alg: {header.get('alg')}")
        key = self._signing_key(issuer, header.get("kid", ""))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        if not _rs256_verify(signing_input, _b64url_decode(sig_b64), key):
            raise AuthenticationError("ID token signature does not verify")
        claims = json.loads(_b64url_decode(payload_b64))
        now = self._now()
        if claims.get("iss") != issuer:
            raise AuthenticationError("ID token issuer mismatch")
        if claims.get("aud") != client_id:
            raise AuthenticationError("ID token audience mismatch")
        if float(claims.get("exp", 0)) <= now:
            raise AuthenticationError("ID token expired")
        if claims.get("nonce") != nonce:
            raise AuthenticationError("ID token nonce mismatch")
        attributes = {}
        for local, remote in (attribute_map or {}).items():
            if remote in claims:
                attributes[local] = claims[remote]
        return IdTokenClaims(
            issuer=issuer, subject=str(claims["sub"]), audience=client_id,
            expires_at=float(claims["exp"]), issued_at=float(claims.get("iat", now)),
            auth_time=float(claims.get("auth_time", claims.get("iat", now))),
            nonce=nonce, amr=tuple(claims.get("amr", [])), acr=str(claims.get("acr", "")),
            attributes=attributes,
        )
