"""Append-only POA&M register (Spec 005 §13, T553; completes the
POA&M half of CLM-005-30).

A plan of action and milestones is a *record*, and in this program
records are ledger events: items are created, milestones are added
and completed, and status changes — each as its own appended event
in the register's scope ledger (the deployment ledger carries the
platform's own register; a tenant's register lives in the tenant's
ledger). Nothing is edited in place and nothing is deleted: the
register a reader sees is a replay, and F-005-30's falsifier — *a
POA&M status change without an appended event* — is unrepresentable
in this design, because the replay is the only read path.

The register is seeded, in the deployment scope, with the item the
program's records have carried since E1: the §3.13.11 FIPS gap,
exactly as the crypto inventory and Spec 005 §13.3 record it —
including that its first milestone is an *owner decision* gated on
a named CUI/defense requirement landing, not engineering work this
phase may start.
"""

from __future__ import annotations

from typing import Any, Optional

from .ledger import (
    POAM_ITEM_CREATED,
    POAM_MILESTONE_ADDED,
    POAM_MILESTONE_COMPLETED,
    POAM_STATUS_CHANGED,
    PlatformLedger,
)

OPEN = "open"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
POAM_STATUSES = frozenset({OPEN, IN_PROGRESS, COMPLETED})

#: The seeded §3.13.11 item, verbatim in substance from the records
#: that carry it: crypto-inventory.md (all 13 rows "No"), the
#: responsibility matrix row 3.13.11 ("Supports — OPEN GAP"), and
#: Spec 005 §13.3 / plan.md (the recorded migration routes and the
#: owner-decision trigger).
FIPS_ITEM = {
    "title": "Employ FIPS-validated cryptography (§3.13.11) — no "
             "inventoried operation uses a FIPS 140-3 validated module",
    "weakness": "Every operation in the platform cryptographic "
                "inventory (crypto-inventory.md, 13 rows) reports "
                "FIPS 140-3 validated: No. Cryptography protecting "
                "CUI is therefore not FIPS-validated today; §3.13.11 "
                "stands as Supports — OPEN GAP in the responsibility "
                "matrix, and a deployment that must satisfy §3.13.11 "
                "for CUI cannot point at any inventory row.",
    "affected_requirements": ["3.13.11"],
    "source_ref": "specs/005-enterprise-platform/crypto-inventory.md",
    "milestones": [
        "Owner decision on the validated-module route, taken when a "
        "named CUI/defense requirement lands (recorded decision, "
        "Spec 005 plan.md): the migration does not start before "
        "that trigger.",
        "Tekmerion service-layer substitution (crypto inventory "
        "rows 4–9): adopt a validated module (e.g. an OpenSSL FIPS "
        "provider route) without touching the record layer — the "
        "first FIPS work item when the CMMC track is scheduled.",
        "Axiomere record layer (crypto inventory rows 1–3): "
        "validated Rust crypto or a boundary redesign placing a "
        "validated module around the record layer — a cross-repo "
        "decision (DN-011), not Tekmerion's unilateral roadmap.",
    ],
}


class PoamRegister:
    """One scope's POA&M register over its platform ledger."""

    def __init__(self, ledger: PlatformLedger) -> None:
        self.ledger = ledger

    # -- writes (events only) ------------------------------------------------

    def _next_item_number(self) -> int:
        return sum(1 for e in self.ledger.events()
                   if e["type"] == POAM_ITEM_CREATED) + 1

    def create_item(self, *, actor_id: str, title: str, weakness: str,
                    affected_requirements: list[str], source_ref: str,
                    owner: str = "") -> str:
        if not affected_requirements:
            raise ValueError("a POA&M item names at least one affected requirement")
        item_id = f"POAM-{self._next_item_number():04d}"
        self.ledger.record(
            POAM_ITEM_CREATED, actor_id=actor_id, target=f"poam:{item_id}",
            item_id=item_id, title=title, weakness=weakness,
            affected_requirements=list(affected_requirements),
            source_ref=source_ref, owner=owner, status=OPEN)
        return item_id

    def _require_item(self, item_id: str) -> dict:
        items = self.items()
        if item_id not in items:
            raise ValueError(f"unknown POA&M item {item_id!r}")
        return items[item_id]

    def add_milestone(self, *, actor_id: str, item_id: str, text: str,
                      due: str = "") -> str:
        item = self._require_item(item_id)
        milestone_id = f"{item_id}-M{len(item['milestones']) + 1}"
        self.ledger.record(
            POAM_MILESTONE_ADDED, actor_id=actor_id, target=f"poam:{item_id}",
            item_id=item_id, milestone_id=milestone_id, text=text, due=due)
        return milestone_id

    def complete_milestone(self, *, actor_id: str, item_id: str,
                           milestone_id: str, note: str = "") -> dict:
        item = self._require_item(item_id)
        known = {m["milestone_id"] for m in item["milestones"]}
        if milestone_id not in known:
            raise ValueError(f"unknown milestone {milestone_id!r} on {item_id}")
        return self.ledger.record(
            POAM_MILESTONE_COMPLETED, actor_id=actor_id, target=f"poam:{item_id}",
            item_id=item_id, milestone_id=milestone_id, note=note)

    def set_status(self, *, actor_id: str, item_id: str, status: str,
                   note: str = "") -> dict:
        """A status change is an appended event — the register's
        current status is whatever the latest event says, and the
        full sequence stays readable in the replay (F-005-30)."""
        self._require_item(item_id)
        if status not in POAM_STATUSES:
            raise ValueError(f"unknown POA&M status {status!r}")
        return self.ledger.record(
            POAM_STATUS_CHANGED, actor_id=actor_id, target=f"poam:{item_id}",
            item_id=item_id, status=status, note=note)

    def seed_fips_item(self, *, actor_id: str) -> Optional[str]:
        """Seed the §3.13.11 item exactly as the records carry it.
        Idempotent: a register already carrying an item sourced
        from the crypto inventory is not seeded twice."""
        for item in self.items().values():
            if item["source_ref"] == FIPS_ITEM["source_ref"] \
                    and "3.13.11" in item["affected_requirements"]:
                return None
        item_id = self.create_item(
            actor_id=actor_id, title=FIPS_ITEM["title"],
            weakness=FIPS_ITEM["weakness"],
            affected_requirements=list(FIPS_ITEM["affected_requirements"]),
            source_ref=FIPS_ITEM["source_ref"], owner="platform")
        for text in FIPS_ITEM["milestones"]:
            self.add_milestone(actor_id=actor_id, item_id=item_id, text=text)
        return item_id

    # -- reads (replay) --------------------------------------------------------

    def items(self) -> dict[str, dict[str, Any]]:
        """The register as a replay of its events, in creation
        order. Status history is part of the item: every change,
        with its sequence number — the audit trail F-005-30 asks
        for is the item itself."""
        items: dict[str, dict[str, Any]] = {}
        for event in self.ledger.events():
            payload = event["payload"]
            kind = event["type"]
            if kind == POAM_ITEM_CREATED:
                items[payload["item_id"]] = {
                    "item_id": payload["item_id"],
                    "title": payload["title"],
                    "weakness": payload["weakness"],
                    "affected_requirements": list(payload["affected_requirements"]),
                    "source_ref": payload["source_ref"],
                    "owner": payload.get("owner", ""),
                    "status": payload.get("status", OPEN),
                    "milestones": [],
                    "status_history": [{
                        "status": payload.get("status", OPEN),
                        "seq": event["seq"], "actor_id": payload.get("actor_id"),
                        "note": "item created",
                    }],
                    "created_seq": event["seq"],
                }
            elif kind == POAM_MILESTONE_ADDED and payload["item_id"] in items:
                items[payload["item_id"]]["milestones"].append({
                    "milestone_id": payload["milestone_id"],
                    "text": payload["text"],
                    "due": payload.get("due", ""),
                    "status": OPEN,
                    "added_seq": event["seq"],
                })
            elif kind == POAM_MILESTONE_COMPLETED and payload["item_id"] in items:
                for milestone in items[payload["item_id"]]["milestones"]:
                    if milestone["milestone_id"] == payload["milestone_id"]:
                        milestone["status"] = COMPLETED
                        milestone["completed_seq"] = event["seq"]
                        milestone["note"] = payload.get("note", "")
            elif kind == POAM_STATUS_CHANGED and payload["item_id"] in items:
                item = items[payload["item_id"]]
                item["status"] = payload["status"]
                item["status_history"].append({
                    "status": payload["status"], "seq": event["seq"],
                    "actor_id": payload.get("actor_id"),
                    "note": payload.get("note", ""),
                })
        return items

    def register_document(self) -> dict[str, Any]:
        """The register in export form (rides the T542 audit export):
        every item with its milestones and full status history."""
        return {"items": list(self.items().values())}
