"""Phase 4 tests: citation pipeline stages 1–3, origin grouping,
adjudication queue, RT-4 sampling, RT-5 cap — seeded defects through
the production paths (a fabricated DOI, tampered metadata, content
that does not support, a metadata-only basis)."""

import io
import urllib.error

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem
from tekmerion.connectors import CrossrefConnector, HttpJson
from tekmerion.store import StudyStore
from tekmerion.verdicts import evaluate_claim, evaluate_run
from tekmerion.verification import (
    Citation,
    KeywordStanceChecker,
    assign_origin_groups,
    check_agreement,
    decide,
    pending_second_reviews,
    queue_state,
    sample_for_second_review,
    second_review_report,
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

CONTRA_WORK = {
    "DOI": "10.1000/contra1",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "Auricular stimulation did not improve sleep quality in this trial.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

META_WORK = {  # resolves and agrees, but no content anyone may check
    "DOI": "10.1000/metaonly",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


class RoutingHttp(HttpJson):
    """Routes by DOI substring, like the live API's shape: unknown DOIs
    raise the HTTPError the real transport raises for a 404
    (CrossrefConnector.resolve classifies that as a None)."""

    def get(self, url, headers=None):
        if "query.bibliographic" in url:
            return {"message": {"items": [REAL_WORK]}}
        for marker, work in (("xyz123", REAL_WORK), ("contra1", CONTRA_WORK),
                             ("metaonly", META_WORK)):
            if marker in url:
                return {"message": work}
        raise urllib.error.HTTPError(url, 404, "Not Found",
                                     hdrs=None, fp=io.BytesIO(b"{}"))


class ExplodingConnector:
    name = "exploding"

    def resolve(self, doi):
        raise ConnectionError("transport down")

    def search(self, query, limit=10):
        raise ConnectionError("transport down")


def crossref():
    return CrossrefConnector(http=RoutingHttp())


def good_citation(cid="CIT-1", **kw):
    base = dict(citation_id=cid, claim_id="CLM-S-001", proposition=PROP,
                doi="10.1000/xyz123", title="Auricular Stimulation and Sleep Quality",
                authors=["Ada Lovelace"], year=2024, venue="Journal of X")
    base.update(kw)
    return Citation(**base)


def store(tmp_path):
    return StudyStore.create(str(tmp_path / "s.axmr"))


# -- stage 1+2+3: the happy path and its three seeded defects ----------------

def test_pipeline_happy_path_content_verified(tmp_path):
    s = store(tmp_path)
    report = verify_citations(s, [good_citation()], [crossref()], actor="researcher")
    r = report.results[0]
    assert (r.resolution, r.agreement, r.content) == ("resolved", "agree", "supports")
    assert r.extractor == "tekmerion.keyword-stance/1"
    assert report.queue_item_ids == []
    checked = [e for e in s.events() if e["type"] == "citation.checked"]
    assert len(checked) == 1 and s.verify().ok


def test_fabricated_doi_fails_stage_1(tmp_path):
    s = store(tmp_path)
    fab = good_citation("CIT-FAB", doi="10.1000/doesnotexist")
    report = verify_citations(s, [fab], [crossref()], actor="researcher")
    r = report.results[0]
    assert r.resolution == "not_found" and r.quarantined
    assert len(report.queue_item_ids) == 1  # quarantine: a human decides


def test_tampered_metadata_fails_stage_2(tmp_path):
    s = store(tmp_path)
    tampered = good_citation("CIT-TAM", year=1999, authors=["Eve Fabricator"])
    report = verify_citations(s, [tampered], [crossref()], actor="researcher")
    r = report.results[0]
    assert r.resolution == "resolved" and r.agreement == "disagree"
    assert set(r.mismatches) == {"year", "authors"} and r.quarantined
    # Quarantined evidence is unverified: a run containing it is INVALID.
    reg = ClaimRegister()
    reg.register(Claim(claim_id="CLM-S-001", statement="X", falsifier="not-X",
                       margin=0.1, sufficiency_floor=1))
    reg.add_evidence("CLM-S-001", to_evidence_item(tampered, r))
    assert evaluate_run(reg, mode="exploratory", controls=[]).run_verdict == "invalid"


def test_unsupported_content_fails_stage_3(tmp_path):
    s = store(tmp_path)
    cit = good_citation("CIT-CON", doi="10.1000/contra1")
    report = verify_citations(s, [cit], [crossref()], actor="researcher")
    r = report.results[0]
    assert (r.resolution, r.agreement, r.content) == ("resolved", "agree", "contradicts")
    item = to_evidence_item(cit, r)
    assert item.stance == "contradicts" and item.contradiction_mass > 0 and item.verified
    reg = ClaimRegister()
    reg.register(Claim(claim_id="CLM-S-001", statement="X", falsifier="not-X",
                       margin=0.1, sufficiency_floor=1))
    reg.add_evidence("CLM-S-001", item)
    v = evaluate_claim(reg.claims["CLM-S-001"], reg.group_masses("CLM-S-001"))
    assert v.verdict == "contradicted"


def test_no_doi_resolves_by_metadata_match(tmp_path):
    s = store(tmp_path)
    cit = good_citation("CIT-ND", doi=None)
    report = verify_citations(s, [cit], [crossref()], actor="researcher")
    assert report.results[0].resolution == "resolved"
    assert report.results[0].agreement == "agree"


def test_k1_accounting_every_citation_gets_an_outcome(tmp_path):
    s = store(tmp_path)
    batch = [
        good_citation("CIT-OK"),
        good_citation("CIT-FAB", doi="10.1000/doesnotexist"),
        good_citation("CIT-META", doi="10.1000/metaonly"),
    ]
    report = verify_citations(s, batch, [crossref()], actor="researcher")
    accounting = report.accounting()
    assert set(accounting) == {"CIT-OK", "CIT-FAB", "CIT-META"}
    assert accounting["CIT-OK"] == "resolved" and accounting["CIT-FAB"] == "not_found"
    assert len([e for e in s.events() if e["type"] == "citation.checked"]) == 3


def test_transport_error_is_an_explicit_outcome(tmp_path):
    s = store(tmp_path)
    report = verify_citations(s, [good_citation("CIT-E")], [ExplodingConnector()], actor="r")
    assert report.results[0].resolution == "error"
    assert "transport down" in report.results[0].detail


# -- stance checker -------------------------------------------------------------

def test_keyword_stance_checker_distinguishes():
    chk = KeywordStanceChecker()
    assert chk.check(PROP, "Auricular stimulation improved sleep quality significantly.") == "supports"
    assert chk.check(PROP, "Auricular stimulation did not improve sleep quality.") == "contradicts"
    assert chk.check(PROP, "We review clinic intake procedures for new patients.") == "contextual"


def test_agreement_ignores_absent_fields():
    item = crossref().resolve("10.1000/xyz123")
    cit = good_citation(year=None, venue=None, authors=[])
    assert check_agreement(cit, item) == ("agree", [])


# -- origin grouping --------------------------------------------------------------

def test_grouping_precedence_keys(tmp_path):
    s = store(tmp_path)
    a = good_citation("CIT-A")
    b = good_citation("CIT-B")  # same DOI as A -> key 1
    c = good_citation("CIT-C", doi="10.1000/metaonly", dataset_id="OSF-REG-1")
    d = good_citation("CIT-D", doi="10.1000/contra1", dataset_id="OSF-REG-1")  # key 2 with C
    e = good_citation("CIT-E", doi=None, title="A Summary of the Stimulation Trial",
                      authors=["Bob Reporter"], year=2025, venue="News",
                      derived_from="CIT-A")  # key 3 -> A's group
    report = verify_citations(s, [a, b, c, d, e], [crossref()], actor="r")
    g = report.origin_groups
    assert g["CIT-A"] == g["CIT-B"] == g["CIT-E"]
    assert g["CIT-C"] == g["CIT-D"] and g["CIT-C"] != g["CIT-A"]


def test_key4_suspects_flagged_not_merged(tmp_path):
    s = store(tmp_path)
    a = good_citation("CIT-A")
    twin = good_citation("CIT-TWIN", doi="10.1000/metaonly")  # same title+author, other DOI
    report = verify_citations(s, [a, twin], [crossref()], actor="r")
    assert report.origin_groups["CIT-A"] != report.origin_groups["CIT-TWIN"]
    kinds = [i["kind"] for i in queue_state(s)["pending"]]
    assert kinds == ["grouping"]  # flagged for a human, never auto-merged


# -- adjudication queue + RT-4 ------------------------------------------------------

def _decided_store(tmp_path, n=20):
    s = store(tmp_path)
    for i in range(n):
        s.enqueue_adjudication({"queue_id": f"ADQ-{i+1:03d}", "kind": "grouping",
                                "citation_ids": ["X", "Y"], "reason": "key 4"},
                               actor="researcher")
        decide(s, f"ADQ-{i+1:03d}", "separate_origin", adjudicator="adjudicator")
    return s


def test_queue_is_ledger_backed_and_decisions_are_appends(tmp_path):
    s = store(tmp_path)
    fab = good_citation("CIT-FAB", doi="10.1000/doesnotexist")
    verify_citations(s, [fab], [crossref()], actor="researcher")
    state = queue_state(s)
    assert len(state["pending"]) == 1 and state["pending"][0]["kind"] == "quarantine"
    qid = state["pending"][0]["queue_id"]
    decide(s, qid, "exclude", adjudicator="adjudicator", rationale="fabricated DOI")
    state = queue_state(s)
    assert state["pending"] == [] and state["decided"][0]["decision"] == "exclude"
    assert state["decided"][0]["decided_by"] == "adjudicator"
    with pytest.raises(ValueError, match="already decided"):
        decide(s, qid, "variant", adjudicator="adjudicator")
    with pytest.raises(ValueError, match="unknown adjudication decision"):
        decide(s, qid, "shrug", adjudicator="adjudicator")
    assert s.verify().ok


def test_sampling_is_deterministic_and_actually_samples():
    ids = [f"ADQ-{i:03d}" for i in range(1, 21)]
    first = sample_for_second_review(ids, fraction=0.10, seed=42)
    second = sample_for_second_review(ids, fraction=0.10, seed=42)
    assert first == second and len(first) == 2  # ceil(10% of 20), reproducible draw
    assert set(first) <= set(ids)


def test_second_review_flow_and_anomaly(tmp_path):
    s = _decided_store(tmp_path)
    drawn = pending_second_reviews(s, fraction=0.10, seed=7)
    assert len(drawn) == 2
    for qid in drawn:
        s.log_second_review(qid, reviewer="reviewer-2", agrees=True)
    assert pending_second_reviews(s, fraction=0.10, seed=7) == []
    # 2 reviews is below the anomaly window: silence is not yet evidence.
    assert second_review_report(s)["anomaly"] is False
    # Grow the window past the minimum with zero disagreements -> flagged.
    for qid in [f"ADQ-{i:03d}" for i in range(1, 7)]:
        if qid not in drawn:
            s.log_second_review(qid, reviewer="reviewer-2", agrees=True)
    report = second_review_report(s)
    assert report["second_reviews"] >= 5 and report["disagreements"] == 0
    assert report["anomaly"] is True and "RT-4" in report["anomaly_reason"]


def test_disagreement_in_window_clears_the_anomaly(tmp_path):
    s = _decided_store(tmp_path, n=6)
    for i in range(1, 7):
        s.log_second_review(f"ADQ-{i:03d}", reviewer="reviewer-2", agrees=(i != 3))
    report = second_review_report(s)
    assert report["disagreements"] == 1 and report["anomaly"] is False
    assert report["disagreement_rate"] == pytest.approx(1 / 6)


# -- RT-5: the metadata-only cap ------------------------------------------------------

def test_metadata_only_pipeline_result_marks_the_item(tmp_path):
    s = store(tmp_path)
    cit = good_citation("CIT-META", doi="10.1000/metaonly")
    report = verify_citations(s, [cit], [crossref()], actor="r")
    r = report.results[0]
    assert r.content == "metadata_only" and not r.quarantined
    item = to_evidence_item(cit, r)
    assert item.metadata_only and item.support_mass == 0.0


def test_rt5_cap_binds_in_the_verdict_path():
    reg = ClaimRegister()
    reg.register(Claim(claim_id="CLM-S-001", statement="X", falsifier="not-X",
                       margin=0.1, sufficiency_floor=1))
    # Registered with a huge mass and falsifier exposure — metadata-only
    # folding must strip both (RT-5 mechanized, not guidance).
    reg.add_evidence("CLM-S-001", EvidenceItem(item_id="m1", origin_group="EVG-1",
                                              stance="supports", support_mass=0.95,
                                              could_falsify=True, metadata_only=True))
    groups = reg.group_masses("CLM-S-001")
    assert groups[0]["support_mass"] == 0.0 and groups[0]["metadata_only"] is True
    v = evaluate_claim(reg.claims["CLM-S-001"], groups)
    assert v.verdict == "inconclusive" and "RT-5" in v.reason


def test_rt5_cap_does_not_bind_a_mixed_basis():
    reg = ClaimRegister()
    reg.register(Claim(claim_id="CLM-S-001", statement="X", falsifier="not-X",
                       margin=0.1, sufficiency_floor=2))
    reg.add_evidence("CLM-S-001", EvidenceItem(item_id="m1", origin_group="EVG-1",
                                              stance="supports", support_mass=0.95,
                                              metadata_only=True))
    for gid in ("EVG-2", "EVG-3"):
        reg.add_evidence("CLM-S-001", EvidenceItem(item_id=gid, origin_group=gid,
                                                  stance="supports", support_mass=0.9,
                                                  could_falsify=True))
    v = evaluate_claim(reg.claims["CLM-S-001"], reg.group_masses("CLM-S-001"))
    assert v.verdict == "supported"  # content-checked groups carry the claim


def test_assign_origin_groups_direct():
    cits = [good_citation("CIT-A"), good_citation("CIT-B")]
    from tekmerion.verification import CitationResult
    results = [CitationResult(citation_id=c.citation_id, claim_id=c.claim_id,
                              resolution="resolved") for c in cits]
    groups, suspects = assign_origin_groups(cits, results)
    assert groups["CIT-A"] == groups["CIT-B"] and suspects == []
