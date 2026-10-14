"""Tekmerion study store — the framework's record layer is Axiomere (DN-007).

One study = one `.axmr` ledger (AXIOVEX/axiomere, via the `axiomere`
Python package). Claims are snapshots, verdicts are typed appends,
withdrawal is a dead snapshot, and a freeze is a Merkle checkpoint.
There is no delete here because there is no delete beneath here.

The Phase 1 prototype (`tekmerion.record`) remains for reference; new
Spec 002 work writes through this module.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    import axiomere
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tekmerion.store requires the axiomere package: "
        "https://github.com/AXIOVEX/axiomere-python (native extension "
        "built from https://github.com/AXIOVEX/axiomere)"
    ) from exc


class StudyStore:
    """A study's Axiomere ledger, with Tekmerion's event vocabulary."""

    def __init__(self, db: "axiomere.Database") -> None:
        self.db = db

    @classmethod
    def create(cls, path: str, *, seed_hex: Optional[str] = None) -> "StudyStore":
        return cls(axiomere.Database.create(path, seed_hex=seed_hex))

    @classmethod
    def open(cls, path: str, *, seed_hex: Optional[str] = None) -> "StudyStore":
        return cls(axiomere.Database.open(path, seed_hex=seed_hex))

    # -- the Tekmerion vocabulary, expressed as Axiomere appends ---------

    def register_claim(self, claim_id: str, content: dict[str, Any], *, actor: str,
                       score: Optional[float] = None) -> dict:
        """Register (or revise) a claim: a new snapshot in its lineage."""
        return self.db.snapshot(claim_id, content, actor=actor, score=score)

    def issue_verdict(self, claim_id: str, verdict: dict[str, Any], *, actor: str) -> dict:
        """Issue a verdict. Verdicts are appends, never edits; a changed
        verdict is a new verdict event superseding by order, with the old
        one still on the record."""
        return self.db.append("verdict.issued", {"claim_id": claim_id, **verdict}, actor=actor)

    def log_query(self, connector: str, query: dict[str, Any], *, actor: str) -> dict:
        """Record a connector query in the study ledger itself, so the
        provenance of everything retrieved is chained and signed."""
        return self.db.append("connector.query", {"connector": connector, **query}, actor=actor)

    def log_citation_check(self, result: dict[str, Any], *, actor: str) -> dict:
        """Record one citation's pipeline outcome (Phase 4): every
        citation gets exactly one of these — that is the K1 accounting."""
        return self.db.append("citation.checked", result, actor=actor)

    def enqueue_adjudication(self, item: dict[str, Any], *, actor: str) -> dict:
        """Place an item in the adjudication queue (WS5 §3). Queue state
        is a projection of these events; there is no queue elsewhere."""
        return self.db.append("adjudication.enqueued", item, actor=actor)

    def decide_adjudication(self, queue_id: str, decision: str, *, adjudicator: str,
                            rationale: str = "") -> dict:
        """Record an adjudicator's decision — named, appended, never an
        edit to the enqueue event (Article IX)."""
        return self.db.append(
            "adjudication.decided",
            {"queue_id": queue_id, "decision": decision, "rationale": rationale},
            actor=adjudicator,
        )

    def log_second_review(self, queue_id: str, *, reviewer: str, agrees: bool) -> dict:
        """Record an independent second review of an adjudication
        decision (RT-4 sampling)."""
        return self.db.append(
            "adjudication.second_review",
            {"queue_id": queue_id, "agrees": agrees},
            actor=reviewer,
        )

    def log_anchor(self, receipt: dict[str, Any], *, actor: str) -> dict:
        """Record an external anchor receipt (AR-1): the checkpoint
        root now also lives where the operator does not control it,
        and the receipt naming it is part of this record (DN-005
        layer 5; Article XIII)."""
        return self.db.append("anchor.recorded", receipt, actor=actor)

    def events(self) -> list:
        return self.db.events()

    def withdraw(self, record_id: str, *, reason: str, actor: str) -> dict:
        """The only removal that exists: dead snapshot, reason recorded,
        score 0.0 — history intact (DN-005)."""
        return self.db.dead(record_id, reason=reason, actor=actor)

    def freeze(self, *, actor: str) -> dict:
        """Freeze = Merkle checkpoint. The root in the returned event is
        the freeze commitment Phase 5 anchors externally (AR-1)."""
        return self.db.checkpoint(actor=actor)

    # -- reads --------------------------------------------------------------

    def current_claims(self, *, include_dead: bool = False) -> dict:
        return self.db.current(include_dead=include_dead)

    def verify(self, *, trusted: Optional[dict] = None,
               expected_head: Optional[dict] = None) -> "axiomere.Verification":
        """Verify this study's ledger (Axiomere Spec 003 policy).

        Bare mode (the default, `trusted=None`) is self-consistency:
        the chain, the checkpoint roots — recomputed from the events,
        never read from the checkpoint payloads — and any signatures
        present are checked, and an honestly unsigned ledger verifies
        with every unsigned event named in the result's
        `unsigned_events` (a visible state, never a silent pass).

        A study whose appends are signed under enrolled keys — a
        store created/opened with `seed_hex` — is verified at the
        study boundary in **trusted mode**: pass
        `trusted={actor: public_key_hex}` and every event must carry
        a signature by its actor's enrolled key; an unsigned append
        or a signature by any other key fails, and the actor is named
        in `untrusted_actors`. `expected_head` pins the recomputed
        head (`head_hash`, `min_events`, `checkpoint_root`) for
        callers comparing against an anchored value."""
        return self.db.verify(trusted=trusted, expected_head=expected_head)
