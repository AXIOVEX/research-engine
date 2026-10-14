"""Claim register (Spec 002 Phase 3; WS2).

A claim carries a mandatory falsifier (Article II — no falsifier, no
registration), a dependency list forming a DAG (a cycle is circular
support and the freeze check rejects it), and a lifecycle that moves
by appends, never edits. Statements are immutable once registered:
a changed statement is a *new* claim that supersedes the old one,
with the link recorded both ways (WS2 §1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class RegistrationError(ValueError):
    pass


@dataclass
class Claim:
    claim_id: str
    statement: str
    falsifier: str
    kind: str = "data"                    # "data" | "interpretation" (decides origin grouping, WS2 §2)
    dependencies: list[str] = field(default_factory=list)   # claim ids and/or EVG- group ids
    margin: Optional[float] = None        # registered margin for the verdict test (WS3)
    sufficiency_floor: Optional[int] = None  # minimum independent origin groups (WS3)
    supersedes: Optional[str] = None
    status: str = "proposed"              # proposed -> registered -> under-review -> verdicted -> superseded|revisited|dead

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id, "statement": self.statement,
            "falsifier": self.falsifier, "kind": self.kind,
            "dependencies": list(self.dependencies), "margin": self.margin,
            "sufficiency_floor": self.sufficiency_floor,
            "supersedes": self.supersedes, "status": self.status,
        }


@dataclass
class EvidenceItem:
    item_id: str
    origin_group: str          # weights accrue to groups, never items (Article V)
    stance: str                 # "supports" | "contradicts" | "contextual"
    support_mass: float = 0.0   # per-group interval masses (WS3 §6)
    contradiction_mass: float = 0.0
    could_falsify: bool = False  # could this item's test have contradicted the claim?
    falsifier_observation: bool = False  # the registered falsifying observation itself
    verified: bool = True       # citation passed verification (WS5); unverified -> run INVALID
    hosted_ok: bool = True      # licence permits the hosted shape (WS1)
    metadata_only: bool = False  # no content check was possible (WS5 §1.3): context only, no mass (RT-5)

    def as_dict(self) -> dict[str, Any]:
        return vars(self).copy()


class ClaimRegister:
    """The study's claims + evidence, with the graph kept honest."""

    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}
        self.evidence: dict[str, list[EvidenceItem]] = {}
        self.frozen = False
        self.registration_hash: Optional[str] = None
        # The exact document whose hash freeze committed (set by
        # tekmerion.freeze.freeze). Lifecycle statuses move after
        # freezing; this capture is what exports bind to (Phase 5).
        self.frozen_document: Optional[dict[str, Any]] = None

    # -- registration -------------------------------------------------------

    def register(self, claim: Claim) -> Claim:
        if not claim.falsifier or not claim.falsifier.strip():
            raise RegistrationError(
                f"{claim.claim_id}: no falsifier — not registered (Article II)"
            )
        if not claim.claim_id.startswith("CLM-"):
            raise RegistrationError(f"{claim.claim_id}: claim ids are CLM-<study>-<nnn>")
        if self.frozen:
            # The wall is unconditional (Spec 013 CLM-013-06, answering
            # RTA-03 / RTD-01): while frozen, NO registration is
            # accepted — not for an existing id, and not for a brand-new
            # id the freeze never saw. A changed design moves by a
            # labeled freeze amendment (CLM-013-07), never by a
            # registration slipping past the wall.
            raise RegistrationError(
                f"{claim.claim_id}: registration is frozen; no claim may be "
                "registered against a frozen study (WS3 §4 wall)"
            )
        existing = self.claims.get(claim.claim_id)
        if existing is not None:
            if (existing.statement != claim.statement
                    or existing.falsifier != claim.falsifier):
                # Statements and falsifiers are immutable by
                # re-registration at EVERY status, including proposed
                # (Spec 013 CLM-013-11, answering RTD-02): evidence
                # gathered under one statement must never silently back
                # another. A byte-identical re-registration is an
                # idempotent retry, not a change, and is not refused;
                # a real change is a new claim that supersedes.
                raise RegistrationError(
                    f"{claim.claim_id}: statement is immutable after registration; "
                    "create a superseding claim"
                )
        for dep in claim.dependencies:
            if dep.startswith("CLM-") and dep not in self.claims and dep != claim.claim_id:
                raise RegistrationError(f"{claim.claim_id}: unknown claim dependency {dep}")
        self.claims[claim.claim_id] = claim
        if claim.supersedes and claim.supersedes in self.claims:
            self.claims[claim.supersedes].status = "superseded"
        return claim

    def add_evidence(self, claim_id: str, item: EvidenceItem) -> None:
        if claim_id not in self.claims:
            raise RegistrationError(f"evidence for unknown claim {claim_id}")
        self.evidence.setdefault(claim_id, []).append(item)

    # -- graph ----------------------------------------------------------------

    def claim_graph(self) -> dict[str, list[str]]:
        return {
            cid: [d for d in c.dependencies if d.startswith("CLM-")]
            for cid, c in self.claims.items()
        }

    def find_cycle(self) -> Optional[list[str]]:
        """Return one cycle as a path, or None. A cycle means two claims
        are each other's justification — circular support (WS2 §3)."""
        graph = self.claim_graph()
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}
        stack: list[str] = []

        def visit(node: str) -> Optional[list[str]]:
            color[node] = GRAY
            stack.append(node)
            for nxt in graph.get(node, []):
                if nxt not in color:
                    continue
                if color[nxt] == GRAY:
                    return stack[stack.index(nxt):] + [nxt]
                if color[nxt] == WHITE:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            color[node] = BLACK
            return None

        for node in graph:
            if color[node] == WHITE:
                found = visit(node)
                if found:
                    return found
        return None

    def group_masses(self, claim_id: str) -> list[dict[str, Any]]:
        """Evidence folded to origin groups: several items in one group
        count once, at the group's strongest masses (Article V)."""
        groups: dict[str, dict[str, Any]] = {}
        for item in self.evidence.get(claim_id, []):
            g = groups.setdefault(item.origin_group, {
                "origin_group": item.origin_group, "support_mass": 0.0,
                "contradiction_mass": 0.0, "could_falsify": False,
                "falsifier_observation": False, "verified": True, "items": 0,
                "metadata_only": True,
            })
            if item.metadata_only:
                # RT-5, mechanized at the fold: a metadata-only item is
                # context only. Whatever masses were registered for it,
                # it contributes no support, no contradiction, and no
                # falsifier exposure — nobody checked its content.
                g["verified"] = g["verified"] and item.verified
                g["items"] += 1
                continue
            g["metadata_only"] = False
            g["support_mass"] = max(g["support_mass"], item.support_mass)
            g["contradiction_mass"] = max(g["contradiction_mass"], item.contradiction_mass)
            g["could_falsify"] = g["could_falsify"] or item.could_falsify
            g["falsifier_observation"] = g["falsifier_observation"] or item.falsifier_observation
            g["verified"] = g["verified"] and item.verified
            g["items"] += 1
        return list(groups.values())
