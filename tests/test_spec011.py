"""Spec 011 tests: evaluation-machinery completion — per-control
outcomes in the run projection, falsifier-observation wiring, bundle
citation completeness (as-cited forms + exclusion markers), and
backward compatibility over the frozen bundles.

The end-to-end fixture mirrors the Phase 7 evaluation's decisive
shapes: a claim whose registered falsifier names a real synthesis
(the Wandel 2010 pattern), a fabricated citation caught and excluded,
and fixture controls — built entirely through the production paths,
then read back **from the exported bundle alone**.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem
from tekmerion.connectors import RetrievedItem
from tekmerion.export import export_bundle, verify_bundle
from tekmerion.freeze import freeze
from tekmerion.store import StudyStore
from tekmerion.verdicts import (
    Control,
    evaluate_claim,
    evaluate_run,
    run_controls,
    run_controls_report,
)
from tekmerion.verification import (
    Citation,
    CitationResult,
    decide,
    falsifier_names_record,
    to_evidence_item,
    verify_citations,
)

# ---------------------------------------------------------------- fixtures

WANDEL_FALSIFIER = (
    "A large-scale synthesis finds glucosamine does not reduce joint "
    "pain versus placebo — the registered falsifying observation is "
    "the Wandel 2010 network meta-analysis's conclusion"
)
PROP = "Glucosamine reduces joint pain"


class FakeConnector:
    """Resolves registered DOIs to fixed records; anything else is
    not found (the fabricated DOI's fate)."""

    name = "fake-record"

    def __init__(self, records):
        self.records = records  # doi -> RetrievedItem

    def resolve(self, doi):
        return self.records.get(doi)

    def search(self, title):
        return []


def record(doi, title, authors, year, abstract):
    return RetrievedItem(
        source="fake", source_id=doi, title=title, authors=authors,
        year=year, venue="Journal of Records", abstract=abstract,
        license_basis="https://creativecommons.org/licenses/by/4.0/",
        hosted_ok=True)


WANDEL = record(
    "10.1000/wandel2010",
    "Effects of glucosamine on joint pain: a network meta-analysis",
    ["Simon Wandel", "Peter Jüni"], 2010,
    "Glucosamine does not reduce joint pain in patients with osteoarthritis.")
SUPPORTING = record(
    "10.1000/support2019",
    "A cohort study of auricular stimulation and sleep",
    ["Ada Lovelace"], 2019,
    "Auricular stimulation improved sleep quality significantly in a controlled trial.")


def claim(cid, **kw):
    base = dict(statement="X holds", falsifier="observing not-X in a powered test",
                margin=0.1, sufficiency_floor=1)
    base.update(kw)
    return Claim(claim_id=cid, **base)


def fixture_controls():
    pos = Control(
        failure_mode="retrieval broken: known-true claim not supported",
        kind="positive",
        claim=claim("CLM-A-900"),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False,
                 "verified": True, "items": 1, "metadata_only": False}],
        expected="supported",
        representative_rationale="same domain and difficulty class as the study claims")
    neg = Control(
        failure_mode="verification decorative: fabricated citation accepted",
        kind="negative",
        claim=claim("CLM-A-901"),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True,
                 "verified": True, "items": 1, "metadata_only": False}],
        expected="contradicted")
    swap = Control(
        failure_mode="integrity machinery decorative: provenance swap undetected",
        kind="swap")
    return [pos, neg, swap]


# ------------------------------------------------------- CLM-011-02 parity

def test_run_controls_parity_on_passing_controls(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    store.register_claim("CLM-A-001", claim("CLM-A-001").as_dict(), actor="researcher")
    store.register_claim("CLM-A-002", claim("CLM-A-002").as_dict(), actor="researcher")
    controls = fixture_controls()
    assert run_controls(controls, store_path=str(tmp_path / "s.axmr")) == []
    outcomes = run_controls_report(controls, store_path=str(tmp_path / "s.axmr"))
    assert [o["kind"] for o in outcomes] == ["positive", "negative", "swap"]
    assert all(o["passed"] and o["executed"] for o in outcomes)
    assert outcomes[0]["observed"] == "supported"
    assert outcomes[1]["observed"] == "contradicted"
    assert outcomes[2]["observed"] == "detected"
    # fixture identity: claim id + a stable hash of the fixture itself
    assert outcomes[0]["fixture"]["claim_id"] == "CLM-A-900"
    assert len(outcomes[0]["fixture"]["sha256"]) == 64
    again = run_controls_report(controls, store_path=str(tmp_path / "s.axmr"))
    assert again[0]["fixture"] == outcomes[0]["fixture"]


def test_run_controls_parity_failure_strings():
    missing = Control(failure_mode="no fixture at all", kind="positive")
    mismatch = Control(
        failure_mode="engine too kind", kind="positive",
        claim=claim("CLM-A-902"),
        groups=[{"origin_group": "G1", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True,
                 "verified": True, "items": 1, "metadata_only": False}],
        expected="supported")
    unknown = Control(failure_mode="mystery", kind="sideways")
    controls = [missing, mismatch, unknown]
    # The exact strings the pre-change implementation produced.
    assert run_controls(controls) == [
        "control missing claim/groups/expected: no fixture at all",
        "positive control failed (engine too kind): expected supported, got contradicted",
        "unknown control kind sideways",
    ]
    outcomes = run_controls_report(controls)
    assert [o["detail"] for o in outcomes if not o["passed"]] == run_controls(controls)
    assert [o["executed"] for o in outcomes] == [False, True, False]
    assert outcomes[0]["fixture"] is None


def test_run_controls_parity_swap_failures(tmp_path):
    swap = Control(failure_mode="swap must bite", kind="swap")
    # No ledger path at all.
    assert run_controls([swap]) == ["swap control requires the study ledger path"]
    outcome = run_controls_report([swap])[0]
    assert outcome["passed"] is False and outcome["observed"] == "not_detected"
    # A ledger too short to tamper with.
    short = tmp_path / "short.axmr"
    short.write_text("AXMR1\n", encoding="utf-8")
    failures = run_controls([swap], store_path=str(short))
    assert failures == ["swap control: ledger too short to swap provenance stubs"]


def test_evaluate_run_carries_control_outcomes(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    c = claim("CLM-A-001")
    reg.register(c)
    store.register_claim("CLM-A-001", c.as_dict(), actor="researcher")
    freeze(store, reg, fixture_controls(), actor="researcher", linked_exploratory=[])
    result = evaluate_run(reg, mode="confirmation", controls=fixture_controls(),
                          store_path=str(tmp_path / "s.axmr"))
    assert result.run_verdict == "valid"
    assert [o["kind"] for o in result.control_outcomes] == ["positive", "negative", "swap"]
    assert all(o["passed"] for o in result.control_outcomes)


# ------------------------------------------------- CLM-011-04/-05 falsifier

def _result(**kw):
    base = dict(citation_id="CIT-X", claim_id="CLM-X-001", resolution="resolved",
                agreement="agree", content="contradicts", origin_group="EVG-001",
                retrieved=WANDEL)
    base.update(kw)
    return CitationResult(**base)


def _citation(**kw):
    base = dict(citation_id="CIT-X", claim_id="CLM-X-001", proposition=PROP,
                doi="10.1000/wandel2010",
                title="Effects of glucosamine on joint pain: a network meta-analysis",
                authors=["Simon Wandel"], year=2010)
    base.update(kw)
    return Citation(**base)


def _named_claim(**kw):
    base = dict(statement="Glucosamine reduces joint pain",
                falsifier=WANDEL_FALSIFIER, margin=0.1, sufficiency_floor=1)
    base.update(kw)
    return Claim(claim_id="CLM-X-001", **base)


def test_falsifier_fires_on_surname_and_year():
    item = to_evidence_item(_citation(), _result(), claim=_named_claim())
    assert item.falsifier_observation is True
    assert item.stance == "contradicts" and item.contradiction_mass > 0


def test_falsifier_fires_on_doi_alone():
    claim = _named_claim(
        falsifier="The observation at doi:10.1000/wandel2010 shows no effect")
    other = record("10.1000/wandel2010", "Some Other Title", ["Jane Doe"], 1999,
                   "Glucosamine does not reduce joint pain.")
    item = to_evidence_item(_citation(), _result(retrieved=other), claim=claim)
    assert item.falsifier_observation is True


def test_falsifier_silent_without_the_full_conjunction():
    named = _named_claim()
    # Generic falsifier names no record.
    assert to_evidence_item(_citation(), _result(), claim=claim("CLM-X-001")
                            ).falsifier_observation is False
    # Title-only naming: no surname, no year, no DOI in the falsifier.
    title_only = _named_claim(
        falsifier="The conclusion of 'Effects of glucosamine on joint pain: "
                  "a network meta-analysis' shows no benefit")
    assert to_evidence_item(_citation(), _result(), claim=title_only
                            ).falsifier_observation is False
    # Surname matches, year does not.
    wrong_year = _named_claim(falsifier="The Wandel 2011 conclusion refutes it")
    assert to_evidence_item(_citation(), _result(), claim=wrong_year
                            ).falsifier_observation is False
    # First-author surname does not match the falsifier's named author.
    other_claim = _named_claim(falsifier="The Smith 2010 conclusion refutes it")
    assert to_evidence_item(_citation(), _result(), claim=other_claim
                            ).falsifier_observation is False
    # Supporting content never carries the observation.
    assert to_evidence_item(_citation(), _result(content="supports"),
                            claim=named).falsifier_observation is False
    # Metadata-only: no content was checked.
    assert to_evidence_item(_citation(), _result(content="metadata_only"),
                            claim=named).falsifier_observation is False
    # Quarantined (disagreement): converts unverified, flag unset.
    item = to_evidence_item(_citation(), _result(agreement="disagree"), claim=named)
    assert item.verified is False and item.falsifier_observation is False
    # Unresolved.
    item = to_evidence_item(_citation(), _result(resolution="not_found",
                                                 agreement=None, content=None),
                            claim=named)
    assert item.verified is False and item.falsifier_observation is False
    # No claim supplied: pre-change behavior, flag unset.
    assert to_evidence_item(_citation(), _result()).falsifier_observation is False
    # Resolved record unavailable to the conversion and no DOI naming.
    assert to_evidence_item(_citation(doi=None), _result(retrieved=None),
                            claim=named).falsifier_observation is False
    # The predicate itself, directly.
    assert falsifier_names_record(named, _citation(), _result()) is True
    assert falsifier_names_record(named, _citation(), _result(content="contextual")) is False


def test_falsifier_verdict_path_and_unchanged_math():
    named = _named_claim(sufficiency_floor=2)  # floor 2, one group: the
    # falsifier branch (pre-existing math) fires before the floor test.
    item = to_evidence_item(_citation(), _result(), claim=named)
    reg = ClaimRegister()
    reg.register(named)
    reg.add_evidence("CLM-X-001", item)
    groups = reg.group_masses("CLM-X-001")
    assert groups[0]["falsifier_observation"] is True
    verdict = evaluate_claim(named, groups)
    assert verdict.verdict == "contradicted"
    assert verdict.reason.startswith("falsifier test fired")
    # Identical groups through the pre-existing falsifier branch by hand:
    # the wiring changes flags on items, never the math on groups.
    manual = [{"origin_group": "EVG-001", "support_mass": 0.0,
               "contradiction_mass": 0.8, "could_falsify": True,
               "falsifier_observation": True, "verified": True, "items": 1,
               "metadata_only": False}]
    assert evaluate_claim(named, manual) == verdict
    plain = [dict(manual[0], falsifier_observation=False)]
    interval_verdict = evaluate_claim(named, plain)
    assert interval_verdict.verdict == "inconclusive"  # floor bites instead
    assert interval_verdict.interval == verdict.interval
    assert interval_verdict.point == verdict.point


# ------------------------------------------- end-to-end + bundle-alone audit

def build_audit_study(tmp_path):
    """The Phase 7 shapes in miniature, through production paths:
    a falsifier-naming claim + its contradicting record, a supported
    claim, a fabricated citation excluded at adjudication."""
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    c1 = Claim(claim_id="CLM-A-001", statement="Glucosamine reduces joint pain",
               falsifier=WANDEL_FALSIFIER, margin=0.1, sufficiency_floor=1)
    c2 = Claim(claim_id="CLM-A-002",
               statement="Auricular stimulation improves sleep quality",
               falsifier="observing no improvement in a powered test",
               margin=0.1, sufficiency_floor=1)
    for c, actor in ((c1, "researcher"), (c2, "co-researcher")):
        reg.register(c)
        store.register_claim(c.claim_id, c.as_dict(), actor=actor)

    conn = FakeConnector({"10.1000/wandel2010": WANDEL,
                          "10.1000/support2019": SUPPORTING})
    cits = [
        Citation(citation_id="CIT-A-101", claim_id="CLM-A-001", proposition=PROP,
                 doi="10.1000/wandel2010", title=WANDEL.title,
                 authors=["Simon Wandel"], year=2010, venue="Journal of Records"),
        Citation(citation_id="CIT-A-102", claim_id="CLM-A-001", proposition=PROP,
                 doi="10.1000/fabricated", title="Invented findings on glucosamine",
                 authors=["Fake Author"], year=2024, venue="Nowhere"),
        Citation(citation_id="CIT-A-201", claim_id="CLM-A-002",
                 proposition="Auricular stimulation improves sleep quality",
                 doi="10.1000/support2019", title=SUPPORTING.title,
                 authors=["Ada Lovelace"], year=2019, venue="Journal of Records"),
    ]
    report = verify_citations(store, cits, [conn], actor="researcher")
    by_id = {r.citation_id: r for r in report.results}
    assert by_id["CIT-A-101"].content == "contradicts"
    assert by_id["CIT-A-102"].resolution == "not_found"
    assert by_id["CIT-A-201"].content == "supports"
    for qid in report.queue_item_ids:
        decide(store, qid, "exclude", adjudicator="adjudicator",
               rationale="fabricated DOI — excluded from the evidence basis")

    claims_by_id = {"CLM-A-001": c1, "CLM-A-002": c2}
    for cit in cits:
        if cit.citation_id == "CIT-A-102":
            continue  # excluded: never enters the evidence basis
        reg.add_evidence(cit.claim_id,
                         to_evidence_item(cit, by_id[cit.citation_id],
                                          claim=claims_by_id[cit.claim_id]))
    frozen = freeze(store, reg, fixture_controls(), actor="researcher",
                    linked_exploratory=[])
    result = evaluate_run(reg, mode="confirmation", controls=fixture_controls(),
                          store_path=str(tmp_path / "s.axmr"))
    assert result.run_verdict == "valid", result.invalid_reasons
    for verdict in result.claim_verdicts:
        store.issue_verdict(verdict.claim_id, verdict.as_dict(), actor="verdict-service")
    retrieved = {r.citation_id: r.retrieved for r in report.results if r.retrieved}
    citations = {c.citation_id: c for c in cits}
    return store, reg, frozen, retrieved, citations


def export_audit(tmp_path, store, reg, retrieved, citations, name="bundle"):
    return export_bundle(store, str(tmp_path / "s.axmr"), str(tmp_path / name),
                         register=reg, controls=fixture_controls(),
                         linked_exploratory=[], retrieved=retrieved,
                         citations=citations)


def test_bundle_alone_audit(tmp_path):
    """Read ONLY the exported bundle; reconstruct the control
    outcomes, the falsifier-path verdict, the exclusion, and the
    as-cited forms — the Phase 7 K3 exercise, as a test."""
    store, reg, frozen, retrieved, citations = build_audit_study(tmp_path)
    export_audit(tmp_path, store, reg, retrieved, citations)
    bundle = tmp_path / "bundle"

    verdicts_doc = json.loads((bundle / "verdicts.json").read_text())
    run_outcome = verdicts_doc["run_outcome"]
    assert run_outcome["outcome"] == "valid"
    assert run_outcome["controls_replayed"] == ["positive", "negative", "swap"]
    outcomes = {o["kind"]: o for o in run_outcome["controls"]}
    assert outcomes["positive"]["passed"] is True
    assert outcomes["positive"]["observed"] == "supported"
    assert outcomes["positive"]["fixture"]["claim_id"] == "CLM-A-900"
    assert outcomes["negative"]["passed"] is True
    assert outcomes["negative"]["observed"] == "contradicted"
    assert outcomes["swap"]["passed"] is True
    assert outcomes["swap"]["observed"] == "detected"
    assert outcomes["swap"]["fixture"]["construction"]  # the tamper is named

    verdicts = {v["claim_id"]: v for v in verdicts_doc["verdicts"]}
    assert verdicts["CLM-A-001"]["verdict"] == "contradicted"
    assert verdicts["CLM-A-001"]["reason"].startswith("falsifier test fired")
    assert verdicts["CLM-A-002"]["verdict"] == "supported"

    items = {i["item_id"]: i for i in
             json.loads((bundle / "evidence" / "items.json").read_text())["items"]}
    assert items["CIT-A-101"]["falsifier_observation"] is True
    assert "CIT-A-102" not in items  # excluded: no evidence, but marked below

    adjudication = json.loads((bundle / "adjudication.json").read_text())
    assert adjudication["excluded_citations"] == [{
        "citation_id": "CIT-A-102", "claim_id": "CLM-A-001",
        "queue_id": "ADQ-001", "decision": "exclude",
        "rationale": "fabricated DOI — excluded from the evidence basis",
    }]

    verification = json.loads((bundle / "verification.json").read_text())
    as_cited = verification["as_cited"]
    assert set(as_cited) == {"CIT-A-101", "CIT-A-102", "CIT-A-201"}
    assert as_cited["CIT-A-102"]["doi"] == "10.1000/fabricated"

    readme = (bundle / "HUMAN-README.md").read_text()
    assert "How citation outcomes become evidence" in readme
    assert "metadata_only" in readme and "falsifier_observation" in readme

    result = verify_bundle(str(bundle))
    assert result.ok, result.failures
    assert result.checks["control_outcomes"] == 3
    assert result.checks["as_cited"] == 3
    assert result.checks["excluded_citations"] == 1


def test_bundle_of_invalid_run_records_control_outcomes(tmp_path):
    """A run invalidated by unverified evidence still records its
    controls' outcomes in the projection (the replay's own)."""
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    c = claim("CLM-A-001")
    reg.register(c)
    store.register_claim("CLM-A-001", c.as_dict(), actor="researcher")
    reg.add_evidence("CLM-A-001", EvidenceItem(
        item_id="CIT-U", origin_group="EVG-001", stance="contextual",
        verified=False))
    freeze(store, reg, fixture_controls(), actor="researcher", linked_exploratory=[])
    export_bundle(store, str(tmp_path / "s.axmr"), str(tmp_path / "bundle"),
                  register=reg, controls=fixture_controls(), linked_exploratory=[])
    doc = json.loads((tmp_path / "bundle" / "verdicts.json").read_text())
    assert doc["run_outcome"]["outcome"] == "invalid"
    outcomes = {o["kind"]: o for o in doc["run_outcome"]["controls"]}
    assert outcomes["swap"]["passed"] is True  # controls behaved; the
    # evidence didn't — both facts are on the record now.
    assert verify_bundle(str(tmp_path / "bundle")).ok


# ---------------------------------------------------------------- tampering

def rehash_manifest(bundle_dir):
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
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")


_tamper_counter = [0]


def _tampered_copy(tmp_path, mutate):
    _tamper_counter[0] += 1
    work = tmp_path / f"case{_tamper_counter[0]}"
    work.mkdir()
    store, reg, frozen, retrieved, citations = build_audit_study(work)
    export_audit(work, store, reg, retrieved, citations, name="orig")
    bundle = work / "tampered"
    shutil.copytree(work / "orig", bundle)
    mutate(bundle)
    rehash_manifest(bundle)
    return verify_bundle(str(bundle))


def _edit_json(bundle, rel, fn):
    path = bundle / rel
    doc = json.loads(path.read_text())
    fn(doc)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


def test_tampered_control_outcome_is_detected(tmp_path):
    def flip(bundle):
        def fn(doc):
            for o in doc["run_outcome"]["controls"]:
                if o["kind"] == "positive":
                    o["passed"] = False
        _edit_json(bundle, "verdicts.json", fn)
    result = _tampered_copy(tmp_path, flip)
    assert not result.ok
    assert any("control" in f for f in result.failures)


def test_dropped_control_outcome_is_detected(tmp_path):
    def drop(bundle):
        def fn(doc):
            doc["run_outcome"]["controls"] = [
                o for o in doc["run_outcome"]["controls"] if o["kind"] != "swap"]
        _edit_json(bundle, "verdicts.json", fn)
    result = _tampered_copy(tmp_path, drop)
    assert not result.ok
    assert any("control" in f for f in result.failures)


def test_misstated_swap_outcome_is_detected(tmp_path):
    def misstate(bundle):
        def fn(doc):
            for o in doc["run_outcome"]["controls"]:
                if o["kind"] == "swap":
                    o["observed"] = "not_detected"
                    o["passed"] = False
        _edit_json(bundle, "verdicts.json", fn)
    result = _tampered_copy(tmp_path, misstate)
    assert not result.ok
    assert any("swap" in f for f in result.failures)


def test_tampered_as_cited_is_detected(tmp_path):
    def relink(bundle):
        def fn(doc):
            doc["as_cited"]["CIT-A-101"]["claim_id"] = "CLM-A-002"
        _edit_json(bundle, "verification.json", fn)
    result = _tampered_copy(tmp_path, relink)
    assert not result.ok
    assert any("as_cited" in f for f in result.failures)

    def ghost(bundle):
        def fn(doc):
            doc["as_cited"]["CIT-GHOST"] = dict(doc["as_cited"]["CIT-A-101"],
                                                citation_id="CIT-GHOST")
        _edit_json(bundle, "verification.json", fn)
    result = _tampered_copy(tmp_path, ghost)
    assert not result.ok
    assert any("as_cited" in f for f in result.failures)


def test_tampered_exclusion_markers_are_detected(tmp_path):
    def drop(bundle):
        def fn(doc):
            doc["excluded_citations"] = []
        _edit_json(bundle, "adjudication.json", fn)
    result = _tampered_copy(tmp_path, drop)
    assert not result.ok
    assert any("excluded_citations" in f for f in result.failures)

    def invent(bundle):
        def fn(doc):
            doc["excluded_citations"].append({
                "citation_id": "CIT-A-201", "claim_id": "CLM-A-002",
                "queue_id": "ADQ-999", "decision": "exclude",
                "rationale": "invented"})
        _edit_json(bundle, "adjudication.json", fn)
    result = _tampered_copy(tmp_path, invent)
    assert not result.ok
    assert any("excluded_citations" in f for f in result.failures)


# ------------------------------------------------------- CLM-011-08 compat

REPO = Path(__file__).resolve().parent.parent

PINNED_VERDICTS = {
    "phase7-v1": [("CLM-E-001", "supported"), ("CLM-E-002", "supported"),
                  ("CLM-E-003", "inconclusive"), ("CLM-E-004", "contradicted"),
                  ("CLM-E-005", "inconclusive")],
    "phase7-v2": [("CLM-E-001", "supported"), ("CLM-E-002", "supported"),
                  ("CLM-E-003", "inconclusive"), ("CLM-E-004", "contradicted"),
                  ("CLM-E-005", "inconclusive")],
    "math-v1": [("CLM-M-110", "contested"), ("CLM-M-210", "contested"),
                ("CLM-M-310", "inconclusive"), ("CLM-M-410", "inconclusive"),
                ("CLM-M-510", "inconclusive"), ("CLM-M-110", "contested"),
                ("CLM-M-210", "contested"), ("CLM-M-310", "inconclusive"),
                ("CLM-M-410", "inconclusive"), ("CLM-M-510", "supported")],
    "math-v2": [("CLM-M-110", "contested"), ("CLM-M-210", "contested"),
                ("CLM-M-310", "inconclusive"), ("CLM-M-410", "inconclusive"),
                ("CLM-M-510", "inconclusive"), ("CLM-M-110", "contested"),
                ("CLM-M-210", "contested"), ("CLM-M-310", "inconclusive"),
                ("CLM-M-410", "inconclusive"), ("CLM-M-510", "supported")],
    "demo-v1": [], "demo-v2": [], "demo-v3": [], "demo-v4": [],
}

FROZEN_BUNDLES = {
    "phase7-v1": REPO / "specs/002-mvp-implementation/evaluation/study/bundle-v1",
    "phase7-v2": REPO / "specs/002-mvp-implementation/evaluation/study/bundle-v2",
    "math-v1": Path.home() / "workspace/math-study/bundle-v1",
    "math-v2": Path.home() / "workspace/math-study/bundle-v2",
    "demo-v1": Path.home() / "workspace/phase5-demo/bundle-v1",
    "demo-v2": Path.home() / "workspace/phase5-demo/bundle-v2",
    "demo-v3": Path.home() / "workspace/phase5-demo/bundle-v3",
    "demo-v4": Path.home() / "workspace/phase5-demo/bundle-v4",
}


@pytest.mark.parametrize("name", sorted(FROZEN_BUNDLES))
def test_frozen_bundles_still_verify_with_verdicts_unchanged(name):
    bundle = FROZEN_BUNDLES[name]
    if not bundle.exists():
        pytest.skip(f"frozen bundle set not present on this machine: {bundle}")
    result = verify_bundle(str(bundle))
    assert result.ok, f"{name}: {result.failures}"
    doc = json.loads((bundle / "verdicts.json").read_text())
    entries = doc["verdicts"] if isinstance(doc, dict) else doc
    assert [(v["claim_id"], v["verdict"]) for v in entries] == PINNED_VERDICTS[name]
    # Absences of the new fields are notes in the checks, not failures.
    if isinstance(doc, dict) and doc.get("run_outcome") is not None:
        assert str(result.checks.get("control_outcomes", "")).startswith("absent")


def test_pre_spec011_shape_verifies_after_stripping_new_keys(tmp_path):
    """A new bundle with the Spec 011 keys removed (and the manifest
    rehashed) is the pre-change shape: it must verify, absences noted."""
    store, reg, frozen, retrieved, citations = build_audit_study(tmp_path)
    export_audit(tmp_path, store, reg, retrieved, citations)
    bundle = tmp_path / "bundle"

    _edit_json(bundle, "verdicts.json",
               lambda d: d["run_outcome"].pop("controls", None))
    _edit_json(bundle, "verification.json", lambda d: d.pop("as_cited", None))
    _edit_json(bundle, "adjudication.json",
               lambda d: d.pop("excluded_citations", None))
    rehash_manifest(bundle)
    result = verify_bundle(str(bundle))
    assert result.ok, result.failures
    assert str(result.checks["control_outcomes"]).startswith("absent")
    assert result.checks["as_cited"] == "absent"
    assert str(result.checks["excluded_citations"]).startswith("absent")


def test_workspace_derive_evidence_wires_the_flag(tmp_path):
    """The shared rebuild path (UI + MCP): a contradicting record the
    claim's falsifier names comes back with the observation set."""
    from tekmerion.ui.state import derive_evidence, rebuild_register

    store = StudyStore.create(str(tmp_path / "s.axmr"))
    reg = ClaimRegister()
    c1 = Claim(claim_id="CLM-A-001", statement="Glucosamine reduces joint pain",
               falsifier=WANDEL_FALSIFIER, margin=0.1, sufficiency_floor=1)
    reg.register(c1)
    store.register_claim("CLM-A-001", c1.as_dict(), actor="researcher")
    cit = Citation(citation_id="CIT-A-101", claim_id="CLM-A-001", proposition=PROP,
                   doi="10.1000/wandel2010", title=WANDEL.title,
                   authors=["Simon Wandel"], year=2010, venue="Journal of Records")
    verify_citations(store, [cit], [FakeConnector({"10.1000/wandel2010": WANDEL})],
                     actor="researcher")
    rebuilt, _info = rebuild_register(store)
    retrieved = {"CIT-A-101": WANDEL.as_dict()}
    derive_evidence(store, rebuilt, retrieved)
    item = rebuilt.evidence["CLM-A-001"][0]
    assert item.falsifier_observation is True
    verdict = evaluate_claim(rebuilt.claims["CLM-A-001"],
                             rebuilt.group_masses("CLM-A-001"))
    assert verdict.verdict == "contradicted"
    assert verdict.reason.startswith("falsifier test fired")
