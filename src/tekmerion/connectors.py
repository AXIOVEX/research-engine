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


class ConnectorError(RuntimeError):
    """A connector failure that is NOT 'no record': auth (401/403),
    rate limit (429), server error (5xx), a transport failure, or a
    malformed response. Raised, never swallowed into a None or an
    empty result, identically on the search and resolve routes of
    every connector, so the pipeline records an `error` outcome —
    an outage must not read as a nonexistent work (Spec 013,
    CLM-013-37 / CLM-013-45; CORE's Spec 012 contract, CLM-012-04,
    is the reference implementation)."""


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
    #: Retraction state asserted by the source of record (Spec 013,
    #: CLM-013-36): None, or the most severe state the source asserts
    #: — "retracted", "expression_of_concern", "corrected". Any state
    #: quarantines the citation in the pipeline; weighing the state
    #: is the adjudicator's act, not the parser's.
    retraction: Optional[str] = None
    #: Why this record is degraded, when the connector knows the
    #: reason is something other than absence (Spec 013,
    #: CLM-013-43): e.g. "output-cap-reached" when CORE's output
    #: fetch cap stopped the search for licensed content early.
    degradation_reason: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source, "source_id": self.source_id, "title": self.title,
            "authors": self.authors, "year": self.year, "venue": self.venue,
            "abstract": self.abstract, "license_basis": self.license_basis,
            "hosted_ok": self.hosted_ok, "retraction": self.retraction,
            "degradation_reason": self.degradation_reason,
        }


def _nc_flag(license_basis: str) -> bool:
    """Non-commercial-only licences exclude an item from the hosted
    deployment shape (rights are recorded per deployment shape, RT2-1)."""
    lb = license_basis.lower()
    return "-nc" in lb or "noncommercial" in lb or "non-commercial" in lb


_DOI_PREFIXES = (
    "https://doi.org/", "http://doi.org/",
    "https://dx.doi.org/", "http://dx.doi.org/",
    "doi.org/", "doi:",
)
#: Characters a reference list or a sentence appends to a DOI: the
#: bare form resolves, these forms must resolve identically.
_DOI_TRAILING_PUNCT = ".,;:!?"


def normalize_doi(raw: Optional[str]) -> str:
    """The one shared DOI normalizer (Spec 013, CLM-013-42; the same
    normalizer CLM-013-14 applies at citation intake). Handles
    surrounding whitespace, `doi:` / `doi.org/` prefixes, case (DOIs
    are case-insensitive), and trailing punctuation a citing context
    adds. Every connector and every pipeline path — resolution,
    grouping, falsifier matching, enrichment — normalizes through
    here; no connector keeps a private form. Returns "" for no DOI."""
    text = (raw or "").strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.strip()
    while text and text[-1] in _DOI_TRAILING_PUNCT:
        text = text[:-1]
    return text.strip().lower()


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

#: Crossref `updated-by` entry types that assert an integrity state
#: on the record, mapped to the model's retraction states (most
#: severe first when several are asserted). Update types that assert
#: no integrity state (new edition, new version) are not listed.
_CROSSREF_UPDATE_STATES = {
    "retraction": "retracted",
    "partial_retraction": "retracted",
    "withdrawal": "retracted",
    "removal": "retracted",
    "expression_of_concern": "expression_of_concern",
    "correction": "corrected",
    "corrigendum": "corrected",
    "erratum": "corrected",
    "clarification": "corrected",
    "addendum": "corrected",
}
_RETRACTION_SEVERITY = {"corrected": 1, "expression_of_concern": 2, "retracted": 3}


def _crossref_retraction(w: dict) -> Optional[str]:
    """The most severe integrity state Crossref asserts for this
    record via `updated-by` (Spec 013, CLM-013-36), or None."""
    best: Optional[str] = None
    for entry in w.get("updated-by") or []:
        kind = str(entry.get("type") or "").strip().lower()
        kind = kind.replace("-", "_").replace(" ", "_")
        state = _CROSSREF_UPDATE_STATES.get(kind)
        if state and (best is None
                      or _RETRACTION_SEVERITY[state] > _RETRACTION_SEVERITY[best]):
            best = state
    return best


def _licence_start(entry: dict):
    """A Crossref licence entry's start moment, from its `start`
    block (`date-time` preferred, `date-parts` otherwise)."""
    from datetime import datetime, timezone

    start = entry.get("start") or {}
    stamp = start.get("date-time")
    if stamp:
        try:
            return datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except ValueError:
            pass
    parts = (start.get("date-parts") or [[]])[0]
    if parts and parts[0]:
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return datetime(parts[0], month, day, tzinfo=timezone.utc)
    return None


def _crossref_content_licence(licenses: list, *, now=None) -> Optional[str]:
    """The licence URL that actually licenses content use, or None
    (Spec 013, CLM-013-39). Entries are qualified: a text-and-data-
    mining licence (`content-version: tdm`) is not a content licence,
    and an entry whose start plus delay has not yet arrived does not
    permit the use yet. The first qualifying entry wins."""
    from datetime import datetime, timedelta, timezone

    now = now or datetime.now(timezone.utc)
    for entry in licenses:
        if str(entry.get("content-version") or "").strip().lower() == "tdm":
            continue
        url = str(entry.get("URL") or "").strip()
        if not url:
            continue
        start = _licence_start(entry)
        if start is not None:
            delay = entry.get("delay-in-days") or 0
            if now < start + timedelta(days=delay):
                continue
        return url
    return None


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

    def _fetch(self, url: str) -> Optional[dict]:
        """One fetch under the shared error contract (Spec 013,
        CLM-013-37/45 — CORE's discipline): the parsed body, or None
        on a genuine 404; 429/5xx and transport failures raise
        ConnectorError, on the search route exactly as on resolve."""
        try:
            return self.http.get(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise ConnectorError(f"crossref: HTTP {exc.code}") from exc
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(f"crossref: transport failure: {exc}") from exc

    def search(self, query: str, *, limit: int = 10) -> list[RetrievedItem]:
        url = f"{self.BASE}/works?{self._params({'query.bibliographic': query, 'rows': limit})}"
        data = self._fetch(url)
        if data is None:
            return []
        return [self._item(w) for w in data.get("message", {}).get("items", [])]

    def resolve(self, doi: str) -> Optional[RetrievedItem]:
        url = (f"{self.BASE}/works/{urllib.parse.quote(normalize_doi(doi), safe='')}"
               f"?{self._params({})}")
        data = self._fetch(url)
        if data is None:
            return None
        return self._item(data.get("message", {}))

    @staticmethod
    def _item(w: dict) -> RetrievedItem:
        licenses = w.get("license") or []
        content_licence = _crossref_content_licence(licenses)
        # The basis names the licence content use rests on when one
        # qualifies; otherwise the first asserted licence stands as
        # provenance (e.g. a TDM licence — asserted, but it licenses
        # no content use, and the redistribution gate refuses it).
        asserted = licenses[0].get("URL", "") if licenses else ""
        license_basis = (content_licence or asserted
                         or "crossref-metadata (no licence asserted)")
        abstract = w.get("abstract")
        if abstract and not content_licence:
            # Abstracts in Crossref are not CC0; without a licence
            # that qualifies for content use the abstract is
            # metadata we may not reuse.
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
            retraction=_crossref_retraction(w),
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

    def _get(self, path: str, kind: str) -> Optional[dict]:
        """One budgeted call under the shared error contract (Spec
        013, CLM-013-37/45 — CORE's discipline): the parsed body, or
        None on a genuine 404. The budget settles whenever OpenAlex
        answered (any HTTP status); 429/5xx raise ConnectorError,
        a transport failure raises it too, and budget exhaustion
        raises BudgetExhausted before any call — none of these is
        ever a silent None."""
        cost = self.budget.reserve(kind)
        sep = "&" if "?" in path else "?"
        try:
            data = self.http.get(f"{self.BASE}{path}{sep}api_key={self.api_key}")
        except urllib.error.HTTPError as exc:
            self.budget.settle(cost)
            if exc.code == 404:
                return None
            raise ConnectorError(f"openalex: HTTP {exc.code}") from exc
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(f"openalex: transport failure: {exc}") from exc
        self.budget.settle(cost)
        return data

    def search(self, query: str, *, limit: int = 10) -> list[RetrievedItem]:
        # Prefer the ~10x cheaper filter path over /works?search=.
        q = urllib.parse.quote(query)
        data = self._get(f"/works?filter=title_and_abstract.search:{q}&per-page={limit}", "filter")
        if data is None:
            return []
        return [self._item(w) for w in data.get("results", [])]

    def resolve(self, openalex_id: str) -> Optional[RetrievedItem]:
        # Accepts a W-id, an OpenAlex URL, or a DOI in any surface
        # form: the shared normalizer (CLM-013-42) reduces DOI forms
        # first — OpenAlex resolves DOIs at /works/doi:<doi>, and a
        # doi:-prefixed or trailing-period form must reach the same
        # route the bare form reaches.
        doi = normalize_doi(openalex_id)
        if doi.startswith("10.") and "/" in doi:
            path = f"/works/doi:{urllib.parse.quote(doi, safe='/')}"
        else:
            raw = (openalex_id or "").strip()
            path = f"/works/{raw.rsplit('/', 1)[-1]}"
        data = self._get(path, "get")
        if data is None:
            return None
        return self._item(data)

    @staticmethod
    def _item(w: dict) -> RetrievedItem:
        asserted_licence = w.get("license") or (
            ((w.get("primary_location") or {}).get("source") or {}).get("license"))
        license_basis = asserted_licence or "openalex-metadata (no licence asserted)"
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
        if abstract and not asserted_licence:
            # The no-licence-no-content rule Crossref and CORE
            # already enforce applies here too (Spec 013,
            # CLM-013-38): unlicensed content mints no mass.
            abstract = None
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
            retraction="retracted" if w.get("is_retracted") else None,
        )


# ------------------------------------------------------------------ core

class CoreApiError(ConnectorError):
    """A CORE failure that is NOT 'no record': auth (401/403), rate
    limit (429), server error (5xx), or a transport failure. Raised,
    never swallowed into a None, so the pipeline records an `error`
    outcome — an outage must not read as a nonexistent work
    (Spec 012, CLM-012-04). The reference implementation of the
    shared ConnectorError contract (Spec 013, CLM-013-37)."""


def _core_author_name(name: Any) -> str:
    """CORE serves author names inverted ("Schuch, Felipe Barreto")
    and polluted ("Stubbs, Brendon; id_orcid"). The junk suffix
    after a semicolon is dropped and the name is normalized to
    natural order at the connector — the same person, the readable
    form (Spec 013, CLM-013-44)."""
    text = " ".join(str(name or "").split(";", 1)[0].split())
    if "," in text:
        family, given = text.split(",", 1)
        return f"{given.strip()} {family.strip()}".strip()
    return text


def _core_authors(names: Any, *, drop_ghosts: bool = False) -> list[str]:
    """A CORE author list, cleaned and deduplicated at ingestion
    (Spec 013, CLM-013-44). CORE's work-level list aggregates the
    author lists of every deposit, so one person arrives in several
    forms ("Schuch, Felipe Barreto", "Felipe B. Schuch", "Schuch,
    Felipe"): entries are keyed by (surname, first given name) and
    the most complete form is kept. With `drop_ghosts` (the
    work-level aggregate only), a singleton entry whose given name
    belongs to one kept author and whose surname belongs to another
    — "Felipe Ward", recombined from Felipe Schuch and Philip B.
    Ward — is a recombination ghost of the aggregation, not a
    person, and is dropped. A single deposit's own list
    (`drop_ghosts=False`) is only cleaned and deduplicated."""
    cleaned = [c for c in (_core_author_name(n) for n in names or []) if c]
    counts: dict[str, int] = {}
    for name in cleaned:
        counts[name] = counts.get(name, 0) + 1
    best: dict[tuple[str, str], str] = {}
    order: list[tuple[str, str]] = []
    for name in cleaned:
        toks = name.split()
        key = (toks[-1].lower(), toks[0].lower())
        if key not in best:
            best[key] = name
            order.append(key)
        elif len(name) > len(best[key]):
            best[key] = name
    kept = [best[k] for k in order]
    if drop_ghosts and len(kept) > 2:
        pairs = [(n.split()[0].lower(), n.split()[-1].lower()) for n in kept]
        result = []
        for i, name in enumerate(kept):
            given, surname = pairs[i]
            ghost = (
                counts.get(name, 0) == 1
                and any(j != i and pairs[j][0] == given and pairs[j][1] != surname
                        for j in range(len(kept)))
                and any(j != i and pairs[j][1] == surname and pairs[j][0] != given
                        for j in range(len(kept)))
            )
            if not ghost:
                result.append(name)
        kept = result
    return kept


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
        # The shared normalizer (CLM-013-42) reduces every DOI
        # surface form before the search, and the work match compares
        # normalized forms on both sides.
        raw = normalize_doi(doi)
        q = urllib.parse.quote(f'doi:"{raw}"')
        data = self._call(f"{self.BASE}/search/works/?q={q}&limit=5", "get")
        if not data:
            return None
        work = None
        for w in data.get("results", []):
            if normalize_doi(w.get("doi")) == raw:
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
        outputs = work.get("outputs") or []
        fetched = 0
        for url in outputs:
            if fetched >= self.MAX_OUTPUT_FETCHES:
                # The cap stopped the search with deposits still
                # unexamined: the record states the true reason, so
                # "output cap reached" is distinguishable from "no
                # licensed deposit exists" (Spec 013, CLM-013-43).
                item.degradation_reason = "output-cap-reached"
                break
            fetched += 1
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
            authors=_core_authors(
                [a.get("name") for a in w.get("authors", [])
                 if isinstance(a, dict)],
                drop_ghosts=True),
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
        authors = _core_authors(
            [a.get("name") for a in out.get("authors", [])
             if isinstance(a, dict)])
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
    """T206: the query itself enters the study ledger before the call
    executes (Spec 013, CLM-013-45), so what was asked, of whom, and
    when is part of the record — including when the call raises: a
    failed search still leaves its connector.query event. The result
    count is not in the event, because the event precedes the call;
    outcomes live in the citation.checked records."""
    store.log_query(connector.name, {"query": query, "limit": limit}, actor=actor)
    return connector.search(query, limit=limit)
