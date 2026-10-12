"""Webhook / event egress (Spec 005 §9, T531) + the incident-response
event classes (T554) — platform events leave as signed records, or
they do not leave.

Shapes and mechanics live here; subscription administration, the
delivery ledger records, and emission hooks live on `PlatformService`
(the `webhooks` section of `service.py`), following the package's
grain (cf. `scim.py`).

The contract (CLM-005-21):
- Every delivery is signed: **HMAC-SHA256** with the tenant's egress
  secret (the `X-Tekmerion-Signature` header carries
  `HMAC_SHA256(timestamp + "." + body)`), or **Ed25519** with the
  tenant's egress signing key (seed in the secrets store by
  reference; the public key is published on the subscription).
- Every delivery carries a timestamp; the stated **replay window is
  300 seconds**. The reference receiver — shipped here, and the
  claim's test instrument — rejects unsigned, badly signed, stale,
  and replayed deliveries. A receiver that cannot reject is not a
  reference; it is a mirror.
- Deliveries retry with backoff up to `MAX_ATTEMPTS`; every attempt's
  outcome is a platform audit event (service-side). There are **no
  sockets in this module**: delivery goes through an injected
  transport callable, exactly as the OIDC client takes its transport
  — an HTTP adapter supplies the real one without semantic change.

T554's security-event classes are named constants here
(`SECURITY_EVENT_CLASSES`); the detectors (`SecurityMonitor`) count
the platform's own recorded failures/revocations in a sliding
window and fire at most one event per window per class per tenant —
a burst is one incident signal, not a second flood.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import secrets as _secrets
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import ed25519
from .errors import PlatformError

SIGNING_HMAC_SHA256 = "hmac-sha256"
SIGNING_ED25519 = "ed25519"
SIGNING_MODES = (SIGNING_HMAC_SHA256, SIGNING_ED25519)

#: The stated replay window (§9): a delivery whose timestamp is older
#: than this — or implausibly ahead — is rejected by the receiver.
REPLAY_WINDOW_SECONDS = 300

MAX_ATTEMPTS = 4                     # initial attempt + 3 retries
BACKOFF_SECONDS = (1.0, 5.0, 25.0)   # delay before retry n (1-based)

HEADER_SIGNATURE = "X-Tekmerion-Signature"
HEADER_TIMESTAMP = "X-Tekmerion-Timestamp"
HEADER_DELIVERY = "X-Tekmerion-Delivery"
HEADER_EVENT = "X-Tekmerion-Event"

# -- T554 security event classes (egress types) ---------------------------

SEC_AUTH_FAILURE_BURST = "security.authentication_failure_burst"
SEC_BREAK_GLASS_USE = "security.break_glass_use"
SEC_REVOCATION_STORM = "security.revocation_storm"
SEC_AUDIT_VERIFICATION_FAILURE = "security.audit_verification_failure"

SECURITY_EVENT_CLASSES = (
    SEC_AUTH_FAILURE_BURST, SEC_BREAK_GLASS_USE,
    SEC_REVOCATION_STORM, SEC_AUDIT_VERIFICATION_FAILURE,
)

#: The operational test-delivery type (every subscription door has one).
EVENT_TEST = "webhook.test"


class WebhookRejection(PlatformError):
    """The reference receiver refused a delivery: missing/invalid
    signature, timestamp outside the replay window, or a replay."""


@dataclass
class WebhookSubscription:
    """A tenant's registered egress endpoint. Secret material is
    never in this record: the HMAC secret and the Ed25519 seed live
    in the secrets store under `secret_ref` / `signing_key_ref`; the
    record carries their fingerprints (safe anywhere) and, for
    Ed25519, the public key (safe by definition)."""
    subscription_id: str
    tenant_id: str
    url: str
    signing: str                       # SIGNING_HMAC_SHA256 | SIGNING_ED25519
    event_classes: tuple[str, ...]     # exact types, "security.*", or "*"
    secret_ref: Optional[str] = None           # HMAC mode: secrets-store ref
    secret_fingerprint: Optional[str] = None   # HMAC mode: SHA-256 of the secret
    signing_key_ref: Optional[str] = None      # Ed25519 mode: secrets-store ref (seed hex)
    signing_public_key_hex: Optional[str] = None
    active: bool = True
    created_by_actor_id: str = ""

    def matches(self, event_type: str) -> bool:
        if not self.active:
            return False
        for pattern in self.event_classes:
            if pattern == "*" or pattern == event_type:
                return True
            if pattern.endswith(".*") and event_type.startswith(pattern[:-1]):
                return True
        return False


@dataclass
class Delivery:
    """One egress delivery and its retry state. `body`/`headers` are
    the exact wire artifacts — a retry re-sends the same signed body
    (the timestamp is the delivery's, not the attempt's, so retries
    do not launder a stale delivery into a fresh one; a delivery that
    ages past the replay window simply fails, recorded)."""
    delivery_id: str
    subscription_id: str
    tenant_id: str
    event_type: str
    body: bytes
    headers: dict
    created_at: float
    attempts: int = 0
    state: str = "pending"           # pending | delivered | failed
    next_attempt_at: float = 0.0
    last_status: Optional[int] = None
    last_error: str = ""


def canonical_body(*, delivery_id: str, event_type: str, tenant_id: str,
                   created_at: float, data: dict) -> bytes:
    """The signed payload: canonical JSON (sorted keys, tight
    separators), whole-second timestamp (§13.4 payload discipline
    applies to what we sign, too)."""
    doc = {
        "id": delivery_id,
        "type": event_type,
        "tenant_id": tenant_id,
        "created_at": int(created_at),
        "data": data,
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_delivery(*, signing: str, timestamp: int, body: bytes,
                  hmac_secret: Optional[bytes] = None,
                  ed25519_seed: Optional[bytes] = None) -> str:
    """The signature over `timestamp + "." + body` — the timestamp is
    inside the signed bytes, so a replayed body cannot be re-dated."""
    message = str(timestamp).encode("ascii") + b"." + body
    if signing == SIGNING_HMAC_SHA256:
        if hmac_secret is None:
            raise PlatformError("HMAC delivery requires the egress secret")
        return _hmac.new(hmac_secret, message, hashlib.sha256).hexdigest()
    if signing == SIGNING_ED25519:
        if ed25519_seed is None:
            raise PlatformError("Ed25519 delivery requires the signing key")
        return ed25519.sign(ed25519_seed, message).hex()
    raise PlatformError(f"unknown signing mode: {signing}")


def build_delivery(subscription: WebhookSubscription, *, event_type: str,
                   data: dict, now: float,
                   hmac_secret: Optional[bytes] = None,
                   ed25519_seed: Optional[bytes] = None) -> Delivery:
    delivery_id = "dlv_" + _secrets.token_hex(8)
    body = canonical_body(delivery_id=delivery_id, event_type=event_type,
                          tenant_id=subscription.tenant_id,
                          created_at=now, data=data)
    timestamp = int(now)
    signature = sign_delivery(
        signing=subscription.signing, timestamp=timestamp, body=body,
        hmac_secret=hmac_secret, ed25519_seed=ed25519_seed)
    headers = {
        HEADER_SIGNATURE: signature,
        HEADER_TIMESTAMP: str(timestamp),
        HEADER_DELIVERY: delivery_id,
        HEADER_EVENT: event_type,
        "Content-Type": "application/json",
    }
    return Delivery(
        delivery_id=delivery_id, subscription_id=subscription.subscription_id,
        tenant_id=subscription.tenant_id, event_type=event_type,
        body=body, headers=headers, created_at=now, next_attempt_at=now)


class ReferenceReceiver:
    """The claim's test instrument (F-005-21): a receiver that
    verifies exactly what §9 promises — signature present and valid,
    timestamp inside the stated replay window, delivery id not seen
    before — and rejects everything else, by name."""

    def __init__(self, *, signing: str,
                 hmac_secret: Optional[bytes] = None,
                 ed25519_public_key: Optional[bytes] = None,
                 now: Callable[[], float],
                 replay_window_seconds: int = REPLAY_WINDOW_SECONDS) -> None:
        if signing not in SIGNING_MODES:
            raise PlatformError(f"unknown signing mode: {signing}")
        self.signing = signing
        self._hmac_secret = hmac_secret
        self._ed25519_public_key = ed25519_public_key
        self._now = now
        self.replay_window_seconds = replay_window_seconds
        self._seen: dict[str, float] = {}   # delivery_id -> expiry

    def accept(self, headers: dict, body: bytes) -> dict:
        """Verify one delivery; returns the decoded event on success,
        raises WebhookRejection naming the failed check otherwise."""
        signature = headers.get(HEADER_SIGNATURE)
        if not signature:
            raise WebhookRejection("missing signature header")
        ts_raw = headers.get(HEADER_TIMESTAMP)
        if not ts_raw:
            raise WebhookRejection("missing timestamp header")
        try:
            timestamp = int(ts_raw)
        except (TypeError, ValueError):
            raise WebhookRejection("timestamp is not an integer")
        now = self._now()
        if abs(now - timestamp) > self.replay_window_seconds:
            raise WebhookRejection(
                f"timestamp outside the {self.replay_window_seconds}s replay window")
        delivery_id = headers.get(HEADER_DELIVERY)
        if not delivery_id:
            raise WebhookRejection("missing delivery id header")
        # Prune the replay register, then check this id.
        self._seen = {k: v for k, v in self._seen.items() if v > now}
        if delivery_id in self._seen:
            raise WebhookRejection(f"replayed delivery: {delivery_id}")
        message = str(timestamp).encode("ascii") + b"." + body
        if self.signing == SIGNING_HMAC_SHA256:
            if self._hmac_secret is None:
                raise WebhookRejection("receiver has no HMAC secret configured")
            expected = _hmac.new(self._hmac_secret, message, hashlib.sha256).hexdigest()
            if not _hmac.compare_digest(expected, signature):
                raise WebhookRejection("signature does not verify (HMAC-SHA256)")
        else:
            if self._ed25519_public_key is None:
                raise WebhookRejection("receiver has no Ed25519 public key configured")
            try:
                signature_bytes = bytes.fromhex(signature)
            except ValueError:
                raise WebhookRejection("signature is not hex")
            if not ed25519.verify(self._ed25519_public_key, message, signature_bytes):
                raise WebhookRejection("signature does not verify (Ed25519)")
        self._seen[delivery_id] = now + self.replay_window_seconds
        return json.loads(body.decode("utf-8"))


# -- T554 detectors ---------------------------------------------------------


class SecurityMonitor:
    """Sliding-window detectors for the T554 event classes that are
    *patterns* (bursts/storms). Break-glass use and audit-verification
    failures are discrete acts — the service emits those directly;
    this monitor exists so a flood of failures becomes ONE signal
    per window instead of a second flood of egress traffic."""

    def __init__(self) -> None:
        self._auth_failures: dict[str, deque] = {}
        self._revocations: dict[str, deque] = {}
        self._last_fired: dict[tuple[str, str], float] = {}

    def _observe(self, store: dict, last_fired_key: tuple[str, str],
                 tenant_id: str, *, now: float, count: int,
                 threshold: int, window: float) -> bool:
        hits = store.setdefault(tenant_id, deque())
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        for _ in range(count):
            hits.append(now)
        if len(hits) < threshold:
            return False
        last = self._last_fired.get(last_fired_key)
        if last is not None and now - last < window:
            return False          # already signalled this window
        self._last_fired[last_fired_key] = now
        return True

    def observe_auth_failure(self, tenant_id: str, *, now: float,
                             threshold: int, window: float) -> bool:
        """True exactly when this failure completes a burst that has
        not already been signalled in the current window."""
        return self._observe(self._auth_failures, ("auth", tenant_id),
                             tenant_id, now=now, count=1,
                             threshold=threshold, window=window)

    def observe_revocations(self, tenant_id: str, *, now: float, count: int,
                            threshold: int, window: float) -> bool:
        """Revocations arrive in ones (a key) and batches (a closure
        sweep); both feed the same storm detector."""
        return self._observe(self._revocations, ("revoke", tenant_id),
                             tenant_id, now=now, count=count,
                             threshold=threshold, window=window)
