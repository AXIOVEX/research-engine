"""Connector tests run on recorded-shape fixtures (no network): each
test names the contract rule it pins."""

import io
import json

import pytest

from tekmerion.connectors import (
    BudgetExhausted,
    CreditBudget,
    CrossrefConnector,
    HttpJson,
    OpenAlexConnector,
)


class FakeHttp(HttpJson):
    def __init__(self, payload):
        self.payload = payload
        self.urls = []

    def get(self, url, headers=None):
        self.urls.append(url)
        return self.payload


CROSSREF_WORK = {
    "DOI": "10.1000/xyz123",
    "title": ["A Study of X"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "<jats:p>Findings.</jats:p>",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

OPENALEX_WORK = {
    "id": "https://openalex.org/W123",
    "doi": "https://doi.org/10.1000/xyz123",
    "title": "A Study of X",
    "publication_year": 2024,
    "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
    "primary_location": {"source": {"display_name": "Journal of X", "license": "cc-by"}},
    "license": "cc-by",
    "abstract_inverted_index": {"Findings": [1], "Strong": [0]},
}


def test_crossref_search_parses_and_captures_license():
    http = FakeHttp({"message": {"items": [CROSSREF_WORK]}})
    items = CrossrefConnector(http=http).search("study of x")
    assert items[0].source_id == "10.1000/xyz123"
    assert items[0].authors == ["Ada Lovelace"]
    assert items[0].year == 2024
    assert "creativecommons" in items[0].license_basis
    assert items[0].abstract  # licence asserted -> abstract usable
    assert "mailto=" in http.urls[0]  # polite pool identification


def test_crossref_abstract_dropped_without_licence():
    work = {k: v for k, v in CROSSREF_WORK.items() if k != "license"}
    http = FakeHttp({"message": {"items": [work]}})
    item = CrossrefConnector(http=http).search("x")[0]
    assert item.abstract is None  # Crossref abstracts are not CC0
    assert "no licence asserted" in item.license_basis


def test_openalex_requires_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        OpenAlexConnector(http=FakeHttp({}))


def test_openalex_filter_search_and_abstract_rebuild():
    http = FakeHttp({"results": [OPENALEX_WORK]})
    budget = CreditBudget(limit=100)
    conn = OpenAlexConnector(http=http, api_key="test-key", budget=budget)
    items = conn.search("study of x")
    assert "filter=title_and_abstract.search" in http.urls[0]  # cheap path, not search
    assert items[0].abstract == "Strong Findings"  # inverted index rebuilt in order
    assert items[0].license_basis == "cc-by"
    assert budget.spent == budget.cost_filter and budget.reserved == 0


def test_openalex_resolve_by_doi_uses_doi_route():
    http = FakeHttp(OPENALEX_WORK)
    conn = OpenAlexConnector(http=http, api_key="k", budget=CreditBudget(limit=10))
    item = conn.resolve("https://doi.org/10.1000/xyz123")
    assert "/works/doi:10.1000/xyz123" in http.urls[0]  # not /works/xyz123 (live-caught bug)
    assert item.title == "A Study of X"


def test_budget_exhaustion_is_a_stop_not_an_overrun():
    budget = CreditBudget(limit=5)
    budget.reserve("filter")
    with pytest.raises(BudgetExhausted):
        budget.reserve("search")  # 1 + 10 > 5


def test_nc_licence_excluded_from_hosted_shape():
    work = dict(CROSSREF_WORK)
    work["license"] = [{"URL": "https://creativecommons.org/licenses/by-nc/4.0/"}]
    item = CrossrefConnector(http=FakeHttp({"message": {"items": [work]}})).search("x")[0]
    assert item.hosted_ok is False


def test_run_query_logs_into_the_ledger(tmp_path):
    pytest.importorskip("axiomere")
    from tekmerion.store import StudyStore

    store = StudyStore.create(str(tmp_path / "s.axmr"))
    http = FakeHttp({"message": {"items": [CROSSREF_WORK]}})
    from tekmerion.connectors import run_query

    items = run_query(store, CrossrefConnector(http=http), "study of x", actor="researcher")
    assert len(items) == 1
    events = store.db.events()
    assert events[-1]["type"] == "connector.query"
    assert events[-1]["payload"]["connector"] == "crossref"
    assert store.verify().ok
