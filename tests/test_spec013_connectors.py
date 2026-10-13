"""Spec 013 WS-6 (Lane A) regression battery: the rt-e connector
probes (rt-e/probes/connectors/code_probes.py + live_probes.py),
ported. Every DEMONSTRATED attack must now fail; every HELD defense
(RTE-26 K1 accounting, RTE-27 licence gates, RTE-28 CORE failure
semantics) must still hold. Fixture values are the recorded live
payloads' own (Wakefield retraction entries, the Schuch TDM licence,
the CORE Schuch author aggregate) — no network."""

import io
import urllib.error
import urllib.parse

import pytest

from tekmerion.connectors import (
    ConnectorError,
    CoreApiError,
    CoreConnector,
    CreditBudget,
    CrossrefConnector,
    HttpJson,
    OpenAlexConnector,
    RetrievedItem,
    normalize_doi,
)
from tekmerion import verification as V
from tekmerion.verification import Citation, check_agreement, verify_citations

SCHUCH = "10.1016/j.jpsychires.2016.02.023"
WAKEFIELD_DOI = "10.1016/S0140-6736(97)11096-0"


def http_error(code):
    return urllib.error.HTTPError("https://x", code, f"HTTP {code}",
                                  hdrs=None, fp=io.BytesIO(b"{}"))


class FakeHttp(HttpJson):
    """Payload-or-raise double, after the rt-e probe harness."""

    def __init__(self, payload=None, exc=None):
        self.payload, self.exc, self.urls = payload, exc, []

    def get(self, url, headers=None):
        self.urls.append(url)
        if self.exc:
            raise self.exc
        return self.payload


# ------------------------------------------------------------ CLM-013-36
# Retraction state: parsed, quarantining, surfaced (RTE-01).

CROSSREF_WAKEFIELD = {
    "DOI": WAKEFIELD_DOI,
    "title": ["Ileal-lymphoid-nodular hyperplasia, non-specific colitis, "
              "and pervasive developmental disorder in children"],
    "author": [{"given": "AJ", "family": "Wakefield"},
               {"given": "SH", "family": "Murch"}],
    "issued": {"date-parts": [[1998, 2, 28]]},
    "container-title": ["The Lancet"],
    # Verbatim entry types from the recorded live payload.
    "updated-by": [
        {"DOI": "10.1016/s0140-6736(04)15715-2", "type": "correction",
         "label": "Correction", "source": "retraction-watch"},
        {"DOI": "10.1016/s0140-6736(10)60175-4", "type": "retraction",
         "label": "Retraction", "source": "retraction-watch"},
    ],
}

OPENALEX_WAKEFIELD = {
    "id": "https://openalex.org/W2144560581",
    "doi": "https://doi.org/10.1016/S0140-6736(97)11096-0",
    "title": ("Ileal-lymphoid-nodular hyperplasia, non-specific colitis, "
              "and pervasive developmental disorder in children"),
    "publication_year": 1998,
    "authorships": [{"author": {"display_name": "AJ Wakefield"}},
                    {"author": {"display_name": "SH Murch"}}],
    "primary_location": {"source": {"display_name": "The Lancet"}},
    "is_retracted": True,
}

WAKEFIELD_CITATION = Citation(
    citation_id="CW", claim_id="CLW",
    proposition="Ileal-lymphoid-nodular hyperplasia is associated with "
                "developmental disorder",
    doi=WAKEFIELD_DOI,
    title="Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and "
          "pervasive developmental disorder in children",
    authors=["AJ Wakefield"], year=1998, venue="The Lancet")


def test_crossref_retraction_parsed_from_updated_by():
    item = CrossrefConnector._item(CROSSREF_WAKEFIELD)
    assert item.retraction == "retracted"


def test_crossref_correction_only_surfaces_as_corrected():
    work = dict(CROSSREF_WAKEFIELD)
    work["updated-by"] = [CROSSREF_WAKEFIELD["updated-by"][0]]
    assert CrossrefConnector._item(work).retraction == "corrected"


def test_openalex_is_retracted_parsed():
    item = OpenAlexConnector._item(OPENALEX_WAKEFIELD)
    assert item.retraction == "retracted"
    plain = dict(OPENALEX_WAKEFIELD, is_retracted=False)
    assert OpenAlexConnector._item(plain).retraction is None


def test_retracted_work_quarantines_despite_stage2_agreement(tmp_path):
    """The RTE-01 attack: both live payloads used to pass the real
    parsers and check_agreement as ('agree', []) and ingest as
    ordinary evidence. Now the citation quarantines on the
    retraction state, and the state is on the record."""
    pytest.importorskip("axiomere")
    from tekmerion.store import StudyStore

    class RoutedHttp(FakeHttp):
        def get(self, url, headers=None):
            self.urls.append(url)
            if "crossref" in url:
                return {"message": CROSSREF_WAKEFIELD}
            return OPENALEX_WAKEFIELD

    store = StudyStore.create(str(tmp_path / "w.axmr"))
    conns = [CrossrefConnector(http=RoutedHttp()),
             OpenAlexConnector(http=RoutedHttp(), api_key="k",
                               budget=CreditBudget(limit=100))]
    report = verify_citations(store, [WAKEFIELD_CITATION], conns, actor="r")
    (result,) = report.results
    assert result.agreement == V.AGREE  # stage 2 still agrees — that was the attack
    assert result.retraction == "retracted"
    assert result.quarantined
    item = V.to_evidence_item(WAKEFIELD_CITATION, result)
    assert item.verified is False  # contributes no evidence mass
    checked = [e for e in store.events() if e["type"] == "citation.checked"]
    assert checked[0]["payload"]["retraction"] == "retracted"
    queue = [e for e in store.events() if e["type"] == "adjudication.enqueued"]
    assert "retracted" in queue[0]["payload"]["reason"]


# ------------------------------------------------------------ CLM-013-37
# One error contract: 404 is the only not_found (RTE-02).

@pytest.mark.parametrize("code", [429, 500, 503])
def test_crossref_resolve_outage_raises_not_none(code):
    conn = CrossrefConnector(http=FakeHttp(exc=http_error(code)))
    with pytest.raises(ConnectorError):
        conn.resolve(SCHUCH)


def test_crossref_resolve_genuine_404_is_none():
    conn = CrossrefConnector(http=FakeHttp(exc=http_error(404)))
    assert conn.resolve(SCHUCH) is None


@pytest.mark.parametrize("code", [429, 500])
def test_openalex_resolve_outage_raises_not_none(code):
    conn = OpenAlexConnector(http=FakeHttp(exc=http_error(code)),
                             api_key="k", budget=CreditBudget(limit=100))
    with pytest.raises(ConnectorError):
        conn.resolve(SCHUCH)


def test_openalex_resolve_genuine_404_is_none():
    conn = OpenAlexConnector(http=FakeHttp(exc=http_error(404)),
                             api_key="k", budget=CreditBudget(limit=100))
    assert conn.resolve(SCHUCH) is None


def test_openalex_budget_exhaustion_raises_not_none():
    conn = OpenAlexConnector(http=FakeHttp({}), api_key="k",
                             budget=CreditBudget(limit=0))
    with pytest.raises(Exception) as excinfo:
        conn.resolve(SCHUCH)
    assert not isinstance(excinfo.value, type(None))


def _pipeline_citation():
    return Citation(citation_id="C1", claim_id="CL1", proposition="x",
                    doi=SCHUCH, title="Exercise as a treatment for depression",
                    authors=["Felipe Schuch"], year=2016)


@pytest.mark.parametrize("code,outcome", [(429, V.ERROR), (500, V.ERROR),
                                          (404, V.NOT_FOUND)])
def test_pipeline_only_crossref_classification(code, outcome):
    """The probe's pipeline cases, verbatim: an outage on the only
    route is ERROR, a genuine 404 is NOT_FOUND."""
    conn = CrossrefConnector(http=FakeHttp(exc=http_error(code)))
    _item, got, _detail = V._resolve(_pipeline_citation(), [conn])
    assert got == outcome


def test_pipeline_only_openalex_429_is_error():
    conn = OpenAlexConnector(http=FakeHttp(exc=http_error(429)),
                             api_key="k", budget=CreditBudget(limit=100))
    _item, got, _detail = V._resolve(_pipeline_citation(), [conn])
    assert got == V.ERROR


# ------------------------------------------------------------ CLM-013-38
# OpenAlex content is licence-gated (RTE-03).

def test_openalex_no_licence_withholds_abstract():
    payload = {"id": "https://openalex.org/W1", "doi": SCHUCH, "title": "T",
               "authorships": [],
               "abstract_inverted_index": {"Exercise": [0], "reduces": [1]}}
    item = OpenAlexConnector._item(payload)
    assert item.abstract is None
    assert item.license_basis == "openalex-metadata (no licence asserted)"


def test_openalex_asserted_licence_keeps_abstract():
    payload = {"id": "https://openalex.org/W1", "doi": SCHUCH, "title": "T",
               "authorships": [], "license": "cc-by",
               "abstract_inverted_index": {"Exercise": [0], "reduces": [1]}}
    assert OpenAlexConnector._item(payload).abstract == "Exercise reduces"


# ------------------------------------------------------------ CLM-013-39
# Crossref licences are qualified: TDM unlocks nothing (RTE-05).

# The live Schuch record's only licence entry, verbatim.
TDM_LICENCE = {
    "start": {"date-parts": [[2016, 6, 1]],
              "date-time": "2016-06-01T00:00:00Z", "timestamp": 1464739200000},
    "content-version": "tdm", "delay-in-days": 0,
    "URL": "https://www.elsevier.com/tdm/userlicense/1.0/",
}


def test_tdm_only_licence_unlocks_no_content():
    work = {"DOI": SCHUCH, "title": ["T"], "author": [],
            "abstract": "Exercise reduces depressive symptoms.",
            "license": [TDM_LICENCE]}
    item = CrossrefConnector._item(work)
    assert item.abstract is None


def test_real_content_licence_after_tdm_entry_unlocks():
    work = {"DOI": SCHUCH, "title": ["T"], "author": [],
            "abstract": "Exercise reduces depressive symptoms.",
            "license": [TDM_LICENCE,
                        {"URL": "https://creativecommons.org/licenses/by/4.0/",
                         "content-version": "vor", "delay-in-days": 0,
                         "start": {"date-parts": [[2016, 6, 1]]}}]}
    item = CrossrefConnector._item(work)
    assert item.abstract is not None
    assert item.license_basis == "https://creativecommons.org/licenses/by/4.0/"


def test_licence_not_yet_in_force_unlocks_no_content():
    work = {"DOI": SCHUCH, "title": ["T"], "author": [],
            "abstract": "Exercise reduces depressive symptoms.",
            "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/",
                          "content-version": "vor", "delay-in-days": 0,
                          "start": {"date-parts": [[2099, 1, 1]]}}]}
    assert CrossrefConnector._item(work).abstract is None


# ------------------------------------------------------------ CLM-013-40
# Resolution compares sources; disagreement quarantines (RTE-04).

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


def _item(source, year, abstract="content"):
    return RetrievedItem(source=source, source_id=SCHUCH,
                         title="Exercise as a treatment for depression",
                         authors=["Felipe Schuch"], year=year,
                         abstract=abstract, license_basis="cc-by")


def test_first_source_wins_is_abolished(tmp_path):
    """The probe: a wrong-but-confident first record (year 1900,
    with content) decided the record alone; the agreeing second
    source was never consulted. Now it is consulted, the
    disagreement between sources is recorded, and the citation
    quarantines on it."""
    pytest.importorskip("axiomere")
    from tekmerion.store import StudyStore

    bad = StubConnector("crossref", resolved=_item("crossref", 1900))
    good = StubConnector("openalex", resolved=_item("openalex", 2016))
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    report = verify_citations(store, [_pipeline_citation()], [bad, good], actor="r")
    (result,) = report.results
    assert good.resolve_calls == 1  # consulted — call count is no longer 0
    assert result.sources_consulted == ["crossref", "openalex"]
    assert result.source_disagreement == ["year"]
    assert result.quarantined


def test_agreeing_content_primary_stands_without_extra_calls(tmp_path):
    """The other direction (Spec 012's discipline, held): a primary
    that resolves, agrees, and carries content is decided on its
    own checked record — no second source is called."""
    pytest.importorskip("axiomere")
    from tekmerion.store import StudyStore

    primary = StubConnector("crossref", resolved=_item("crossref", 2016))
    second = StubConnector("core", resolved=_item("core", 2016))
    store = StudyStore.create(str(tmp_path / "s2.axmr"))
    report = verify_citations(store, [_pipeline_citation()], [primary, second],
                              actor="r")
    (result,) = report.results
    assert second.resolve_calls == 0
    assert result.resolution == V.RESOLVED and not result.quarantined
    assert result.source_disagreement == []


# ------------------------------------------------------------ CLM-013-41
# Enrichment asserts candidate identity in the pipeline (RTE-06).

def test_enrichment_refuses_a_different_doi_candidate():
    """The probe: a candidate carrying a DIFFERENT work's record
    (10.9999/DIFFERENT-WORK) with an abstract and one shared surname
    was substituted as the citation's content. The pipeline now
    refuses it on identity, before any agreement test."""
    primary = RetrievedItem(source="crossref", source_id=SCHUCH,
                            title="Exercise as a treatment for depression",
                            authors=["Felipe Schuch"], year=2016, abstract=None,
                            license_basis="crossref-metadata (no licence asserted)")
    alien = RetrievedItem(source="core", source_id="10.9999/DIFFERENT-WORK",
                          title="Exercise as a treatment for depression",
                          authors=["Felipe Schuch"], year=2016,
                          abstract="Exercise is an effective treatment.",
                          license_basis="https://creativecommons.org/licenses/by/4.0/")

    class AlienStub:
        name = "core"

        def resolve(self, doi):
            return alien

    enriched, note = V._enrich(_pipeline_citation(), primary, [AlienStub()])
    assert enriched is primary
    assert "not the cited DOI" in note


# ------------------------------------------------------------ CLM-013-42
# One shared DOI normalizer (RTE-07).

@pytest.mark.parametrize("form", [
    SCHUCH, SCHUCH.upper(), "doi:" + SCHUCH, "https://doi.org/" + SCHUCH,
    SCHUCH + ".", SCHUCH + "  ", "  " + SCHUCH,
])
def test_normalize_doi_all_surface_forms(form):
    assert normalize_doi(form) == SCHUCH


def test_pipeline_norm_doi_delegates_to_the_shared_normalizer():
    assert V._norm_doi("https://doi.org/10.1000/XYZ2.") == "10.1000/xyz2"


def test_doi_variants_reach_the_same_routes():
    """The probe's variant matrix: a trailing period or a doi:
    prefix must not defeat any route the bare form resolves on."""
    forms = [SCHUCH.upper(), "doi:" + SCHUCH, SCHUCH + ".", SCHUCH + "  "]
    for form in forms:
        h = FakeHttp({"message": {}})
        CrossrefConnector(http=h).resolve(form)
        assert "10.1016%2Fj.jpsychires.2016.02.023" in h.urls[0]
        h2 = FakeHttp({})
        OpenAlexConnector(http=h2, api_key="k",
                          budget=CreditBudget(limit=100)).resolve(form)
        assert "/works/doi:10.1016/j.jpsychires.2016.02.023" in h2.urls[0]
        h3 = FakeHttp({"results": []})
        CoreConnector(http=h3, api_key="k").resolve(form)
        assert 'doi:"10.1016/j.jpsychires.2016.02.023"' in urllib.parse.unquote(h3.urls[0])


# ------------------------------------------------------------ CLM-013-43
# CORE degradation states its true reason (RTE-08).

CORE_OUTS = [f"https://api.core.ac.uk/v3/outputs/{n}" for n in (1, 2, 3, 4)]


def _core_fake_http(work, outputs_by_url):
    class CoreFake(FakeHttp):
        def get(self, url, headers=None):
            self.urls.append(url)
            if "/search/works/" in url:
                return {"results": [work]}
            for out_url, payload in outputs_by_url.items():
                if out_url in url:
                    return payload
            raise AssertionError(url)
    return CoreFake()


def test_output_cap_reached_is_the_recorded_reason():
    """The probe's fabricated work: four outputs, only the fourth
    licensed. It used to record plain NO_LICENCE_BASIS — 'no
    licensed deposit exists' — when the truth was the fetch cap."""
    work = {"id": 9, "doi": SCHUCH, "title": "T", "authors": [],
            "yearPublished": 2016, "journals": [], "abstract": "",
            "outputs": CORE_OUTS}
    no_lic = {"id": 1, "doi": SCHUCH, "title": "T", "authors": [],
              "abstract": "x", "fullText": "y"}
    good = {"id": 4, "doi": SCHUCH, "title": "T", "authors": [],
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "abstract": "licensed content", "fullText": ""}
    outputs = {CORE_OUTS[0]: no_lic, CORE_OUTS[1]: no_lic,
               CORE_OUTS[2]: no_lic, CORE_OUTS[3]: good}
    item = CoreConnector(http=_core_fake_http(work, outputs),
                         api_key="k").resolve(SCHUCH)
    assert item.abstract is None
    assert item.degradation_reason == "output-cap-reached"


def test_no_cap_signal_when_every_output_was_examined():
    work = {"id": 9, "doi": SCHUCH, "title": "T", "authors": [],
            "yearPublished": 2016, "journals": [], "abstract": "",
            "outputs": CORE_OUTS[:2]}
    no_lic = {"id": 1, "doi": SCHUCH, "title": "T", "authors": [],
              "abstract": "x", "fullText": "y"}
    outputs = {CORE_OUTS[0]: no_lic, CORE_OUTS[1]: no_lic}
    item = CoreConnector(http=_core_fake_http(work, outputs),
                         api_key="k").resolve(SCHUCH)
    assert item.abstract is None
    assert item.degradation_reason is None
    assert item.license_basis == CoreConnector.NO_LICENCE_BASIS


# ------------------------------------------------------------ CLM-013-44
# CORE authors normalized and deduplicated (RTE-09).

# The recorded live CORE Schuch work-level author list, verbatim:
# 15 aggregate entries for a six-author paper.
CORE_SCHUCH_AUTHORS_RAW = [
    "Simon Rosenbaum", "Ward, Felipe", "Stubbs, Brendon",
    "Felipe B. Schuch", "Schuch, Felipe Barreto", "Schuch, Felipe",
    "Philip B. Ward", "Richards, Justin", "Davy Vancampfort",
    "Rosenbaum, Simon", "Brendon Stubbs", "Stubbs, Brendon; id_orcid",
    "Vancampfort, Davy", "Ward, Philip B.", "Justin Richards",
]


def test_core_work_authors_deduped_and_cleaned():
    work = {"id": 1, "doi": SCHUCH, "title": "T",
            "authors": [{"name": n} for n in CORE_SCHUCH_AUTHORS_RAW],
            "yearPublished": 2016, "journals": [], "abstract": ""}
    item = CoreConnector._work_item(work)
    assert len(item.authors) == 6
    assert set(item.authors) == {
        "Simon Rosenbaum", "Brendon Stubbs", "Felipe Barreto Schuch",
        "Philip B. Ward", "Justin Richards", "Davy Vancampfort",
    }
    assert not any("id_orcid" in a or ";" in a for a in item.authors)
    assert "Felipe Ward" not in item.authors  # the recombination ghost


# ------------------------------------------------------------ CLM-013-45
# Classification once, both routes; query logged before execution (RTE-10).

@pytest.mark.parametrize("code", [429, 500])
def test_search_route_classifies_like_the_resolve_route(code):
    """The same failure used to classify differently by route:
    search errors propagated raw while resolve errors vanished
    into not_found. Both routes now raise the one ConnectorError."""
    with pytest.raises(ConnectorError):
        CrossrefConnector(http=FakeHttp(exc=http_error(code))).search("x")
    with pytest.raises(ConnectorError):
        OpenAlexConnector(http=FakeHttp(exc=http_error(code)), api_key="k",
                          budget=CreditBudget(limit=100)).search("x")
    with pytest.raises(CoreApiError):  # CORE's contract, unchanged (RTE-28)
        CoreConnector(http=FakeHttp(exc=http_error(code)), api_key="k").search("x")


def test_no_doi_search_outage_is_error_not_not_found():
    cit = Citation(citation_id="C9", claim_id="CL1", proposition="x",
                   doi=None, title="Exercise as a treatment for depression",
                   authors=["Felipe Schuch"], year=2016)
    conn = CrossrefConnector(http=FakeHttp(exc=http_error(429)))
    _item, outcome, _detail = V._resolve(cit, [conn])
    assert outcome == V.ERROR


def test_run_query_logs_before_execution_even_when_search_raises(tmp_path):
    """run_query used to log only after search returned, so a
    raising search left no connector.query event at all."""
    pytest.importorskip("axiomere")
    from tekmerion.connectors import run_query
    from tekmerion.store import StudyStore

    class ExplodingSearch:
        name = "exploding"

        def search(self, query, *, limit=10):
            raise ConnectorError("exploding: HTTP 503")

    store = StudyStore.create(str(tmp_path / "q.axmr"))
    with pytest.raises(ConnectorError):
        run_query(store, ExplodingSearch(), "depression exercise", actor="r")
    events = [e for e in store.events() if e["type"] == "connector.query"]
    assert len(events) == 1
    assert events[0]["payload"]["connector"] == "exploding"
    assert events[0]["payload"]["query"] == "depression exercise"


def test_run_query_success_still_logs_once(tmp_path):
    pytest.importorskip("axiomere")
    from tekmerion.connectors import run_query
    from tekmerion.store import StudyStore

    store = StudyStore.create(str(tmp_path / "q2.axmr"))
    http = FakeHttp({"message": {"items": []}})
    items = run_query(store, CrossrefConnector(http=http), "x", actor="r")
    assert items == []
    events = [e for e in store.events() if e["type"] == "connector.query"]
    assert len(events) == 1


# ------------------------------------------------------------ HELD defenses
# RTE-26 (K1 accounting), RTE-27 (licence gates), RTE-28 (CORE semantics).

def test_k1_accounting_with_the_new_classification(tmp_path):
    """Every citation still gets exactly one ledgered outcome —
    now with the outage labeled error, not fabricated not_found."""
    pytest.importorskip("axiomere")
    from tekmerion.store import StudyStore

    class MixedHttp(FakeHttp):
        def get(self, url, headers=None):
            self.urls.append(url)
            if "xyz123" in url:
                return {"message": {
                    "DOI": "10.1000/xyz123", "title": ["A Study of X"],
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "issued": {"date-parts": [[2024, 5, 1]]},
                    "container-title": ["Journal of X"],
                    "abstract": "Findings support the proposition fully.",
                    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}]}}
            if "doesnotexist" in url:
                raise http_error(404)
            raise http_error(429)

    store = StudyStore.create(str(tmp_path / "k1.axmr"))
    conn = CrossrefConnector(http=MixedHttp())
    batch = [
        Citation(citation_id="CIT-OK", claim_id="CL1", proposition="x",
                 doi="10.1000/xyz123", title="A Study of X",
                 authors=["Ada Lovelace"], year=2024),
        Citation(citation_id="CIT-FAB", claim_id="CL1", proposition="x",
                 doi="10.1000/doesnotexist"),
        Citation(citation_id="CIT-OUT", claim_id="CL1", proposition="x",
                 doi="10.1000/outage"),
    ]
    report = verify_citations(store, batch, [conn], actor="r")
    accounting = report.accounting()
    assert accounting == {"CIT-OK": "resolved", "CIT-FAB": "not_found",
                          "CIT-OUT": "error"}
    checked = [e for e in store.events() if e["type"] == "citation.checked"]
    assert len(checked) == 3


def test_core_failure_semantics_unchanged():
    """RTE-28 held: CORE's 404 is the only None; everything else
    raises CoreApiError — and CoreApiError is the shared contract's
    own type now."""
    assert CoreConnector(http=FakeHttp(exc=http_error(404)),
                         api_key="k").resolve(SCHUCH) is None
    with pytest.raises(CoreApiError):
        CoreConnector(http=FakeHttp(exc=http_error(429)),
                      api_key="k").resolve(SCHUCH)
    assert issubclass(CoreApiError, ConnectorError)


def test_core_no_licence_gate_unchanged():
    """RTE-27 held: a CORE work asserting no licence yields no
    content and never a permissive default basis."""
    work = {"id": 1, "doi": SCHUCH, "title": "T", "authors": [],
            "yearPublished": 2016, "journals": [],
            "abstract": "unlicensed text"}
    item = CoreConnector._work_item(work)
    assert item.abstract is None
    assert item.license_basis == CoreConnector.NO_LICENCE_BASIS
