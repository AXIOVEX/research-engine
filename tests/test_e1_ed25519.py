"""The service-layer Ed25519 (platform/ed25519.py) against the record
layer's Rust implementation: identical key derivation from the same
seeds is what makes enrollment fingerprints and gate signatures mean
the same thing on both sides of the platform/study boundary.
"""

import axiomere
import pytest

from tekmerion.platform import ed25519


def test_key_derivation_matches_axiomere_rust_core():
    for _ in range(25):
        seed_hex, pk_hex = axiomere.generate_keypair()
        assert ed25519.publickey_from_seed(bytes.fromhex(seed_hex)).hex() == pk_hex


def test_sign_verify_roundtrip_and_negatives():
    seed_hex, pk_hex = axiomere.generate_keypair()
    seed, pk = bytes.fromhex(seed_hex), bytes.fromhex(pk_hex)
    sig = ed25519.sign(seed, b"canonical intent")
    assert ed25519.verify(pk, b"canonical intent", sig)
    assert not ed25519.verify(pk, b"canonical intent!", sig)
    assert not ed25519.verify(pk, b"canonical intent", bytes([sig[0] ^ 1]) + sig[1:])
    assert not ed25519.verify(pk, b"canonical intent", sig[:32] + b"\xff" * 32)  # S out of range
    assert not ed25519.verify(b"\x00" * 32, b"canonical intent", sig)
    assert not ed25519.verify(pk, b"canonical intent", b"short")


def test_signatures_are_deterministic_rfc8032():
    seed_hex, _ = axiomere.generate_keypair()
    seed = bytes.fromhex(seed_hex)
    assert ed25519.sign(seed, b"m") == ed25519.sign(seed, b"m")


def test_bad_seed_lengths_rejected():
    with pytest.raises(ValueError):
        ed25519.publickey_from_seed(b"\x01" * 31)
    with pytest.raises(ValueError):
        ed25519.sign(b"\x01" * 33, b"m")
