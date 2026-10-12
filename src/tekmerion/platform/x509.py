"""Minimal X.509 reading for SAML metadata (Spec 005 E2, T513).

The SP needs exactly two things from an IdP signing certificate in
imported metadata: the RSA public key it carries, and its validity
window. Trust does NOT come from the certificate's chain — it comes
from the tenant's configuration act (the metadata was imported by an
authorized admin for this tenant), so no path validation happens
here and this module never pretends otherwise. A small DER reader is
all that takes; stdlib-only, like the rest of the platform plane.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


class CertificateError(ValueError):
    pass


def _read_tlv(data: bytes, pos: int) -> tuple[int, bytes, int]:
    """(tag, content, next_pos) for one DER TLV at `pos`."""
    if pos + 2 > len(data):
        raise CertificateError("truncated DER")
    tag = data[pos]
    pos += 1
    first = data[pos]
    pos += 1
    if first & 0x80:
        n = first & 0x7F
        if n == 0 or pos + n > len(data):
            raise CertificateError("bad DER length")
        length = int.from_bytes(data[pos:pos + n], "big")
        pos += n
    else:
        length = first
    if pos + length > len(data):
        raise CertificateError("truncated DER value")
    return tag, data[pos:pos + length], pos + length


def _children(content: bytes) -> list[tuple[int, bytes]]:
    out = []
    pos = 0
    while pos < len(content):
        tag, val, pos = _read_tlv(content, pos)
        out.append((tag, val))
    return out


def _parse_time(tag: int, val: bytes) -> float:
    text = val.decode("ascii")
    if tag == 0x17:  # UTCTime YYMMDDHHMMSSZ
        yy = int(text[0:2])
        year = 2000 + yy if yy < 50 else 1900 + yy
        rest = text[2:]
    elif tag == 0x18:  # GeneralizedTime YYYYMMDDHHMMSSZ
        year = int(text[0:4])
        rest = text[4:]
    else:
        raise CertificateError("unexpected time encoding in certificate")
    if not rest.endswith("Z"):
        raise CertificateError("only Zulu certificate times are handled")
    rest = rest[:-1]
    month, day = int(rest[0:2]), int(rest[2:4])
    hour, minute, second = int(rest[4:6]), int(rest[6:8]), int(rest[8:10])
    return datetime(year, month, day, hour, minute, second,
                    tzinfo=timezone.utc).timestamp()


@dataclass
class CertificateInfo:
    der: bytes
    rsa_n: int
    rsa_e: int
    not_before: float
    not_after: float

    @property
    def fingerprint(self) -> str:
        """SHA-256 of the DER — the value audit records carry (§9)."""
        return hashlib.sha256(self.der).hexdigest()

    def jwk(self) -> dict:
        """The key in the shape `oidc._rs256_verify` consumes."""
        def b64(x: int) -> str:
            return base64.urlsafe_b64encode(
                x.to_bytes((x.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")
        return {"kty": "RSA", "n": b64(self.rsa_n), "e": b64(self.rsa_e)}


def parse_certificate(der: bytes) -> CertificateInfo:
    """Extract (RSA key, validity) from a DER certificate."""
    tag, cert_body, end = _read_tlv(der, 0)
    if tag != 0x30 or end != len(der):
        raise CertificateError("not a DER certificate sequence")
    parts = _children(cert_body)
    if len(parts) != 3:
        raise CertificateError("certificate must have exactly 3 parts")
    tbs = parts[0][1]
    fields = _children(tbs)
    # TBSCertificate: [0] version (optional), serial, signature alg,
    # issuer, validity, subject, subjectPublicKeyInfo, ...
    idx = 1 if fields and fields[0][0] == 0xA0 else 0
    if len(fields) < idx + 6:
        raise CertificateError("TBSCertificate too short")
    validity = _children(fields[idx + 3][1])
    if len(validity) != 2:
        raise CertificateError("validity must hold two times")
    not_before = _parse_time(*validity[0])
    not_after = _parse_time(*validity[1])
    spki = _children(fields[idx + 5][1])
    if len(spki) != 2:
        raise CertificateError("subjectPublicKeyInfo malformed")
    bit_string = spki[1][1]
    if not bit_string or bit_string[0] != 0:
        raise CertificateError("subjectPublicKey BIT STRING must be byte-aligned")
    tag, rsa_body, end = _read_tlv(bit_string[1:], 0)
    if tag != 0x30:
        raise CertificateError("RSAPublicKey is not a sequence")
    ints = _children(rsa_body)
    if len(ints) != 2:
        raise CertificateError("RSAPublicKey must hold modulus and exponent")
    n = int.from_bytes(ints[0][1], "big")
    e = int.from_bytes(ints[1][1], "big")
    return CertificateInfo(der=der, rsa_n=n, rsa_e=e,
                           not_before=not_before, not_after=not_after)


def parse_certificate_b64(text: str) -> CertificateInfo:
    """Metadata carries certificates as whitespace-wrapped base64."""
    compact = "".join(text.split())
    try:
        der = base64.b64decode(compact, validate=True)
    except Exception as exc:
        raise CertificateError("certificate is not valid base64") from exc
    return parse_certificate(der)
