"""Verification service (Spec 002 Phase 4; WS5 §1, WS2 §2; RT-4, RT-5).

Fabricated references are the signature failure of AI research tools,
so citation verification is a pipeline, not a prompt (WS5 §1). Three
stages, mapping one-to-one onto the three ways a citation can lie:

1. **Resolution** — the citation resolves against a source of record
   (DOI via a connector; no DOI, a source-native record matched on
   title + authors + venue + year). Every citation receives exactly
   one explicit outcome — resolved / not_found / error — and every
   outcome is appended to the study ledger as a `citation.checked`
   event. That accounting is K1 at pipeline level: nothing is
   silently skipped, including transport failures.
2. **Agreement** — the fields the study relies on (title, authorship,
   year, venue) are compared between the citing context and the
   resolved record. A material mismatch quarantines the citation: it
   enters the adjudication queue and contributes no evidence until an
   adjudicator resolves it (WS5 §1.2, §3).
3. **Content check** — where the claim attributes a finding to the
   source, stance extraction runs on the *retrieved* content (the
   licence-permitted abstract the connectors hand back), never on a
   model's memory of the paper. No retrievable content → the citation
   is `metadata_only`: context only, no support mass (RT-5, enforced
   in `claims.group_masses` / `verdicts.evaluate_claim`).

Citations are folded to origin groups by the WS2 §2 precedence keys;
key 4 (near-duplicate fingerprint) is flagged for human adjudication,
never auto-merged. Grouping adjudications are sampled for independent
second review at a registered fraction (default 10%, RT-4), by a
deterministic seeded draw; a reviewed window with zero disagreements
is flagged as an anomaly, not celebrated.

The stance checker is a seam: extractors carry an identity (WS2), and
the Phase 4 baseline is a deterministic lexical checker. A model-based
extractor plugs in by satisfying the same two-member protocol
(`name`, `check(proposition, content) -> stance`).
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .claims import EvidenceItem
from .connectors import RetrievedItem

RESOLVED = "resolved"
NOT_FOUND = "not_found"
ERROR = "error"

AGREE = "agree"
DISAGREE = "disagree"

SUPPORTS = "supports"
CONTRADICTS = "contradicts"
CONTEXTUAL = "contextual"
METADATA_ONLY = "metadata_only"

#: Adjudication decisions. `exclude` drops the item from the evidence
#: basis; `variant` rules a metadata mismatch a legitimate variant so
#: the item stands; `same_origin` / `separate_origin` settle grouping
#: disputes (WS5 §3 defaults: exclusion for quarantine, one origin for
#: grouping until decided — assignment here stays explicit either way).
DECISIONS = ("exclude", "variant", "same_origin", "separate_origin")

DEFAULT_SECOND_REVIEW_FRACTION = 0.10  # RT-4 registered default
DEFAULT_ANOMALY_MIN_REVIEWS = 5        # window below this cannot acquit a queue


# ------------------------------------------------------------------ inputs

@dataclass
class Citation:
    """What a study cites, as the citing context states it. Stage 2
    exists because these fields can be wrong about a real paper."""
    citation_id: str
    claim_id: str
    proposition: str                       # the finding attributed to the source
    doi: Optional[str] = None
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    dataset_id: Optional[str] = None      # WS2 grouping key 2 (dataset / registration)
    derived_from: Optional[str] = None    # WS2 grouping key 3 (citation_id this derives from)

    def as_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id, "claim_id": self.claim_id,
            "proposition": self.proposition, "doi": self.doi, "title": self.title,
            "authors": list(self.authors), "year": self.year, "venue": self.venue,
            "dataset_id": self.dataset_id, "derived_from": self.derived_from,
        }


@dataclass
class CitationResult:
    citation_id: str
    claim_id: str
    resolution: str                        # resolved | not_found | error
    agreement: Optional[str] = None        # agree | disagree (resolved only)
    mismatches: list[str] = field(default_factory=list)
    content: Optional[str] = None          # supports | contradicts | contextual | metadata_only
    origin_group: str = ""
    extractor: str = ""
    source: Optional[str] = None           # connector that resolved it
    source_id: Optional[str] = None        # retrieved record's native id
    detail: str = ""                       # error text / notes
    retrieved: Optional[RetrievedItem] = field(default=None, repr=False)

    @property
    def quarantined(self) -> bool:
        """Quarantined items contribute no evidence until adjudicated:
        unresolved (not_found / error) or materially disagreeing."""
        return self.resolution != RESOLVED or self.agreement == DISAGREE

    def as_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id, "claim_id": self.claim_id,
            "resolution": self.resolution, "agreement": self.agreement,
            "mismatches": list(self.mismatches), "content": self.content,
            "origin_group": self.origin_group, "extractor": self.extractor,
            "source": self.source, "source_id": self.source_id, "detail": self.detail,
        }


# ------------------------------------------------------------------ stage 3 seam

_STOPWORDS = {"the", "a", "an", "of", "in", "on", "for", "and", "or", "to",
              "with", "by", "is", "are", "was", "were", "be", "been", "that",
              "this", "it", "its", "at", "from", "as"}
_NEGATIONS = {"not", "no", "never", "none", "without", "failed", "fails", "fail"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", (text or "").lower())


def _key(token: str) -> str:
    """Crude stem: shared 5-character prefix (improve/improvement)."""
    return token[:5] if len(token) > 5 else token


class KeywordStanceChecker:
    """Deterministic lexical stance baseline. A sentence of the content
    supports the proposition when it carries most of the proposition's
    key terms; the same sentence carrying a negation contradicts it;
    anything else is contextual. Crude by design — its value is that
    it is inspectable, reproducible, and honestly labeled; model-based
    extraction replaces it at this seam, with its identity recorded."""

    name = "tekmerion.keyword-stance/1"

    def check(self, proposition: str, content: str) -> str:
        prop_keys = {_key(t) for t in _tokens(proposition)
                     if t not in _STOPWORDS and len(t) >= 3}
        if not prop_keys or not content:
            return CONTEXTUAL
        need = math.ceil(0.6 * len(prop_keys))
        hit = False
        negated = False
        for sentence in re.split(r"[.!?]", content):
            toks = _tokens(sentence)
            keys = {_key(t) for t in toks}
            if len(prop_keys & keys) >= need:
                hit = True
                if _NEGATIONS & set(toks):
                    negated = True
        if not hit:
            return CONTEXTUAL
        return CONTRADICTS if negated else SUPPORTS


# ------------------------------------------------------------------ stage 2

def _norm(text: str) -> str:
    return " ".join(_tokens(text or ""))


def _surname(author: str) -> str:
    parts = _tokens(author)
    return parts[-1] if parts else ""


def _text_match(cited: str, retrieved: str) -> bool:
    a, b = set(_tokens(cited)), set(_tokens(retrieved))
    if not a or not b:
        return False
    jaccard = len(a & b) / len(a | b)
    return jaccard >= 0.6 or _norm(cited) in _norm(retrieved) or _norm(retrieved) in _norm(cited)


def check_agreement(citation: Citation, item: RetrievedItem) -> tuple[str, list[str]]:
    """Compare the fields the study relies on. Only fields present on
    both sides are judged; absence is a coverage fact, not a mismatch."""
    mismatches: list[str] = []
    if citation.title and item.title and not _text_match(citation.title, item.title):
        mismatches.append("title")
    if citation.authors and item.authors:
        cited = {_surname(a) for a in citation.authors}
        got = {_surname(a) for a in item.authors}
        if not (cited & got):
            mismatches.append("authors")
    if citation.year and item.year and citation.year != item.year:
        mismatches.append("year")
    if citation.venue and item.venue and not _text_match(citation.venue, item.venue):
        mismatches.append("venue")
    return (DISAGREE if mismatches else AGREE), mismatches


# ------------------------------------------------------------------ stage 1

def _resolve(citation: Citation, connectors: list) -> tuple[Optional[RetrievedItem], str, str]:
    """Resolve against a source of record. Returns (item, outcome,
    detail); an exception from every attempted route is an explicit
    `error` outcome, never a silent skip."""
    last_error = ""
    if citation.doi:
        for conn in connectors:
            try:
                item = conn.resolve(citation.doi)
            except Exception as exc:  # transport/parse failure = explicit outcome
                last_error = f"{getattr(conn, 'name', 'connector')}: {exc}"
                continue
            if item is not None:
                return item, RESOLVED, ""
        return None, (ERROR if last_error else NOT_FOUND), last_error
    # No DOI: source-native record matched on title + authors + venue +
    # year (WS5 §1.1) — the first agreeing candidate resolves; if the
    # source answers but nothing agrees, the best candidate is carried
    # forward and stage 2 renders the disagreement explicitly.
    best: Optional[RetrievedItem] = None
    for conn in connectors:
        try:
            candidates = conn.search(citation.title)
        except Exception as exc:
            last_error = f"{getattr(conn, 'name', 'connector')}: {exc}"
            continue
        for cand in candidates:
            if best is None:
                best = cand
            if check_agreement(citation, cand)[0] == AGREE:
                return cand, RESOLVED, ""
    if best is not None:
        return best, RESOLVED, ""
    return None, (ERROR if last_error else NOT_FOUND), last_error


# ------------------------------------------------------------------ grouping (WS2 §2)

def _norm_doi(doi: Optional[str]) -> str:
    raw = (doi or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    return raw


def assign_origin_groups(
    citations: list[Citation],
    results: list[CitationResult],
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Fold citations to origin groups by the WS2 keys, applied as
    pairwise equivalence in precedence order: 1. same DOI /
    source-native ID, 2. same dataset or registration ID (two papers
    from one dataset are one origin for data claims — the WS2 §2 hard
    case; a citation carries `dataset_id` when its claim's registration
    records the dataset as the origin), 3. explicit derivation link.
    Key 4 (near-duplicate title + authorship fingerprint) never merges:
    it returns suspect pairs for human adjudication. Group IDs are
    assigned deterministically in first-appearance order."""
    res_by_id = {r.citation_id: r for r in results}
    parent = {c.citation_id: c.citation_id for c in citations}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def union_by(key_of) -> None:
        seen: dict[tuple[str, str], str] = {}
        for c in citations:
            key = key_of(c)
            if key is None:
                continue
            if key in seen:
                union(seen[key], c.citation_id)
            else:
                seen[key] = c.citation_id

    def doi_key(c: Citation) -> Optional[tuple[str, str]]:
        r = res_by_id.get(c.citation_id)
        doi = _norm_doi(c.doi) or _norm_doi(r.source_id if r else None)
        return ("doi", doi) if doi else None

    def dataset_key(c: Citation) -> Optional[tuple[str, str]]:
        return ("dataset", c.dataset_id.strip().lower()) if c.dataset_id else None

    union_by(doi_key)       # key 1
    union_by(dataset_key)   # key 2
    for c in citations:     # key 3: derivation links
        if c.derived_from and c.derived_from in parent:
            union(c.citation_id, c.derived_from)

    groups: dict[str, str] = {}
    root_to_group: dict[str, str] = {}
    for c in citations:
        root = find(c.citation_id)
        if root not in root_to_group:
            root_to_group[root] = f"EVG-{len(root_to_group) + 1:03d}"
        groups[c.citation_id] = root_to_group[root]

    # Key 4: near-duplicate fingerprint — same normalized title, shared
    # authorship surname, but different groups. Suspects, not merges.
    suspects: list[tuple[str, str]] = []
    for i, a in enumerate(citations):
        for b in citations[i + 1:]:
            if groups[a.citation_id] == groups[b.citation_id]:
                continue
            if not a.title or _norm(a.title) != _norm(b.title):
                continue
            if {_surname(x) for x in a.authors} & {_surname(x) for x in b.authors}:
                suspects.append((a.citation_id, b.citation_id))
    return groups, suspects


# ------------------------------------------------------------------ the pipeline

def _run_stages(citation: Citation, connectors: list, checker: Any) -> CitationResult:
    item, outcome, detail = _resolve(citation, connectors)
    result = CitationResult(citation_id=citation.citation_id, claim_id=citation.claim_id,
                            resolution=outcome, detail=detail,
                            extractor=getattr(checker, "name", type(checker).__name__))
    if item is None:
        return result
    result.retrieved = item
    result.source = item.source
    result.source_id = item.source_id
    result.agreement, result.mismatches = check_agreement(citation, item)
    if not item.abstract:
        # No licence-permitted content survived the connectors' rules:
        # metadata-only — context only, no support mass (RT-5).
        result.content = METADATA_ONLY
    else:
        # Stance extraction on the retrieved content, not on memory.
        result.content = checker.check(citation.proposition, item.abstract)
    return result


@dataclass
class VerificationReport:
    results: list[CitationResult]
    origin_groups: dict[str, str]
    queue_item_ids: list[str] = field(default_factory=list)
    second_review_fraction: float = DEFAULT_SECOND_REVIEW_FRACTION

    def accounting(self) -> dict[str, str]:
        """K1 accounting: exactly one outcome per input citation."""
        return {r.citation_id: r.resolution for r in self.results}

    def outcome_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.resolution] = counts.get(r.resolution, 0) + 1
        return counts


def verify_citations(
    store: Any,
    citations: list[Citation],
    connectors: list,
    *,
    actor: str,
    content_checker: Any = None,
    second_review_fraction: float = DEFAULT_SECOND_REVIEW_FRACTION,
) -> VerificationReport:
    """Run stages 1–3 over a batch, group origins, log every outcome
    to the study ledger, and enqueue whatever needs a human: unresolved
    or disagreeing citations (quarantine) and key-4 grouping suspects."""
    checker = content_checker or KeywordStanceChecker()
    results = [_run_stages(c, connectors, checker) for c in citations]
    groups, suspects = assign_origin_groups(citations, results)
    for r in results:
        r.origin_group = groups[r.citation_id]

    queue_ids: list[str] = []
    enqueued = len([e for e in store.events() if e["type"] == "adjudication.enqueued"])

    def enqueue(kind: str, payload: dict[str, Any], reason: str) -> None:
        nonlocal enqueued
        enqueued += 1
        queue_id = f"ADQ-{enqueued:03d}"
        store.enqueue_adjudication(
            {"queue_id": queue_id, "kind": kind, "reason": reason, **payload}, actor=actor
        )
        queue_ids.append(queue_id)

    for r in results:
        store.log_citation_check(r.as_dict(), actor=actor)
        if r.quarantined:
            reason = ("resolution failed" if r.resolution != RESOLVED
                      else f"metadata disagreement: {', '.join(r.mismatches)}")
            enqueue("quarantine", {"citation_id": r.citation_id, "claim_id": r.claim_id,
                                   "result": r.as_dict()}, reason)
    for a_id, b_id in suspects:
        enqueue("grouping", {"citation_ids": [a_id, b_id]},
                "near-duplicate fingerprint (WS2 key 4): one origin or two?")

    return VerificationReport(results=results, origin_groups=groups,
                              queue_item_ids=queue_ids,
                              second_review_fraction=second_review_fraction)


def to_evidence_item(citation: Citation, result: CitationResult, *,
                     support_mass: float = 0.8,
                     contradiction_mass: float = 0.8) -> EvidenceItem:
    """Convert a checked citation into register evidence. Quarantined
    citations convert as unverified (a run containing one is INVALID
    until adjudication — WS5 §1.2); metadata-only citations convert
    as context with no mass (RT-5)."""
    base = {"item_id": citation.citation_id, "origin_group": result.origin_group,
            "hosted_ok": result.retrieved.hosted_ok if result.retrieved else True}
    if result.quarantined:
        return EvidenceItem(stance=CONTEXTUAL, verified=False, **base)
    if result.content == SUPPORTS:
        return EvidenceItem(stance=SUPPORTS, support_mass=support_mass,
                            could_falsify=True, **base)
    if result.content == CONTRADICTS:
        return EvidenceItem(stance=CONTRADICTS, contradiction_mass=contradiction_mass,
                            could_falsify=True, **base)
    if result.content == METADATA_ONLY:
        return EvidenceItem(stance=CONTEXTUAL, metadata_only=True, **base)
    return EvidenceItem(stance=CONTEXTUAL, could_falsify=True, **base)


# ------------------------------------------------------------------ adjudication queue

def queue_state(store: Any) -> dict[str, Any]:
    """Replay the ledger into queue state: pending items, decided
    items (with their decisions), and second reviews. State is a
    projection — the events are the record (DN-005)."""
    items: dict[str, dict[str, Any]] = {}
    for event in store.events():
        payload = event["payload"]
        if event["type"] == "adjudication.enqueued":
            items[payload["queue_id"]] = {**payload, "status": "pending",
                                          "decision": None, "second_reviews": []}
        elif event["type"] == "adjudication.decided" and payload["queue_id"] in items:
            item = items[payload["queue_id"]]
            item["status"] = "decided"
            item["decision"] = payload["decision"]
            item["decided_by"] = event["actor"]
            item["rationale"] = payload.get("rationale", "")
        elif event["type"] == "adjudication.second_review" and payload["queue_id"] in items:
            items[payload["queue_id"]]["second_reviews"].append(
                {"reviewer": event["actor"], "agrees": payload["agrees"]})
    pending = [i for i in items.values() if i["status"] == "pending"]
    decided = [i for i in items.values() if i["status"] == "decided"]
    return {"pending": pending, "decided": decided, "items": items}


def decide(store: Any, queue_id: str, decision: str, *, adjudicator: str,
           rationale: str = "") -> dict:
    if decision not in DECISIONS:
        raise ValueError(f"unknown adjudication decision {decision!r}; expected one of {DECISIONS}")
    state = queue_state(store)
    if queue_id not in state["items"]:
        raise ValueError(f"unknown queue item {queue_id}")
    if state["items"][queue_id]["status"] != "pending":
        raise ValueError(f"queue item {queue_id} already decided — decisions are appends; "
                         "a changed decision is a new adjudication, not an edit")
    return store.decide_adjudication(queue_id, decision,
                                     adjudicator=adjudicator, rationale=rationale)


def sample_for_second_review(decided_ids: list[str], *, fraction: float, seed: int) -> list[str]:
    """Deterministic seeded draw (RT-4): same decision set + same seed
    selects the same items, so the sample itself is auditable."""
    ids = sorted(set(decided_ids))
    if not ids or fraction <= 0:
        return []
    k = min(len(ids), max(1, math.ceil(fraction * len(ids))))
    return sorted(random.Random(seed).sample(ids, k))


def pending_second_reviews(store: Any, *, fraction: float, seed: int) -> list[str]:
    """Decided items drawn for second review that have none yet."""
    state = queue_state(store)
    decided = [i["queue_id"] for i in state["decided"]]
    reviewed = {i["queue_id"] for i in state["decided"] if i["second_reviews"]}
    return [q for q in sample_for_second_review(decided, fraction=fraction, seed=seed)
            if q not in reviewed]


def second_review_report(store: Any, *,
                         min_reviews_for_anomaly: int = DEFAULT_ANOMALY_MIN_REVIEWS) -> dict[str, Any]:
    """The RT-4 report: how many second reviews, how many disagreed,
    and the rubber-stamp anomaly — a reviewed window at or above the
    minimum sample with zero disagreements is flagged, because a
    check that never disagrees is treated like a control that never
    fails (RT-4). The bundle carries this report (Phase 5)."""
    reviews = [r for item in queue_state(store)["items"].values()
               for r in item["second_reviews"]]
    disagreements = sum(1 for r in reviews if not r["agrees"])
    anomaly = len(reviews) >= min_reviews_for_anomaly and disagreements == 0
    return {
        "second_reviews": len(reviews),
        "disagreements": disagreements,
        "disagreement_rate": (disagreements / len(reviews)) if reviews else None,
        "anomaly": anomaly,
        "anomaly_reason": (
            f"rubber-stamp anomaly: {len(reviews)} second reviews, zero disagreements (RT-4)"
            if anomaly else ""
        ),
    }
