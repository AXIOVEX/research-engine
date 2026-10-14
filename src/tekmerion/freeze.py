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
from typing import Any, Optional

from .claims import ClaimRegister
from .verdicts import Control, fixture_identity

#: The freeze event and its only lawful successor (Spec 013
#: CLM-013-07): a study carries ONE `study.frozen` event; any later
#: change to the frozen design is a labeled amendment act, appended
#: as `study.frozen.amended`, never a second silent freeze.
FREEZE_EVENT = "study.frozen"
AMENDMENT_EVENT = "study.frozen.amended"

#: The freeze modes (Spec 013 CLM-013-08): validated here, at the
#: freeze layer, so every surface — UI actions, MCP tools, direct
#: calls — inherits the refusal of any other value.
FREEZE_MODES = ("confirmation", "exploratory")


class FreezeError(RuntimeError):
    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("freeze check failed: " + "; ".join(failures))


def control_fixture_commitments(controls: list[Control]) -> list[dict[str, Any]]:
    """Each control's fixture commitment: the fixture's identity
    (production `fixture_identity` construction) or None when the
    control carries no executable fixture (the swap control; an
    incomplete fixture). Carried in the registration document and in
    the freeze/amendment event payloads, so the fixtures a run may
    execute are committed at freeze time (Spec 013 CLM-013-09,
    answering RTA-04: the freeze sidecar stops being an uncommitted
    input)."""
    return [
        {"kind": c.kind, "failure_mode": c.failure_mode,
         "fixture": fixture_identity(c)}
        for c in controls
    ]


def registration_document(register: ClaimRegister, controls: list[Control], mode: str,
                          linked_exploratory: list[str], *,
                          predictions: Optional[dict[str, Any]] = None,
                          amendment: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "mode": mode,
        "claims": [c.as_dict() for c in register.claims.values()],
        "controls": [
            {"failure_mode": c.failure_mode, "kind": c.kind, "expected": c.expected,
             "representative_rationale": c.representative_rationale,
             "fixture": fixture_identity(c)}
            for c in controls
        ],
        "linked_exploratory": list(linked_exploratory),  # RT-3 disclosure duty
    }
    if predictions is not None:
        # Evaluation predictions enter the commitment (Spec 013
        # CLM-013-04, answering RTA-10(i)): "recorded before the
        # freeze" is a hash fact inside the sealed record, not a
        # companion-file claim.
        doc["predictions"] = predictions
        doc["predictions_hash"] = predictions_hash(predictions)
    if amendment is not None:
        # The amendment labeling is part of the committed document:
        # the new registration states, inside its own hash, which
        # registration it amends and why (CLM-013-07).
        doc["amendment"] = dict(amendment)
    return doc


def registration_hash(doc: dict[str, Any]) -> str:
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def predictions_hash(predictions: dict[str, Any]) -> str:
    canonical = json.dumps(predictions, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_predictions(store: Any, predictions: dict[str, Any], *,
                       actor: str) -> dict[str, Any]:
    """Append an evaluation's predictions to the study ledger as an
    `evaluation.predictions` event. Called before the freeze, the
    event precedes the `study.frozen` event in the sealed record
    (CLM-013-04's second commitment form)."""
    return store.db.append(
        "evaluation.predictions",
        {"predictions": predictions,
         "predictions_hash": predictions_hash(predictions)},
        actor=actor,
    )


def binding_frozen_event(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """The freeze consumers bind to (Spec 013 CLM-013-07): when the
    record carries labeled amendment events, the latest amendment
    binds — it amends the freeze in the open, with a stated reason.
    Otherwise the binding freeze is the LAST `study.frozen` event.

    On any ledger the remediated code can produce, first and last
    coincide: `freeze` refuses a second freeze outright (the RTA-03
    laundering path is closed at the append, which is where the
    demonstrated attack entered), and a regime change is possible
    only as a labeled amendment. The last-freeze fallback exists for
    pre-remediation ledgers only: the deposited Spec 003 math-study
    ledger carries two unlabeled `study.frozen` events (seq 62 and
    seq 87, from the run-2 re-freeze) with its registration and
    verdicts issued under the second, so binding to the first would
    fail verification of a frozen, deposited artifact — falsifying
    CLM-013-46. The stricter bind-to-first reading of CLM-013-07 is
    therefore NOT shipped for multi-freeze legacy ledgers; the
    conflict is recorded in the lane report for spec resolution."""
    frozen = [e for e in events if e["type"] == FREEZE_EVENT]
    if not frozen:
        return None
    amendments = [e for e in events if e["type"] == AMENDMENT_EVENT]
    if amendments:
        return amendments[-1]
    return frozen[-1]


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
        if ctl.kind in ("positive", "negative") and ctl.claim is not None:
            # No vacuous FIXTURE controls (Spec 013 CLM-013-10,
            # answering RTA-05): a control carrying an evaluation
            # fixture whose expectation is not decisive, or whose
            # evidence groups are empty, cannot fail — it would
            # "pass" a run having evaluated nothing. That is the
            # Phase 5 no-op defect in the fixture family, and a
            # fixture control that cannot fail is a freeze failure
            # (Article VI). The scope is fixture controls exactly as
            # the claim states: a fixture-less control declaration
            # (the console's registered controls) never executes —
            # run_controls_for runs only fixture-carrying controls
            # plus the swap control — so it can never be reported
            # executed-and-passed, and stays outside this claim.
            if ctl.expected not in ("supported", "contradicted"):
                failures.append(
                    f"{ctl.kind} control ({ctl.failure_mode}): expected verdict "
                    f"{ctl.expected!r} is not decisive — a fixture control must "
                    "expect supported or contradicted (Article VI)")
            if not ctl.groups:
                failures.append(
                    f"{ctl.kind} control ({ctl.failure_mode}): fixture has no "
                    "evidence groups — a control that evaluates nothing "
                    "cannot fail (Article VI)")
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


def _validate_mode(mode: str) -> None:
    if mode not in FREEZE_MODES:
        raise FreezeError([
            f"unknown freeze mode {mode!r}: mode must be one of "
            f"{list(FREEZE_MODES)} (Spec 013 CLM-013-08)"])


def _commit(store: Any, register: ClaimRegister, doc: dict[str, Any], *,
            actor: str, event_type: str,
            extra_payload: dict[str, Any]) -> dict[str, Any]:
    """Append the freeze/amendment event + checkpoint for an already
    checked registration document, and move the register's lifecycle
    to match. Shared by freeze() and amend_freeze() so the two acts
    differ only in their event type and labels — never in rigor."""
    reg_hash = registration_hash(doc)
    # Capture the frozen document on the register before statuses
    # move: exports (Phase 5) bind to exactly this document, and its
    # hash — checked against the ledger commitment — is the proof.
    register.frozen_document = json.loads(json.dumps(doc))
    event = store.db.append(
        event_type,
        {"registration_hash": reg_hash, "mode": doc["mode"],
         "claims": sorted(register.claims),
         "linked_exploratory": list(doc["linked_exploratory"]),
         "control_fixtures": control_fixture_commitments_from_doc(doc),
         **extra_payload},
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
        "frozen_event_seq": event["seq"],
        "checkpoint_root": checkpoint["payload"]["merkle_root"],
        "checkpoint_seq": checkpoint["seq"],
    }


def control_fixture_commitments_from_doc(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """The fixture commitments as the registration document states
    them (the event payload mirrors the document, so a ledger-only
    consumer holds the same commitment the hash seals)."""
    return [
        {"kind": c.get("kind"), "failure_mode": c.get("failure_mode"),
         "fixture": c.get("fixture")}
        for c in doc.get("controls", [])
    ]


def freeze(store: Any, register: ClaimRegister, controls: list[Control], *,
           actor: str, mode: str = "confirmation",
           linked_exploratory: list[str] | None = None,
           deployment_shape: str = "hosted",
           predictions: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Run the freeze check and, if clean, commit the freeze into the
    study ledger: a `study.frozen` event carrying the registration
    hash, followed by the Merkle checkpoint that seals the range.

    A study freezes ONCE (Spec 013 CLM-013-07): if the ledger already
    carries a freeze, or the register is already frozen, this refuses
    — a changed design is an amendment act (`amend_freeze`), appended
    labeled as such, never a second silent freeze."""
    _validate_mode(mode)
    existing = [e for e in store.events() if e["type"] == FREEZE_EVENT]
    if existing or register.frozen:
        bound = binding_frozen_event(store.events())
        bound_hash = bound["payload"].get("registration_hash") if bound else None
        raise FreezeError([
            "study is already frozen"
            + (f" (registration {bound_hash})" if bound_hash else "")
            + "; a changed design requires an amendment act "
              "(tekmerion.freeze.amend_freeze), never a second freeze"])
    failures = freeze_check(register, controls, mode=mode,
                            linked_exploratory=linked_exploratory,
                            deployment_shape=deployment_shape)
    if failures:
        raise FreezeError(failures)
    linked = list(linked_exploratory or [])
    doc = registration_document(register, controls, mode, linked,
                                predictions=predictions)
    return _commit(store, register, doc, actor=actor,
                   event_type=FREEZE_EVENT, extra_payload={})


def amend_freeze(store: Any, register: ClaimRegister, controls: list[Control], *,
                 actor: str, reason: str, mode: str | None = None,
                 linked_exploratory: list[str] | None = None,
                 deployment_shape: str = "hosted",
                 predictions: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """The amendment act (Spec 013 CLM-013-07): the ONLY way to change
    a frozen study's design. Appends a labeled `study.frozen.amended`
    event whose payload — and whose registration document, inside its
    own hash — names the registration it amends and the reason.
    Consumers bind to the amendment openly (see
    `binding_frozen_event`); nothing about the original freeze is
    rewritten or hidden."""
    events = store.events()
    bound = binding_frozen_event(events)
    if bound is None:
        raise FreezeError([
            "no freeze to amend: the study is not frozen — use freeze()"])
    if not reason or not reason.strip():
        raise FreezeError([
            "an amendment act must state its reason (CLM-013-07): the "
            "label is what distinguishes an amendment from a laundering"])
    if mode is None:
        mode = bound["payload"].get("mode", "confirmation")
    _validate_mode(mode)
    if linked_exploratory is None:
        linked_exploratory = list(bound["payload"].get("linked_exploratory") or [])
    failures = freeze_check(register, controls, mode=mode,
                            linked_exploratory=linked_exploratory,
                            deployment_shape=deployment_shape)
    if failures:
        raise FreezeError(failures)
    linked = list(linked_exploratory or [])
    amends_hash = bound["payload"].get("registration_hash")
    doc = registration_document(
        register, controls, mode, linked, predictions=predictions,
        amendment={"reason": reason, "amends_registration_hash": amends_hash,
                   "amends_event_seq": bound["seq"],
                   "amends_event_type": bound["type"]})
    result = _commit(
        store, register, doc, actor=actor, event_type=AMENDMENT_EVENT,
        extra_payload={"label": "amendment", "reason": reason,
                       "amends_registration_hash": amends_hash,
                       "amends_event_seq": bound["seq"]})
    return {**result, "amended": True, "amends_registration_hash": amends_hash}
