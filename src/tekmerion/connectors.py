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
- CORE (Spec 012) is the WS1 full-text content channel: discovery is
  the Work, the licence + content unit is the Output (one per
  repository deposit), and a record asserting no licence yields no
  content — the same rule as Crossref's, applied per deposit.
- Sources without a verified public API (tDAR, ADS) or with
  non-commercial framing (BASE) are NOT connectors here (WS1 registry).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

USER_AGENT = "Tekmerion/0.1 (Axiovex Systems; https://axiovexsystems.com)"


@dataclass
class RetrievedItem:
    source: str            # "crossref" | "openalex" | "core"
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


# ------------------------------------------------------------------ core

class CoreApiError(RuntimeError):
    """A CORE failure that is NOT 'no record': auth (401/403), rate
    limit (429), server error (5xx), or a transport failure. Raised,
    never swallowed into a None, so the pipeline records an `error`
    outcome — an outage must not read as a nonexistent work
    (Spec 012, CLM-012-04)."""


def _core_author_name(name: Any) -> str:
    """CORE serves author names inverted ("Schuch, Felipe Barreto").
    Stage 2 matches on surnames, so names are normalized to natural
    order at the connector — the same person, the readable form."""
    text = str(name or "").strip()
    if "," in text:
        family, given = text.split(",", 1)
        return f"{given.strip()} {family.strip()}".strip()
    return text


def _core_year(value: Any, fallback: Any = None) -> Optional[int]:
    for raw in (value, fallback):
        if raw is None:
            continue
        text = str(raw).strip()
        digits = text[:4]
        if digits.isdigit():
            return int(digits)
    return None


def _core_venue(record: dict) -> Optional[str]:
    """Venue means the journal/container title — the pipeline's
    stage 2 compares it against the cited venue. CORE deposits often
    carry only a publisher ("Pergamon Press" for the Journal of
    Psychiatric Research); a publisher is not a venue, and claiming
    it as one would manufacture a venue disagreement against the
    very records CORE exists to enrich (observed live, 2026-10-12).
    No journal on the record -> no venue, and stage 2 does not
    judge an absent field."""
    for j in record.get("journals") or []:
        title = j.get("title") if isinstance(j, dict) else j
        if title:
            return str(title)
    return None


def _licence_permits_content(value: str) -> bool:
    """Does this asserted licence value actually license content use?

    CORE's deposit-level licence field is messy: alongside real
    licence URLs it carries restriction markers — 'intranet' was
    observed live on a Schuch deposit whose abstract it would have
    unlocked (Spec 012 smoke, 2026-10-12). A marker is not a licence.
    Content is usable only when the value is a recognizable licence
    instrument: a licence URL, a rights-statement URL, or a known
    licence identifier. Anything else — empty, a restriction marker,
    or an unrecognized string — does NOT unlock content; the basis is
    still recorded verbatim, so the degradation stays visible."""
    text = (value or "").strip()
    if not text:
        return False
    low = text.lower()
    if low in ("intranet", "restricted", "closed", "embargoed",
               "unknown", "none", "n/a", "all rights reserved"):
        return False
    if low.startswith(("http://", "https://")):
        return ("licen" in low or "rightsstatements" in low
                or "legalcode" in low or "publicdomain" in low)
    return low in {
        "cc0", "cc0-1.0", "pddl-1.0", "odc-by-1.0",
        "cc-by", "cc-by-3.0", "cc-by-4.0", "cc-by-sa-4.0",
        "cc-by-nc-4.0", "cc-by-nd-4.0", "cc-by-nc-sa-4.0",
        "cc-by-nc-nd-4.0", "public domain", "mit", "apache-2.0",
        "bsd-3-clause", "gpl-3.0",
    }


class CoreConnector:
    """CORE API v3 — the WS1 full-text content channel (Spec 012).

    Shape of the source, established by live probe (2026-10-12):
    there is no /works/doi: route (resolution by DOI is a search,
    `q=doi:"…"`); the Work carries metadata and sometimes an abstract
    but no licence; each Output (one per repository deposit) carries
    the licence, its own abstract, and the full text. So the item is
    built from the first output — in the work's listed order, at most
    MAX_OUTPUT_FETCHES — that asserts a licence permitting content
    use and carries content;
    if none qualifies, the item is the work's metadata with content
    dropped and the basis saying so (CLM-012-03).

    Auth is a Bearer key; v3 withholds full text from keyless
    callers, so the connector refuses to construct without one,
    exactly as OpenAlexConnector does. CORE publishes no per-call
    dollar price (free registered key, token-metered tiers), so spend
    is accounted in budget units and calls only (CLM-012-05)."""

    name = "core"
    BASE = "https://api.core.ac.uk/v3"
    MAX_OUTPUT_FETCHES = 3
    NO_LICENCE_BASIS = "core-aggregated (no per-work licence asserted)"
    FULLTEXT_PLACEHOLDER = "Not available for public API users."

    def __init__(self, http: Optional[HttpJson] = None, api_key: Optional[str] = None,
                 budget: Optional[CreditBudget] = None) -> None:
        self.http = http or HttpJson()
        self.api_key = api_key or os.environ.get("CORE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "CORE requires a free registered API key (API v3 withholds "
                "full text from keyless callers): set CORE_API_KEY "
                "(owner account, core.ac.uk)"
            )
        self.budget = budget or CreditBudget(limit=1000)

    # -- transport with status translation (CLM-012-04) --

    def _call(self, url: str, kind: str) -> Optional[dict]:
        """One budgeted call. Returns the parsed body, or None when
        CORE answered 404 (no such route/record — the caller decides
        what absence means). The budget settles whenever CORE answered
        (any HTTP status — the call counts against the token tier);
        auth/rate/server failures raise CoreApiError, and a transport
        failure (no answer, nothing settles) raises it too."""
        cost = self.budget.reserve(kind)
        try:
            data = self.http.get(
                url, headers={"Authorization": f"Bearer {self.api_key}"})
        except urllib.error.HTTPError as exc:
            self.budget.settle(cost)
            if exc.code == 404:
                return None
            raise CoreApiError(
                f"core: HTTP {exc.code} from api.core.ac.uk") from exc
        except Exception as exc:
            raise CoreApiError(f"core: transport failure: {exc}") from exc
        self.budget.settle(cost)
        return data

    # -- interface --

    def search(self, query: str, *, limit: int = 10) -> list[RetrievedItem]:
        q = urllib.parse.quote(query)
        data = self._call(f"{self.BASE}/search/works/?q={q}&limit={limit}", "search")
        if not data:
            return []
        return [self._work_item(w) for w in data.get("results", [])]

    def resolve(self, doi: str) -> Optional[RetrievedItem]:
        raw = doi.strip()
        if "doi.org/" in raw:
            raw = raw.split("doi.org/", 1)[-1]
        if raw.lower().startswith("doi:"):
            raw = raw[4:].strip()
        q = urllib.parse.quote(f'doi:"{raw}"')
        data = self._call(f"{self.BASE}/search/works/?q={q}&limit=5", "get")
        if not data:
            return None
        work = None
        for w in data.get("results", []):
            if (w.get("doi") or "").strip().lower() == raw.lower():
                work = w
                break
        if work is None:
            return None
        return self._resolve_work(work)

    # -- record construction --

    def _resolve_work(self, work: dict) -> RetrievedItem:
        item = self._work_item(work)
        if item.abstract:
            return item
        for url in (work.get("outputs") or [])[: self.MAX_OUTPUT_FETCHES]:
            try:
                out = self._call(url, "get")
            except CoreApiError:
                # A found work whose deposits cannot be consulted is a
                # degraded resolve, not a failed one: the metadata
                # record stands. (The search step's own failure raises
                # in _call before we ever get here.)
                break
            if not out:
                continue  # a 404 deposit is skipped, never fatal
            candidate = self._output_item(out, work)
            if candidate is not None:
                return candidate
        return item

    @staticmethod
    def _content(record: dict, license_basis: str) -> Optional[str]:
        """The record's usable content: abstract preferred, full text
        otherwise — and only when the record's asserted licence is a
        recognizable licence instrument (see _licence_permits_content).
        The keyless-placeholder string is not content."""
        if not _licence_permits_content(license_basis):
            return None
        abstract = (record.get("abstract") or "").strip()
        if abstract:
            return abstract
        full = (record.get("fullText") or "").strip()
        if full and full != CoreConnector.FULLTEXT_PLACEHOLDER:
            return full
        return None

    @staticmethod
    def _work_item(w: dict) -> RetrievedItem:
        license_basis = (w.get("license") or "").strip()
        return RetrievedItem(
            source="core",
            source_id=w.get("doi") or str(w.get("id", "")),
            title=w.get("title") or "",
            authors=[a for a in
                     (_core_author_name(a.get("name")) for a in w.get("authors", [])
                      if isinstance(a, dict)) if a],
            year=_core_year(w.get("yearPublished")),
            venue=_core_venue(w),
            abstract=CoreConnector._content(w, license_basis),
            license_basis=license_basis or CoreConnector.NO_LICENCE_BASIS,
            hosted_ok=not _nc_flag(license_basis),
        )

    @staticmethod
    def _output_item(out: dict, work: dict) -> Optional[RetrievedItem]:
        """An item built from one deposit, or None when the deposit
        does not qualify (asserts no licence, or carries no content)."""
        license_basis = (out.get("license") or "").strip()
        content = CoreConnector._content(out, license_basis)
        if not license_basis or content is None:
            return None
        authors = [a for a in
                   (_core_author_name(a.get("name")) for a in out.get("authors", [])
                    if isinstance(a, dict)) if a]
        if not authors:
            authors = CoreConnector._work_item(work).authors
        return RetrievedItem(
            source="core",
            source_id=out.get("doi") or work.get("doi") or str(out.get("id", "")),
            title=out.get("title") or work.get("title") or "",
            authors=authors,
            year=_core_year(out.get("yearPublished"), out.get("publishedDate"))
                 or _core_year(work.get("yearPublished")),
            venue=_core_venue(out) or _core_venue(work),
            abstract=content,
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
