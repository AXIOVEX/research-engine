"""Phase 2 connectors — Crossref + OpenAlex (Spec 002, WS1 registry).

Contract rules carried from the architecture, not reinvented here:
- Every retrieved item carries `license_basis` (mandatory, per-record):
  Semantic Scholar taught the program that no source may be assumed
  openly licensed; Crossref abstracts are NOT CC0, so an abstract is
  only usable when a licence is actually asserted for the record.
- Every query is logged into the study's Axiomere ledger (T206), so
  provenance of retrieved items is chained like everything else.
- OpenAlex (post 2026-02-13) needs a free API key and meters credits;
  filter calls are ~10x cheaper than search calls, so this connector
  prefers filters, and every call reserves against a budget first —
  exhaustion is a stop, never a surprise (RT2-2 discipline).
- Sources without a verified public API (tDAR, ADS) or with
  non-commercial framing (BASE) are NOT connectors here (WS1 registry).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

USER_AGENT = "Tekmerion/0.1 (Axiovex Systems; https://axiovexsystems.com)"


@dataclass
class RetrievedItem:
    source: str            # "crossref" | "openalex"
    source_id: str         # DOI (crossref) or OpenAlex work id
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    license_basis: str = "unknown (not asserted by source)"
    hosted_ok: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source, "source_id": self.source_id, "title": self.title,
            "authors": self.authors, "year": self.year, "venue": self.venue,
            "abstract": self.abstract, "license_basis": self.license_basis,
            "hosted_ok": self.hosted_ok,
        }


def _nc_flag(license_basis: str) -> bool:
    """Non-commercial-only licences exclude an item from the hosted
    deployment shape (rights are recorded per deployment shape, RT2-1)."""
    lb = license_basis.lower()
    return "-nc" in lb or "noncommercial" in lb or "non-commercial" in lb


class HttpJson:
    """Tiny JSON-over-HTTP client; injectable for tests."""

    def __init__(self, opener: Optional[Callable[..., Any]] = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def get(self, url: str, headers: Optional[dict] = None) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        with self._opener(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))


# ------------------------------------------------------------------ budget

class BudgetExhausted(RuntimeError):
    pass


@dataclass
class CreditBudget:
    """Freeze-time reservation discipline (RT2-2): callers reserve the
    estimated cost before a call; exhaustion raises, and the run treats
    that as a stop condition — never a silent overrun.

    Unit costs are configuration, not scripture: the verified relation
    is filter ~10x cheaper than search (WS1 registry, 2026-10-11)."""

    limit: int
    cost_search: int = 10
    cost_filter: int = 1
    cost_get: int = 1
    reserved: int = 0
    spent: int = 0

    def reserve(self, kind: str) -> int:
        cost = {"search": self.cost_search, "filter": self.cost_filter, "get": self.cost_get}[kind]
        if self.reserved + self.spent + cost > self.limit:
            raise BudgetExhausted(
                f"credit budget exhausted: limit {self.limit}, spent {self.spent}, "
                f"reserved {self.reserved}, next {kind} costs {cost}"
            )
        self.reserved += cost
        return cost

    def settle(self, cost: int) -> None:
        self.reserved -= cost
        self.spent += cost


# ------------------------------------------------------------------ crossref

class CrossrefConnector:
    """Resolution source of record (WS1). Polite pool: identify with a
    mailto; no key exists or is needed."""

    name = "crossref"
    BASE = "https://api.crossref.org"

    def __init__(self, http: Optional[HttpJson] = None, mailto: str = "research@axiovexsystems.com") -> None:
        self.http = http or HttpJson()
        self.mailto = mailto

    def _params(self, extra: dict) -> str:
        return urllib.parse.urlencode({**extra, "mailto": self.mailto})

    def search(self, query: str, *, limit: int = 10) -> list[RetrievedItem]:
        url = f"{self.BASE}/works?{self._params({'query.bibliographic': query, 'rows': limit})}"
        data = self.http.get(url)
        return [self._item(w) for w in data.get("message", {}).get("items", [])]

    def resolve(self, doi: str) -> Optional[RetrievedItem]:
        url = f"{self.BASE}/works/{urllib.parse.quote(doi, safe='')}?{self._params({})}"
        try:
            data = self.http.get(url)
        except Exception:
            return None
        return self._item(data.get("message", {}))

    @staticmethod
    def _item(w: dict) -> RetrievedItem:
        licenses = w.get("license") or []
        license_basis = licenses[0].get("URL", "") if licenses else "crossref-metadata (no licence asserted)"
        abstract = w.get("abstract")
        if abstract and not licenses:
            # Abstracts in Crossref are not CC0; without an asserted
            # licence the abstract is metadata we may not reuse.
            abstract = None
        authors = [
            " ".join(p for p in [a.get("given", ""), a.get("family", "")] if p).strip()
            for a in w.get("author", [])
        ]
        year = None
        for key in ("issued", "published", "created"):
            parts = (w.get(key) or {}).get("date-parts") or []
            if parts and parts[0]:
                year = parts[0][0]
                break
        return RetrievedItem(
            source="crossref",
            source_id=w.get("DOI", ""),
            title=(w.get("title") or [""])[0],
            authors=authors,
            year=year,
            venue=(w.get("container-title") or [None])[0],
            abstract=abstract,
            license_basis=license_basis,
            hosted_ok=not _nc_flag(license_basis),
        )


# ------------------------------------------------------------------ openalex

class OpenAlexConnector:
    """OpenAlex with key auth + credit budget (WS1 registry, 2026 rules)."""

    name = "openalex"
    BASE = "https://api.openalex.org"

    def __init__(self, http: Optional[HttpJson] = None, api_key: Optional[str] = None,
                 budget: Optional[CreditBudget] = None) -> None:
        self.http = http or HttpJson()
        self.api_key = api_key or os.environ.get("OPENALEX_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAlex requires a free API key since 2026-02-13: "
                "set OPENALEX_API_KEY (owner account, openalex.org)"
            )
        self.budget = budget or CreditBudget(limit=1000)

    def _get(self, path: str, kind: str) -> dict:
        cost = self.budget.reserve(kind)
        sep = "&" if "?" in path else "?"
        data = self.http.get(f"{self.BASE}{path}{sep}api_key={self.api_key}")
        self.budget.settle(cost)
        return data

    def search(self, query: str, *, limit: int = 10) -> list[RetrievedItem]:
        # Prefer the ~10x cheaper filter path over /works?search=.
        q = urllib.parse.quote(query)
        data = self._get(f"/works?filter=title_and_abstract.search:{q}&per-page={limit}", "filter")
        return [self._item(w) for w in data.get("results", [])]

    def resolve(self, openalex_id: str) -> Optional[RetrievedItem]:
        # Accepts a W-id, an OpenAlex URL, or a DOI (bare or doi.org URL):
        # OpenAlex resolves DOIs at /works/doi:<doi> — a plain suffix is
        # not enough (caught in live verification, 2026-10-11).
        raw = openalex_id.strip()
        if "doi.org/" in raw:
            raw = raw.split("doi.org/", 1)[-1]
        if raw.startswith("10.") and "/" in raw:
            path = f"/works/doi:{urllib.parse.quote(raw, safe='/')}"
        else:
            path = f"/works/{raw.rsplit('/', 1)[-1]}"
        try:
            data = self._get(path, "get")
        except Exception:
            return None
        return self._item(data)

    @staticmethod
    def _item(w: dict) -> RetrievedItem:
        license_basis = w.get("license") or (
            ((w.get("primary_location") or {}).get("source") or {}).get("license")
            or "openalex-metadata (no licence asserted)"
        )
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in w.get("authorships", [])
        ]
        abstract = None
        inv = w.get("abstract_inverted_index")
        if inv:
            words = sorted(
                ((pos, word) for word, positions in inv.items() for pos in positions)
            )
            abstract = " ".join(word for _, word in words)
        return RetrievedItem(
            source="openalex",
            source_id=w.get("doi") or w.get("id", ""),
            title=w.get("title") or w.get("display_name") or "",
            authors=[a for a in authors if a],
            year=w.get("publication_year"),
            venue=(((w.get("primary_location") or {}).get("source") or {}).get("display_name")),
            abstract=abstract,
            license_basis=license_basis,
            hosted_ok=not _nc_flag(license_basis),
        )


# ------------------------------------------------------------------ query log

def run_query(store: Any, connector: Any, query: str, *, actor: str, limit: int = 10) -> list[RetrievedItem]:
    """T206: the query itself enters the study ledger before results are
    used, so what was asked, of whom, and when is part of the record."""
    items = connector.search(query, limit=limit)
    store.log_query(connector.name, {"query": query, "limit": limit, "results": len(items)}, actor=actor)
    return items
