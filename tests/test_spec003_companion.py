"""Axiomere Spec 003 companion (AXM-003-15), Tekmerion half.

The core now RECOMPUTES checkpoint roots during verification; these
tests prove Tekmerion's own flows consume that fact:

- a ledger whose checkpoint payload carries a root transplanted
  from another study's history — chain internally consistent, every
  signature valid — fails production verification, at the raw file
  check and through `verify_bundle` / `verify_anchor` /
  `verify_platform_audit_export` (the rt-b p01b construction, ported);
- at the study boundary, a store signed under an enrolled key
  verifies in trusted mode, and an append by any other key under the
  enrolled actor's name — which bare verification accepts as
  self-consistent — fails trusted verification with the actor named;
- an honestly unsigned ledger (the production study shape, and the
  frozen historical set's shape) still verifies in bare mode, with
  every unsigned event VISIBLE in the result and in the bundle
  verification record — never silently passed, never retro-failed.
"""

import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

import axiomere as ax  # noqa: E402

from tekmerion.export import verify_anchor, verify_bundle  # noqa: E402
from tekmerion.platform.exports import (  # noqa: E402
    export_platform_audit,
    verify_platform_audit_export,
)
from tekmerion.platform.ledger import PlatformLedger  # noqa: E402
from tekmerion.store import StudyStore  # noqa: E402

from test_phase5 import build_study, export  # noqa: E402,F401


# -- pure-Python Ed25519 (RFC 8032), for re-signing a forged line ----
# The forgery must carry a VALID signature by the forger's own key —
# that is the p01b construction: nothing about the file is broken
# except the root it claims. (Validated against the core: identical
# signatures for the same seed and message.)

_Q = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)


def _xrecover(y):
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q)
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_BY = (4 * pow(5, _Q - 2, _Q)) % _Q
_B = (_xrecover(_BY), _BY)


def _edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    den = pow(1 + _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    x3 = (x1 * y2 + x2 * y1) * den % _Q
    den2 = pow(1 - _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    y3 = (y1 * y2 + x1 * x2) * den2 % _Q
    return x3, y3


def _scalarmult(P, e):
    Q = (0, 1)
    while e > 0:
        if e & 1:
            Q = _edwards(Q, P)
        P = _edwards(P, P)
        e >>= 1
    return Q


def _encode_point(P):
    x, y = P
    out = bytearray(32)
    for i in range(255):
        if (y >> i) & 1:
            out[i // 8] |= 1 << (i % 8)
    if x & 1:
        out[31] |= 0x80
    return bytes(out)


def _clamped(h32: bytes) -> int:
    a = int.from_bytes(h32, "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a


def ed25519_sign(seed: bytes, msg: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    a = _clamped(h[:32])
    pub = _encode_point(_scalarmult(_B, a))
    r = int.from_bytes(hashlib.sha512(h[32:] + msg).digest(), "little") % _L
    r_enc = _encode_point(_scalarmult(_B, r))
    k = int.from_bytes(hashlib.sha512(r_enc + pub + msg).digest(), "little")
    s = (r + k * a) % _L
    return r_enc + s.to_bytes(32, "little")


# -- canonical form + chain surgery -----------------------------------

def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _event_hash(ev) -> str:
    body = {k: ev[k] for k in ("seq", "type", "ts", "actor", "payload", "prev_hash")}
    return hashlib.sha256((ev["prev_hash"] + _canonical(body)).encode()).hexdigest()


def _read_events(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "AXMR1"
    return [json.loads(line) for line in lines[1:] if line.strip()]


def _write_events(path, events):
    lines = ["AXMR1"] + [_canonical(ev) for ev in events]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_chain_faithful(events):
    """The surgery tooling must reproduce the core's own hashes on
    an untouched ledger — otherwise a post-surgery failure could be
    the tooling's arithmetic, not the forgery's lie."""
    prev = "0" * 64
    for ev in events:
        assert ev["prev_hash"] == prev
        assert _event_hash(ev) == ev["hash"], f"hash mismatch at seq {ev['seq']}"
        prev = ev["hash"]


def _rechain(events, from_seq):
    """Recompute prev_hash/hash from `from_seq` onward (unsigned
    events only — a signed chain is re-signed event by event by its
    forger, as in the raw test below)."""
    prev = "0" * 64
    for ev in events:
        if ev["seq"] >= from_seq:
            assert "sig" not in ev, "rechain helper is for unsigned ledgers"
            ev["prev_hash"] = prev
            ev["hash"] = _event_hash(ev)
        prev = ev["hash"]


def _rehash_bundle_manifest(bundle_dir):
    """The sophisticated attacker (mirrors test_phase5's helper):
    after altering bundle files, fix the manifest's file hashes and
    bundle hash so the manifest is self-consistent again."""
    bundle = Path(bundle_dir)
    manifest = json.loads((bundle / "manifest.json").read_text())
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    manifest["bundle_hash"] = hashlib.sha256(
        _canonical(core).encode()).hexdigest()
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


# -- (a) the transplant, raw: signed ledgers, valid signatures --------

def test_transplanted_checkpoint_root_fails_production_verification(tmp_path):
    # The victim: a signed study whose history includes a withdrawal
    # (a dead snapshot) before its checkpoint seals the range.
    victim_seed, _ = ax.generate_keypair()
    victim = ax.Database.create(str(tmp_path / "victim.axmr"), seed_hex=victim_seed)
    victim.snapshot("CLM-V", {"statement": "the original claim"}, actor="researcher", score=0.9)
    victim.dead("CLM-V", reason="retracted by the authors", actor="adjudicator")
    victim_cp = victim.checkpoint(actor="researcher")
    victim_root = victim_cp["payload"]["merkle_root"]

    # The attacker: a different signed history — no withdrawal in it —
    # sealed by its own honest checkpoint.
    attacker_seed, attacker_pub = ax.generate_keypair()
    attacker_path = str(tmp_path / "attacker.axmr")
    attacker = ax.Database.create(attacker_path, seed_hex=attacker_seed)
    attacker.snapshot("CLM-A", {"statement": "a cleaner claim"}, actor="researcher", score=0.9)
    attacker.snapshot("CLM-A", {"statement": "a cleaner claim, widened"}, actor="researcher", score=0.95)
    honest_cp = attacker.checkpoint(actor="researcher")
    assert honest_cp["payload"]["merkle_root"] != victim_root
    assert ax.verify_file(attacker_path).ok

    # The forgery (rt-b p01b): transplant the victim's externally
    # anchored root into the attacker's checkpoint payload, then
    # re-hash and re-sign the checkpoint event with the attacker's
    # own key. Chain consistent, signatures valid — the root is the
    # only lie.
    events = _read_events(attacker_path)
    _assert_chain_faithful(events)
    cp = events[-1]
    assert cp["type"] == "checkpoint"
    cp["payload"]["merkle_root"] = victim_root
    cp["hash"] = _event_hash(cp)
    cp["sig"] = ed25519_sign(bytes.fromhex(attacker_seed),
                             cp["hash"].encode()).hex()
    assert cp["signer"] == attacker_pub
    forged = str(tmp_path / "forged.axmr")
    _write_events(forged, events)

    result = ax.verify_file(forged)
    assert not result.ok
    assert result.reason == "checkpoint-root-mismatch"
    # Every signature the verifier reached is genuine (it rejects at
    # the checkpoint event, whose root it recomputes before the
    # signature step) — the rejection is the recomputed root, not a
    # signature failure.
    assert result.signatures_failed == 0
    assert result.signatures_checked == len(events) - 1


# -- (a) the transplant through Tekmerion's bundle + anchor paths -----

def test_transplanted_root_fails_bundle_and_anchor_verification(tmp_path):
    store, reg, _frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved, "bundle-a")
    bundle = tmp_path / "bundle-a"

    # An honestly unsigned production bundle verifies — and its
    # verification record SHOWS the unsigned state (every event
    # listed), rather than passing silently.
    honest = verify_bundle(str(bundle))
    assert honest.ok, honest.failures
    ledger_events = _read_events(bundle / "ledger" / "study.axmr")
    assert honest.checks["ledger_verify"]["unsigned_events"] == \
        [e["seq"] for e in ledger_events]
    assert honest.checks["ledger_verify"]["signatures_checked"] == 0
    assert honest.checks["ledger_head_pin"]["ok"]

    # A different history supplies the victim root (a standalone
    # ledger with different claims — its own checkpoint over its
    # own events).
    victim_db = ax.Database.create(str(tmp_path / "victim.axmr"))
    victim_db.snapshot("CLM-V", {"statement": "an unrelated result"},
                       actor="researcher", score=0.7)
    victim_root = victim_db.checkpoint(actor="researcher")["payload"]["merkle_root"]
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["study"]["checkpoint_root"] != victim_root

    # The forgery: transplant the victim root into bundle A's
    # ledger checkpoint, re-chain the (unsigned) remainder, and
    # restate the manifest so bundle and manifest agree on the lie.
    events = _read_events(bundle / "ledger" / "study.axmr")
    _assert_chain_faithful(events)
    cps = [e for e in events if e["type"] == "checkpoint"]
    assert cps, "exported study ledger carries a checkpoint"
    cp = cps[-1]
    cp["payload"]["merkle_root"] = victim_root
    _rechain(events, cp["seq"])
    _write_events(bundle / "ledger" / "study.axmr", events)

    manifest["study"]["checkpoints"] = [
        {"seq": e["seq"], "upto_seq": e["payload"]["upto_seq"],
         "merkle_root": e["payload"]["merkle_root"]}
        for e in events if e["type"] == "checkpoint"]
    manifest["study"]["checkpoint_root"] = victim_root
    manifest["study"]["head_hash"] = events[-1]["hash"]
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest = _rehash_bundle_manifest(bundle)

    # The production verifier now recomputes the root from the
    # ledger's own events: the transplant fails even though the
    # chain, the manifest, and every file hash are consistent.
    raw = ax.verify_file(str(bundle / "ledger" / "study.axmr"))
    assert not raw.ok and raw.reason == "checkpoint-root-mismatch"
    result = verify_bundle(str(bundle))
    assert not result.ok
    assert any("production verification" in f or "recomputed" in f
               for f in result.failures)

    # The anchor path binds only through a verified bundle: a public
    # record naming the transplanted root and the forged bundle's
    # own hash cannot rescue it.
    record = {
        "id": 999, "doi": "10.5281/zenodo.999",
        "created": "2026-10-13T00:00:00Z",
        "metadata": {"description":
                     f"bundle {manifest['bundle_hash']} root {victim_root}"},
        "files": [],
    }
    anchor = verify_anchor(str(bundle), record)
    assert not anchor.ok
    assert any("does not verify" in f for f in anchor.failures)


def test_transplanted_root_fails_platform_export_verification(tmp_path):
    ledger_path = str(tmp_path / "audit.axmr")
    ledger = PlatformLedger.create(ledger_path, scope="deployment")
    ledger.record("tenant.created", actor_id="root", target="tenant:t1")
    ledger.record("role.granted", actor_id="root", target="identity:i1")
    ledger.checkpoint(actor_id="root")
    manifest = export_platform_audit(ledger, ledger_path, str(tmp_path / "exp"))
    honest_root = manifest["ledger"]["checkpoint_root"]

    out = tmp_path / "exp"
    assert verify_platform_audit_export(str(out)).ok

    # Transplant a foreign root, re-chain, restate the manifest.
    foreign_root = "ab" * 32
    assert foreign_root != honest_root
    events = _read_events(out / "ledger" / "audit.axmr")
    _assert_chain_faithful(events)
    cp = [e for e in events if e["type"] == "checkpoint"][-1]
    cp["payload"]["merkle_root"] = foreign_root
    _rechain(events, cp["seq"])
    _write_events(out / "ledger" / "audit.axmr", events)
    m = json.loads((out / "manifest.json").read_text())
    m["ledger"]["checkpoints"] = [
        {"seq": e["seq"], "upto_seq": e["payload"]["upto_seq"],
         "merkle_root": e["payload"]["merkle_root"]}
        for e in events if e["type"] == "checkpoint"]
    m["ledger"]["checkpoint_root"] = foreign_root
    m["ledger"]["head_hash"] = events[-1]["hash"]
    (out / "manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
    _rehash_bundle_manifest(out)

    result = verify_platform_audit_export(str(out))
    assert not result.ok
    assert any("production verification" in f or "recomputed" in f
               for f in result.failures)


# -- (b) trusted mode at the study boundary ----------------------------

def test_trusted_mode_binds_appends_to_the_enrolled_key(tmp_path):
    seed, pub = ax.generate_keypair()
    path = str(tmp_path / "signed.axmr")
    store = StudyStore.create(path, seed_hex=seed)
    store.register_claim("CLM-1", {"statement": "X holds", "falsifier": "obs Y"},
                         actor="researcher", score=0.8)
    store.issue_verdict("CLM-1", {"verdict": "supported"}, actor="researcher")

    # The enrolled ledger verifies bare and in trusted mode.
    assert store.verify().ok
    trusted = store.verify(trusted={"researcher": pub})
    assert trusted.ok, trusted

    # An append by a DIFFERENT key under the enrolled actor's name:
    # bare verification accepts it — the file is self-consistent and
    # the signature is valid for the key it carries. That is exactly
    # why the boundary requires the trusted map.
    attacker_seed, _ = ax.generate_keypair()
    raw = ax.Database.open(path, seed_hex=attacker_seed)
    raw.append("verdict.issued", {"claim_id": "CLM-1", "verdict": "contradicted"},
               actor="researcher")
    assert store.verify().ok
    refused = store.verify(trusted={"researcher": pub})
    assert not refused.ok
    assert "researcher" in refused.untrusted_actors or \
        refused.reason == "signer-key-mismatch"


def test_unsigned_append_to_signed_study_fails_verification(tmp_path):
    seed, _pub = ax.generate_keypair()
    path = str(tmp_path / "signed2.axmr")
    store = StudyStore.create(path, seed_hex=seed)
    store.register_claim("CLM-1", {"statement": "X holds", "falsifier": "obs Y"},
                         actor="researcher", score=0.8)
    assert store.verify().ok

    # The seedless-append construction (red team C p08): reopen the
    # ledger with no key at all and append. A ledger carrying
    # signature material no longer verifies with an unsigned event
    # in it — in any mode.
    raw = ax.Database.open(path)
    forged = raw.append("verdict.issued",
                        {"claim_id": "CLM-1", "verdict": "contradicted"},
                        actor="researcher")
    result = store.verify()
    assert not result.ok
    assert result.reason == "unsigned-event"
    assert forged["seq"] in result.unsigned_events


# -- (c) honestly unsigned ledgers: verify, visibly ---------------------

def test_unsigned_study_verifies_with_its_state_visible(tmp_path):
    path = str(tmp_path / "unsigned.axmr")
    store = StudyStore.create(path)  # the production study shape: no seed
    store.register_claim("CLM-1", {"statement": "X holds", "falsifier": "obs Y"},
                         actor="researcher", score=0.8)
    store.freeze(actor="researcher")
    result = store.verify()
    assert result.ok
    assert result.signatures_checked == 0
    assert list(result.unsigned_events) == [e["seq"] for e in store.events()]
