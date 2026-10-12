"""Freeze workflow (Spec 002 Phase 3; WS3 §3).

Draft -> freeze check -> freeze. The freeze check is automated and
fails closed: every claim has a falsifier; the graph is acyclic;
controls have named failure modes and representative rationales;
margins and sufficiency floors are set; source rights permit the
planned storage shape. At freeze, the registration is hashed and the
hash is committed into the study's Axiomere ledger as a Merkle
checkpoint — from that moment the design is immutable, and any later
change is an amendment producing a new registration version, never a
rewrite (WS3 §3 step 5).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .claims import ClaimRegister
from .verdicts import Control


class FreezeError(RuntimeError):
    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("freeze check failed: " + "; ".join(failures))


def registration_document(register: ClaimRegister, controls: list[Control], mode: str,
                          linked_exploratory: list[str]) -> dict[str, Any]:
    return {
        "mode": mode,
        "claims": [c.as_dict() for c in register.claims.values()],
        "controls": [
            {"failure_mode": c.failure_mode, "kind": c.kind, "expected": c.expected,
             "representative_rationale": c.representative_rationale}
            for c in controls
        ],
        "linked_exploratory": list(linked_exploratory),  # RT-3 disclosure duty
    }


def registration_hash(doc: dict[str, Any]) -> str:
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def freeze_check(register: ClaimRegister, controls: list[Control], *,
                 mode: str = "confirmation",
                 linked_exploratory: list[str] | None = None,
                 deployment_shape: str = "hosted") -> list[str]:
    """Return the list of blocking failures (empty = freezable)."""
    failures: list[str] = []

    if not register.claims:
        failures.append("no claims registered")
    for claim in register.claims.values():
        if not claim.falsifier or not claim.falsifier.strip():
            failures.append(f"{claim.claim_id}: missing falsifier")
        if claim.margin is None:
            failures.append(f"{claim.claim_id}: margin not set")
        if claim.sufficiency_floor is None:
            failures.append(f"{claim.claim_id}: sufficiency floor not set")

    cycle = register.find_cycle()
    if cycle:
        failures.append(f"dependency cycle (circular support): {' -> '.join(cycle)}")

    if not controls:
        failures.append("no controls registered")
    for ctl in controls:
        if not ctl.failure_mode or not ctl.failure_mode.strip():
            failures.append("a control has no named failure mode (WS3 §2: failure mode first)")
        if ctl.kind == "positive" and not ctl.representative_rationale:
            failures.append("positive control lacks a representative rationale (RT-6)")
    kinds = {c.kind for c in controls}
    for required in ("positive", "negative", "swap"):
        if required not in kinds:
            failures.append(f"missing {required} control")

    if deployment_shape == "hosted":
        for cid, items in register.evidence.items():
            for item in items:
                if not item.hosted_ok:
                    failures.append(
                        f"{cid}: evidence {item.item_id} licence does not permit the hosted shape (WS1)"
                    )

    if mode == "confirmation" and linked_exploratory is None:
        failures.append(
            "confirmation registration must disclose linked exploratory studies (RT-3) — "
            "pass an empty list if there are none"
        )
    return failures


def freeze(store: Any, register: ClaimRegister, controls: list[Control], *,
           actor: str, mode: str = "confirmation",
           linked_exploratory: list[str] | None = None,
           deployment_shape: str = "hosted") -> dict[str, Any]:
    """Run the freeze check and, if clean, commit the freeze into the
    study ledger: a `study.frozen` event carrying the registration
    hash, followed by the Merkle checkpoint that seals the range."""
    failures = freeze_check(register, controls, mode=mode,
                            linked_exploratory=linked_exploratory,
                            deployment_shape=deployment_shape)
    if failures:
        raise FreezeError(failures)
    linked = list(linked_exploratory or [])
    doc = registration_document(register, controls, mode, linked)
    reg_hash = registration_hash(doc)
    frozen_event = store.db.append(
        "study.frozen",
        {"registration_hash": reg_hash, "mode": mode, "claims": sorted(register.claims),
         "linked_exploratory": linked},
        actor=actor,
    )
    checkpoint = store.freeze(actor=actor)
    for claim in register.claims.values():
        if claim.status == "proposed":
            claim.status = "registered"
    register.frozen = True
    register.registration_hash = reg_hash
    return {
        "registration_hash": reg_hash,
        "frozen_event_seq": frozen_event["seq"],
        "checkpoint_root": checkpoint["payload"]["merkle_root"],
        "checkpoint_seq": checkpoint["seq"],
    }
