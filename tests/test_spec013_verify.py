"""Spec 013 Lane D — WS-2 verification consumers (CLM-013-01/02).

Ports of the red-team probes rt-a p01 (bundle evidence tamper) and
p02 (anchor gap) that demonstrated RTA-01/RTA-02 against the shipped
0.1.0: an evidence-flipped, manifest-rehashed copy of the real Phase 7
bundle verified ok=True and re-derived the opposite verdict, and it
passed verify_anchor against the real Zenodo record because the
presented bundle's own hash was never compared to any anchored value.

Fixtures are the repo's frozen Phase 7 bundles (bundle-v1/v2) and a
record fixture carrying the values the real public record
(Zenodo 23319126, captured by rt-a p02) actually states: the anchored
Merkle root, bundle-v1's hash (NOT bundle-v2's), and the deposited
file's md5. Bundle-v2's own hash is anchored in the OSF registration
84dk7 record (RTE-24); the OSF-shaped fixture here states exactly the
values that record states for bundle-v2.
"""
import json
import shutil
from pathlib import Path

import pytest

from tekmerion import export as export_mod
from tekmerion.export import verify_anchor, verify_bundle

REPO = Path(__file__).resolve().parents[1]
BUNDLE_V1 = REPO / "specs/002-mvp-implementation/evaluation/study/bundle-v1"
BUNDLE_V2 = REPO / "specs/002-mvp-implementation/evaluation/study/bundle-v2"

# The real Zenodo 23319126 record (Phase 7 deposit of bundle-v1),
# values as captured by rt-a/probes/p02_anchor_gap.py.
ZENODO_RECORD = {
    "id": 23319126,
    "doi": "10.5281/zenodo.23319126",
    "created": "2026-10-12T13:56:18.552121+00:00",
    "metadata": {
        "title": "Tekmerion Spec 002 Phase 7 evaluation — audit bundle "
                 "(frozen run vs kill criteria K1–K5)",
        "description": (
            "Tekmerion audit bundle (format tekmerion-audit-bundle/1).\n"
            "Merkle checkpoint root (anchored value): "
            "a4c798715c05ae151849ddf0e7c4a3dcb7b119620757b088686bd18d24e6c049\n"
            "Bundle hash (SHA-256): "
            "296786be0f31d212435b64c89f685a9c14b31cff6f36b6c603e41d05c21b10c2\n"
            "Registration hash: "
            "977c1db162e9ba06b3e34c633a5bbae96fe4779aa49c43356b564cc8c3b9ac9b"),
    },
    "files": [{"key": "bundle-v1.zip", "size": 16047,
               "checksum": "md5:4f28bbc34390df9e660dfc941e308112"}],
}


def _copy(src: Path, tmp_path: Path, name: str) -> Path:
    dst = tmp_path / name
    shutil.copytree(src, dst)
    return dst


def _rehash(bundle: Path) -> None:
    """Manifest rehash exactly as rt-a's attacker did it — with the
    export module's own helpers, so the tampered file set is bound by
    a self-consistent manifest."""
    mpath = bundle / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["sha256"] = export_mod._sha256(data)
        entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    manifest["bundle_hash"] = export_mod._sha256(export_mod._canonical(core))
    mpath.write_bytes(export_mod._dump(manifest))


def _flip_items(bundle: Path, *, groups_too: bool = False,
                delete_one: bool = False) -> None:
    """rt-a p01: CLM-E-001's evidence items flip supports ->
    contradicts (0.8 mass), on the bundle copy only."""
    path = bundle / "evidence" / "items.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for item in doc["items"]:
        if item["claim_id"] == "CLM-E-001":
            item["stance"] = "contradicts"
            item["support_mass"] = 0.0
            item["contradiction_mass"] = 0.8
    if delete_one:
        doc["items"] = [i for i in doc["items"]
                        if i["item_id"] != "CIT-E-102"]
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    if groups_too:
        path = bundle / "evidence" / "groups.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        for g in doc["groups"]:
            if g["claim_id"] == "CLM-E-001":
                g["support_mass"] = 0.0
                g["contradiction_mass"] = 0.8
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


# --------------------------------------------------------------- CLM-013-01

def test_frozen_phase7_bundles_verify_and_rederive():
    """Pristine frozen bundles pass, with the re-derivation check
    actually running (fold compared, standing verdicts re-derived)."""
    for src in (BUNDLE_V1, BUNDLE_V2):
        result = verify_bundle(str(src))
        assert result.ok, result.failures
        assert result.checks["evidence_fold_groups"] > 0
        assert result.checks["verdicts_rederived"] == 5


def test_items_only_tamper_fails_verification(tmp_path):
    """rt-a p01 variant (a): items flipped, groups left as issued."""
    bundle = _copy(BUNDLE_V2, tmp_path, "tampered")
    _flip_items(bundle)
    _rehash(bundle)
    result = verify_bundle(str(bundle))
    assert not result.ok
    assert any("fold of evidence/items.json" in f for f in result.failures)
    assert any("does not re-derive" in f and "CLM-E-001" in f
               for f in result.failures)


def test_items_and_groups_tamper_fails_on_rederivation(tmp_path):
    """rt-a p01 variant (b): items AND groups flipped consistently —
    the fold agrees with itself, so only verdict re-derivation can
    catch it: the bundle's own evidence re-derives 'contradicted'
    where 'supported' was issued."""
    bundle = _copy(BUNDLE_V2, tmp_path, "tampered")
    _flip_items(bundle, groups_too=True)
    _rehash(bundle)
    result = verify_bundle(str(bundle))
    assert not result.ok
    assert any("does not re-derive" in f and "CLM-E-001" in f
               and "'contradicted'" in f for f in result.failures)


def test_item_deleted_tamper_fails_verification(tmp_path):
    """rt-a p01 variant (c): one of CLM-E-001's items deleted."""
    bundle = _copy(BUNDLE_V2, tmp_path, "tampered")
    _flip_items(bundle, delete_one=True)
    _rehash(bundle)
    result = verify_bundle(str(bundle))
    assert not result.ok
    assert any("CLM-E-001" in f for f in result.failures)


def test_groups_only_tamper_fails_on_fold(tmp_path):
    """Groups edited without touching items: the fold comparison
    alone must catch the disagreement."""
    bundle = _copy(BUNDLE_V2, tmp_path, "tampered")
    path = bundle / "evidence" / "groups.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for g in doc["groups"]:
        if g["claim_id"] == "CLM-E-001":
            g["support_mass"] = 0.0
            g["contradiction_mass"] = 0.8
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    _rehash(bundle)
    result = verify_bundle(str(bundle))
    assert not result.ok
    assert any("fold of evidence/items.json" in f for f in result.failures)


# --------------------------------------------------------------- CLM-013-02

def test_anchor_binds_the_deposited_bundle_itself():
    """Bundle-v1 IS the bundle Zenodo 23319126 deposits: the record
    states its own hash and root, so it verifies as anchored — the
    deposited bundle no longer needs a successor to vouch for it."""
    result = verify_anchor(str(BUNDLE_V1), ZENODO_RECORD)
    assert result.ok, result.failures
    assert result.details["own_hash_anchor"] == "anchored"


def test_anchor_successor_bundle_is_named_unanchored(tmp_path):
    """rt-a p02, pristine side: bundle-v2 presented against bundle-v1's
    record validates the receipt chain but is NOT itself anchored by
    that record — the outcome is named, and the presentation does
    not pass (pre-fix this returned ok=True)."""
    result = verify_anchor(str(BUNDLE_V2), ZENODO_RECORD)
    assert not result.ok
    assert result.details["own_hash_anchor"] == "unanchored"
    assert any("own bundle_hash is not anchored" in f
               for f in result.failures)
    # The receipt chain itself is intact: it contributes no failure.
    assert not any("anchored root" in f or "deposited bundle's hash" in f
                   for f in result.failures)


def test_anchor_tampered_bundle_fails(tmp_path):
    """rt-a p02, attack side (F-013-2): the evidence-tampered,
    rehashed bundle must not pass verify_anchor against the real
    anchored record."""
    bundle = _copy(BUNDLE_V2, tmp_path, "tampered")
    _flip_items(bundle)
    _rehash(bundle)
    result = verify_anchor(str(bundle), ZENODO_RECORD)
    assert not result.ok


def test_anchor_record_stating_own_hash_passes():
    """Bundle-v2's own hash IS anchored — in the OSF registration
    84dk7 record, which states exactly bundle-v2's checkpoint root
    and bundle hash (RTE-24). Against a record stating them, the
    own-hash binding passes."""
    manifest = json.loads((BUNDLE_V2 / "manifest.json")
                          .read_text(encoding="utf-8"))
    osf_record = {
        "id": 84_067,
        "doi": "10.17605/OSF.IO/84DK7",
        "created": "2026-10-12T15:21:45Z",
        "metadata": {"description": (
            "OSF registration of the Tekmerion Phase 7 evaluation "
            "bundle. Registration hash: "
            "977c1db162e9ba06b3e34c633a5bbae96fe4779aa49c43356b564cc8c3b9ac9b; "
            f"checkpoint root: {manifest['study']['checkpoint_root']}; "
            f"bundle hash: {manifest['bundle_hash']}.")},
        "files": [],
    }
    result = verify_anchor(str(BUNDLE_V2), osf_record)
    assert result.ok, result.failures
    assert result.details["own_hash_anchor"] == "anchored"


def test_anchor_foreign_record_still_rejected(tmp_path):
    """A record stating a different bundle's hash and root anchors
    nothing about this bundle (the HELD defense from rt-a p08's
    family: wrong-record presentations fail)."""
    foreign = json.loads(json.dumps(ZENODO_RECORD))
    foreign["id"] = 99999999
    foreign["doi"] = "10.5281/zenodo.99999999"
    foreign["metadata"]["description"] = foreign["metadata"]["description"].replace(
        "296786be0f31d212435b64c89f685a9c14b31cff6f36b6c603e41d05c21b10c2",
        "ab" * 32)
    result = verify_anchor(str(BUNDLE_V1), foreign)
    assert not result.ok
