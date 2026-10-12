"""Spec 003 math-layer tests: the stage model as seeded defects.

Each test names the failure it exists to catch: a sorry in the bytes
must fail proof verification from the artifact itself; a scope mismatch
between the pinned formal statement and the original problem must be
adjudicable; a contested attribution must hold the parent contested;
a verified-but-unexplained claim must raise the digestion risk flag.
Compile tests use the real local toolchain where one exists and skip
where it does not (CI has none — the claimed/not-runnable states are
the honest record there, and they are tested as states)."""

import hashlib

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem
from tekmerion.freeze import freeze
from tekmerion.mathclaims import (
    ATTRIBUTION,
    CLAIMED_BY_SOURCE,
    FAITHFUL,
    NOT_RUNNABLE,
    PROOF,
    RUN_BY_US,
    UNEXPLAINED,
    LeanRunner,
    attribution_state,
    compose_parent,
    digestion_state,
    faithfulness_pair,
    ingest_lean_artifact,
    IngestionError,
    lane2_state,
    pin_faithfulness,
    proof_evidence,
    record_acceptance,
    record_digestion,
    record_reliability,
    register_dispute,
    register_theorem,
    reliability_record,
    subclaim_id,
    theorem_report,
)
from tekmerion.store import StudyStore
from tekmerion.verdicts import Control, evaluate_claim, evaluate_run

CLEAN = "theorem t_one_eq_one : 1 = 1 := rfl\n"
WITH_SORRY = "theorem big_result : 1 = 2 := sorry\n"
MATHLIB_DEP = "import Mathlib\ntheorem x_from_mathlib : True := trivial\n"

RUNNER = LeanRunner()
needs_lean = pytest.mark.skipif(not RUNNER.available(),
                                reason="no local Lean toolchain in this environment")


def _store(tmp_path):
    return StudyStore.create(str(tmp_path / "study.axmr"))


def _fetch_map(mapping):
    def fetch(url):
        if url not in mapping:
            raise OSError(f"no such artifact: {url}")
        return mapping[url]
    return fetch


def _register():
    reg = ClaimRegister()
    register_theorem(reg, parent_id="CLM-T-110", headline="X solved Y",
                     claimant="Claimant", problem="Problem Y")
    return reg


def _controls():
    pos = Control(
        failure_mode="verification broken: known-true claim not supported",
        kind="positive",
        claim=Claim(claim_id="CLM-T-900", statement="control: true claim",
                    falsifier="observing it false", margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported",
        representative_rationale="known-answer control")
    neg = Control(
        failure_mode="verification decorative: false claim supported",
        kind="negative",
        claim=Claim(claim_id="CLM-T-901", statement="control: false claim",
                    falsifier="observing it true", margin=0.1, sufficiency_floor=1),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    return [pos, neg, swap]


# ------------------------------------------------------------- registration

def test_theorem_registration_shape():
    reg = _register()
    assert len(reg.claims) == 6
    parent = reg.claims["CLM-T-110"]
    assert sorted(parent.dependencies) == sorted(
        subclaim_id("CLM-T-110", r) for r in
        ("faithful", "proof_verified", "genuinely_open", "attribution", "significance"))
    assert reg.find_cycle() is None
    for claim in reg.claims.values():
        assert claim.falsifier.strip()


# ---------------------------------------------------------------- ingestion

def test_ingestion_records_claimed_compile(tmp_path):
    store = _store(tmp_path)
    url = "https://example.org/artifact.lean"
    ing = ingest_lean_artifact(
        store, url=url, actor="archivist",
        fetcher=_fetch_map({url: WITH_SORRY.encode()}),
        source_compile_claim={"claimed_by": "claimant CI", "ref": "https://example.org/ci"})
    assert ing.sha256 == hashlib.sha256(WITH_SORRY.encode()).hexdigest()
    assert ing.sorry_count == 1
    assert ing.compile_status == CLAIMED_BY_SOURCE
    assert ing.declarations[0]["name"] == "big_result"
    assert any(e["type"] == "math.lean_ingested" for e in store.events())


def test_ingestion_fetch_failure_is_a_gap_not_a_fact(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(IngestionError):
        ingest_lean_artifact(store, url="https://example.org/gone.lean",
                             actor="archivist", fetcher=_fetch_map({}))


def test_sorry_in_bytes_is_the_falsifying_observation(tmp_path):
    store = _store(tmp_path)
    url = "https://example.org/artifact.lean"
    ing = ingest_lean_artifact(store, url=url, actor="archivist",
                               fetcher=_fetch_map({url: WITH_SORRY.encode()}))
    item = proof_evidence(ing, item_id="EV-P", origin_group="artifact")
    assert item.falsifier_observation and item.contradiction_mass >= 0.9
    reg = _register()
    reg.add_evidence(subclaim_id("CLM-T-110", PROOF), item)
    verdict = evaluate_claim(reg.claims[subclaim_id("CLM-T-110", PROOF)],
                             reg.group_masses(subclaim_id("CLM-T-110", PROOF)))
    assert verdict.verdict == "contradicted"


@needs_lean
def test_compile_run_by_us_clean_and_axiom_free(tmp_path):
    store = _store(tmp_path)
    url = "https://example.org/clean.lean"
    ing = ingest_lean_artifact(store, url=url, actor="archivist",
                               fetcher=_fetch_map({url: CLEAN.encode()}),
                               runner=RUNNER)
    assert ing.compile_status == RUN_BY_US
    assert ing.compile_detail["passed"] is True
    assert ing.compile_detail["toolchain"].startswith("Lean (version 4.")
    assert ing.compile_detail["axioms"]["axioms"] == []
    item = proof_evidence(ing, item_id="EV-P", origin_group="artifact")
    assert item.stance == "supports" and item.could_falsify


@needs_lean
def test_sorry_axiom_caught_by_probe_even_when_compile_passes(tmp_path):
    store = _store(tmp_path)
    url = "https://example.org/sorry.lean"
    ing = ingest_lean_artifact(store, url=url, actor="archivist",
                               fetcher=_fetch_map({url: WITH_SORRY.encode()}),
                               runner=RUNNER)
    # Lean accepts a sorry with a warning: the compile "passes", and the
    # axioms probe is what convicts it.
    assert ing.compile_detail["passed"] is True
    assert any("sorryAx" in a for a in ing.compile_detail["axioms"]["axioms"])
    assert proof_evidence(ing, item_id="EV-P", origin_group="g").falsifier_observation


@needs_lean
def test_mathlib_dependency_is_not_runnable_not_a_proof_failure(tmp_path):
    store = _store(tmp_path)
    url = "https://example.org/mathlib.lean"
    ing = ingest_lean_artifact(store, url=url, actor="archivist",
                               fetcher=_fetch_map({url: MATHLIB_DEP.encode()}),
                               runner=RUNNER)
    assert ing.compile_status == NOT_RUNNABLE
    item = proof_evidence(ing, item_id="EV-P", origin_group="artifact")
    assert not item.falsifier_observation  # environment gap, not a refutation


# -------------------------------------------------------------- faithfulness

def test_faithfulness_pair_pinned_and_mismatch_contradicts(tmp_path):
    store = _store(tmp_path)
    reg = _register()
    faithful_id = subclaim_id("CLM-T-110", FAITHFUL)
    pin_faithfulness(
        store, claim_id=faithful_id,
        formal_statement="for periodic boundary conditions and a given smooth forcing, a smooth solution exists",
        original_statement="does a smooth solution exist for arbitrary initial data on R^3, unforced?",
        original_source="https://example.org/problem-statement",
        actor="registrar")
    pair = faithfulness_pair(store, faithful_id)
    assert "periodic" in pair["formal_statement"]
    assert "arbitrary initial data" in pair["original_statement"]
    # The adjudicator judges from the pinned pair: scope is narrower.
    reg.add_evidence(faithful_id, EvidenceItem(
        item_id="EV-F", origin_group="adjudication", stance="contradicts",
        contradiction_mass=0.9, could_falsify=True, falsifier_observation=True))
    verdict = evaluate_claim(reg.claims[faithful_id], reg.group_masses(faithful_id))
    assert verdict.verdict == "contradicted"


# --------------------------------------------------------------- attribution

def test_dispute_refuses_one_sided_evidence(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        register_dispute(
            store, claim_id=subclaim_id("CLM-T-110", ATTRIBUTION),
            parties=["A", "B"], positions={"A": "ours", "B": "theirs"},
            evidence={"A": [{"url": "https://example.org/a", "retrieved": "2026-10-12"}]},
            actor="registrar")


def test_contested_attribution_caps_parent(tmp_path):
    store = _store(tmp_path)
    attr_id = subclaim_id("CLM-T-110", ATTRIBUTION)
    two_sided = {p: [{"url": f"https://example.org/{p}", "retrieved": "2026-10-12"}]
                 for p in ("A", "B")}
    register_dispute(store, claim_id=attr_id, parties=["A", "B"],
                     positions={"A": "priority ours", "B": "priority theirs"},
                     evidence=two_sided, actor="registrar")
    assert attribution_state(store, attr_id) == "contested"
    subs = {r: {"verdict": "supported", "reason": "ok"} for r in
            ("faithful", "proof_verified", "genuinely_open", "attribution", "significance")}
    tv = compose_parent("CLM-T-110", subs, attribution_contested=True,
                        remains_not_understood="the method's generality",
                        digestion={"state": UNEXPLAINED, "risk_flag": True},
                        lane1_verification="checked", lane2_acceptance="unexplained")
    assert tv.verdict == "contested"
    tv2 = compose_parent("CLM-T-110", subs, attribution_contested=False,
                         remains_not_understood="the method's generality",
                         digestion={"state": UNEXPLAINED, "risk_flag": True},
                         lane1_verification="checked", lane2_acceptance="unexplained")
    assert tv2.verdict == "supported"


def test_composition_precedence_and_refusals():
    subs = {r: {"verdict": "supported", "reason": ""} for r in
            ("faithful", "proof_verified", "genuinely_open", "attribution", "significance")}
    subs["faithful"] = {"verdict": "contradicted", "reason": "scope"}
    tv = compose_parent("CLM-T-110", subs, attribution_contested=False,
                        remains_not_understood="x",
                        digestion={"state": UNEXPLAINED, "risk_flag": True},
                        lane1_verification="checked", lane2_acceptance="unexplained")
    assert tv.verdict == "contradicted" and "faithful" in tv.reason
    subs["faithful"] = {"verdict": "inconclusive", "reason": "gap"}
    tv = compose_parent("CLM-T-110", subs, attribution_contested=False,
                        remains_not_understood="x",
                        digestion={"state": UNEXPLAINED, "risk_flag": True},
                        lane1_verification="checked", lane2_acceptance="unexplained")
    assert tv.verdict == "inconclusive" and "faithful" in tv.reason
    with pytest.raises(ValueError):
        compose_parent("CLM-T-110", subs, attribution_contested=False,
                       remains_not_understood="  ",
                       digestion={"state": UNEXPLAINED, "risk_flag": True},
                       lane1_verification="checked", lane2_acceptance="unexplained")


# ------------------------------------------------------ digestion + the lanes

def test_unexplained_is_a_flagged_state_and_lane2_needs_humans(tmp_path):
    store = _store(tmp_path)
    parent = "CLM-T-110"
    assert digestion_state(store, parent)["state"] == UNEXPLAINED
    assert digestion_state(store, parent)["risk_flag"] is True
    assert lane2_state(store, parent) == "unexplained"
    # Lane-1 activity does not move lane 2.
    ingest_lean_artifact(store, url="https://example.org/c.lean", actor="archivist",
                         fetcher=_fetch_map({"https://example.org/c.lean": CLEAN.encode()}))
    assert lane2_state(store, parent) == "unexplained"
    record_digestion(store, claim_id=parent, explainer="A. Human",
                     artifact_ref="https://example.org/explainer", actor="adjudicator")
    assert digestion_state(store, parent)["state"] == "explained"
    assert lane2_state(store, parent) == "explained"
    record_acceptance(store, claim_id=parent, stage="accepted", by="A. Human",
                      evidence_ref="https://example.org/explainer", actor="adjudicator")
    assert lane2_state(store, parent) == "accepted"


# --------------------------------------------------------------- reliability

def test_reliability_seed_and_refusal(tmp_path):
    store = _store(tmp_path)
    record_reliability(store, source_id="src-1",
                       asserted_claim="Source 1 asserted theorem T in Oct 2025",
                       outcome="resolved_false",
                       resolution_ref="https://example.org/retraction-notice",
                       actor="archivist")
    rec = reliability_record(store, "src-1")
    assert rec["src-1"]["events"][0]["outcome"] == "resolved_false"
    with pytest.raises(ValueError):
        record_reliability(store, source_id="src-2", asserted_claim="",
                           outcome="resolved_false", resolution_ref="",
                           actor="archivist")


# ------------------------------------------------------------ the full study

def _keys_deep(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k))
            _keys_deep(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _keys_deep(v, acc)
    return acc


def test_full_theorem_run_and_report(tmp_path):
    store = _store(tmp_path)
    reg = _register()
    parent = "CLM-T-110"
    # Multi-actor from the first lines: the swap control must be able to bite.
    store.register_claim(parent, reg.claims[parent].as_dict(), actor="registrar")
    store.db.append("math.study_opened", {"study": "fixture"}, actor="archivist")
    for role in ("faithful", "proof_verified", "genuinely_open", "attribution", "significance"):
        reg.add_evidence(subclaim_id(parent, role), EvidenceItem(
            item_id=f"EV-{role}", origin_group=f"g-{role}", stance="supports",
            support_mass=0.9, could_falsify=True))
    frozen = freeze(store, reg, _controls(), actor="registrar", linked_exploratory=[])
    assert frozen["checkpoint_root"]
    result = evaluate_run(reg, mode="confirmation", controls=_controls(),
                          store_path=str(tmp_path / "study.axmr"))
    assert result.run_verdict == "valid", result.invalid_reasons
    records = theorem_report(store, result, [parent],
                             remains_not_understood={parent: "why the method works"})
    (rec,) = records
    assert rec["verdict"] == "supported"
    assert rec["lane2_acceptance"] == "unexplained"
    assert rec["digestion"]["risk_flag"] is True
    assert rec["remains_not_understood"] == "why the method works"
    keys = _keys_deep(rec, set())
    assert not any("solved" in k for k in keys)  # CLM-003-10: no tallies


# ------------------------------------------------------------- openness (audit NC fix)

def test_openness_check_emits_evidence_not_a_verdict(tmp_path):
    """Audit NC (2026-10-12): openness_check shipped untested. Fixture:
    a stub status source + stub connector; the check must ledger an
    evidence record (math.openness_checked + connector.query), hash the
    page, surface status words, and issue NO verdict of its own."""
    from tekmerion.connectors import RetrievedItem
    from tekmerion.mathclaims import openness_check

    class StubConnector:
        name = "stub"
        def search(self, query, limit=10):
            return [RetrievedItem(source="stub", source_id="10.0000/stub.1",
                                  title="A prior solution in the literature",
                                  authors=["A. Prior"], year=1998, venue="Stub J.",
                                  abstract=None, license_basis="cc0", hosted_ok=True)]

    store = _store(tmp_path)
    page = "Erdos problem 9999 — Status: open. No solution is known."
    rec = openness_check(
        store, problem="Erdos problem 9999",
        status_url="https://status.example/9999", actor="researcher",
        connectors=(StubConnector(),), queries=("erdos 9999 solution",),
        status_fetcher=lambda url: (200, page), retrieved="2026-10-12")
    assert rec["http_status"] == 200
    assert rec["page_sha256"] == hashlib.sha256(page.encode()).hexdigest()
    assert "open" in rec["status_words_present"]
    assert rec["searches"][0]["results"] == 1
    types = [e["type"] for e in store.db.events()]
    assert "math.openness_checked" in types
    assert "connector.query" in types
    assert not any(t.startswith("verdict") for t in types)
    assert store.verify().ok
