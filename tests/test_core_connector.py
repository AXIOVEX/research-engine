"""Spec 012 — CORE connector (CLM-012-01…08).

Recorded-fixture tests: the payload shapes are field-faithful to the
live v3 probe of 2026-10-12 (sanitized; no live call, no key). Each
test names the contract rule it pins.
"""

from __future__ import annotations

import io
import urllib.error

import pytest

from tekmerion.connectors import (
    BudgetExhausted,
    CoreApiError,
    CoreConnector,
    CreditBudget,
    HttpJson,
    RetrievedItem,
)
from tekmerion.verification import (
    AGREE,
    ERROR,
    METADATA_ONLY,
    NOT_FOUND,
    RESOLVED,
    SUPPORTS,
    Citation,

    assign_origin_groups,
    verify_citations,
)

DOI = "10.1016/j.jpsychires.2016.02.023"
OUT1 = "https://api.core.ac.uk/v3/outputs/111"
OUT2 = "https://api.core.ac.uk/v3/outputs/222"
OUT3 = "https://api.core.ac.uk/v3/outputs/333"
NC_LICENCE = "http://creativecommons.org/licenses/by-nc-nd/4.0/"
CC_LICENCE = "https://creativecommons.org/licenses/by/4.0/"

# A work as v3 serves it (probe-shaped): metadata + an abstract, NO
# licence field, outputs listed as URLs.
WORK = {
    "id": 25706038,
    "doi": DOI,
    "title": "Exercise as a treatment for depression: a meta-analysis "
             "adjusting for publication bias",
    "authors": [{"name": "Schuch, Felipe Barreto"}, {"name": "Vancampfort, Davy"}],
    "yearPublished": 2016,
    "journals": [],
    "publisher": "Elsevier BV",
    "abstract": "Work-level abstract text that no licence covers.",
    "outputs": [OUT1, OUT2, OUT3],
}

OUTPUT_NO_LICENCE = {
    "id": 111, "doi": DOI,
    "title": WORK["title"],
    "authors": [{"name": "Schuch, Felipe Barreto"}],
    "yearPublished": "2016", "journals": [], "publisher": None,
    "abstract": "A deposit abstract with no licence asserted.",
    "fullText": "Full text behind no asserted licence.",
}

OUTPUT_NC = {
    "id": 222, "doi": DOI,
    "title": WORK["title"],
    "authors": [{"name": "Schuch, Felipe Barreto"}],
    "yearPublished": "2016", "journals": [], "publisher": None,
    "license": NC_LICENCE,
    "abstract": "Exercise is an effective treatment reducing depressive "
                "symptoms in adults with depression.",
    "fullText": "",
}

OUTPUT_FULLTEXT_ONLY = {
    "id": 333, "doi": DOI,
    "title": WORK["title"],
    "authors": [{"name": "Schuch, Felipe Barreto"}],
    "yearPublished": "2016", "journals": [], "publisher": None,
    "license": CC_LICENCE,
    "abstract": "",
    "fullText": "Exercise reduces symptoms of depression. The full text "
                "body is the only content this deposit carries.",
}


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.core.ac.uk/v3", code, f"HTTP {code}", hdrs=None,
        fp=io.BytesIO(b"{}"))


class CoreFakeHttp(HttpJson):
    """Routes by URL substring; a payload that is an exception raises."""

    def __init__(self, routes):
        self.routes = routes
        self.urls: list[str] = []
        self.headers_seen: list[dict] = []

    def get(self, url, headers=None):  # noqa: D102 - fake
        self.urls.append(url)
        self.headers_seen.append(headers or {})
        for needle, payload in self.routes:
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"unexpected URL: {url}")


def connector(routes, **kw) -> CoreConnector:
    kw.setdefault("api_key", "fixture-key")
    return CoreConnector(http=CoreFakeHttp(routes), **kw)


def search_route(payload):
    return [("/search/works/", payload)]


# ------------------------------------------------------------- CLM-012-01/-08

def test_key_gate_refuses_keyless_construction(monkeypatch):
    monkeypatch.delenv("CORE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CORE_API_KEY"):
        CoreConnector(http=CoreFakeHttp([]))


def test_bearer_header_sent_and_source_is_core():
    http = CoreFakeHttp(search_route({"results": [WORK]}))
    conn = CoreConnector(http=http, api_key="fixture-key")
    items = conn.search("exercise depression")
    assert http.headers_seen[0]["Authorization"] == "Bearer fixture-key"
    assert items[0].source == "core"


# ------------------------------------------------------------- CLM-012-03

def test_search_work_without_licence_drops_content():
    conn = connector(search_route({"results": [WORK]}))
    (item,) = conn.search("exercise depression")
    # The work HAS an abstract; no licence is asserted for it, so the
    # content is dropped at the connector and the basis says why.
    assert item.abstract is None
    assert item.license_basis == CoreConnector.NO_LICENCE_BASIS
    assert item.hosted_ok is True  # nothing hosted; nothing asserted NC
    # Author names are normalized out of CORE's inverted form.
    assert item.authors == ["Felipe Barreto Schuch", "Davy Vancampfort"]
    assert item.source_id == DOI and item.year == 2016
    # The work lists a publisher but no journal: publisher is not a
    # venue (a live pass-over, 2026-10-12, taught this).
    assert item.venue is None


def test_venue_comes_from_journals_only():
    work = dict(WORK, journals=[{"title": "Journal of Psychiatric Research"}])
    conn = connector(search_route({"results": [work]}))
    (item,) = conn.search("exercise depression")
    assert item.venue == "Journal of Psychiatric Research"


def test_resolve_builds_item_from_first_licensed_content_output():
    conn = connector([
        ("/search/works/", {"results": [WORK]}),
        (OUT1, OUTPUT_NO_LICENCE),   # no licence -> does not qualify
        (OUT2, OUTPUT_NC),           # licence + abstract -> the record
        (OUT3, OUTPUT_FULLTEXT_ONLY),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.source == "core"
    assert item.abstract == OUTPUT_NC["abstract"]
    assert item.license_basis == NC_LICENCE
    # NC licence: stance-checkable, but never served from a hosted shape.
    assert item.hosted_ok is False
    assert item.year == 2016  # output year arrives as a string
    # OUT3 was never fetched: consultation stops at the first qualifier.
    assert not any(OUT3 in u for u in conn.http.urls)


def test_resolve_falls_back_to_full_text_when_no_abstract():
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT1])]}),
        (OUT1, OUTPUT_FULLTEXT_ONLY),
    ])
    item = conn.resolve(DOI)
    assert item is not None
    assert item.abstract == OUTPUT_FULLTEXT_ONLY["fullText"]
    assert item.license_basis == CC_LICENCE and item.hosted_ok is True


def test_placeholder_full_text_is_not_content():
    placeholder = dict(OUTPUT_FULLTEXT_ONLY,
                       fullText="Not available for public API users.")
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT1])]}),
        (OUT1, placeholder),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.abstract is None
    assert item.license_basis == CoreConnector.NO_LICENCE_BASIS


def test_resolve_degrades_to_metadata_when_no_output_qualifies():
    conn = connector([
        ("/search/works/", {"results": [WORK]}),
        (OUT1, OUTPUT_NO_LICENCE),
        (OUT2, OUTPUT_NO_LICENCE),
        (OUT3, OUTPUT_NO_LICENCE),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.abstract is None
    assert item.license_basis == CoreConnector.NO_LICENCE_BASIS


def test_restriction_marker_is_not_a_licence():
    # Found live (2026-10-12 smoke): a Schuch deposit asserts licence
    # "intranet" — a restriction marker, not a licence. It must not
    # unlock content; the next qualifying deposit is used instead.
    intranet = dict(OUTPUT_NC, license="intranet")
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT1, OUT2])]}),
        (OUT1, intranet),
        (OUT2, OUTPUT_NC),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.license_basis == NC_LICENCE


def test_only_restriction_marker_degrades_to_metadata():
    intranet = dict(OUTPUT_NC, license="intranet")
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT1])]}),
        (OUT1, intranet),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.abstract is None


def test_output_404_is_skipped_not_fatal():
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT1, OUT2])]}),
        (OUT1, http_error(404)),
        (OUT2, OUTPUT_NC),
    ])
    item = conn.resolve(DOI)
    assert item is not None and item.license_basis == NC_LICENCE


# ------------------------------------------------------------- CLM-012-04

def test_resolve_no_matching_work_is_none():
    conn = connector(search_route({"results": []}))
    assert conn.resolve(DOI) is None
    other = dict(WORK, doi="10.9999/other")
    conn2 = connector(search_route({"results": [other]}))
    assert conn2.resolve(DOI) is None  # search answered; not our work


@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
def test_api_failures_raise_never_none(code):
    conn = connector(search_route(http_error(code)))
    with pytest.raises(CoreApiError):
        conn.resolve(DOI)
    with pytest.raises(CoreApiError):
        conn.search("anything")


def test_transport_failure_raises():
    conn = connector([("/search/works/", ConnectionError("down"))])
    with pytest.raises(CoreApiError):
        conn.resolve(DOI)


# ------------------------------------------------------------- CLM-012-05

def test_budget_reserved_first_and_settled_on_answer():
    budget = CreditBudget(limit=100)
    conn = connector([
        ("/search/works/", {"results": [dict(WORK, outputs=[OUT2])]}),
        (OUT2, OUTPUT_NC),
    ], budget=budget)
    conn.resolve(DOI)
    # 1 DOI search (a "get") + 1 output fetch (a "get") = 2 units.
    assert budget.spent == 2


def test_budget_exhaustion_stops_before_any_http():
    budget = CreditBudget(limit=0)
    conn = connector(search_route({"results": [WORK]}), budget=budget)
    with pytest.raises(BudgetExhausted):
        conn.search("exercise")
    assert conn.http.urls == []  # no call was made


# ------------------------------------------------- pipeline (CLM-012-02/-06/-07)

SUPPORTING = ("Exercise is an effective treatment reducing depressive "
              "symptoms in adults with depression.")

CITATION = Citation(
    citation_id="CIT-T-302", claim_id="CLM-T-001",
    proposition="Exercise is an effective treatment for reducing "
                "depressive symptoms",
    doi=DOI, title=WORK["title"], authors=["Felipe Schuch"], year=2016)


def meta_item(source: str) -> RetrievedItem:
    return RetrievedItem(
        source=source, source_id=DOI, title=WORK["title"],
        authors=["Felipe Schuch"], year=2016, venue=None, abstract=None,
        license_basis="unknown (not asserted by source)")


def content_item(source: str, abstract: str | None = None) -> RetrievedItem:
    return RetrievedItem(
        source=source, source_id=DOI, title=WORK["title"],
        authors=["Felipe Schuch"], year=2016, venue=None,
        abstract=abstract or SUPPORTING,
        license_basis=NC_LICENCE, hosted_ok=False)


class StubConnector:
    def __init__(self, name, *, resolved=None, raises=None):
        self.name = name
        self._resolved = resolved
        self._raises = raises
        self.resolve_calls = 0

    def resolve(self, doi):
        self.resolve_calls += 1
        if self._raises is not None:
            raise self._raises
        return self._resolved

    def search(self, query, *, limit=10):
        return []


def run(tmp_path, connectors, citation=CITATION, tag="s"):
    from tekmerion.store import StudyStore

    store = StudyStore.create(str(tmp_path / f"{tag}.axmr"))
    report = verify_citations(store, [citation], connectors, actor="researcher")
    (result,) = report.results
    return result


def test_fold_two_sources_one_origin_group(tmp_path):
    # The same DOI resolved via two different sources (in two runs of
    # the pipeline) folds into ONE origin group: derivative folding
    # never double-counts a work found in two sources (CLM-012-02).
    cit_a = Citation(**{**CITATION.__dict__, "citation_id": "CIT-T-A"})
    cit_b = Citation(**{**CITATION.__dict__, "citation_id": "CIT-T-B"})
    via_primary = run(tmp_path, [StubConnector("crossref", resolved=content_item("crossref"))],
                      citation=cit_a, tag="a")
    via_core = run(tmp_path, [StubConnector("core", resolved=content_item("core"))],
                   citation=cit_b, tag="b")
    groups, _suspects = assign_origin_groups([cit_a, cit_b], [via_primary, via_core])
    assert groups["CIT-T-A"] == groups["CIT-T-B"]


def test_enrichment_fires_on_metadata_only_primary(tmp_path):
    core = StubConnector("core", resolved=content_item("core"))
    result = run(tmp_path, [StubConnector("crossref", resolved=meta_item("crossref")), core])
    assert result.resolution == RESOLVED and result.agreement == AGREE
    assert result.content == SUPPORTS  # checked — not metadata_only
    assert result.source == "core"
    assert "content via core" in result.detail


def test_enrichment_licence_degradation_stays_metadata_only(tmp_path):
    # CORE's record carries no usable content (the real connector
    # drops unlicensed content, so its item is metadata too): the
    # citation stays metadata_only — degradation is the outcome,
    # never a silent stance check on unlicensed text.
    core = StubConnector("core", resolved=meta_item("core"))
    result = run(tmp_path, [StubConnector("crossref", resolved=meta_item("crossref")), core])
    assert result.content == METADATA_ONLY and result.source == "crossref"


def test_enrichment_disagreement_is_passed_over(tmp_path):
    alien = RetrievedItem(
        source="core", source_id=DOI,
        title="Glucosamine for joint pain: a systematic review",
        authors=["Jane Doe"], year=2019, venue=None,
        abstract=SUPPORTING,
        license_basis=CC_LICENCE)
    core = StubConnector("core", resolved=alien)
    result = run(tmp_path, [StubConnector("crossref", resolved=meta_item("crossref")), core])
    assert result.content == METADATA_ONLY and result.source == "crossref"
    assert "passed over" in result.detail


def test_enrichment_failure_never_unresolves(tmp_path):
    core = StubConnector("core", raises=CoreApiError("core: HTTP 429"))
    result = run(tmp_path, [StubConnector("crossref", resolved=meta_item("crossref")), core])
    assert result.resolution == RESOLVED and result.content == METADATA_ONLY
    assert "enrichment via core failed" in result.detail


def test_no_enrichment_when_primary_has_content(tmp_path):
    core = StubConnector("core", resolved=content_item("core"))
    with_core = run(tmp_path, [StubConnector("crossref", resolved=content_item("crossref")), core],
                    tag="wc")
    without = run(tmp_path, [StubConnector("crossref", resolved=content_item("crossref"))],
                  tag="wo")
    assert core.resolve_calls == 0  # CORE never called (CLM-012-06)
    assert (with_core.resolution, with_core.agreement, with_core.content,
            with_core.source, with_core.source_id, with_core.detail) == \
           (without.resolution, without.agreement, without.content,
            without.source, without.source_id, without.detail)


def test_core_outage_on_only_route_is_error_not_not_found(tmp_path):
    core = StubConnector("core", raises=CoreApiError("core: HTTP 503"))
    result = run(tmp_path, [core])
    assert result.resolution == ERROR and result.resolution != NOT_FOUND


# ------------------------------------------------------------- CLM-012-08

def test_mcp_default_connectors_key_gated(monkeypatch):
    from tekmerion.mcp import server

    monkeypatch.delenv("CORE_API_KEY", raising=False)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    assert [c.name for c in server._default_connectors()] == ["crossref"]
    monkeypatch.setenv("CORE_API_KEY", "fixture-key")
    names = [c.name for c in server._default_connectors()]
    assert names == ["crossref", "core"]  # appended last; order conserved
