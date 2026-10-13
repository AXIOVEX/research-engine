"""Phase 5 tests: audit bundle, standalone verification, deposit
gating, and the anchor loop — seeded defects through the production
paths (a flipped byte, an altered manifest root, a truncated ledger,
a foreign study's anchor record). The live Zenodo demonstration is a
manual smoke (recorded in tasks.md), not a CI dependency; the anchor
loop is exercised end-to-end here against the local transport, whose
receipts are honestly labeled local."""

import io
import urllib.error
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister
from tekmerion.connectors import CrossrefConnector, HttpJson, RetrievedItem, run_query
from tekmerion.deposit import (
    DepositError,
    LocalTransport,
    deposit_bundle,
    osf_metadata,
    package_bundle,
    record_anchor,
    zenodo_metadata,
)
from tekmerion.export import ExportError, export_bundle, verify_anchor, verify_bundle
from tekmerion.freeze import freeze
from tekmerion.store import StudyStore
from tekmerion.verdicts import Control, evaluate_run
from tekmerion.verification import (
    Citation,
    decide,
    pending_second_reviews,
    to_evidence_item,
    verify_citations,
)

PROP = "Auricular stimulation improves sleep quality"

REAL_WORK = {
    "DOI": "10.1000/xyz123",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "Auricular stimulation improved sleep quality significantly in a controlled trial.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

META_WORK = {  # resolves and agrees, carries no content anyone may check
    "DOI": "10.1000/metaonly",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


class RoutingHttp(HttpJson):
    def get(self, url, headers=None):
        if "query.bibliographic" in url:
            return {"message": {"items": [REAL_WORK]}}
        for marker, work in (("xyz123", REAL_WORK), ("metaonly", META_WORK)):
            if marker in url:
                return {"message": work}
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=io.BytesIO(b"{}"))


def crossref():
    return CrossrefConnector(http=RoutingHttp())


def claim(cid, **kw):
    base = dict(statement="X holds", falsifier="observing not-X in a powered test",
                margin=0.1, sufficiency_floor=1)
    base.update(kw)
    return Claim(claim_id=cid, **base)


def controls():
    pos = Control(
        failure_mode="retrieval broken: known-true claim not supported",
        kind="positive",
        claim=claim("CLM-S-900"),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported",
        representative_rationale="same domain and difficulty class as the study claims",
    )
    neg = Control(
        failure_mode="verification decorative: fabricated citation accepted",
        kind="negative",
        claim=claim("CLM-S-901"),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    return [pos, neg, swap]


def citation(cid, claim_id, doi):
    return Citation(citation_id=cid, claim_id=claim_id, proposition=PROP, doi=doi,
                    title="Auricular Stimulation and Sleep Quality",
                    authors=["Ada Lovelace"], year=2024, venue="Journal of X")


def build_study(tmp_path, name="s"):
    """A complete small study through the production paths: register,
    retrieve, verify, adjudicate, freeze, verdict — ready to export."""
    store = StudyStore.create(str(tmp_path / f"{name}.axmr"))
    reg = ClaimRegister()
    for cid, stmt, actor in (
            ("CLM-S-001", "Auricular stimulation improves sleep quality", "researcher"),
            ("CLM-S-002", "The effect replicates in a second cohort", "co-researcher")):
        c = claim(cid, statement=stmt)
        reg.register(c)
        store.register_claim(cid, c.as_dict(), actor=actor)

    run_query(store, crossref(), "auricular stimulation sleep", actor="researcher")
    cits = [citation("CIT-1", "CLM-S-001", "10.1000/xyz123"),
            citation("CIT-2", "CLM-S-002", "10.1000/metaonly"),
            citation("CIT-3", "CLM-S-001", "10.1000/doesnotexist")]
    report = verify_citations(store, cits, [crossref()], actor="researcher")
    by_id = {r.citation_id: r for r in report.results}
    assert by_id["CIT-1"].content == "supports"
    assert by_id["CIT-2"].content == "metadata_only"
    assert by_id["CIT-3"].resolution == "not_found"

    for qid in report.queue_item_ids:
        decide(store, qid, "exclude", adjudicator="adjudicator",
               rationale="fabricated DOI — excluded from the evidence basis")
    for qid in pending_second_reviews(store, fraction=0.10, seed=7):
        store.log_second_review(qid, reviewer="second-reviewer", agrees=True)

    reg.add_evidence("CLM-S-001", to_evidence_item(cits[0], by_id["CIT-1"]))
    reg.add_evidence("CLM-S-002", to_evidence_item(cits[1], by_id["CIT-2"]))

    frozen = freeze(store, reg, controls(), actor="researcher", linked_exploratory=[])
    result = evaluate_run(reg, mode="confirmation", controls=controls(),
                          store_path=str(tmp_path / f"{name}.axmr"))
    assert result.run_verdict == "valid"
    for verdict in result.claim_verdicts:
        store.issue_verdict(verdict.claim_id, verdict.as_dict(), actor="verdict-service")
    retrieved = {r.citation_id: r.retrieved for r in report.results if r.retrieved}
    return store, reg, frozen, retrieved


def export(tmp_path, store, reg, retrieved, name="bundle"):
    return export_bundle(store, str(tmp_path / "s.axmr"), str(tmp_path / name),
                         register=reg, controls=controls(), linked_exploratory=[],
                         retrieved=retrieved)


def tree_bytes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def rehash_manifest(bundle_dir):
    """The sophisticated attacker: after altering a file, fix the
    manifest's file hashes and bundle hash to match."""
    bundle = Path(bundle_dir)
    manifest = json.loads((bundle / "manifest.json").read_text())
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode()
    manifest["bundle_hash"] = hashlib.sha256(canonical).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


# -- the bundle and its standalone verifier ---------------------------------

def test_bundle_verifies_standalone(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    manifest = export(tmp_path, store, reg, retrieved)
    assert manifest["study"]["checkpoint_root"] == frozen["checkpoint_root"]
    assert manifest["study"]["registration_hash"] == frozen["registration_hash"]
    assert manifest["anchors"] == []
    result = verify_bundle(str(tmp_path / "bundle"))
    assert result.ok, result.failures
    readme = (tmp_path / "bundle" / "HUMAN-README.md").read_text()
    assert "not externally anchored" in readme  # honesty before the anchor exists


def test_export_is_deterministic(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved, "b1")
    export(tmp_path, store, reg, retrieved, "b2")
    assert tree_bytes(tmp_path / "b1") == tree_bytes(tmp_path / "b2")


def test_flipped_byte_fails_verification(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    path = tmp_path / "bundle" / "verdicts.json"
    data = bytearray(path.read_bytes())
    data[40] ^= 0x01
    path.write_bytes(bytes(data))
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok and any("sha256 mismatch" in f for f in result.failures)


def test_unlisted_file_fails_verification(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    (tmp_path / "bundle" / "smuggled.json").write_text("{}")
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok and any("unlisted file" in f for f in result.failures)


def test_altered_manifest_root_fails_even_rehashed(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    manifest_path = tmp_path / "bundle" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["study"]["checkpoint_root"] = "00" * 32
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rehash_manifest(tmp_path / "bundle")  # attacker fixes every hash
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok
    assert any("checkpoint" in f for f in result.failures)


def test_truncated_ledger_fails_even_rehashed(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    ledger = tmp_path / "bundle" / "ledger" / "study.axmr"
    lines = ledger.read_text().splitlines()
    ledger.write_text("\n".join(lines[:-1]) + "\n")
    rehash_manifest(tmp_path / "bundle")
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok


def test_tampered_ledger_payload_fails_production_verification(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    ledger = tmp_path / "bundle" / "ledger" / "study.axmr"
    lines = ledger.read_text().splitlines()
    event = json.loads(lines[1])
    event["actor"] = "mallory"
    lines[1] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    ledger.write_text("\n".join(lines) + "\n")
    rehash_manifest(tmp_path / "bundle")
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok
    assert any("production verification" in f for f in result.failures)


def test_tampered_registration_fails_binding_even_rehashed(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    reg_path = tmp_path / "bundle" / "registration.json"
    doc = json.loads(reg_path.read_text())
    doc["claims"][0]["statement"] = "A quietly weakened claim"
    reg_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    rehash_manifest(tmp_path / "bundle")
    result = verify_bundle(str(tmp_path / "bundle"))
    assert not result.ok
    assert any("registration" in f for f in result.failures)


def test_export_refuses_unfrozen_and_mismatched_registration(tmp_path):
    store = StudyStore.create(str(tmp_path / "u.axmr"))
    reg = ClaimRegister()
    reg.register(claim("CLM-S-001"))
    with pytest.raises(ExportError, match="not frozen"):
        export_bundle(store, str(tmp_path / "u.axmr"), str(tmp_path / "ub"),
                      register=reg, controls=controls(), linked_exploratory=[])

    store2, reg2, frozen2, _ = build_study(tmp_path, "s2")
    # A presented registration that is not the frozen document (here:
    # the captured document itself altered) must be refused.
    reg2.frozen_document["claims"][0]["statement"] = "Edited after freeze"
    with pytest.raises(ExportError, match="does not hash"):
        export_bundle(store2, str(tmp_path / "s2.axmr"), str(tmp_path / "ub2"),
                      register=reg2, controls=controls(), linked_exploratory=[])


# -- coverage + rights gate ----------------------------------------------------

def test_coverage_reports_metadata_only_groups(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    coverage = json.loads((tmp_path / "bundle" / "coverage.json").read_text())
    c1 = coverage["per_claim"]["CLM-S-001"]
    c2 = coverage["per_claim"]["CLM-S-002"]
    assert (c1["groups_content_checked"], c1["groups_metadata_only"]) == (1, 0)
    assert c1["group_coverage"] == 1.0
    assert (c2["groups_content_checked"], c2["groups_metadata_only"]) == (0, 1)
    assert c2["group_coverage"] == 0.0  # shown, not hidden (WS5 §2)
    assert c1["citations_unresolved"] == 1  # the fabricated citation is counted


def test_content_rights_gate_and_substitution_listing(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    unlicensed = RetrievedItem(
        source="crossref", source_id="10.1000/xyz123", title="T", authors=["A"],
        year=2024, venue="V", abstract="An abstract nobody licensed us to redistribute.",
        license_basis="unknown (not asserted by source)")
    retrieved["CIT-9"] = unlicensed
    manifest = export(tmp_path, store, reg, retrieved)
    # CIT-1's abstract is CC-BY: redistributable, content file present.
    content = tmp_path / "bundle" / "evidence" / "content" / "CIT-1.txt"
    assert content.exists() and "improved sleep quality" in content.read_text()
    # CIT-9: stub only, and the substitution is on the manifest.
    assert not (tmp_path / "bundle" / "evidence" / "content" / "CIT-9.txt").exists()
    assert any(s["item"] == "CIT-9" for s in manifest["content_substitutions"])
    assert verify_bundle(str(tmp_path / "bundle")).ok


# -- deposit: gating, metadata, packaging ---------------------------------------

def test_deposit_requires_named_approval(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    transport = LocalTransport(str(tmp_path / "depo"))
    with pytest.raises(DepositError, match="adjudicator-approved"):
        deposit_bundle(str(tmp_path / "bundle"), transport, approved_by="")
    with pytest.raises(DepositError, match="adjudicator-approved"):
        deposit_bundle(str(tmp_path / "bundle"), transport, approved_by="   ")


def test_deposit_refuses_unverifiable_bundle(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    (tmp_path / "bundle" / "claims.json").write_text("{}")
    transport = LocalTransport(str(tmp_path / "depo"))
    with pytest.raises(DepositError, match="does not verify"):
        deposit_bundle(str(tmp_path / "bundle"), transport, approved_by="Adjudicator A")


def test_deposit_metadata_states_root_and_bundle_hash(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    manifest = export(tmp_path, store, reg, retrieved)
    meta = zenodo_metadata(manifest)["metadata"]
    assert manifest["study"]["checkpoint_root"] in meta["description"]
    assert manifest["bundle_hash"] in meta["description"]
    osf = osf_metadata(manifest)
    assert osf["anchor_values"]["checkpoint_root"] == manifest["study"]["checkpoint_root"]
    assert osf["anchor_values"]["bundle_hash"] == manifest["bundle_hash"]


def test_package_is_deterministic(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    export(tmp_path, store, reg, retrieved)
    p1 = package_bundle(str(tmp_path / "bundle"), str(tmp_path / "a.zip"))
    p2 = package_bundle(str(tmp_path / "bundle"), str(tmp_path / "b.zip"))
    assert p1.read_bytes() == p2.read_bytes()


# -- the anchor loop (local transport; the live Zenodo run is the manual smoke)

def anchored_study(tmp_path):
    store, reg, frozen, retrieved = build_study(tmp_path)
    manifest = export(tmp_path, store, reg, retrieved)
    transport = LocalTransport(str(tmp_path / "depo"))
    receipt = deposit_bundle(str(tmp_path / "bundle"), transport,
                             approved_by="Adjudicator A",
                             package_out=str(tmp_path / "bundle.zip"))
    record_anchor(store, receipt, actor="adjudicator")
    store.freeze(actor="adjudicator")
    manifest2 = export_bundle(store, str(tmp_path / "s.axmr"), str(tmp_path / "bundle2"),
                              register=reg, controls=controls(), linked_exploratory=[],
                              retrieved=retrieved)
    record = transport.record(str(receipt["record_id"]))
    return store, receipt, manifest2, record, transport


def test_anchor_loop_end_to_end_local(tmp_path):
    store, receipt, manifest2, record, transport = anchored_study(tmp_path)
    assert receipt["root"] == manifest2["study"]["checkpoints"][0]["merkle_root"]
    assert manifest2["anchors"] and manifest2["anchors"][0]["root"] == receipt["root"]
    assert verify_bundle(str(tmp_path / "bundle2")).ok
    result = verify_anchor(str(tmp_path / "bundle2"), record,
                           package_path=str(tmp_path / "bundle.zip"))
    assert result.ok, result.failures
    readme = (tmp_path / "bundle2" / "HUMAN-README.md").read_text()
    assert "not externally anchored" not in readme
    assert "local-filesystem" in readme  # the receipt's mechanism, named honestly


def test_anchor_verification_rejects_foreign_record(tmp_path):
    store, receipt, manifest2, record, transport = anchored_study(tmp_path)
    # A second study deposited through the same transport: its record
    # states a different root and bundle hash.
    (tmp_path / "other").mkdir()
    store_b, reg_b, frozen_b, retrieved_b = build_study(tmp_path / "other", "sb")
    export_bundle(store_b, str(tmp_path / "other" / "sb.axmr"),
                  str(tmp_path / "other" / "bundleb"), register=reg_b,
                  controls=controls(), linked_exploratory=[], retrieved=retrieved_b)
    receipt_b = deposit_bundle(str(tmp_path / "other" / "bundleb"), transport,
                               approved_by="Adjudicator A",
                               package_out=str(tmp_path / "other" / "bundleb.zip"))
    foreign = transport.record(str(receipt_b["record_id"]))
    result = verify_anchor(str(tmp_path / "bundle2"), foreign,
                           package_path=str(tmp_path / "bundle.zip"))
    assert not result.ok


def test_anchor_verification_rejects_tampered_public_record(tmp_path):
    store, receipt, manifest2, record, transport = anchored_study(tmp_path)
    record["metadata"]["description"] = record["metadata"]["description"].replace(
        receipt["root"], "ff" * 32)
    result = verify_anchor(str(tmp_path / "bundle2"), record)
    assert not result.ok
    assert any("does not state the anchored root" in f for f in result.failures)
