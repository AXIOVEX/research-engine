"""Identity↔signing-key binding (Spec 005 §3, T504/T505/T506).

The registry is a **projection of the tenant's platform ledger**:
enrollment, rotation, revocation, and closure are events; the
registry rebuilds from them and holds no truth of its own. A key is
accepted for new appends iff its latest lifecycle state is *enrolled*
(not superseded by rotation, not revoked, not closed). Historical
signatures keep verifying regardless — verification consults the
public key, never the registry (F-005-04's second half).

Custody modes are distinguished on the record, never blurred (§3):
- *self-custody* — the private key never leaves the actor's control;
  signatures arrive at the gate already made.
- *delegated custody* — the platform signs server-side inside an
  authorized session. E1's signer is a **software development signer**
  standing in for a KMS/HSM: it exists so the custody plumbing —
  mode recorded on every append, session binding, step-up — is real
  and tested. It is not an HSM and the inventory (T549) says so.
"""

from __future__ import annotations

import hashlib
import secrets as _secrets
import time
from dataclasses import dataclass
from typing import Optional

from . import ed25519
from .directory import CUSTODY_DELEGATED, CUSTODY_MODES, CUSTODY_SELF
from .errors import GateDenied
from .ledger import (
    KEY_CLOSED, KEY_ENROLLED, KEY_REVOKED, KEY_ROTATED, PlatformLedger,
)

STATUS_ENROLLED = "enrolled"
STATUS_SUPERSEDED = "superseded"
STATUS_REVOKED = "revoked"
STATUS_CLOSED = "closed"
STATUS_UNKNOWN = "unknown"


def fingerprint(public_key: bytes) -> str:
    """Key fingerprint: SHA-256 of the public key, hex. This is what
    ledgers carry — never names, never emails (§4)."""
    return hashlib.sha256(public_key).hexdigest()


@dataclass
class KeyRecord:
    fingerprint: str
    public_key_hex: str
    identity_id: str
    actor_id: str
    custody: str
    status: str = STATUS_ENROLLED
    enrolled_seq: Optional[int] = None
    replaced_by: Optional[str] = None


class KeyRegistry:
    """Per-tenant projection over the tenant platform ledger."""

    def __init__(self, ledger: PlatformLedger, *, now=time.time) -> None:
        self.ledger = ledger
        self._now = now
        self.keys: dict[str, KeyRecord] = {}
        self._nonces: dict[str, tuple[str, float]] = {}  # nonce -> (identity_id, expires)
        self.rebuild()

    # -- projection --------------------------------------------------------

    def rebuild(self) -> None:
        self.keys = {}
        for ev in self.ledger.events():
            p = ev["payload"]
            t = ev["type"]
            if t == KEY_ENROLLED:
                self.keys[p["key_fingerprint"]] = KeyRecord(
                    fingerprint=p["key_fingerprint"],
                    public_key_hex=p["public_key"],
                    identity_id=p["identity_id"],
                    actor_id=p["actor_id"],
                    custody=p["custody"],
                    enrolled_seq=ev["seq"],
                )
            elif t == KEY_ROTATED:
                old = self.keys.get(p["key_fingerprint"])
                if old is not None:
                    old.status = STATUS_SUPERSEDED
                    old.replaced_by = p["new_key_fingerprint"]
                new = self.keys.get(p["new_key_fingerprint"])
                if new is not None:
                    new.status = STATUS_ENROLLED
            elif t == KEY_REVOKED:
                rec = self.keys.get(p["key_fingerprint"])
                if rec is not None:
                    rec.status = STATUS_REVOKED
            elif t == KEY_CLOSED:
                rec = self.keys.get(p["key_fingerprint"])
                if rec is not None:
                    rec.status = STATUS_CLOSED

    # -- queries -------------------------------------------------------------

    def get(self, fp: str) -> Optional[KeyRecord]:
        return self.keys.get(fp)

    def status(self, fp: str) -> str:
        rec = self.keys.get(fp)
        return rec.status if rec is not None else STATUS_UNKNOWN

    def is_accepted(self, fp: str) -> bool:
        """Accepted for NEW appends. Superseded, revoked, closed, and
        unknown keys are all refused at the gate."""
        return self.status(fp) == STATUS_ENROLLED

    def keys_for_identity(self, identity_id: str) -> list[KeyRecord]:
        return [k for k in self.keys.values() if k.identity_id == identity_id]

    # -- enrollment ceremony (T504) -------------------------------------------

    def issue_nonce(self, identity_id: str, *, ttl_seconds: float = 300) -> str:
        nonce = _secrets.token_hex(32)
        self._nonces[nonce] = (identity_id, self._now() + ttl_seconds)
        return nonce

    def enroll(self, *, identity_id: str, actor_id: str, public_key: bytes,
               custody: str, proof_signature: bytes, nonce: str,
               recorded_by_actor_id: str,
               countersigned_by_actor_id: Optional[str] = None) -> KeyRecord:
        """Enroll a key after proof of possession: the presenter signs
        the server nonce with the private key; the registry verifies
        before the enrollment event exists. A failed proof records
        nothing and raises — there is no pending state to exploit.
        `countersigned_by_actor_id` records a tenant admin's
        countersign on the event where §3 requires one (adjudicator
        re-enrollment, T522) — the subject's own actor ID stays the
        payload's `subject_actor_id`; the countersign is additive."""
        if custody not in CUSTODY_MODES:
            raise GateDenied(f"unknown custody mode: {custody}")
        pending = self._nonces.pop(nonce, None)
        if pending is None or pending[0] != identity_id or pending[1] < self._now():
            raise GateDenied("enrollment nonce unknown, mismatched, or expired")
        if not ed25519.verify(public_key, nonce.encode("utf-8"), proof_signature):
            raise GateDenied("proof of possession failed: signature does not verify")
        fp = fingerprint(public_key)
        if fp in self.keys and self.keys[fp].status == STATUS_ENROLLED:
            raise GateDenied("key already enrolled")
        extra = {}
        if countersigned_by_actor_id is not None:
            extra["countersigned_by_actor_id"] = countersigned_by_actor_id
        self.ledger.record(
            KEY_ENROLLED, actor_id=recorded_by_actor_id,
            target=f"key:{fp}",
            identity_id=identity_id, subject_actor_id=actor_id,
            key_fingerprint=fp, public_key=public_key.hex(), custody=custody,
            **extra,
        )
        self.rebuild()
        return self.keys[fp]

    # -- lifecycle (T505) --------------------------------------------------------

    def rotate(self, *, old_fingerprint: str, new_public_key: bytes,
               proof_signature: bytes, nonce: str, recorded_by_actor_id: str) -> KeyRecord:
        """Rotation supersedes: enroll the new key (with its own proof
        of possession), then record the rotation naming the key it
        replaces. The old key stops being accepted at this event; its
        historical signatures are untouched (they verify against the
        public key, which the record keeps)."""
        old = self.keys.get(old_fingerprint)
        if old is None or old.status != STATUS_ENROLLED:
            raise GateDenied("only an enrolled key can be rotated")
        new_rec = self.enroll(
            identity_id=old.identity_id, actor_id=old.actor_id,
            public_key=new_public_key, custody=old.custody,
            proof_signature=proof_signature, nonce=nonce,
            recorded_by_actor_id=recorded_by_actor_id,
        )
        self.ledger.record(
            KEY_ROTATED, actor_id=recorded_by_actor_id,
            target=f"key:{old_fingerprint}",
            identity_id=old.identity_id, subject_actor_id=old.actor_id,
            key_fingerprint=old_fingerprint,
            new_key_fingerprint=new_rec.fingerprint,
        )
        self.rebuild()
        return self.keys[new_rec.fingerprint]

    def revoke(self, *, fp: str, recorded_by_actor_id: str, reason: str = "") -> None:
        rec = self.keys.get(fp)
        if rec is None:
            raise GateDenied(f"cannot revoke unknown key: {fp}")
        if rec.status in (STATUS_REVOKED, STATUS_CLOSED):
            return  # already terminal; revocation is idempotent on the record
        self.ledger.record(
            KEY_REVOKED, actor_id=recorded_by_actor_id, target=f"key:{fp}",
            identity_id=rec.identity_id, subject_actor_id=rec.actor_id,
            key_fingerprint=fp, reason=reason,
        )
        self.rebuild()

    def close_for_identity(self, *, identity_id: str, recorded_by_actor_id: str,
                           reason: str = "deprovisioned") -> int:
        """Close every still-accepted key of an identity (deprovisioning,
        §4): each closure is its own event; history is untouched."""
        n = 0
        for rec in list(self.keys.values()):
            if rec.identity_id == identity_id and rec.status == STATUS_ENROLLED:
                self.ledger.record(
                    KEY_CLOSED, actor_id=recorded_by_actor_id, target=f"key:{rec.fingerprint}",
                    identity_id=identity_id, subject_actor_id=rec.actor_id,
                    key_fingerprint=rec.fingerprint, reason=reason,
                )
                n += 1
        if n:
            self.rebuild()
        return n


# -- signers -----------------------------------------------------------------


class LocalKeySigner:
    """A software key holder standing *client-side* of the gate: in
    production this is the actor's device/enclave (self-custody); in
    tests it is how a client key signs. Holds a raw seed — test and
    development use only."""

    custody = CUSTODY_SELF

    def __init__(self, seed_hex: str) -> None:
        self._seed = bytes.fromhex(seed_hex)
        self.public_key = ed25519.publickey_from_seed(self._seed)
        self.fingerprint = fingerprint(self.public_key)

    def sign(self, message: bytes) -> bytes:
        return ed25519.sign(self._seed, message)


class DelegatedSigner:
    """Server-side signer for delegated custody (T506). **Development
    signer**: holds seeds in process memory, standing in for the
    KMS/HSM of §3. It signs only when handed an authorized session
    context by the gate, and every signature it produces is recorded
    with `custody: delegated` + the authorizing session — the record
    attests exactly what happened, including that a software signer,
    not an HSM, made it."""

    custody = CUSTODY_DELEGATED

    def __init__(self) -> None:
        self._seeds: dict[str, bytes] = {}  # fingerprint -> seed

    def hold(self, seed_hex: str) -> str:
        seed = bytes.fromhex(seed_hex)
        fp = fingerprint(ed25519.publickey_from_seed(seed))
        self._seeds[fp] = seed
        return fp

    def sign(self, fp: str, message: bytes) -> bytes:
        seed = self._seeds.get(fp)
        if seed is None:
            raise GateDenied(f"delegated signer does not hold key: {fp}")
        return ed25519.sign(seed, message)
